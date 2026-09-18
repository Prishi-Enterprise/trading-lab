---
name: gold-tracker
description: Operate, tune or fix the Ahmedabad gold price tracker in this repo — check live prices, change alert thresholds or interval, set up WhatsApp alerts, install the Mac launchd job, learn polling interval from history, or repair a scraper after a site change.
---

# Gold tracker playbooks

Read `AGENTS.md` first for layout and conventions. All commands run from the repo root.

## 1. Check it's working
1. `python3 -m unittest discover -s tests -v` — must be green.
2. `python3 -m goldtracker check` — should list `bullions:gold24k_10g`, `bullions:mcx_gold_10g`,
   `aib:retail_999_10g`… with today's timestamps. If your shell's network is sandboxed, run it on
   the Mac terminal, or open the URLs from `config.json` in a browser tool to eyeball prices.
3. `python3 -m goldtracker status` — today's `open`, `last`, `alerts_sent`, `interval_min`.
4. `tail -50 state/launchd.log` — per-tick log lines (`… vs open … = -0.42%`).

## 2. Change thresholds / watched metrics / hours
- Edit `config.json`:
  - `thresholds_pct`: negative = drop, positive = rise. Current: `[-2,-5,-10,2,5,10]`.
  - `watch`: list of `{metric, label}`; metric ids come from `check`.
  - `active_days` (0=Mon…6=Sun), `active_window` IST `["HH:MM","HH:MM"]`.
- No restart needed (each tick re-reads config) **except** interval changes → step 4.
- Quick one-off override without editing: `THRESHOLDS_PCT=-1,1 python3 -m goldtracker run --force`.

## 3. Set up / switch WhatsApp provider
Follow `docs/whatsapp.md`. Then put creds in `.env` (copy `.env.example`), set `NOTIFIER=`,
and verify with `python3 -m goldtracker test-alert`. Never commit `.env`.

## 4. Install / change the Mac schedule
- `./scripts/install_launchd.sh` — installs `com.goldtracker.ahmedabad`, runs every
  `interval.minutes` (fixed) or `interval.min` (adaptive). Re-run after changing `interval`.
- `./scripts/install_launchd.sh uninstall` to remove.
- Runs only while the Mac is awake; missed ticks run on wake.

## 5. Learn a better polling interval
1. Let it run a few days at a fixed 10 min (history accumulates in `state/history.csv`).
2. `python3 -m goldtracker analyze` → per metric, per IST hour: checks, how many saw a price change,
   suggested minutes (≥60 % checks changing → `min`; ≤10 % → `max`; linear in between).
3. To let the tracker apply it automatically: set `"interval": {"mode": "adaptive", "minutes": 10,
   "min": 5, "max": 30}` (optionally `"learn_from": ["bullions:gold24k_10g"]` to learn only from the
   slow association rate), then re-run `./scripts/install_launchd.sh` (launchd now fires every `min`
   minutes; ticks skip until the learned interval for that hour has passed).

## 6. Fix a broken parser (site changed markup / Cloudflare)
Symptoms: `check` prints `ERROR … no prices found`, or you got a "tracker can't read any price
source" WhatsApp.
1. Get the raw HTML: `curl -sA "Mozilla/5.0" <url> -o /tmp/page.html` (or via a browser tool:
   `await (await fetch(location.href)).text()` in the page). If it's a Cloudflare challenge page,
   see docs/research.md → "If blocked".
2. Find the price markup (search for a visible number, e.g. `154,090` or `₹1,51,119`).
3. Save a trimmed but *real* snippet over `tests/fixtures/<source>_ahmedabad.html` and update the
   expected numbers in `tests/test_tracker.py`.
4. Fix the regex in `goldtracker/sources.py`, run tests, then `check` live.
5. Note the change + date in `docs/research.md`.

## 7. Add another city / source
- Same site, other city: bullions.co.in uses `/location/<city>/`; allindiabullion uses
  `/gold-rate/<state>/<city>`. Duplicate the repo folder or point `GOLD_CONFIG` at a second config
  with its own `state_file`, and install a second launchd label.
- New site: add `parse_<name>(html) -> Dict[str, Quote]` in `sources.py`, register it in `PARSERS`,
  add the URL under `config.sources`, add a fixture + test.
