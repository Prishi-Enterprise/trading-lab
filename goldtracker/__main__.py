"""CLI.

  python -m goldtracker check              # fetch + print all current quotes (no state, no alerts)
  python -m goldtracker run [--force]      # one tracker tick (what cron runs)
  python -m goldtracker status             # show today's open / last / alerts from state file
  python -m goldtracker test-alert         # send a sample alert through the configured NOTIFIER
  python -m goldtracker analyze            # how often prices change per hour -> suggested interval
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from . import learn, sources, tracker
from .notify import Alert, NotifyError, get_notifier
from .timeutil import IST, inr


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="goldtracker")
    p.add_argument("cmd", choices=["check", "run", "status", "test-alert", "analyze"])
    p.add_argument("--force", action="store_true", help="ignore active window")
    p.add_argument("--notifier", help="override NOTIFIER env (console|meta|twilio|callmebot)")
    p.add_argument("--config", help="path to config.json")
    a = p.parse_args(argv)

    tracker.load_dotenv()
    cfg = tracker.load_config(a.config)

    if a.cmd == "check":
        rc = 0
        for src, s in cfg["sources"].items():
            try:
                for q in sources.fetch(src, s["url"]).values():
                    extra = " ".join(f"{k}={inr(v)}" for k, v in q.extra.items())
                    ts = q.as_of.strftime("%d %b %H:%M") if q.as_of else "?"
                    print(f"{q.metric:28} {inr(q.price):>12}  @ {ts}  {extra}")
            except sources.SourceError as e:
                print(f"{src:28} ERROR {e}")
                rc = 2
        return rc

    if a.cmd == "analyze":
        print(learn.report(cfg, tracker.state_path(cfg).parent / "history.csv"))
        return 0

    if a.cmd == "status":
        print(json.dumps(tracker.load_state(tracker.state_path(cfg)), indent=2, ensure_ascii=False))
        return 0

    try:
        notifier = get_notifier(a.notifier)
    except NotifyError as e:
        print(f"ERROR {e}")
        return 3

    if a.cmd == "test-alert":
        now = datetime.now(IST).strftime("%d %b %H:%M IST")
        text = f"✅ Gold tracker test message ({cfg.get('city', 'Ahmedabad')}) – WhatsApp alerts are working. {now}"
        try:
            notifier.send(Alert("Gold tracker test", inr(150000), -10.0, inr(166667), now, text))
        except NotifyError as e:
            print(f"ERROR {e}")
            return 3
        print(f"sent via {notifier.name}")
        return 0

    return tracker.run(cfg, notifier, force=a.force)


if __name__ == "__main__":
    sys.exit(main())
