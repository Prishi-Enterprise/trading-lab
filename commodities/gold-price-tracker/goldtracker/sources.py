"""Price sources: fetch + parse Ahmedabad gold rates from public pages.

Both sites server-render their prices into HTML, so a plain GET + regex is enough.
Parsers are pure functions (html -> quotes) so they can be tested against fixtures
in tests/fixtures/. When a site changes its markup, update the regex here and
refresh the fixture (see skills/gold-tracker/SKILL.md -> "Fix a broken parser").
"""
from __future__ import annotations

import gzip
import html as htmllib
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Dict, Optional

from .timeutil import IST

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)


@dataclass
class Quote:
    source: str            # "bullions" | "aib"
    key: str               # e.g. "gold24k_10g"
    label: str             # human label
    price: float           # INR
    unit: str              # "10g"
    as_of: Optional[datetime] = None   # tz-aware (IST) timestamp the site claims, if any
    extra: Dict[str, float] = field(default_factory=dict)

    @property
    def metric(self) -> str:
        return f"{self.source}:{self.key}"


class SourceError(Exception):
    pass


def http_get(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-IN,en;q=0.9",
            "Accept-Encoding": "gzip",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                data = gzip.decompress(data)
            return data.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        raise SourceError(f"GET {url} failed: {e}") from e


def _num(s: str) -> float:
    return float(s.replace(",", "").replace("₹", "").strip())


# --------------------------------------------------------------------------- bullions.co.in

_BUL_UPDATED = re.compile(
    r"Last Update</i>\s*:\s*<strong>\s*[A-Za-z]+,\s*(\d{1,2} [A-Za-z]{3} \d{4}) (\d{1,2}):(\d{2})\s*([AP]M)?",
)
_BUL_GOLD_ROW = re.compile(
    r"<td[^>]*text-left[^>]*>\s*Gold (\d{2}) Karat.*?</td>((?:\s*<td[^>]*>[\d,.]+</td>)+)",
    re.S,
)
_BUL_CELL = re.compile(r"<td[^>]*>([\d,.]+)</td>")
_BUL_MCX = re.compile(
    r"Gold - India MCX.*?</td>((?:\s*<td[^>]*>\s*<div>[^<]*</div>\s*</td>){7})", re.S
)
_BUL_DIV = re.compile(r"<div>([^<]*)</div>")


def _bul_time(date_s: str, hh: str, mm: str, ampm: Optional[str]) -> datetime:
    h = int(hh)
    # The site sometimes prints 24h time with a PM suffix ("21:05 PM"); only apply AM/PM for h<=12.
    if ampm and h <= 12:
        if ampm == "PM" and h != 12:
            h += 12
        if ampm == "AM" and h == 12:
            h = 0
    d = datetime.strptime(date_s, "%d %b %Y")
    return d.replace(hour=h, minute=int(mm), tzinfo=IST)


def parse_bullions(page: str) -> Dict[str, Quote]:
    out: Dict[str, Quote] = {}
    m = _BUL_UPDATED.search(page)
    as_of = _bul_time(*m.groups()) if m else None

    for karat, cells in _BUL_GOLD_ROW.findall(page):
        vals = _BUL_CELL.findall(cells)
        if len(vals) < 2:
            continue
        # columns: 1 Gram, 10 Gram, 100 Gram, 1 Kg, 1 Ounce, 1 Tola
        key = f"gold{karat}k_10g"
        if key not in out:  # first table on page = gold table
            out[key] = Quote("bullions", key, f"Gold {karat}K /10g (bullions.co.in)",
                             _num(vals[1]), "10g", as_of)

    m = _BUL_MCX.search(page)
    if m:
        v = _BUL_DIV.findall(m.group(1))
        # Price, Change, Change%, High, Low, Previous, Last Update ("18 Sep, 10:35")
        mcx_time = as_of
        tm = re.match(r"\s*(\d{1,2}) ([A-Za-z]{3}), (\d{1,2}):(\d{2})", v[6])
        if tm:
            year = (as_of or datetime.now(IST)).year
            mcx_time = datetime.strptime(f"{tm.group(1)} {tm.group(2)} {year}", "%d %b %Y").replace(
                hour=int(tm.group(3)), minute=int(tm.group(4)), tzinfo=IST)
        out["mcx_gold_10g"] = Quote(
            "bullions", "mcx_gold_10g", "Gold MCX /10g", _num(v[0]), "10g", mcx_time,
            extra={"high": _num(v[3]), "low": _num(v[4]), "prev_close": _num(v[5])},
        )
    if not out:
        raise SourceError("bullions: no prices found in page (markup changed?)")
    return out


# --------------------------------------------------------------------------- allindiabullion.com

_AIB_CARD = re.compile(
    r'<div class="[^"]*text-slate-400[^"]*">\s*([A-Z0-9 ]+?)\s*</div>\s*'
    r"<span[^>]*>\s*(GOLD|SILVER)\s*</span>\s*</div>\s*"
    r'<div class="mt-2">\s*<span[^>]*>\s*(?:₹|&#x20B9;|&#8377;)?\s*([\d,.]+)\s*</span>',
)
_AIB_TIME = re.compile(r'<time dateTime="([^"]+)"', re.I)


def parse_aib(page: str) -> Dict[str, Quote]:
    out: Dict[str, Quote] = {}
    as_of = None
    m = _AIB_TIME.search(page)
    if m:
        try:
            as_of = datetime.fromisoformat(m.group(1).replace("Z", "+00:00")).astimezone(IST)
        except ValueError:
            as_of = None
    for label, metal, price in _AIB_CARD.findall(page):
        if metal != "GOLD":
            continue
        key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") + "_10g"  # retail_999_10g, rtgs_995_10g...
        if key not in out:
            out[key] = Quote("aib", key, f"Gold {htmllib.unescape(label)} /10g (allindiabullion.com)",
                             _num(price), "10g", as_of)
    if not out:
        raise SourceError("aib: no prices found in page (markup changed or Cloudflare challenge?)")
    return out


PARSERS: Dict[str, Callable[[str], Dict[str, Quote]]] = {
    "bullions": parse_bullions,
    "aib": parse_aib,
}


def fetch(source: str, url: str, getter: Callable[[str], str] = http_get) -> Dict[str, Quote]:
    if source not in PARSERS:
        raise SourceError(f"unknown source {source!r}")
    return PARSERS[source](getter(url))
