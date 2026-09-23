"""Download public research inputs, preserving date-stamped raw responses.

No credentials, paid endpoints, order APIs or brokerage account access.
"""
import argparse
import csv
import io
import json
import sys
import urllib.request
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent


def get(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2)+"\n")
    temporary.replace(path)


def nse(day, symbols):
    url = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv.zip"
    with zipfile.ZipFile(io.BytesIO(get(url))) as archive:
        csv_files = [name for name in archive.namelist() if name.endswith(".csv")]
        if len(csv_files) != 1:
            raise ValueError("Unexpected NSE archive contents")
        rows = csv.DictReader(io.StringIO(archive.read(csv_files[0]).decode("utf-8-sig")))
        selected = [r for r in rows if r.get("TckrSymb") in symbols and r.get("SctySrs") == "EQ"]
    if {r["TckrSymb"] for r in selected} != set(symbols) or any(r["TradDt"] != str(day) for r in selected):
        raise ValueError("NSE archive date or symbols do not match request")
    return {"source_url": url, "fetched_at_utc": datetime.now(timezone.utc).isoformat(), "rows": selected}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asof", required=True, type=date.fromisoformat)
    args = parser.parse_args()
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    if args.asof > now.date() or (args.asof == now.date() and now.hour < 16):
        parser.error("Only fetch completed sessions at/after 16:00 IST")
    cfg = json.loads((ROOT/"research-config.json").read_text())
    folder = ROOT/"state/market-data"
    archive = folder/"snapshots"/str(args.asof)
    symbols = [s.removesuffix(".NS") for s in cfg["symbols"]]
    latest = nse(args.asof, symbols)
    write_json(folder/f"nse-{args.asof}.json", latest)
    missing_days = set()
    for symbol in cfg["symbols"]:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=10y&interval=1d&events=div%2Csplits"
        payload = json.loads(get(url))
        result = payload["chart"]["result"][0]
        quote = result["indicators"]["quote"][0]
        for i, stamp in enumerate(result["timestamp"]):
            day = datetime.fromtimestamp(stamp, ZoneInfo("Asia/Kolkata")).date()
            if day <= args.asof and any(quote[key][i] is None for key in ("open", "high", "low", "close", "volume")):
                missing_days.add(day)
        document = {"source_url": url, "fetched_at_utc": datetime.now(timezone.utc).isoformat(), "payload": payload}
        # Keep the first fetched daily snapshot; corrections remain visible in latest files.
        if not (archive/f"{symbol}.json").exists():
            write_json(archive/f"{symbol}.json", document)
        write_json(folder/f"{symbol}.json", document)
        print(f"Downloaded {symbol}: {len(result['timestamp'])} vendor rows")
    for day in sorted(missing_days):
        path = folder/f"nse-{day}.json"
        if not path.exists():
            write_json(path, nse(day, symbols))
        print(f"NSE repair available for {day}")
    print(f"NSE end-of-day verification available for {args.asof}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.exit(f"Data refresh failed; do not issue new paper orders: {exc}")
