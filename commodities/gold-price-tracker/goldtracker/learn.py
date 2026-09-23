"""Learn how often prices actually change, to tune the polling interval.

Every tracker tick appends to state/history.csv. From that we find *change events*
(price different from the previous observation of the same metric) and compute,
per IST hour, how often a check saw a new price.

- `python -m goldtracker analyze` prints the table + a suggested interval per hour.
- With config.interval.mode = "adaptive", the tracker itself uses the learned
  per-hour interval: launchd fires every `interval.min` minutes and a tick is skipped
  if the last check was more recent than the learned interval for this hour.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


def read_history(path: Path) -> List[Tuple[datetime, str, float]]:
    if not path.exists():
        return []
    rows = []
    with path.open() as f:
        for r in csv.DictReader(f):
            try:
                rows.append((datetime.fromisoformat(r["checked_at"]), r["metric"], float(r["price"])))
            except (KeyError, ValueError):
                continue
    return rows


def hourly_change_rate(rows, metrics=None) -> Dict[int, Tuple[int, int]]:
    """hour -> (checks, checks_that_saw_a_change), across the given metrics (default all)."""
    last: Dict[str, float] = {}
    last_day: Dict[str, object] = {}
    out: Dict[int, List[int]] = defaultdict(lambda: [0, 0])
    for ts, metric, price in sorted(rows):
        if metrics and metric not in metrics:
            continue
        if last_day.get(metric) != ts.date():  # first obs of the day is not a "change"
            last_day[metric], last[metric] = ts.date(), price
            continue
        out[ts.hour][0] += 1
        if price != last[metric]:
            out[ts.hour][1] += 1
        last[metric] = price
    return {h: (c, ch) for h, (c, ch) in out.items()}


def suggest_minutes(checks: int, changes: int, cur: int, lo: int, hi: int, min_samples: int = 6) -> int:
    """If most checks see a change we are under-sampling -> go faster; if almost none do -> slower."""
    if checks < min_samples:
        return cur
    rate = changes / checks
    if rate >= 0.6:
        return lo
    if rate <= 0.1:
        return hi
    # scale linearly between hi (rate .1) and lo (rate .6)
    return int(round(hi - (rate - 0.1) / 0.5 * (hi - lo)))


def learned_interval(cfg: dict, history: Path, hour: int) -> int:
    iv = cfg.get("interval", {})
    cur, lo, hi = iv.get("minutes", 30), iv.get("min", 30), iv.get("max", 120)
    if iv.get("mode", "fixed") != "adaptive":
        return cur
    metrics = iv.get("learn_from") or [w["metric"] for w in cfg["watch"]]
    rates = hourly_change_rate(read_history(history), set(metrics))
    checks, changes = rates.get(hour, (0, 0))
    return suggest_minutes(checks, changes, cur, lo, hi)


def report(cfg: dict, history: Path) -> str:
    rows = read_history(history)
    if not rows:
        return "no history yet (state/history.csv) – let the tracker run for a few days first"
    iv = cfg.get("interval", {})
    cur, lo, hi = iv.get("minutes", 30), iv.get("min", 30), iv.get("max", 120)
    days = len({r[0].date() for r in rows})
    lines = [f"history: {len(rows)} observations over {days} day(s); mode={iv.get('mode', 'fixed')}", ""]
    for metric in sorted({r[1] for r in rows}):
        rates = hourly_change_rate(rows, {metric})
        lines.append(f"{metric}")
        lines.append("  hour  checks  changes  rate   suggested")
        for h in sorted(rates):
            c, ch = rates[h]
            lines.append(f"  {h:02d}:00 {c:6d} {ch:8d}  {ch / c if c else 0:5.0%}   "
                         f"{suggest_minutes(c, ch, cur, lo, hi)} min")
        lines.append("")
    return "\n".join(lines)
