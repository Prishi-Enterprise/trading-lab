# NSE-only paper experiment: 25 September–1 October 2026

This is a seven-calendar-day, paper-only data and execution experiment. The initial 25 September decision can be recorded only after that day's completed NSE bhavcopy becomes available, at or after 16:00 IST. The first possible simulated entry is the next NSE session, expected 28 September. Each later decision must be recorded on its actual completed session; missed days are not backdated. There is no recurring background schedule.

`research-config-nse-v2.json` freezes the same two ETF breakout rules and paper risk assumptions as the stopped v1. The sole intended experimental change is the input source: official NSE cash-market bhavcopy for every historical and prospective bar. Do not use Yahoo inputs or old trial snapshots in this experiment. The v1 config and records remain untouched.

Pretrial diagnostic on the downloaded NSE series through 24 September: the unchanged rules produced **zero closed trades and ₹0 simulated net P&L from 1 June–24 September 2026**. This is retrospective and does not count as a prospective result. A seven-day no-trade outcome is plausible; this run primarily tests data reliability and the paper workflow, not whether the strategy can cover subscriptions. Do not loosen rules during the run to force a trade.

## Data and daily record

From the repository root:

```sh
python3 scripts/fetch_nse_only.py --through 2026-09-24
# On 25 September after 16:00 IST, with the official archive available:
python3 scripts/fetch_nse_only.py --through 2026-09-25
python3 -m tradinglab.nse_paper --asof 2026-09-25
```

For later completed trial sessions, replace both dates with today's NSE date. The fetcher keeps first-seen official ZIP bytes under ignored `state/nse-only/archives/` and writes `state/nse-only/fetch-manifest.json` with missing weekday archives and request failures. The loader checks weekday gaps against the [2025 NSE cash-market holiday circular](https://nsearchives.nseindia.com/content/circulars/CMTR65587.pdf) and [2026 NSE equity holiday table](https://www.nseindia.com/resources/exchange-communication-holidays), and requires the [special Sunday session on 1 February 2026](https://nsearchives.nseindia.com/content/circulars/CMPT72389.pdf). An unexpected missing trading date blocks the run. It also requires both EQ ETF rows, matching dates, valid OHLC/volume, at least 200 shared sessions and the exact requested latest session. A large close-to-close jump blocks the run for possible corporate-action review. The paper recorder checks earlier frozen source hashes and signals, and writes once to ignored `state/nse-only/snapshots/`.

The frozen strategy's next-open fill, entry cap, stop, slippage, estimated fees, one-position limit and ₹5,000 total paper loss threshold remain as documented in [v1's rule section](PAPER-WEEK.md#frozen-version-etf-breakout-v1). A no-trade decision is a valid output. Paper fills are approximations, not quotes or real orders. Do not infer profitability from a seven-day record or use it to authorise live trading.

At the 1 October review, report each completed session, source gaps, decisions, simulated fills, costs, closed and open P&L, drawdown and rule violations. State plainly if the dataset or trade count is too small to evaluate the strategy. Keep Dhan API feasibility and any future broker-funded experiment separately versioned.
