"""Daily-bar ETF paper research. No order routing or account integration."""

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, ROUND_DOWN, ROUND_UP, ROUND_HALF_UP
from pathlib import Path
from zoneinfo import ZoneInfo

D = Decimal
ZERO = D(0)
CENT = D("0.01")
IST = ZoneInfo("Asia/Kolkata")
ROOT = Path(__file__).resolve().parent.parent


def money(value, up=False):
    return value.quantize(CENT, rounding=ROUND_UP if up else ROUND_HALF_UP)


@dataclass(frozen=True)
class Bar:
    day: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


def load_bars(path, asof):
    raw = path.read_bytes()
    document = json.loads(raw)
    result = document["payload"]["chart"]["result"][0]
    if result["meta"]["currency"] != "INR":
        raise ValueError("Research requires INR quotes")
    quote = result["indicators"]["quote"][0]
    adjusted = result["indicators"].get("adjclose", [{}])[0].get("adjclose", [])
    bars, repairs = [], []
    for i, stamp in enumerate(result["timestamp"]):
        day = datetime.fromtimestamp(stamp, IST).date()
        if day > asof:
            continue
        raw_values = [quote[key][i] for key in ("open", "high", "low", "close")]
        volume = quote["volume"][i]
        if any(value is None for value in raw_values) or volume is None:
            repair_path = path.parent/f"nse-{day}.json"
            if not repair_path.exists():
                raise ValueError(f"Missing price on {day}; fetch NSE bhavcopy before backtesting")
            repair = json.loads(repair_path.read_text())
            matches = [r for r in repair["rows"] if r["TckrSymb"] == result["meta"]["symbol"].removesuffix(".NS") and r["TradDt"] == str(day) and r["SctySrs"] == "EQ"]
            if len(matches) != 1:
                raise ValueError(f"No unique matching NSE record for {day}")
            row = matches[0]
            raw_values = [row[key] for key in ("OpnPric", "HghPric", "LwPric", "ClsPric")]
            volume = int(row["TtlTradgVol"])
            repairs.append({"date": str(day), "source_url": repair["source_url"],
                            "sha256": hashlib.sha256(repair_path.read_bytes()).hexdigest()})
        values = [D(str(value)) for value in raw_values]
        if any(not x.is_finite() or x <= 0 for x in values):
            raise ValueError(f"Invalid price on {day}; do not silently drop a bar")
        opening, high, low, close = values
        if low > min(opening, close) or high < max(opening, close) or low > high:
            raise ValueError(f"Inconsistent OHLC on {day}")
        if type(volume) is not int or volume < 0:
            raise ValueError(f"Invalid volume on {day}")
        if bars and day <= bars[-1].day:
            raise ValueError("Duplicate or unordered market dates")
        # Refuse unmodelled distributions rather than mixing adjusted close and raw OHLC.
        if adjusted and adjusted[i] is not None and abs(D(str(adjusted[i])) - close) > CENT:
            raise ValueError(f"Unmodelled adjusted/raw close difference on {day}")
        bars.append(Bar(day, opening, high, low, close, volume))
    events = result.get("events", {})
    if events:
        raise ValueError("Corporate actions require explicit handling before this backtest")
    if not bars:
        raise ValueError("No prices on or before as-of date")
    return bars, {"source_url": document["source_url"], "sha256": hashlib.sha256(raw).hexdigest(),
                  "fetched_at_utc": document["fetched_at_utc"], "rows": len(bars),
                  "first_day": str(bars[0].day), "last_day": str(bars[-1].day), "repairs": repairs}


def fees(value, side, same_day=False):
    """Approximate current standard Groww/NSE equity ETF costs, not a contract note.

    Delivery-cost assumptions throughout; same-day exits get higher intraday STT
    but retain delivery stamp/DP costs conservatively. Higher DP tier is used.
    """
    if value <= 0 or side not in ("buy", "sell"):
        raise ValueError("Positive notional and buy/sell side required")
    brokerage = min(value * D("0.025"), max(D(5), min(D(20), value * D("0.001"))))
    exchange = value * D("0.0000297")
    sebi = value * D("0.000001")
    ipft = value * D("0.000001")
    dp = D(20) if side == "sell" else ZERO
    gst = (brokerage + exchange + sebi + ipft + dp) * D("0.18")
    stamp = value * D("0.00015") if side == "buy" else ZERO
    stt = value * (D("0.00025") if same_day else D("0.00001")) if side == "sell" else ZERO
    return money(brokerage + exchange + sebi + ipft + dp + gst + stamp + stt, up=True)


def indicators(bars, i, cfg):
    trend, lookback, length = cfg["trend_sessions"], cfg["breakout_sessions"], cfg["atr_sessions"]
    if i < max(trend - 1, lookback, length):
        return None
    sma = sum(b.close for b in bars[i-trend+1:i+1]) / trend
    high = max(b.high for b in bars[i-lookback:i])
    tr = [max(bars[j].high - bars[j].low, abs(bars[j].high - bars[j-1].close),
              abs(bars[j].low - bars[j-1].close)) for j in range(i-length+1, i+1)]
    atr = sum(tr) / length  # Simple-average ATR, explicitly not Wilder smoothing.
    turnover = sum(b.close * b.volume for b in bars[i-lookback+1:i+1]) / lookback
    return {"sma": sma, "previous_high": high, "atr": atr, "average_turnover": turnover}


def size_plan(cap, stop, cash, cfg):
    if stop <= 0 or stop >= cap:
        return 0
    budget = min(cash, D(cfg["max_position_value"]))
    qty = int(budget // cap)
    slip = D(cfg["slippage_bps"]) / 10000
    stop_fill = money(stop * (1-slip))
    while qty > 0:
        value = qty * cap
        planned_loss = qty * (cap-stop_fill) + fees(value, "buy") + fees(qty*stop_fill, "sell")
        if value + fees(value, "buy") <= cash and planned_loss <= D(cfg["planned_risk_per_trade"]):
            return qty
        qty -= 1
    return 0


def candidate(bars, i, cfg, cash):
    ind = indicators(bars, i, cfg)
    if not ind:
        return None
    bar = bars[i]
    reasons = []
    if bar.close <= ind["sma"]:
        reasons.append("close_not_above_200_session_average")
    if bar.close <= ind["previous_high"]:
        reasons.append("no_close_above_previous_20_session_high")
    if ind["average_turnover"] < D(cfg["minimum_average_turnover"]):
        reasons.append("insufficient_average_turnover")
    stop = money(bar.close - D(cfg["stop_atr_multiple"]) * ind["atr"])
    cap = (bar.close * (1 + D(cfg["entry_cap_bps"])/10000)).quantize(CENT, rounding=ROUND_DOWN)
    qty = size_plan(cap, stop, cash, cfg)
    if not qty:
        reasons.append("no_size_within_cash_and_risk_limits")
    return {"signal_day": str(bar.day), "close": money(bar.close), **ind,
            "eligible": not reasons, "reasons": reasons, "entry_cap": cap,
            "initial_stop": stop, "quantity": qty,
            "breakout_strength": bar.close/ind["previous_high"]-1}


def run_backtest(series, cfg, start, end, liquidate_end=True, frozen_signals=None):
    symbols = sorted(series)
    calendar = [b.day for b in series[symbols[0]]]
    if any([b.day for b in series[s]] != calendar for s in symbols):
        raise ValueError("Instrument calendars differ; investigate missing bars")
    indices = [i for i, day in enumerate(calendar) if start <= day <= end]
    if not indices:
        raise ValueError("No sessions in backtest interval")
    cash = initial = D(cfg["paper_capital"])
    loss_limit = D(cfg["total_loss_limit"])
    slip = D(cfg["slippage_bps"])/10000
    position = None
    trades, curve = [], []
    halted = False
    peak = initial
    max_dd = ZERO
    max_adverse_dd = ZERO
    total_fees = ZERO
    exposed_days = 0

    def close_position(price, day, reason):
        nonlocal position, cash, total_fees
        price = money(price * (1-slip))
        value = price * position["quantity"]
        exit_fee = fees(value, "sell", same_day=day == position["entry_day"])
        cash += value - exit_fee
        total_fees += exit_fee
        trades.append({"symbol": position["symbol"], "signal_day": position["signal_day"],
                       "entry_day": str(position["entry_day"]), "exit_day": str(day),
                       "entry_price": position["entry_price"], "exit_price": price,
                       "quantity": position["quantity"], "reason": reason,
                       "holding_sessions": position["sessions"],
                       "fees": position["entry_fee"] + exit_fee,
                       "net": value-exit_fee-position["entry_value"]-position["entry_fee"]})
        position = None

    for i in indices:
        day = calendar[i]
        had_position = position is not None
        exited = False
        if position:
            bar = series[position["symbol"]][i]
            position["sessions"] += 1
            if bar.open <= position["stop"]:
                close_position(bar.open, day, "gap_below_stop")
            elif position["exit_next_open"]:
                close_position(bar.open, day, "trend_or_time_exit")
            elif bar.low <= position["stop"]:
                close_position(position["stop"], day, "stop")
            exited = position is None

        if not position and not exited and not halted and i > 0:
            candidates = []
            for symbol in symbols:
                if frozen_signals is None:
                    plan = candidate(series[symbol], i-1, cfg, cash)
                else:
                    signal_day = str(calendar[i-1])
                    if signal_day not in frozen_signals:
                        raise ValueError(f"Missing pre-recorded decision for {signal_day}; do not invent a past paper signal")
                    plan = dict(frozen_signals[signal_day][symbol])
                    for key in ("breakout_strength", "entry_cap", "initial_stop"):
                        plan[key] = D(str(plan[key]))
                    # Frozen quantity can only decrease if paper cash is insufficient.
                    plan["quantity"] = min(plan["quantity"], size_plan(plan["entry_cap"], plan["initial_stop"], cash, cfg))
                    plan["eligible"] = plan["eligible"] and plan["quantity"] > 0
                if plan and plan["eligible"]:
                    candidates.append((plan["breakout_strength"], symbol, plan))
            if candidates:
                _, symbol, plan = max(candidates, key=lambda x: (x[0], x[1]))
                bar = series[symbol][i]
                fill = money(bar.open * (1+slip), up=True)
                # One-session order; no chasing a gap and no assumed later intraday touch.
                if plan["initial_stop"] < bar.open and fill <= plan["entry_cap"]:
                    qty = plan["quantity"]
                    value = qty * fill
                    entry_fee = fees(value, "buy")
                    cash -= value + entry_fee
                    total_fees += entry_fee
                    position = {"symbol": symbol, "quantity": qty, "entry_price": fill,
                                "entry_value": value, "entry_fee": entry_fee,
                                "entry_day": day, "signal_day": plan["signal_day"],
                                "stop": plan["initial_stop"], "highest_close": fill,
                                "exit_next_open": False, "sessions": 1}
                    had_position = True
                    if bar.low <= position["stop"]:
                        close_position(position["stop"], day, "entry_day_stop")

        # Liquidation equity includes sell costs/slippage, even for open positions.
        equity = cash
        adverse_equity = cash
        if position:
            bar = series[position["symbol"]][i]
            value = money(bar.close * (1-slip)) * position["quantity"]
            equity += value - fees(value, "sell")
            low_value = money(bar.low * (1-slip)) * position["quantity"]
            adverse_equity += low_value - fees(low_value, "sell")
            if initial - adverse_equity >= loss_limit:
                halted = True
                position["exit_next_open"] = True
            ind = indicators(series[position["symbol"]], i, cfg)
            position["highest_close"] = max(position["highest_close"], bar.close)
            if ind:
                # Today's close-derived stop becomes active only on the next session.
                position["stop"] = max(position["stop"], money(position["highest_close"] - D(cfg["stop_atr_multiple"])*ind["atr"]))
                position["exit_next_open"] |= bar.close < ind["sma"] or position["sessions"] >= cfg["max_holding_sessions"]
        if initial - equity >= loss_limit:
            halted = True
            if position:
                position["exit_next_open"] = True
        max_adverse_dd = max(max_adverse_dd, peak-adverse_equity)
        peak = max(peak, equity)
        max_dd = max(max_dd, peak-equity)
        exposed_days += had_position
        curve.append({"date": str(day), "equity": money(equity), "cash": money(cash)})

    if position and liquidate_end:
        # Final liquidation is for measurement only; it is not a strategy sell signal.
        close_position(series[position["symbol"]][indices[-1]].close, calendar[indices[-1]], "evaluation_end")
        curve[-1]["equity"] = money(cash)
        curve[-1]["cash"] = money(cash)
    monthly = {}
    previous = initial
    for point in curve:
        key = point["date"][:7]
        monthly[key] = monthly.get(key, ZERO) + point["equity"]-previous
        previous = point["equity"]
    final_equity = curve[-1]["equity"]
    years = D((calendar[indices[-1]]-calendar[indices[0]]).days)/D("365.25")
    return {"start": str(calendar[indices[0]]), "end": str(calendar[indices[-1]]),
            "starting_capital": initial, "ending_equity": money(final_equity), "net": money(final_equity-initial),
            "cash": money(cash), "open_position": position,
            "return_percent": (final_equity/initial-1)*100,
            "annualised_return_percent": ((float(final_equity/initial)**(1/float(years)))-1)*100 if years > 0 and final_equity > 0 else None,
            "closed_trades": len(trades), "wins": sum(t["net"] > 0 for t in trades),
            "total_fees": total_fees, "max_daily_liquidation_drawdown": money(max_dd),
            "adverse_bar_drawdown_vs_prior_close_peak": money(max_adverse_dd),
            "halted_at_loss_limit": halted,
            "market_exposure_percent": D(exposed_days)/len(curve)*100,
            "average_monthly_pnl": sum(monthly.values())/len(monthly),
            "months_at_least_5500": sum(v >= 5500 for v in monthly.values()),
            "month_count": len(monthly), "monthly_pnl": monthly, "trades": trades, "curve": curve}


def buy_hold(bars, cfg, start, end, allocation=None):
    window = [b for b in bars if start <= b.day <= end]
    cash = D(cfg["paper_capital"])
    slip = D(cfg["slippage_bps"])/10000
    entry = money(window[0].open*(1+slip), up=True)
    spend = min(cash, D(allocation)) if allocation else cash
    qty = int(spend // entry)
    while qty and qty*entry + fees(qty*entry, "buy") > spend:
        qty -= 1
    if not qty:
        return {"net": ZERO, "return_percent": ZERO, "note": "Insufficient cash"}
    cash -= qty*entry + fees(qty*entry, "buy")
    exit_value = qty * money(window[-1].close*(1-slip))
    final = cash + exit_value - fees(exit_value, "sell")
    return {"net": money(final-D(cfg["paper_capital"])), "return_percent": (final/D(cfg["paper_capital"])-1)*100,
            "note": "Passive comparator; remaining cash uninvested; not risk-matched", "initial_allocation_cap": spend}


def main():
    parser = argparse.ArgumentParser(description="Frozen ETF daily-bar research; paper only")
    parser.add_argument("--asof", required=True, type=date.fromisoformat)
    parser.add_argument("--config", type=Path, default=ROOT/"research-config.json")
    parser.add_argument("--data", type=Path, default=ROOT/"state/market-data")
    parser.add_argument("--output", type=Path, default=ROOT/"state/research-results.json")
    args = parser.parse_args()
    now = datetime.now(IST)
    if args.asof > now.date() or (args.asof == now.date() and now.time() < time(16, 0)):
        parser.error("Use a completed market day; today's bars require 16:00 IST or later")
    cfg = json.loads(args.config.read_text())
    if cfg["mode"] != "paper":
        parser.error("Only paper mode supported")
    series, provenance = {}, {}
    for symbol in cfg["symbols"]:
        series[symbol], provenance[symbol] = load_bars(args.data/f"{symbol}.json", args.asof)
    official_path = args.data/f"nse-{args.asof}.json"
    official = json.loads(official_path.read_text())
    for symbol, bars in series.items():
        matches = [r for r in official["rows"] if r["TckrSymb"] == symbol.removesuffix(".NS") and r["TradDt"] == str(args.asof) and r["SctySrs"] == "EQ"]
        if len(matches) != 1 or bars[-1].day != args.asof:
            raise ValueError(f"No fresh NSE cross-check for {symbol}")
        row = matches[0]
        for key, source_key in (("open", "OpnPric"), ("high", "HghPric"), ("low", "LwPric"), ("close", "ClsPric")):
            if abs(getattr(bars[-1], key)-D(row[source_key])) > D("0.015"):
                raise ValueError(f"Latest {symbol} {key} disagrees with NSE; hold signals")
        if bars[-1].volume != int(row["TtlTradgVol"]):
            raise ValueError(f"Latest {symbol} volume disagrees with NSE; hold signals")
        provenance[symbol]["latest_nse_crosscheck"] = official["source_url"]
    report = {"asof": str(args.asof), "generated_at": now.isoformat(), "strategy": cfg,
              "provenance": provenance, "historical_evaluations": {}, "signals": {}}
    for name, start, end in [
        ("development_2018_2022", date(2018,1,1), date(2022,12,31)),
        ("reserved_2023_2025", date(2023,1,1), date(2025,12,31)),
        ("recent_2026", date(2026,1,1), args.asof)]:
        if start > args.asof:
            continue
        end = min(end, args.asof)
        base = run_backtest(series, cfg, start, end)
        stress_cfg = {**cfg, "slippage_bps": "25"}
        stress = run_backtest(series, stress_cfg, start, end)
        report["historical_evaluations"][name] = {
            "base": base, "stress_25bps": stress,
            "buy_hold_niftybees": buy_hold(series["NIFTYBEES.NS"], cfg, start, end),
            "buy_hold_niftybees_10000_cap": buy_hold(series["NIFTYBEES.NS"], cfg, start, end, cfg["max_position_value"]),
            "cash_return": "0; no assumed interest"}
    for symbol, bars in series.items():
        plan = candidate(bars, len(bars)-1, cfg, D(cfg["paper_capital"]))
        plan["data_fresh"] = bars[-1].day == args.asof
        if not plan["data_fresh"]:
            plan["eligible"] = False
            plan["reasons"].append("stale_daily_bar")
        report["signals"][symbol] = plan
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, default=str, indent=2)+"\n")
    compact = {"output": str(args.output), "signals": report["signals"], "evaluations": {
        name: {"net": data["base"]["net"], "trades": data["base"]["closed_trades"],
               "max_drawdown": data["base"]["max_daily_liquidation_drawdown"],
               "stress_net": data["stress_25bps"]["net"], "buy_hold_net": data["buy_hold_niftybees"]["net"]}
        for name, data in report["historical_evaluations"].items()}}
    print(json.dumps(compact, default=str, indent=2))


if __name__ == "__main__":
    main()
