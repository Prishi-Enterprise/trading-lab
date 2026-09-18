# Gold Price Tracker — agent instructions

Canonical instructions for any coding agent (Claude Code, Cowork, Cursor, Codex…).
`CLAUDE.md` just imports this file. Everything needed to operate the project lives in
this repo — no account-level memory, skills or connectors are required.

## What it does
Polls Ahmedabad gold rates every ~10 min (macOS launchd), records the day's **opening price**
per metric, and sends a **WhatsApp alert** when the price moves **±2 / ±5 / ±10 %** vs that
open (each threshold once per metric per day). Polling interval can be learned from how
often prices actually change (`interval.mode = "adaptive"`).

## Layout
```
goldtracker/
  sources.py    fetch + regex parsers for bullions.co.in and allindiabullion.com (pure, testable)
  tracker.py    one tick: window check → fetch → open/threshold logic → notify → state
  learn.py      change-rate per IST hour from state/history.csv → suggested/adaptive interval
  notify.py     WhatsApp notifiers: console | meta (Cloud API) | twilio | callmebot
  timeutil.py   IST tz + Indian ₹ formatting
  __main__.py   CLI: check | run [--force] | status | test-alert | analyze
config.json     city, window, thresholds, interval, sources, watched metrics (no secrets)
.env            secrets (git-ignored) — template in .env.example
state/          runtime only, git-ignored: state.json, history.csv, launchd.log
scripts/install_launchd.sh   install/uninstall the Mac job
tests/          stdlib unittest + HTML fixtures captured from the real sites
docs/           research.md (source findings), whatsapp.md (WhatsApp API setup)
skills/gold-tracker/SKILL.md   step-by-step playbooks (plain markdown, any agent; `scripts/link_skills.sh` exposes it to Claude Code/Cursor)
```

## Commands
```bash
python3 -m unittest discover -s tests -v   # always run after changes (no network needed)
python3 -m goldtracker check               # live fetch, prints every parsed metric
python3 -m goldtracker run --force         # one tick ignoring the active window
python3 -m goldtracker status              # today's open / last / alerts_sent
python3 -m goldtracker test-alert          # send sample WhatsApp via NOTIFIER
python3 -m goldtracker analyze             # how often prices change, suggested interval per hour
./scripts/install_launchd.sh [uninstall]   # (re)install the Mac job after config interval changes
```

## Conventions / constraints
- **Zero dependencies**: stdlib only, Python ≥ 3.9 (macOS system python). Don't add requests/bs4.
- Parsers are regex over server-rendered HTML. When a site changes markup: capture fresh HTML
  into `tests/fixtures/`, fix regex, run tests. See the skill's "Fix a broken parser".
- Metric ids are `<source>:<key>` e.g. `bullions:gold24k_10g`, `bullions:mcx_gold_10g`,
  `aib:retail_999_10g`, `aib:rtgs_999_10g`. Run `check` to list all.
- Opening price = first quote of the IST day whose *site timestamp* is today (stale quotes skipped).
- Never commit `.env` or `state/`. Secrets only via env.
- Be polite to the sites: don't poll faster than every 5 min.

## Gotchas
- Both sites are behind Cloudflare. A plain GET works today; if `check` starts returning
  "no prices found", it's likely a challenge page — see docs/research.md for fallbacks.
- allindiabullion.com's live ticks come via `/api/token` + websocket (bot-protected). We only
  read the server-rendered snapshot, which is refreshed on each page load.
- The bullions.co.in Ahmedabad association rate changes only a few times a day; MCX moves
  continuously. That's why both are watched.
- Sandboxed agent shells (e.g. Cowork cloud/VM) may have an egress allowlist that blocks these
  sites. Test live fetches from the Mac terminal, or a browser tool; unit tests work anywhere.
