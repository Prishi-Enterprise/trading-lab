# Open strategy screen on official NSE ETF bars — 25 September 2026

This is a **retrospective research screen**, separate from the frozen 25 September–1 October prospective NSE-only paper experiment. It is not a trading recommendation. No broker account, order API, paid data or live order was used.

## Sources and fixed hypotheses

- [Groww's strategy overview](https://groww.in/blog/algorithmic-trading-strategies) identifies trend following and mean reversion as plausible daily-bar families, but does not give a complete executable specification. Its arbitrage, index-rebalancing and VWAP/TWAP examples need simultaneous markets, event data or intraday executions that our daily NSE ETF bars cannot validate. Its machine-learning category needs much more data and a separate validation design.
- [Backtesting.py's 10/20 SMA crossover example](https://github.com/kernc/backtesting.py/blob/ca2e2611621e472542ba90f7243a1fa06a7d7108/README.md) supplies fixed moving-average lengths. Its example can sell short; this screen changes the reverse signal to **exit a long** because our scope is unleveraged long-only ETFs.
- [Backtrader's 10/30 SMA signal example](https://github.com/mementum/backtrader/blob/b853d7c90b6721476eb5a5ea3135224e33db1f14/samples/strategy-selection/strategy-selection.py) supplies a second fixed crossover pair, also evaluated long-only.
- **20-day mean reversion at 10% below average** is our explicit exploratory interpretation of Groww's illustration of selling at 10% above a 20-day average and buying far below it. Groww does not specify this long entry threshold or the exit threshold. We defined them before running this screen: buy at or below 90% of the 20-day average and exit at or above the average.

The upstream projects are [AGPL-3.0](https://github.com/kernc/backtesting.py/blob/ca2e2611621e472542ba90f7243a1fa06a7d7108/LICENSE.md) and [GPL-3.0](https://github.com/mementum/backtrader/blob/b853d7c90b6721476eb5a5ea3135224e33db1f14/LICENSE). This repository contains an independent, standard-library implementation of these generic rule ideas; it does not copy or distribute either framework's code.

## Data and measurement

The input is **284 validated, first-seen official NSE cash-market bhavcopy ZIPs**, 1 August 2025–24 September 2026, for `NIFTYBEES` and `JUNIORBEES` EQ rows. The existing NSE loader rejects missing expected sessions, duplicate ETF rows, invalid prices, large possible corporate-action jumps, and a missing special Sunday session. Raw ZIPs, their hashes, every simulated trade and the output JSON remain in ignored local `state/`. Run `python3 -m scripts.compare_daily_strategies` from this repository to reproduce the screen.

All candidates use the same **17 September 2025–24 September 2026** evaluation window after indicator warm-up. The later chronological slice begins **16 June 2026**. It is a useful time breakdown, **not an untouched out-of-sample claim**: we inspected the full results in the same research pass. We have no prior multi-year NSE regime sample or independent reviewer yet.

Signals use only the completed previous close; fills occur at the next session's open. Assumptions: ₹28,000 paper starting capital, one position up to ₹10,000, at most ₹250 planned stop risk including estimated costs, 5% fixed stop, 60-session holding cap, 10 basis points slippage on each side, and the existing estimated Groww/NSE ETF fee function. [Groww's published pricing](https://groww.in/pricing) was rechecked on 25 September; the code's ETF-specific tax and fee model remains an estimate, and actual account terms or contract notes could differ. A gap can exceed the planned stop risk. A ₹5,000 paper loss threshold halts new exposure and triggers next-open review exit; it did not fire in this sample. The passive comparison buys up to ₹10,000 of one ETF at the window's first open and values it at the last close, leaving remaining paper cash idle. Each ETF is evaluated **separately**, so rows cannot be added into a combined portfolio result. The stop, holding cap and sizing are our common screen assumptions, not claims about the upstream authors' rules.

## Results, rupees after estimated fees and slippage

| ETF | Rule | Full window | Trades | Later slice | Later trades | Full-window adverse drawdown |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| NIFTYBEES | 10/20 SMA | -₹363.49 | 7 | -₹185.45 | 2 | ₹593.43 |
| NIFTYBEES | 10/30 SMA | -₹344.18 | 5 | -₹7.28 | 1 | ₹583.16 |
| NIFTYBEES | 20-day, -10% mean reversion | ₹0.00 | 0 | ₹0.00 | 0 | ₹0.00 |
| JUNIORBEES | 10/20 SMA | -₹555.29 | 8 | +₹64.38 | 2 | ₹831.93 |
| JUNIORBEES | 10/30 SMA | -₹536.95 | 5 | +₹44.58 | 1 | ₹756.80 |
| JUNIORBEES | 20-day, -10% mean reversion | ₹0.00 | 0 | ₹0.00 | 0 | ₹0.00 |
| NIFTYBEES | capped buy and hold | -₹806.79 | 1 purchase | -₹371.61 | 1 purchase | — |
| JUNIORBEES | capped buy and hold | +₹323.53 | 1 purchase | -₹132.88 | 1 purchase | — |

All crossover variants lost money over the full window. Adding their estimated fees back still leaves all four full-window outcomes negative; the finding is not caused by the particular fee estimate alone. The small positive JUNIORBEES later-slice outcomes contain just one or two trades, so they provide no evidence of repeatable edge. The mean-reversion threshold never fired; ₹0 is an inactivity result, not a successful strategy. Buy and hold is a reference with different exposure and risk. None of these results demonstrates the ability to offset the ₹5,500 partial or ₹11,000 full monthly subscription bill.

## What to do next

1. Keep this screen and the live NSE-only paper trial separate. Do not modify the trial's frozen v2 rules or inject retrospective crossover signals into its record.
2. Extend official NSE history across several market regimes, verify ETF corporate actions and distributions, and independently audit the fill, cost and drawdown calculations before treating any candidate as validated.
3. Research a broader **predeclared** set of distinct daily-bar hypotheses and include failed candidates. Avoid threshold tuning on this short sample. Only then choose a new, separately versioned prospective paper experiment with a measurable trade-count/data-quality goal.

The screen code is [`scripts/compare_daily_strategies.py`](../scripts/compare_daily_strategies.py); its chronology and sizing tests are [`tests/test_strategy_screen.py`](../tests/test_strategy_screen.py). The local pilot JSON records source hashes, rules, individual trades and equity curves under `state/strategy-screen/pilot.json`.
