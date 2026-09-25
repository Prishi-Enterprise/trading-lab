"""Run one scheduled NSE-only paper check on a completed trial session.

This deterministic runner uses existing local data and the public NSE archive.
It cannot place orders or create a past paper signal.
"""

import json
import os
import subprocess
import sys
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
IST = ZoneInfo("Asia/Kolkata")
TRIAL_DAYS = frozenset(date.fromisoformat(value) for value in (
    "2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01"))
SCHEDULE_LABEL = "in.prishi.tradinglab.nse-paper-week-2026"


def should_retire(now):
    local = now.astimezone(IST)
    return local.date() > max(TRIAL_DAYS) or (local.date() == max(TRIAL_DAYS)
            and local.time() >= time(20, 30))


def check(now=None, invoke=None, root=ROOT):
    now = now or datetime.now(IST)
    if now.tzinfo is None:
        raise ValueError("A timezone-aware clock is required")
    local = now.astimezone(IST)
    day = local.date()
    if day not in TRIAL_DAYS:
        return {"date": str(day), "status": "outside_trial", "ran": False}
    if local.time() < time(16):
        return {"date": str(day), "status": "market_not_complete", "ran": False}
    snapshot = root / "state/nse-only/snapshots" / f"{day}.json"
    if snapshot.exists():
        return {"date": str(day), "status": "snapshot_already_frozen", "ran": False}
    command = [sys.executable, "-m", "tradinglab.nse_paper", "--asof", str(day)]
    invoke = invoke or subprocess.run
    result = invoke(command, cwd=root, capture_output=True, text=True, timeout=180)
    return {"date": str(day), "status": "snapshot_recorded" if result.returncode == 0 else "blocked",
            "ran": True, "exit_code": result.returncode,
            "stdout": result.stdout[-4000:], "stderr": result.stderr[-4000:]}


def main():
    now = datetime.now(IST)
    try:
        outcome = check(now)
    except Exception as exc:
        outcome = {"date": str(now.date()), "status": "blocked", "ran": True,
                   "error": f"{type(exc).__name__}: {exc}"}
    outcome["checked_at"] = now.isoformat()
    folder = ROOT / "state/nse-only/automation"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "checks.jsonl").open("a") as output:
        output.write(json.dumps(outcome) + "\n")
    print(json.dumps(outcome))
    if should_retire(now):
        # The final check, or next login after a missed check, retires this job.
        plist = Path.home() / "Library/LaunchAgents" / f"{SCHEDULE_LABEL}.plist"
        if plist.exists():
            plist.unlink()
        subprocess.run(["/bin/launchctl", "bootout", f"gui/{os.getuid()}/{SCHEDULE_LABEL}"],
                       capture_output=True, timeout=10, check=False)
    return 1 if outcome["status"] == "blocked" else 0


if __name__ == "__main__":
    sys.exit(main())
