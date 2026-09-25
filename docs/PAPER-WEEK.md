# Paper week: 22–28 September 2026

**Stopped 25 September 2026.** Yahoo/NSE data disagreement blocked prospective observations. The old heartbeat is paused and this runbook is retained for audit. Missing days must not be reconstructed as prospective decisions. See [the separate NSE-only trial](NSE-ONLY-PAPER-WEEK.md) for current work.

## Authority and purpose

The user authorised research, historical data/screeners, buy/sell timing and limit suggestions, with the user executing any eventual real orders. They explicitly require one week of dummy testing before actual investment. This version remains paper-only throughout. A completed week is an operational review milestone, not automatic approval or evidence of profitability. No brokerage credentials, orders, paid data or account opening are part of the trial.

Scheduled sessions: Tuesday 22, Wednesday 23, Thursday 24, Friday 25, Monday 28 September, subject to exchange changes. [NSE's 2026 cash-market holiday circular](https://nsearchives.nseindia.com/content/circulars/CMTR71775.pdf) lists no planned closure during these dates. Weekend sessions are not assumed. Record closing data after 16:00 IST and prepare the next session's paper decision at 17:30 IST. Today's 21 September snapshot seeds tomorrow's decision.

## Frozen version: etf-breakout-v1

Configuration is `research-config.json`; its hash is recorded in each paper snapshot. Parameter changes during the week require a new, separately named research version and trial directory; they must not replace this baseline. Document the reason before inspecting the changed strategy's next results. Fix software bugs with a record of affected results. Do not tune on five days of returns, increase risk to produce trades, or discard a losing variant.

### Budget assumptions — paper only

- Organisation fund: ₹50,000. Research scenario reserves ₹22,000 for two subscription payments and uses ₹28,000 as simulated trading cash. This split has not allocated or deposited real funds.
- At most **one open position** across the two correlated equity ETFs. No leverage, options, short selling, margin funding or averaging down.
- Maximum entry notional **₹10,000**; remaining paper cash stays uninvested.
- Planned stop loss including estimated round-trip charges and exit slippage: at most **₹250 per position**. The initial stop determines share quantity; do not choose a tight stop merely to buy more.
- User's cumulative loss threshold: **₹5,000 for the whole experiment**, including open-position losses and costs. It does not reset each month. Stop new signals at a breach and review the position; a gap can exceed this threshold.
- Subscription payments are outside trading P&L. This experiment does not manufacture monthly withdrawals or assume ₹5,500 income.

### Entry, cancellation and exits

Universe: NIFTYBEES and JUNIORBEES, chosen before backtesting as broad Indian equity ETFs. They remain equity-risk products and are correlated. No search over today's best-performing stocks or universe expansion during this baseline.

1. After a completed session, an ETF qualifies only if its close is above its 200-session simple average **and** above the highest high of the previous 20 sessions, excluding the signal session. Average approximate turnover over 20 sessions must exceed ₹1 crore. ATR is the simple mean of 14 true ranges, not Wilder-smoothed ATR.
2. Initial stop = signal close minus 2 × ATR. Maximum next-session entry price = signal close × 1.003, rounded down to ₹0.01. Quantity is the largest whole number meeting the ₹10,000 notional, ₹250 planned-risk and available-cash constraints, with costs included. No quantity means no trade.
3. When both qualify, select the larger percentage breakout over its prior high; ties use ticker order deterministically. One position only.
4. **Paper buy time:** next exchange session's opening print, simulated only after that session's OHLC is available. Buy only if the opening print is above the stop and the assumed fill (open + 0.10%) is no higher than the price cap. Otherwise cancel that day's paper entry; do not chase it or assume a later intraday fill. This is a daily-bar execution approximation, not a live opening-price guarantee.
5. **Paper stop:** on entry day or later, a low reaching the active stop assumes an exit at stop minus 0.10%. If a later session opens below the stop, use that lower opening price minus slippage. Entry-day stop costs conservatively include delivery charges plus the higher intraday ETF STT.
6. After each close, trail the stop upward only: max(existing stop, highest closing price since entry minus 2 × current ATR). The new stop applies **next session**, never retroactively to today's low.
7. If a close falls below the 200-session average or the position reaches 60 sessions, mark an exit for the next opening print. There is no fixed profit target in this trend-following baseline. No same-session re-entry after an exit.
8. Missing, stale or contradictory data means no new paper order. Paper fills are clearly simulated. If a user supplies an observed executable quote, preserve it separately; never replace the model fill without versioning the assumption.

## Daily workflow

From `/Users/priya/PrishiAI/products/trading-lab`, using today's completed exchange date:

```sh
python3 scripts/fetch_market_data.py --asof YYYY-MM-DD
python3 -m tradinglab.research --asof YYYY-MM-DD
python3 -m tradinglab.paper --asof YYYY-MM-DD
```

The downloader retrieves public Yahoo daily bars and NSE's official bhavcopy, and fetches a source-documented NSE repair for missing vendor bars. The research command checks the latest OHLC and volume against NSE before producing signals. Local networking may need the tool's standard network approval mechanism. A failed download/check means record the blocker, not an invented price or trade.

`state/paper-trial/snapshots/YYYY-MM-DD.json` freezes signals, strategy hash and input-price hash. Re-runs cannot overwrite that day's record. Forward replay uses only signals recorded before the next session; missing past snapshots block replay. It leaves positions open rather than artificially closing them at every daily review. Input corrections or configuration changes stop replay for review. The initial historical study liquidates at evaluation boundaries only for measurement; those exits must not be represented as live or forward strategy instructions.

For each new eligible candidate, provide a **PAPER ONLY** card with symbol, quote/source timestamp, signal reason, valid next session, entry ceiling, initial stop, quantity, notional, planned loss including charges, cancellation rules and exit rule. For an existing position, report the next active stop and any exit signal. When none qualifies, record a no-trade day without manufacturing an order. Do not send real orders.

The user asked for a week-long test, not repetitive status notifications. Scheduled reviews should stay quiet when nothing actionable changes and notify on new paper entry/exit decisions, risk breaches, data failures that prevent the trial, and the final review. Local scheduled runs depend on the Codex host being available; a missed run must not be backdated into a prospective signal.

## Review on 28 September

Operational note, 21 September: the original unzoned schedule fired at 17:30 UTC (23:00 IST), before the first trial session. The existing automation was corrected to 12:00 UTC (17:30 IST) on weekdays, with a fixed cutoff at the 28 September review. This is a timezone correction, not an extension of the experiment. The 21 September seed snapshot was checked against refreshed NSE-verified data and left unchanged; the pretrial run does not count as a trial session. Audit: `state/paper-trial/audits/2026-09-21-pretrial-check.json`.

Report every paper decision, simulated fill, actual observed quote if supplied, fees, open positions, realised/unrealised P&L, drawdown and rule violations. Retain open-position marks separately from realised cash; stop issuing new orders after the trial end. Explain whether there were enough trades to learn anything about execution. A zero-trade week is valid. Do not annualise a week's return, infer a stable win rate, promise subscription coverage or switch to live trading automatically.

The first historical study is weak and does not justify deployment. Keep the frozen baseline as a reproducibility/operations test. Further strategies require a written economic rationale, preserved failed variants, multiple market regimes and untouched evaluation data; week-long parameter fitting is not validation.
