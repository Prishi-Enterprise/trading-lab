import argparse
import json
from pathlib import Path

from .core import funding, review


ROOT = Path(__file__).resolve().parent.parent


def rupees(value):
    return f"INR {value:,.2f}"


def main():
    parser = argparse.ArgumentParser(description="Prishi trading lab — offline, paper only")
    parser.add_argument("command", choices=["status", "review"])
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--month", help="YYYY-MM; defaults to first expense month")
    parser.add_argument("--project-income", default="0", help="Monthly net project-income scenario, not recorded revenue")
    parser.add_argument("--journal", type=Path, help="Local JSON file containing closed paper trades")
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text())
        if not isinstance(config, dict):
            raise ValueError("Config must be a JSON object")
        target_month = args.month or config["expense_start_month"]
        plan = funding(config, target_month, args.project_income)
        print(f"PRISHI TRADING LAB | PAPER ONLY | Funding month: {target_month}")
        print(f"Organisation starting fund: {rupees(plan['organisation_budget'])}")
        print(f"Paper capital assumption (not allocated live): {rupees(plan['capital'])}")
        print(f"Subscription to cover: {rupees(plan['bill'])}")
        print(f"Net project-income scenario: {rupees(plan['project_income_scenario'])}")
        print(f"Half-cost gap: {rupees(plan['half_gap'])} | required return: {plan['half_required_percent']:.2f}%")
        print(f"Full-cost gap: {rupees(plan['full_gap'])} | required return: {plan['full_required_percent']:.2f}%")
        print("Requirements only, not forecasts. Income tax is not modelled.")
        payments = plan['full_bill_payments_from_starting_fund']
        if payments is not None:
            print(f"If the same monthly gap persists: {payments} full payments from the starting fund, then {rupees(plan['remainder_after_full_payments'])} left.")
            print("This spends principal; it does not preserve capital. Assumes no other costs or trading gains/losses.")
        else:
            print("No subscription funding gap for this month's scenario.")
        print("Actual trading income recorded: none. No broker connection or live orders.")
        if config.get('affordable_total_loss') is not None:
            print(f"Declared total experiment loss limit: INR {config['affordable_total_loss']} (not a monthly allowance).")
        if args.command == "review":
            if args.journal is None:
                raise ValueError("review requires --journal; see examples/paper-trades.json")
            result = review(config, json.loads(args.journal.read_text()), target_month)
            print(f"\nSIMULATED JOURNAL: {args.journal}")
            print(f"Closed trades: {result['count']} | net profitable trades: {result['wins']}")
            print(f"All-journal simulated equity: {rupees(result['equity'])}")
            print(f"All-journal net P&L after entered costs: {rupees(result['net'])}")
            print(f"{target_month} realised paper P&L: {rupees(result['month_net'])} ({result['month_count']} trades)")
            print(f"Maximum closed-trade drawdown: {rupees(result['max_closed_trade_drawdown'])}")
            print(f"Maximum closed-trade loss below starting capital: {rupees(result['max_closed_trade_loss_from_start'])}")
            if result['loss_limit_ever_breached']:
                print("STOP AND REVIEW: the journal reached the total loss limit. Later recovery does not clear this flag.")
            else:
                print("No recorded closed-trade limit breach. Open-position risk is unchecked; this is not clearance to trade.")
            if result['mean_net_per_trade'] is not None:
                print(f"Observed mean net/trade: {rupees(result['mean_net_per_trade'])}")
            print("Paper results do not fund bills or establish a profitable strategy.")
            print("Open-position losses, deposits, withdrawals and income tax are not modelled.")
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
        parser.exit(2, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
