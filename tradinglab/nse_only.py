"""Official NSE bhavcopy inputs for the separate, paper-only ETF trial."""

import csv
import hashlib
import io
import json
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

from .research import Bar, IST, ROOT

SYMBOLS = ("NIFTYBEES", "JUNIORBEES")
ARCHIVES = ROOT / "state/nse-only/archives"
# NSE equity-market holidays in the collected history. Confirmed against the
# official 2025 cash-market circular and NSE's 2026 equity holiday table.
# Extend only from a documented exchange notice; unexpected gaps block signals.
KNOWN_HOLIDAYS = frozenset(date.fromisoformat(value) for value in (
    "2025-08-15", "2025-08-27", "2025-10-02", "2025-10-22",
    "2025-11-05", "2025-12-25", "2026-01-15", "2026-01-26",
    "2026-03-03", "2026-03-26", "2026-03-31", "2026-04-03",
    "2026-04-14", "2026-05-01", "2026-05-28", "2026-06-26",
    "2026-09-14", "2026-10-02"))
SPECIAL_SESSIONS = frozenset((date(2026, 2, 1),))  # Union Budget Sunday session.


def archive_url(day):
    return f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv.zip"


def fetch_archive(day, folder=ARCHIVES):
    """Keep the first official archive bytes; a 404 is recorded by the caller."""
    path = folder / f"{day}.zip"
    if path.exists():
        return path
    request = urllib.request.Request(archive_url(day), headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        if len([n for n in archive.namelist() if n.endswith(".csv")]) != 1:
            raise ValueError(f"Unexpected NSE archive for {day}")
    folder.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(payload)
    return path


def load_archive(path, day):
    payload = path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [n for n in archive.namelist() if n.endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"Unexpected NSE archive for {day}")
        rows = list(csv.DictReader(io.StringIO(archive.read(names[0]).decode("utf-8-sig"))))
    selected = [r for r in rows if r.get("TckrSymb") in SYMBOLS and r.get("SctySrs") == "EQ"]
    if len(selected) != len(SYMBOLS) or {r["TckrSymb"] for r in selected} != set(SYMBOLS):
        raise ValueError(f"Missing or duplicate ETF row on {day}")
    bars = {}
    for row in selected:
        if row["TradDt"] != str(day):
            raise ValueError(f"Mismatched archive date on {day}")
        values = [Decimal(row[k]) for k in ("OpnPric", "HghPric", "LwPric", "ClsPric")]
        opening, high, low, close = values
        if any(not v.is_finite() or v <= 0 for v in values) or low > min(opening, close) or high < max(opening, close):
            raise ValueError(f"Invalid ETF OHLC on {day}")
        volume = int(row["TtlTradgVol"])
        if volume < 0:
            raise ValueError(f"Invalid ETF volume on {day}")
        bars[row["TckrSymb"] + ".NS"] = Bar(day, opening, high, low, close, volume)
    return bars, {"date": str(day), "url": archive_url(day), "sha256": hashlib.sha256(payload).hexdigest()}


def load_series(folder, asof, minimum=200):
    series = {symbol + ".NS": [] for symbol in SYMBOLS}
    provenance = []
    for path in sorted(folder.glob("*.zip")):
        day = date.fromisoformat(path.stem)
        if day > asof:
            continue
        bars, source = load_archive(path, day)
        for symbol, bar in bars.items():
            previous = series[symbol]
            if previous and (day <= previous[-1].day or abs(bar.close / previous[-1].close - 1) > Decimal("0.20")):
                raise ValueError(f"Unordered data or possible corporate action in {symbol} on {day}")
            previous.append(bar)
        provenance.append(source)
    if len(provenance) < minimum or provenance[-1]["date"] != str(asof):
        raise ValueError(f"Need {minimum} official shared sessions through {asof}; found {len(provenance)}")
    observed = {date.fromisoformat(source["date"]) for source in provenance}
    day = min(observed)
    while day <= asof:
        expected = (day.weekday() < 5 and day not in KNOWN_HOLIDAYS) or day in SPECIAL_SESSIONS
        if expected and day not in observed:
            raise ValueError(f"Missing NSE archive for expected trading day {day}")
        day += timedelta(days=1)
    return series, provenance


def completed_today(asof):
    now = datetime.now(IST)
    if asof != now.date() or now.time() < time(16, 0):
        raise ValueError("Prospective NSE decision requires today's completed session after 16:00 IST")
    return now
