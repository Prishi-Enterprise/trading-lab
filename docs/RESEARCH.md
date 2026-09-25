# Research protocol

Status: etf-breakout-v1 has been specified and tested on roughly ten years of public daily ETF prices, with a source-documented missing-day repair and latest-price NSE verification. Initial results are weak; no trading advantage is established. See [initial report](../reports/2026-09-21-initial-research.md) and [authorised paper-week runbook](PAPER-WEEK.md). The user requested buy/sell timing and limits for manual execution, with at least a week of dummy testing before any investment. No live trades are enabled.

## Before selecting a market

Confirmed: ₹50,000 is for the Prishi organisation, separate from personal living expenses; the user uses Groww, holds equities for months but can adapt, and accepts at most ₹5,000 total trading loss for the experiment. The user will arrange a fresh demat account; existing personal holdings are outside scope and must not be requested. Research begins with an empty paper portfolio without waiting for account opening. Confirm review time, subscription reserve, actual trading allocation and new account details before a live trial. The organisation fund is not permission to invest or lose that amount. Preserve the distinction between subscription runway and paper capital assumptions.

Interpret the loss threshold as net trading loss from experiment starting capital, including charges and unrealised losses, without a monthly reset. Subscription spending is separate and must never mask trading losses. A breached threshold means stop adding exposure and review remaining positions promptly; this project cannot execute that action. Gaps and poor liquidity can exceed a stop, so the threshold is not a guaranteed maximum loss. The current closed-trade journal only reports one part of this risk.

Potential starting research area, not an approved recommendation: unleveraged daily-bar swing trading in liquid Indian equities or ETFs. The instrument choice, data licence, historical coverage, corporate-action handling and actual fee schedule must be checked before implementation. The gold tracker reads indicative retail/MCX snapshots; these must not be substituted for executable quotes or a clean historical dataset.

## Evidence workflow

1. Write one hypothesis and freeze the rules: instrument universe, signal time, execution time, entry/exit, position size, cost assumptions and conditions for no trade. Record all rejected variants to expose multiple testing.
2. Acquire timestamped data from a permitted source. Preserve raw inputs and their provenance; validate missing bars, exchange sessions, corporate actions, and changes in index membership. No fabricated or forward-filled prices treated as tradable observations.
3. Backtest without future information. A signal requiring today's closing price cannot assume a fill at that same closing price. Model spreads, statutory charges, brokerage, slippage, overnight gaps and unfilled orders. Stops are not guaranteed execution prices.
4. Use chronological development and untouched evaluation periods covering differing conditions. Compare to a relevant passive benchmark and cash. Report losses, largest drawdown including open positions, turnover, exposure, trade count, cost sensitivity, and uncertainty. A minimum trade count or positive mean alone is not proof.
5. Record prospective paper signals before outcomes are known. Keep losing signals and no-trade days. Review disagreement between historical assumptions and observed executable prices. Paper fills can be optimistic.
6. Only consider discussing a small live trial once suitability and evidence have been reviewed. A paper result never automatically enables orders. Define an affordable loss limit first; never increase position size to catch up to a bill.

Do not promise monthly income or capital preservation. Subscription expenses start in October 2026; show ₹5,500 and ₹11,000 funding scenarios separately, and keep project receipts distinct from paper results. The original five-session paper monitor was stopped on 25 September and its heartbeat deleted. The separate NSE-only week has finite local checks through 1 October; neither experiment connects a broker, places orders or purchases data. Preserve each frozen baseline; version later hypotheses independently. See the [open strategy screen](../reports/2026-09-25-open-strategy-screen.md) for exploratory comparisons.

## Source context

[SEBI, 24 July 2024: individual intraday equity-cash traders](https://www.sebi.gov.in/media-and-notifications/press-releases/jul-2024/sebi-study-finds-that-7-out-of-10-individual-intraday-traders-in-equity-cash-segment-make-losses_84948.html) reports seven out of ten made losses. This is evidence about the studied intraday population, not a probability estimate for a future strategy, a swing-trading backtest, or a reason to claim AI chart analysis will succeed.
