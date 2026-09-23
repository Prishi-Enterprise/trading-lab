# Gold Price Tracker · Trading Lab

Ahmedabad gold price tracker → WhatsApp alerts when price moves **±2 / ±5 / ±10 %** vs the day's
opening price. The hosted dashboard uses Supabase Cron and an Edge Function on a 30-minute base
schedule, then learns a 30–120 minute collection interval by IST hour. The zero-dependency Python
runner remains available as a local fallback (Python ≥ 3.9 stdlib).

The hosted worker reads [bullions.co.in](https://bullions.co.in/location/ahmedabad/) for the
Ahmedabad association rate and MCX snapshot, plus the timestamped 24K showroom rate from
[Suvarnakrupa](https://www.suvarnakrupa.in/today-gold-rate). The local fallback also supports
[allindiabullion.com](https://allindiabullion.com/gold-rate/gujarat/ahmedabad); that site blocks
Supabase datacenter traffic. Findings in [docs/research.md](docs/research.md).

## Quick start (Mac)
```bash
cd ~/PrishiAI/trading-lab/commodities/gold-price-tracker
python3 -m unittest discover -s tests       # offline tests
python3 -m goldtracker check                # live prices from both sites
cp .env.example .env                        # then pick a WhatsApp provider: docs/whatsapp.md
python3 -m goldtracker test-alert           # confirm WhatsApp works
./scripts/install_launchd.sh                # start the adaptive local fallback
tail -f state/launchd.log
```

## Daily use
| | |
|---|---|
| `python3 -m goldtracker status` | today's open, last price, alerts sent |
| `python3 -m goldtracker analyze` | how often prices change per hour → suggested interval |
| `python3 -m goldtracker dashboard` | sanitized JSON for the authenticated Trading Lab page |
| edit `config.json` | thresholds, watched metrics, hours, interval mode |
| `./scripts/install_launchd.sh uninstall` | stop |

## Working on it with an AI agent
All module instructions are in this directory: [AGENTS.md](AGENTS.md) (canonical),
[CLAUDE.md](CLAUDE.md) (imports it), and playbooks in
[skills/gold-tracker/SKILL.md](skills/gold-tracker/SKILL.md) (run `./scripts/link_skills.sh` once to expose it to Claude Code / Cursor). Open the folder in
Claude Code / Cowork / Cursor and ask e.g. "check the gold tracker is healthy" or "the bullions
parser broke, fix it".
