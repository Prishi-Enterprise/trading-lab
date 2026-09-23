# Initial trading research — 21 September 2026

**Decision: no paper buy for 22 September under etf-breakout-v1. No live buy/sell recommendation.** The first tested strategy does not support the subscription-income objective. It remains an operational paper-test baseline, not a deployable strategy.

## Latest screen

NSE end-of-day prices for 21 September, verified against the downloaded vendor series:

| Instrument | Close | 200-session average | Prior 20-session high | Decision |
|---|---:|---:|---:|---|
| NIFTYBEES | ₹267.76 | ₹277.22 | ₹283.94 | No trade: below trend average and breakout level |
| JUNIORBEES | ₹782.31 | ₹754.99 | ₹821.90 | No trade: below breakout level |

These are completed-session observations, not executable quotes. The highs are reference levels, **not standing buy orders**. A future qualifying close would require newly calculated entry/stop/quantity values; the levels expire as the rolling window changes. No active entry limit or stop is issued while the screen fails.

Latest primary input: [NSE bhavcopy, 21 September 2026](https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20260921_F_0000.csv.zip). The fund sponsor describes [NIFTYBEES as tracking Nifty 50](https://etf.nipponindiaim.com/Funds/details/14) and [JUNIORBEES as tracking Nifty Next 50](https://mf.nipponindiaim.com/FundsAndPerformance/Pages/NipponIndia-ETF-Nifty-Next-50-Junior-BeES.aspx).

## Frozen historical test

Hypothetical trading pot ₹28,000, at most one ₹10,000 position, planned risk ₹250 per trade, stop at 2 × 14-session ATR. A close must break above the prior 20-session high and 200-session average; entry is next open subject to a +0.30% price cap. Trailing stop and 60-session maximum hold. All parameters were selected before inspecting strategy results. See [full execution rules](../docs/PAPER-WEEK.md).

Results include estimated standard Groww/NSE equity-ETF costs and 0.10% slippage per fill, before personal income tax. Each evaluation starts afresh with ₹28,000 and closes any remaining position at the end for measurement. These intervals are **not** three simultaneous accounts or one compounded equity curve.

| Evaluation window | Trades | Net P&L | Return on ₹28,000 | Max daily liquidation drawdown | P&L at 0.25% slippage |
|---|---:|---:|---:|---:|---:|
| 2018–2022 | 15 | −₹2,249.29 | −8.03% | ₹2,261.09 | −₹2,201.68 |
| 2023–2025 reserved evaluation | 10 | +₹482.91 | +1.72% | ₹1,079.86 | +₹546.25 |
| 2026 through 21 September | 1 | −₹70.44 | −0.25% | ₹92.68 | −₹79.48 |

**No calendar month in these evaluations reached ₹5,500 net.** The 2023–2025 profit is for the entire three-year window, not per month. That interval's average monthly marked P&L was approximately ₹13.41, with only ten trades and substantial uncertainty. The slippage stress can occasionally improve aggregate P&L because the fixed price cap skips different trades and risk-based sizing changes; it is a different execution scenario, not a claim that higher costs help trading.

For context, buying and holding NIFTYBEES with a ₹10,000 initial allocation and the rest of the ₹28,000 idle produced estimated net P&L of +₹8,060.71, +₹4,541.85 and −₹1,004.82 respectively. The benchmark is not risk-matched: market exposure, stops and holding duration differ. Cash is modelled at zero return. These comparisons do not constitute a recommendation to buy and hold.

## Data and cost limitations

- Public Yahoo Finance chart data: approximately ten years, 2,475 dated vendor entries per instrument. Inputs and source URLs are saved locally with SHA-256 hashes. One all-null day, 24 October 2025, was repaired from [NSE's report for that exact day](https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20251024_F_0000.csv.zip), with provenance retained. No bars were silently dropped or forward-filled.
- Latest open, high, low, close and volume match NSE. The entire ten-year vendor history has not been independently audited. Vendor-adjusted historical prices and absence of reported corporate actions are a limitation, not proof that no corporate actions occurred. This is a present-day execution-cost simulation over the vendor series, not an exact reconstruction of historical trades/unit denominations.
- Current charges are applied across all historical periods to ask what the rule might cost under today's assumptions; these are not historical broker charges. Standard-account pricing is assumed and must be checked for the new account. ETF STT differs from individual-stock STT: [Groww's ETF-specific schedule](https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-pricing/what-is-stt). Other charges follow [Groww pricing](https://groww.in/pricing). The model uses the higher published DP tier and conservatively retains delivery charges for same-day stops while applying the higher intraday STT. Brokerage rounding and contract-note aggregation may differ. Fund expenses are embedded in traded prices, not charged a second time.
- Daily OHLC does not establish bid/ask spreads, executable opening fills, intraday sequence or stop liquidity. Gap exits can exceed the planned risk. Reported maximum drawdown measures daily liquidation equity; it is not a tick-level worst drawdown or a future loss bound.
- The two ETFs were chosen for broad exposure and continuity; this does not eliminate fund-selection/survivorship bias. No current constituent stock basket was backfilled. The reserved window is historical research, not genuine prospective performance. Low trade counts make conclusions about an edge unreliable.
- No screenshots, observed live fills, real trades, paid API or broker connection have been used. The results are simulations. The subscription reserve and business revenue are outside these results.

## Paper week

From 22–28 September, preserve the baseline and test daily data validation, prospective decisions, simulated fills, accounting and risk controls. Real investment remains off for the whole week. Do not tune the baseline retrospectively; log separately versioned ideas and retain failures. Completion of five sessions does not justify live deployment by itself.

The initial 21 September paper snapshot contains ₹28,000 simulated cash, no positions and no eligible orders. See [paper-week operating instructions](../docs/PAPER-WEEK.md). Research code has 36 passing offline tests covering next-session execution, future-data isolation, fees, gaps, sizing, loss limits and prospective-signal enforcement.

## Reproduce

```sh
cd /Users/priya/PrishiAI/trading-lab
python3 scripts/fetch_market_data.py --asof 2026-09-21
python3 -m tradinglab.research --asof 2026-09-21
python3 -m unittest discover -s tests -v
```

The current-date paper command refuses backdating. Historical results and complete trade/equity records are in `state/research-results.json`; that runtime file can be regenerated, while prospective snapshots are retained separately and cannot be overwritten by rerunning the recorder. Frozen report figures above correspond to the original 21 September inputs; vendor corrections may change a later historical rerun and must be disclosed.
