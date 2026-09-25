# Prishi trading lab

Read README.md, config.json and docs/RESEARCH.md before extending this project.

The user will arrange a fresh demat account for this experiment. Existing personal holdings are explicitly out of scope; do not request them again or make research depend on them. The new account has not been confirmed opened, funded or connected. Groww is the user's existing broker; confirm the new account's actual broker and applicable charges when available. Begin with an empty research portfolio, not an assumed ₹50,000 brokerage balance.

- Python 3.9+ standard library only. Run `python3 -m unittest discover -s tests -v` after code changes.
- `commodities/gold-price-tracker` is the migrated zero-dependency Ahmedabad gold watcher. Preserve its parser fixtures and operating constraints, keep its runtime `state/` and `.env` ignored, and run its own unittest suite after module changes.
- This is a paper-research project with daily-data downloaders, frozen ETF screener/backtest and prospective paper recorders. There is no brokerage connection, streaming price feed or order execution. The 22–28 September version was stopped on 25 September due to data disagreement; read docs/NSE-ONLY-PAPER-WEEK.md for the separately versioned 25 September–1 October NSE-only trial. The user executes any eventual real orders and has required dummy testing before investment.
- ₹50,000 is the total Prishi organisation fund, separate from personal living expenses. It is not a confirmed brokerage deposit or an agreed trading allocation. The user uses Groww and generally holds equities for months, but is willing to adapt. Total accepted loss limit is ₹5,000 for the experiment, not per month. Subscription reserve and deployable trading amount remain undecided. `capital_ceiling` is a paper-only assumption bounded by `organisation_budget`; never interpret it as money allocated to live trading.
- Treat the ₹5,000 limit as net trading loss from the experiment's starting capital, including charges and open-position losses, excluding subscription withdrawals. Current CLI flags only recorded closed-trade loss from starting paper capital; retain any historical breach even after recovery. It cannot enforce the full limit or guarantee execution prices. No automatic live orders.
- September 2026 subscription is already paid. Start expense scenarios in October 2026. Show the original ₹5,500 offset and the full ₹11,000 bill separately. Never treat either return requirement as an expected yield.
- Keep real business income, simulated profits, realised trading profits and principal separate. A cost offset supplied to the CLI is a hypothetical scenario, not an accounting entry.
- Use Decimal for money. Include round-trip costs, reject non-finite values, and validate chronological, cash-funded trades. Preserve negative outcomes and never silently discard failed records.
- Example data is fictional and must stay visibly labelled. Do not invent live quotes, backtest results, broker permissions, or source freshness.
- Journal is closed long trades only, at most one position at a time, with next entry after previous exit date. It cannot measure intratrade losses or support overlapping positions.
- Keep credentials, broker statements, personal financial records and journals in ignored local state/, not committed examples.
- No paid services, live orders or autonomous trading are enabled. The old `prishi-paper-trading-week` heartbeat was deleted on 25 September. The NSE-only trial has local automatic checks only through 1 October 2026; the runner refuses dates outside that week and removes the LaunchAgent after the final check. Record a prospective decision only on the current completed market day. Notify only on actionable paper changes, data failures or final results. Resolve actual allocation and evidence before any discussion of a live trial. A completed week is not automatic approval.
- research-config.json is the frozen etf-breakout-v1 baseline. It uses ₹28,000 paper capital, a hypothetical ₹22,000 subscription reserve, one position capped at ₹10,000, and ₹250 planned stop risk including costs. Preserve the config hash during the prospective week. Version later hypotheses separately; never tune away a failed backtest or rewrite a past signal.
- research-config-nse-v2.json freezes the same rules for a separate official-NSE-only data experiment. Store its raw archives and snapshots under ignored state/nse-only; never combine its results with v1.

## Commands

```sh
python3 -m tradinglab status
python3 -m tradinglab status --month 2026-10 --project-income 4000
python3 -m tradinglab review --journal examples/paper-trades.json --month 2026-09
python3 -m unittest discover -s tests -v
python3 scripts/fetch_market_data.py --asof YYYY-MM-DD
python3 -m tradinglab.research --asof YYYY-MM-DD
python3 -m tradinglab.paper --asof YYYY-MM-DD
python3 scripts/fetch_nse_only.py --through YYYY-MM-DD
python3 -m tradinglab.nse_paper --asof YYYY-MM-DD
cd commodities/gold-price-tracker && python3 -m unittest discover -s tests -v
```
