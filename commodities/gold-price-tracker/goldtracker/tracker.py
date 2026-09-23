"""Core loop (one invocation = one check). Designed to be run every ~10 min by cron,
GitHub Actions or launchd. State lives in a small JSON file so runs are stateless otherwise.

Rules
- "Opening price" = first price seen today (IST) whose site timestamp is also today,
  at/after config.active_window[0]. Stale quotes (site still showing yesterday) are ignored.
- Alert when change vs open crosses a threshold in config.thresholds_pct
  (negative = drop, positive = rise). Each threshold fires at most once per metric per day.
- Polling interval: fixed (config.interval.minutes) or "adaptive" – learned per IST hour
  from how often prices actually changed in state/history.csv (see learn.py).
- If every source fails `failure_alert_after` runs in a row, send one "tracker broken" alert per day.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from . import learn, sources
from .notify import Alert, NotifyError
from .timeutil import IST, inr

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = ROOT / "config.json"


# --------------------------------------------------------------------------- config / env

def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Tiny .env loader (KEY=VALUE lines). Real env vars win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_config(path: Optional[Path] = None) -> dict:
    cfg = json.loads(Path(path or os.environ.get("GOLD_CONFIG") or DEFAULT_CONFIG).read_text())
    # env override for quick experiments: THRESHOLDS_PCT="-2,-5,-10"
    if os.environ.get("THRESHOLDS_PCT"):
        cfg["thresholds_pct"] = [float(x) for x in os.environ["THRESHOLDS_PCT"].split(",") if x.strip()]
    return cfg


def state_path(cfg: dict) -> Path:
    p = Path(os.environ.get("GOLD_STATE") or cfg.get("state_file", "state/state.json"))
    return p if p.is_absolute() else ROOT / p


def load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    tmp.replace(path)


def append_history(path: Path, now: datetime, q: sources.Quote) -> None:
    hist = path.parent / "history.csv"
    hist.parent.mkdir(parents=True, exist_ok=True)
    new = not hist.exists()
    with hist.open("a") as f:
        if new:
            f.write("checked_at,metric,price,site_as_of\n")
        f.write(f"{now.isoformat(timespec='seconds')},{q.metric},{q.price:.2f},"
                f"{q.as_of.isoformat(timespec='minutes') if q.as_of else ''}\n")


def dashboard_payload(cfg: dict, state: dict) -> dict:
    """Return the sanitized record published to the authenticated dashboard."""
    run = state.get("last_run") or {}
    if not run.get("checked_at"):
        raise ValueError("No completed tracker run is available")

    metrics = []
    for watched in cfg.get("watch", []):
        metric = watched["metric"]
        latest = state.get("last", {}).get(metric)
        if not latest:
            continue
        opened = state.get("open", {}).get(metric)
        change_pct = None
        if opened and opened.get("price"):
            change_pct = round((latest["price"] - opened["price"]) / opened["price"] * 100, 4)
        metrics.append({
            "metric": metric,
            "label": watched.get("label", metric),
            "price": latest["price"],
            "unit": "INR / 10g",
            "as_of": latest.get("as_of"),
            "checked_at": latest.get("checked_at"),
            "open_price": opened.get("price") if opened else None,
            "open_at": opened.get("at") if opened else None,
            "change_pct": change_pct,
            "alerts_sent": state.get("alerts_sent", {}).get(metric, []),
        })

    status = run.get("status", "failed")
    labels = {
        "verified": "Gold sources verified",
        "partial": "Gold update partially verified",
        "failed": "Gold sources unavailable",
    }
    summaries = {
        "verified": f"Recorded {len(metrics)} watched metrics from same-day public source snapshots.",
        "partial": f"Recorded {len(metrics)} watched metrics, with one or more source or freshness issues.",
        "failed": "No current watched metric could be verified; the previous quote remains historical only.",
    }
    return {
        "observed_at": run["checked_at"],
        "observed_on": state.get("date"),
        "status": status,
        "headline": labels.get(status, labels["failed"]),
        "summary": summaries.get(status, summaries["failed"]),
        "metrics": metrics,
        "issues": run.get("issues", []),
        "interval_minutes": state.get("interval_min", cfg.get("interval", {}).get("minutes", 10)),
        "source": "Ahmedabad gold tracker",
    }


# --------------------------------------------------------------------------- helpers

def _hm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def in_window(cfg: dict, now: datetime) -> bool:
    if now.weekday() not in cfg.get("active_days", [0, 1, 2, 3, 4, 5]):
        return False
    start, end = cfg.get("active_window", ["09:00", "23:45"])
    mins = now.hour * 60 + now.minute
    return _hm(start) <= mins <= _hm(end)


def crossed(pct: float, thr: float) -> bool:
    return pct <= thr if thr < 0 else pct >= thr


def fetch_all(cfg: dict, getter: Callable[[str], str]) -> Tuple[Dict[str, sources.Quote], List[str]]:
    needed = {w["metric"].split(":", 1)[0] for w in cfg["watch"]}
    quotes: Dict[str, sources.Quote] = {}
    errors: List[str] = []
    for src in sorted(needed):
        url = cfg["sources"][src]["url"]
        try:
            for q in sources.fetch(src, url, getter).values():
                quotes[q.metric] = q
        except sources.SourceError as e:
            errors.append(str(e))
    return quotes, errors


def build_alert(label: str, q: sources.Quote, open_price: float, open_at: str, pct: float,
                thr: float, city: str) -> Alert:
    arrow = "🔻" if pct < 0 else "🔺"
    as_of = (q.as_of or datetime.now(IST)).strftime("%d %b %H:%M IST")
    text = (
        f"{arrow} Gold alert – {city}\n"
        f"{label}: {inr(q.price)}\n"
        f"Today's open: {inr(open_price)} ({open_at})\n"
        f"Change: {pct:+.2f}% (threshold {thr:+g}%)\n"
        f"As of {as_of}"
    )
    return Alert(title=label, price=inr(q.price), change_pct=pct, open_price=inr(open_price),
                 as_of=as_of, text=text)


# --------------------------------------------------------------------------- main entry

def run(cfg: dict, notifier, now: Optional[datetime] = None, force: bool = False,
        getter: Callable[[str], str] = sources.http_get, log: Callable[[str], None] = print) -> int:
    """Returns exit code: 0 ok / skipped, 2 all sources failed, 3 notify failed."""
    now = (now or datetime.now(IST)).astimezone(IST)
    if not force and not in_window(cfg, now):
        log(f"outside active window ({now:%a %H:%M} IST) – skipping")
        return 0

    spath = state_path(cfg)
    state = load_state(spath)
    today = now.date().isoformat()

    # adaptive polling: launchd fires every interval.min; skip if the learned interval hasn't elapsed
    interval = learn.learned_interval(cfg, spath.parent / "history.csv", now.hour)
    last_run = state.get("last_run_at")
    if not force and last_run:
        elapsed = (now - datetime.fromisoformat(last_run)).total_seconds() / 60
        if elapsed < interval - 1:  # 1 min slack for scheduler jitter
            log(f"last check {elapsed:.0f} min ago < interval {interval} min – skipping")
            return 0

    if state.get("date") != today:
        state = {"date": today, "open": {}, "alerts_sent": {}, "last": {},
                 "fail_streak": state.get("fail_streak", 0), "fail_alerted": None}
    state["last_run_at"] = now.isoformat(timespec="seconds")
    state["interval_min"] = interval

    quotes, errors = fetch_all(cfg, getter)
    issues = list(errors)
    for e in errors:
        log(f"WARN {e}")

    city = cfg.get("city", "Ahmedabad")
    rc = 0
    if not quotes:
        state["fail_streak"] = state.get("fail_streak", 0) + 1
        n = cfg.get("failure_alert_after", 6)
        if state["fail_streak"] >= n and state.get("fail_alerted") != today:
            msg = (f"⚠️ Gold tracker ({city}) can't read any price source for {state['fail_streak']} runs.\n"
                   + "\n".join(errors)[:600])
            try:
                notifier.send(Alert("tracker error", "-", 0.0, "-", now.strftime("%d %b %H:%M IST"), msg))
                state["fail_alerted"] = today
            except NotifyError as e:
                log(f"ERROR notify: {e}")
        state["last_run"] = {"checked_at": now.isoformat(timespec="seconds"),
                             "status": "failed", "issues": issues}
        save_state(spath, state)
        return 2
    state["fail_streak"] = 0

    thresholds = sorted(cfg.get("thresholds_pct", [-10]), key=abs)
    for w in cfg["watch"]:
        metric, label = w["metric"], w.get("label", w["metric"])
        q = quotes.get(metric)
        if not q:
            log(f"WARN {metric}: not available this run")
            issues.append(f"{metric}: not available this run")
            continue
        append_history(spath, now, q)
        state["last"][metric] = {"price": q.price, "as_of": q.as_of.isoformat() if q.as_of else None,
                                 "checked_at": now.isoformat(timespec="seconds")}

        if q.as_of and q.as_of.date() != now.date():
            log(f"{metric}: {inr(q.price)} is stale (site time {q.as_of:%d %b %H:%M}) – waiting for today's rate")
            issues.append(f"{metric}: source quote is stale ({q.as_of.isoformat()})")
            continue

        op = state["open"].get(metric)
        if not op:
            state["open"][metric] = {"price": q.price,
                                     "at": (q.as_of or now).strftime("%H:%M IST")}
            log(f"{metric}: opening price set to {inr(q.price)}")
            continue

        pct = (q.price - op["price"]) / op["price"] * 100
        sent = state["alerts_sent"].setdefault(metric, [])
        hits = [t for t in thresholds if crossed(pct, t) and t not in sent]
        log(f"{metric}: {inr(q.price)} vs open {inr(op['price'])} = {pct:+.2f}%")
        if not hits:
            continue
        worst = max(hits, key=abs)
        try:
            notifier.send(build_alert(label, q, op["price"], op["at"], pct, worst, city))
            sent.extend(hits)
            log(f"ALERT sent for {metric} ({worst:+g}%) via {notifier.name}")
        except NotifyError as e:
            log(f"ERROR notify: {e}")
            issues.append(f"{metric}: notification failed")
            rc = 3  # not marked as sent -> retried next run

    state["last_run"] = {"checked_at": now.isoformat(timespec="seconds"),
                         "status": "verified" if not issues else "partial", "issues": issues}
    save_state(spath, state)
    return rc
