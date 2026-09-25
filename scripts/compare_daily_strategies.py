"""Exploratory NSE ETF strategy screen. Never writes prospective paper signals."""

import argparse
import hashlib
import json
from datetime import date
from decimal import Decimal, ROUND_DOWN
from pathlib import Path

from tradinglab.nse_only import ARCHIVES, load_series
from tradinglab.research import ROOT, buy_hold, fees, money

D = Decimal
CAPITAL = D("28000")
POSITION_CAP = D("10000")
PLANNED_RISK = D("250")
SLIPPAGE = D("0.001")
STOP_FRACTION = D("0.05")
MAX_HOLD = 60
RULES = ("sma_cross_10_20", "sma_cross_10_30", "mean_reversion_20_10pct")


def average(bars, end, length):
    if end + 1 < length:
        return None
    return sum((b.close for b in bars[end-length+1:end+1]), D(0)) / length


def decision(bars, i, rule):
    """Decide after bar i closes; execution can only occur on bar i+1."""
    if rule in ("sma_cross_10_20", "sma_cross_10_30"):
        slow_length = 20 if rule.endswith("20") else 30
        if i < slow_length:
            return False, False
        fast, slow = average(bars, i, 10), average(bars, i, slow_length)
        prior_fast, prior_slow = average(bars, i-1, 10), average(bars, i-1, slow_length)
        return prior_fast <= prior_slow and fast > slow, prior_fast >= prior_slow and fast < slow
    if rule == "mean_reversion_20_10pct":
        mean = average(bars, i, 20)
        if mean is None:
            return False, False
        return bars[i].close <= mean * D("0.90"), bars[i].close >= mean
    raise ValueError(f"Unknown rule: {rule}")


def quantity(entry, cash):
    stop = money(entry * (1 - STOP_FRACTION))
    q = int((POSITION_CAP / entry).to_integral_value(rounding=ROUND_DOWN))
    while q:
        value = q * entry
        buy_fee = fees(value, "buy")
        stop_proceeds = q * money(stop * (1-SLIPPAGE))
        worst_planned_loss = value + buy_fee - stop_proceeds + fees(stop_proceeds, "sell")
        if value + buy_fee <= cash and worst_planned_loss <= PLANNED_RISK:
            return q, stop
        q -= 1
    return 0, stop


def simulate(bars, rule, start_index, end_index):
    minimum_start = 31 if rule == "sma_cross_10_30" else 21
    if start_index < minimum_start or end_index >= len(bars) or start_index > end_index:
        raise ValueError("Need warm-up history and a valid evaluation window")
    cash, position = CAPITAL, None
    trades, curve = [], []
    total_fees, peak, max_drawdown, max_adverse_drawdown, exposure = D(0), CAPITAL, D(0), D(0), 0
    halted = False

    def sell(raw_price, day, reason):
        nonlocal cash, position, total_fees
        price = money(raw_price * (1-SLIPPAGE))
        proceeds = price * position["quantity"]
        sell_fee = fees(proceeds, "sell", same_day=day == position["entry_day"])
        cash += proceeds - sell_fee
        total_fees += sell_fee
        trades.append({"entry_day": str(position["entry_day"]), "exit_day": str(day),
                       "quantity": position["quantity"], "reason": reason,
                       "net": str(money(proceeds-sell_fee-position["spent"]))})
        position = None

    for i in range(start_index, end_index + 1):
        bar = bars[i]
        enter, exit_signal = decision(bars, i-1, rule)
        exited = False
        if position:
            position["held"] += 1
            if halted:
                sell(bar.open, bar.day, "loss_limit_review")
            elif bar.open <= position["stop"]:
                sell(bar.open, bar.day, "gap_stop")
            elif exit_signal or position["held"] > MAX_HOLD:
                sell(bar.open, bar.day, "signal_or_time")
            elif bar.low <= position["stop"]:
                sell(position["stop"], bar.day, "stop")
            exited = position is None
        if not position and not exited and enter and not halted:
            entry = money(bar.open * (1+SLIPPAGE), up=True)
            q, stop = quantity(entry, cash)
            if q:
                value = q * entry
                buy_fee = fees(value, "buy")
                cash -= value + buy_fee
                total_fees += buy_fee
                position = {"quantity": q, "entry_day": bar.day, "stop": stop,
                            "spent": value + buy_fee, "held": 1}
                if bar.low <= stop:
                    sell(stop, bar.day, "entry_day_stop")
        equity = adverse_equity = cash
        if position:
            exposure += 1
            liquidation = money(bar.close * (1-SLIPPAGE)) * position["quantity"]
            equity += liquidation - fees(liquidation, "sell")
            adverse_liquidation = money(bar.low * (1-SLIPPAGE)) * position["quantity"]
            adverse_equity += adverse_liquidation - fees(adverse_liquidation, "sell")
        if CAPITAL-min(equity, adverse_equity) >= D("5000"):
            halted = True
        max_adverse_drawdown = max(max_adverse_drawdown, peak-adverse_equity)
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak-equity)
        curve.append({"date": str(bar.day), "equity": str(money(equity))})

    if position:
        # Measurement-only liquidation; does not imply a strategy exit order.
        sell(bars[end_index].close, bars[end_index].day, "evaluation_end")
        curve[-1]["equity"] = str(money(cash))
    return {"start": str(bars[start_index].day), "end": str(bars[end_index].day),
            "net": str(money(cash-CAPITAL)), "return_pct_on_28000": str(money((cash/CAPITAL-1)*100)),
            "closed_trades": len(trades), "wins": sum(D(t["net"]) > 0 for t in trades),
            "total_fees": str(money(total_fees)), "max_close_to_close_drawdown": str(money(max_drawdown)),
            "max_intraday_adverse_drawdown": str(money(max_adverse_drawdown)),
            "loss_limit_triggered": halted, "exposure_sessions": exposure,
            "trades": trades, "equity_curve": curve}


def main():
    parser = argparse.ArgumentParser(description="Retrospective, paper-only NSE ETF strategy screen")
    parser.add_argument("--asof", type=date.fromisoformat, default=date(2026, 9, 24))
    parser.add_argument("--archives", type=Path, default=ARCHIVES)
    parser.add_argument("--output", type=Path, default=ROOT / "state/strategy-screen/pilot.json")
    args = parser.parse_args()
    if args.asof >= date(2026, 9, 25):
        parser.error("This pilot is frozen to pretrial history through 24 September 2026")
    series, provenance = load_series(args.archives, args.asof)
    count = len(provenance)
    # The final 25% is a later chronological slice, with earlier history for indicators.
    split = count - count // 4
    evaluations = {}
    comparators = {}
    for symbol, bars in series.items():
        evaluations[symbol] = {
            rule: {"all": simulate(bars, rule, 31, count-1),
                   "later_slice": simulate(bars, rule, split, count-1)}
            for rule in RULES}
        comparators[symbol] = {
            name: {key: str(value) for key, value in buy_hold(
                bars, {"paper_capital": str(CAPITAL), "slippage_bps": "10"},
                bars[start].day, bars[-1].day, allocation=str(POSITION_CAP)).items()}
            for name, start in (("all", 31), ("later_slice", split))}
    report = {"purpose": "exploratory retrospective screen, not the active paper trial",
              "asof": str(args.asof), "sessions": count, "first_session": provenance[0]["date"],
              "later_slice_first_session": provenance[split]["date"],
              "source": "official NSE cash-market bhavcopy, two EQ ETFs",
              "source_sha256": hashlib.sha256("".join(p["sha256"] for p in provenance).encode()).hexdigest(),
              "rules": list(RULES), "assumptions": {"capital": str(CAPITAL),
              "position_cap": str(POSITION_CAP), "planned_stop_risk": str(PLANNED_RISK),
              "stop_fraction": str(STOP_FRACTION), "slippage_each_side": str(SLIPPAGE),
              "max_hold_sessions": MAX_HOLD, "fills": "next-session open; stop gap at actual open",
              "fees": "tradinglab.research.fees estimate"}, "evaluations": evaluations,
              "buy_hold_comparator": comparators}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"asof": report["asof"], "sessions": count,
                      "later_slice_first_session": report["later_slice_first_session"],
                      "buy_hold_comparator": {symbol: {name: values["net"] for name, values in cases.items()}
                                              for symbol, cases in comparators.items()},
                      "summary": {symbol: {rule: {name: {k: result[k] for k in
                              ("net", "closed_trades", "total_fees", "max_close_to_close_drawdown",
                               "max_intraday_adverse_drawdown", "loss_limit_triggered")}
                              for name, result in cases.items()} for rule, cases in values.items()}
                              for symbol, values in evaluations.items()}}, indent=2))


if __name__ == "__main__":
    main()
