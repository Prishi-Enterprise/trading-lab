"""Collect official NSE bhavcopies for the separately versioned paper trial."""

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradinglab.nse_only import ARCHIVES, SPECIAL_SESSIONS, fetch_archive, load_series
from tradinglab.research import IST, ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-date", type=date.fromisoformat, default=date(2025, 8, 1))
    parser.add_argument("--through", type=date.fromisoformat, required=True)
    args = parser.parse_args()
    now = datetime.now(IST)
    if args.through > now.date() or (args.through == now.date() and now.hour < 16):
        parser.error("Fetch only completed NSE sessions after 16:00 IST")
    missing, failed = [], []
    day = args.from_date
    while day <= args.through:
        if day.weekday() < 5 or day in SPECIAL_SESSIONS:
            try:
                if fetch_archive(day) is None:
                    missing.append(str(day))
            except Exception as exc:
                failed.append({"date": str(day), "error": str(exc)})
        day += timedelta(days=1)
    manifest = {"through": str(args.through), "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                "missing_weekday_archives": missing, "fetch_failures": failed}
    path = ROOT / "state/nse-only/fetch-manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    if failed:
        raise ValueError(f"{len(failed)} NSE archive requests failed; inspect {path}")
    series, provenance = load_series(ARCHIVES, args.through)
    print(json.dumps({"sessions": len(provenance), "first": provenance[0]["date"],
                      "last": provenance[-1]["date"], "missing_weekday_archives": missing,
                      "symbols": list(series)}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.exit(f"NSE-only history incomplete; no paper decision: {exc}")
