"""Exact-decimal planning and review of sequential, closed paper trades."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation


ZERO = Decimal("0")


def amount(value, name, positive=False):
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not number.is_finite() or number < 0 or (positive and number == 0):
        raise ValueError(f"{name} must be {'positive' if positive else 'non-negative'} and finite")
    if number != number.quantize(Decimal("0.01")):
        raise ValueError(f"{name} supports at most two decimal places")
    return number


def month(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}", value):
        raise ValueError("month must be YYYY-MM")
    date.fromisoformat(value + "-01")
    return value


def validate_config(config):
    if config.get("mode") != "paper":
        raise ValueError("Only paper mode is supported")
    if config.get("currency") != "INR":
        raise ValueError("Only INR is supported")
    budget = amount(config["organisation_budget"], "organisation_budget", positive=True)
    capital = amount(config["capital_ceiling"], "capital_ceiling", positive=True)
    if capital > budget:
        raise ValueError("Paper capital cannot exceed the organisation budget")
    if config.get("affordable_total_loss") is not None:
        loss_limit = amount(config["affordable_total_loss"], "affordable_total_loss")
        if loss_limit > budget:
            raise ValueError("Loss limit cannot exceed organisation budget")
    amount(config["monthly_subscription"], "monthly_subscription")
    month(config["expense_start_month"])


def funding(config, target_month, project_income="0"):
    validate_config(config)
    month(target_month)
    capital = amount(config["capital_ceiling"], "capital_ceiling", positive=True)
    budget = amount(config["organisation_budget"], "organisation_budget", positive=True)
    income = amount(project_income, "project_income")
    bill = amount(config["monthly_subscription"], "monthly_subscription")
    if target_month < config["expense_start_month"]:
        bill = ZERO
    half_gap = max(ZERO, bill / 2 - income)
    full_gap = max(ZERO, bill - income)
    return {
        "capital": capital,
        "organisation_budget": budget,
        "full_bill_payments_from_starting_fund": int(budget // full_gap) if full_gap else None,
        "remainder_after_full_payments": budget % full_gap if full_gap else budget,
        "bill": bill,
        "project_income_scenario": income,
        "half_gap": half_gap,
        "full_gap": full_gap,
        "half_required_percent": half_gap / capital * 100,
        "full_required_percent": full_gap / capital * 100,
    }


def review(config, trades, target_month):
    """No overlapping positions, deposits, withdrawals, shorts, or open trades.

    All round-trip costs are reserved when checking cash sufficiency. Cost input
    includes fees and estimated slippage not already captured in fill prices.
    """
    validate_config(config)
    month(target_month)
    if not isinstance(trades, list):
        raise ValueError("Journal must be a JSON array")
    capital = amount(config["capital_ceiling"], "capital_ceiling", positive=True)
    equity = peak = capital
    drawdown = month_net = max_loss_from_start = ZERO
    limit = config.get("affordable_total_loss")
    limit = amount(limit, "affordable_total_loss") if limit is not None else None
    limit_breached = limit == ZERO
    wins = count = month_count = 0
    previous_exit = None
    identifiers = set()
    for trade in trades:
        if not isinstance(trade, dict):
            raise ValueError("Each journal entry must be an object")
        identifier = trade["id"]
        if not isinstance(identifier, str) or not identifier.strip() or identifier in identifiers:
            raise ValueError("Trade ids must be unique non-empty strings")
        identifiers.add(identifier)
        if trade.get("mode") != "paper" or trade.get("side") != "long":
            raise ValueError("Journal accepts only long paper trades")
        if not isinstance(trade.get("symbol"), str) or not trade["symbol"].strip():
            raise ValueError("Each trade needs a symbol")
        entry_date = date.fromisoformat(trade["entry_date"])
        exit_date = date.fromisoformat(trade["exit_date"])
        if exit_date < entry_date or (previous_exit and entry_date <= previous_exit):
            raise ValueError("Use chronological, non-overlapping trades; next entry must be after prior exit day")
        previous_exit = exit_date
        quantity = trade["quantity"]
        if type(quantity) is not int or quantity <= 0:
            raise ValueError("quantity must be a positive integer")
        entry = amount(trade["entry_price"], "entry_price", positive=True)
        exit_price = amount(trade["exit_price"], "exit_price", positive=True)
        costs = amount(trade["costs"], "costs")
        if entry * quantity + costs > equity:
            raise ValueError(f"Trade {identifier} exceeds available simulated cash")
        net = (exit_price - entry) * quantity - costs
        equity += net
        max_loss_from_start = max(max_loss_from_start, capital - equity)
        if limit is not None and capital - equity >= limit:
            limit_breached = True
        count += 1
        wins += net > 0
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
        if trade["exit_date"][:7] == target_month:
            month_net += net
            month_count += 1
    return {
        "count": count,
        "wins": wins,
        "equity": equity,
        "net": equity - capital,
        "month_count": month_count,
        "month_net": month_net,
        "max_closed_trade_drawdown": drawdown,
        "max_closed_trade_loss_from_start": max_loss_from_start,
        "loss_limit": limit,
        "loss_limit_ever_breached": limit_breached,
        "mean_net_per_trade": (equity - capital) / count if count else None,
    }
