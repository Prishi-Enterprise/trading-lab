# NSE-only paper experiment: 25 September–1 October 2026

This is a seven-calendar-day, paper-only data and execution experiment. The initial 25 September decision can be recorded only after that day's completed NSE bhavcopy becomes available, at or after 16:00 IST. The first possible simulated entry is the next NSE session, expected 28 September. Each later decision must be recorded on its actual completed session; missed days are not backdated.

Supabase Cron invokes the `nse-paper-week` Edge Function at **18:30 and 20:30 IST** on 25, 28, 29, 30 September and 1 October. The second check retries if the NSE archive was late; a verified snapshot cannot be overwritten. The function refuses to decide before 16:00 IST or outside those dates. The final 20:30 check retires both cron jobs. The replaced Mac LaunchAgent `in.prishi.tradinglab.nse-paper-week-2026` was unloaded and its plist removed after a successful authenticated cloud smoke check on 25 September. A missed day cannot be filled retrospectively. A blocked check appears on the experiment detail page and requires source review. No Codex notification or live-trading service is involved.

`research-config-nse-v2.json` freezes the same two ETF breakout rules and paper risk assumptions as the stopped v1. The sole intended experimental change is the input source: official NSE cash-market bhavcopy for every historical and prospective bar. Do not use Yahoo inputs or old trial snapshots in this experiment. The v1 config and records remain untouched.

Pretrial diagnostic on the downloaded NSE series through 24 September: the unchanged rules produced **zero closed trades and ₹0 simulated net P&L from 1 June–24 September 2026**. This is retrospective and does not count as a prospective result. A seven-day no-trade outcome is plausible; this run primarily tests data reliability and the paper workflow, not whether the strategy can cover subscriptions. Do not loosen rules during the run to force a trade.

## Data and daily record

The cloud worker uses 284 validated official NSE sessions through 24 September, seeded as 568 ETF bars in a service-role-only table. It fetches each new official ZIP directly, validates the two ETF rows, keeps the first source hash, checks the frozen historical prefix and previous paper signal, and writes the day's record to `paper_updates` under `etf-breakout-nse-v2`. The browser dashboard reads this record through member-only RLS and refreshes once per minute. The stopped v1 data remains under its own experiment ID.

For independent local verification, from the repository root:

```sh
python3 scripts/fetch_nse_only.py --through 2026-09-24
# On a completed trial day after 16:00 IST, with the official archive available:
python3 scripts/fetch_nse_only.py --through 2026-09-25
# Inspect the new ZIP and compare the cloud snapshot; do not create a second
# authoritative prospective decision for a day already frozen in Supabase.
```

For later completed trial sessions, replace the date with today's NSE date. The fetcher keeps first-seen official ZIP bytes under ignored `state/nse-only/archives/` and writes `state/nse-only/fetch-manifest.json` with missing weekday archives and request failures. Both implementations check weekday gaps against the [2025 NSE cash-market holiday circular](https://nsearchives.nseindia.com/content/circulars/CMTR65587.pdf) and [2026 NSE equity holiday table](https://www.nseindia.com/resources/exchange-communication-holidays), and require the [special Sunday session on 1 February 2026](https://nsearchives.nseindia.com/content/circulars/CMPT72389.pdf). Unexpected gaps, invalid OHLC/volume, a missing ETF row or a possible corporate-action jump block signals. The local recorder remains available for code-level comparison, but the Supabase record is the prospective trial ledger.

The frozen strategy's next-open fill, entry cap, stop, slippage, estimated fees, one-position limit and ₹5,000 total paper loss threshold remain as documented in [v1's rule section](PAPER-WEEK.md#frozen-version-etf-breakout-v1). A no-trade decision is a valid output. Paper fills are approximations, not quotes or real orders. Do not infer profitability from a seven-day record or use it to authorise live trading.

At the 1 October review, report each completed session, source gaps, decisions, simulated fills, costs, closed and open P&L, drawdown and rule violations. State plainly if the dataset or trade count is too small to evaluate the strategy. Keep Dhan API feasibility and any future broker-funded experiment separately versioned.
