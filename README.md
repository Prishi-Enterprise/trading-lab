# Prishi Trading Lab

Research and paper-trade review under PrishiAI. Self-contained Python 3.9+ project with no dependencies, following the gold tracker's portable layout. Includes a capital planner, manual journal analyser, public daily-data downloader, frozen ETF screener/backtest and prospective paper recorder. No brokerage connection or real-order execution.

The authenticated [Trading Lab frontend](frontend/README.md) presents the frozen paper record, data-quality blocks, risk limits and historical evidence behind a separate email-code login. It has its own Supabase and Vercel projects so Festival membership and financial data remain isolated. The dashboard is deployed at [trading.prishi.in](https://trading.prishi.in).

Trading Lab has two main sections:

- **Stocks** — the frozen ETF breakout research and prospective paper record.
- **Commodities** — focused observation tools, beginning with the migrated [Ahmedabad Gold Price Tracker](commodities/gold-price-tracker/README.md).

The gold tracker retains its original Git history inside this repository. Its runtime state and notification credentials remain local and ignored.

**Current result:** [21 September research report](reports/2026-09-21-initial-research.md). The first strategy has weak historical results and neither ETF qualifies for a 22 September paper buy. No profitable strategy has been established.

**Authorised trial:** [22–28 September paper week](docs/PAPER-WEEK.md). Five weekday reviews at 17:30 IST are scheduled through the current Codex task, with a final review on 28 September. The host must be available. No real investment during this test; completion does not automatically enable it. A new eligible paper card includes entry ceiling, stop, quantity, cost assumptions and expiry. Quiet no-trade days remain in the record.

## Financial context — 21 September 2026

- Total Prishi organisation fund: **₹50,000**, separate from personal living expenses. No live trading allocation or brokerage deposit has been made by this project. The user uses **Groww**, normally holds equities for **months**, and is willing to adapt.
- Subscription: approximately **₹11,000/month**. September is paid; planning begins **October 2026**.
- Original half-cost objective: **₹5,500/month**, requiring **11% monthly** on ₹50,000 after trading costs and before personal income tax.
- Full bill: **₹11,000/month**, requiring **22% monthly** on the same capital on that basis.
- These are required returns, not forecasts or guaranteed income. Preserving the full ₹50,000 while withdrawing those amounts cannot be promised. Any withdrawal from principal fails the capital-preservation objective.
- With no income, other costs or trading gains/losses, ₹50,000 covers **four full ₹11,000 payments and leaves ₹6,000**. Beginning in October, those four payments cover October through January; February is not fully funded. This spends principal and does not meet the capital-preservation objective.
- User's maximum accepted trading loss is **₹5,000 total for the experiment**, not per month. No live trading allocation is set. `capital_ceiling` is a paper simulation assumption, not a live allocation of the organisation fund. The software records **zero actual trading income**.
- Faaya supplies irregular project income. Radhe Festival can demonstrate work to prospective small software/SaaS clients. Neither future sales nor unpaid invoices count as money available for bills. The gold tracker is a separate existing project, not evidence of a tradable strategy.

## Run locally

```sh
cd /Users/priya/PrishiAI/products/trading-lab
python3 -m tradinglab status
python3 -m tradinglab status --month 2026-10 --project-income 4000
python3 -m tradinglab review --journal examples/paper-trades.json --month 2026-09
python3 -m unittest discover -s tests -v
python3 scripts/fetch_market_data.py --asof 2026-09-21
python3 -m tradinglab.research --asof 2026-09-21
```

For a current-day prospective snapshot after the research report: `python3 -m tradinglab.paper --asof YYYY-MM-DD`. This refuses backdating and overwrite. The manual journal below uses the original ₹50,000 capital-ceiling scenario; the separate frozen research config uses ₹28,000 paper capital and ₹22,000 reserved outside the experiment. Neither is a live allocation.

The income argument is **net cash from project work available toward that month's bill**, entered as a scenario. It reduces both the half-cost and full-cost funding gaps independently; they are alternatives, not amounts to add together. The CLI does not store it or withdraw anything. All CLI values are INR. The default month is the configured first expense month, not the current date.

Example journal results are deliberately fictional: net **₹60**, simulated ending equity **₹50,060**, maximum drawdown between closed trades **₹220**. They are not recommendations, actual trades or evidence of an edge. Default October paper P&L is zero because all example trades close in September.

## Keep a paper journal

Create `state/paper-trades.json` as a JSON array using the example schema, then run `review --journal state/paper-trades.json --month YYYY-MM`. The ignored state directory is for local data only. Keep a backup; this initial version reads files and never writes a journal.

Each completed trade needs a unique id, `mode: paper`, `side: long`, symbol, ISO entry/exit dates, integer quantity, prices and explicit total round-trip costs. Costs include broker/exchange/statutory charges and estimated slippage if not already reflected in fill prices; they exclude personal income tax. Enter a realistic estimate even if the broker advertises zero brokerage. A zero input is accepted for arithmetic testing, not treated as a verified fee schedule.

This first model permits only sequential cash-funded positions. The next position must open after the prior position's exit date; same-day reuse and overlapping holdings need a later position-aware engine. It checks full entry notional plus costs against simulated cash. It reports lifetime journal equity and separately the chosen month's realised paper P&L. It does not model open positions, mark-to-market drawdown, corporate actions, taxes, deposits or withdrawals, or independently verify manual entries.

The reviewer flags any recorded net loss of ₹5,000 or more from starting paper capital, including entered trading costs. The flag persists if later trades recover and does not reset across months. It retains subsequent historical records for audit. This is an offline warning, not an order block. Actual risk assessment also needs unrealised losses and estimated exit costs. An unbreached journal is not proof of remaining risk capacity. Price gaps can exceed a planned stop; ₹5,000 is a decision threshold, not a guaranteed maximum outcome.

Broker charges and account-data requirements: [Groww notes](docs/GROWW.md).

## Layout

```text
AGENTS.md / CLAUDE.md    portable agent instructions
config.json             organisation ceiling, bill, user constraints
research-config.json    frozen paper strategy and research allocation
tradinglab/             planner, manual journal, daily-bar backtest, paper recorder
scripts/                public-data downloader
examples/               explicitly fictional records
tests/                  offline validation of financial calculations
docs/                   research protocol, broker notes and paper-week runbook
reports/                dated research conclusions including failed strategies
state/                  ignored market inputs, results and frozen paper snapshots
frontend/               private Next.js progress dashboard and Supabase schema
```

This project is maintained in the public `Prishi-Enterprise/trading-lab` repository with `main` as its only branch. Public source access does not bypass the dashboard login or Supabase row-level security.

The user will arrange a **fresh demat account** for this experiment. Existing holdings are explicitly outside scope and no holdings export is required to begin. The new account is not yet confirmed opened, funded or connected. Groww is the user's current broker; verify the new account's broker and charges when available.

The paper portfolio starts empty. Remaining live-setup details are the subscription reserve, actual amount allocated/deposited and execution availability. These do not block the authorised research. Do not assume the entire organisation fund is tradeable cash. Next: run the documented paper week, preserve every result and separately research improvements without changing the frozen baseline.
