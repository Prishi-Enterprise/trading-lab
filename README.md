# gold-price-tracker

Ahmedabad gold price tracker → WhatsApp alerts when price moves **±2 / ±5 / ±10 %** vs the day's
opening price. Runs on a Mac via launchd every 10 min; can learn a better interval from how often
prices actually change. Zero dependencies (Python ≥ 3.9 stdlib).

Sources: [bullions.co.in](https://bullions.co.in/location/ahmedabad/) (24K/22K association rate +
live MCX) and [allindiabullion.com](https://allindiabullion.com/gold-rate/gujarat/ahmedabad)
(retail/RTGS 999/995). Findings in [docs/research.md](docs/research.md).

## Quick start (Mac)
```bash
cd ~/PrishiAI/gold-price-tracker
python3 -m unittest discover -s tests       # offline tests
python3 -m goldtracker check                # live prices from both sites
cp .env.example .env                        # then pick a WhatsApp provider: docs/whatsapp.md
python3 -m goldtracker test-alert           # confirm WhatsApp works
./scripts/install_launchd.sh                # start the 10-min schedule
tail -f state/launchd.log
```

## Daily use
| | |
|---|---|
| `python3 -m goldtracker status` | today's open, last price, alerts sent |
| `python3 -m goldtracker analyze` | how often prices change per hour → suggested interval |
| edit `config.json` | thresholds, watched metrics, hours, interval mode |
| `./scripts/install_launchd.sh uninstall` | stop |

## Working on it with an AI agent
All instructions are in the repo, not in any AI account: [AGENTS.md](AGENTS.md) (canonical),
[CLAUDE.md](CLAUDE.md) (imports it), and playbooks in
[skills/gold-tracker/SKILL.md](skills/gold-tracker/SKILL.md) (run `./scripts/link_skills.sh` once to expose it to Claude Code / Cursor). Open the folder in
Claude Code / Cowork / Cursor and ask e.g. "check the gold tracker is healthy" or "the bullions
parser broke, fix it".
