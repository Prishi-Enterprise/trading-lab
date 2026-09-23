import copy
import json
import unittest
from decimal import Decimal
from pathlib import Path

from tradinglab.core import funding, review


ROOT = Path(__file__).resolve().parent.parent


class TradingLabTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "config.json").read_text())
        self.trades = json.loads((ROOT / "examples/paper-trades.json").read_text())

    def test_original_and_full_bill_targets(self):
        result = funding(self.config, "2026-10")
        self.assertEqual(result["half_gap"], Decimal("5500"))
        self.assertEqual(result["full_gap"], Decimal("11000"))
        self.assertEqual(result["half_required_percent"], Decimal("11"))
        self.assertEqual(result["full_required_percent"], Decimal("22"))

    def test_paid_september_excluded(self):
        result = funding(self.config, "2026-09")
        self.assertEqual(result["bill"], 0)
        self.assertEqual(result["full_required_percent"], 0)

    def test_subscription_runway_spends_organisation_fund(self):
        result = funding(self.config, "2026-10")
        self.assertEqual(result["full_bill_payments_from_starting_fund"], 4)
        self.assertEqual(result["remainder_after_full_payments"], Decimal("6000"))
        covered = funding(self.config, "2026-10", "11000")
        self.assertIsNone(covered["full_bill_payments_from_starting_fund"])
        self.assertEqual(covered["remainder_after_full_payments"], Decimal("50000"))

    def test_paper_allocation_cannot_exceed_organisation_fund(self):
        self.config["capital_ceiling"] = "50001"
        with self.assertRaisesRegex(ValueError, "organisation budget"):
            funding(self.config, "2026-10")

    def test_year_boundary_and_project_contribution(self):
        result = funding(self.config, "2027-01", "4000")
        self.assertEqual(result["half_gap"], Decimal("1500"))
        self.assertEqual(result["full_gap"], Decimal("7000"))
        self.assertEqual(result["half_required_percent"], Decimal("3"))
        self.assertEqual(result["full_required_percent"], Decimal("14"))

    def test_surplus_income_does_not_create_negative_target(self):
        result = funding(self.config, "2026-10", "15000")
        self.assertEqual(result["half_gap"], 0)
        self.assertEqual(result["full_gap"], 0)

    def test_invalid_funding_inputs(self):
        for value in ("NaN", "Infinity", "-1", "0.001", "no"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                funding(self.config, "2026-10", value)
        for value in ("2026-13", "2026-1", "bad"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                funding(self.config, value)

    def test_costs_losses_drawdown_and_month_filter(self):
        result = review(self.config, self.trades, "2026-09")
        # +180, -220, +100 after round-trip costs.
        self.assertEqual(result["equity"], Decimal("50060"))
        self.assertEqual(result["net"], Decimal("60"))
        self.assertEqual(result["month_net"], Decimal("60"))
        self.assertEqual(result["max_closed_trade_drawdown"], Decimal("220"))
        self.assertEqual(result["mean_net_per_trade"], Decimal("20"))
        self.assertEqual(result["wins"], 2)
        october = review(self.config, self.trades, "2026-10")
        self.assertEqual(october["month_net"], 0)
        self.assertEqual(october["month_count"], 0)
        self.assertEqual(october["equity"], Decimal("50060"))

    def test_losing_journal_is_not_clamped_to_zero(self):
        result = review(self.config, [self.trades[1]], "2026-09")
        self.assertEqual(result["net"], Decimal("-220"))
        self.assertEqual(result["equity"], Decimal("49780"))
        self.assertEqual(result["wins"], 0)

    def test_fees_can_turn_a_gross_winner_into_a_net_loser(self):
        self.trades[0]["exit_price"] = "100.10"
        result = review(self.config, self.trades[:1], "2026-09")
        self.assertEqual(result["net"], Decimal("-10"))
        self.assertEqual(result["wins"], 0)

    def test_oversized_position_including_costs_rejected(self):
        self.trades[0]["quantity"] = 500
        with self.assertRaisesRegex(ValueError, "simulated cash"):
            review(self.config, self.trades, "2026-09")

    def test_losses_reduce_next_position_budget(self):
        self.trades[0]["exit_price"] = "90"
        self.trades[1]["quantity"] = 245
        # Remaining cash 48,980; second entry + costs would need 49,020.
        with self.assertRaisesRegex(ValueError, "simulated cash"):
            review(self.config, self.trades, "2026-09")

    def test_bad_trade_inputs_rejected(self):
        for key, value in (
            ("quantity", 0), ("quantity", -1), ("quantity", 0.5),
            ("quantity", True), ("entry_price", "NaN"), ("exit_price", "Infinity"),
            ("entry_price", "0"), ("costs", "-1"), ("mode", "live"),
            ("side", "short"), ("symbol", ""), ("exit_date", "2026-09-01"),
        ):
            trades = copy.deepcopy(self.trades)
            trades[0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                review(self.config, trades, "2026-09")

    def test_overlapping_or_duplicate_trades_rejected(self):
        self.trades[1]["entry_date"] = self.trades[0]["exit_date"]
        with self.assertRaisesRegex(ValueError, "non-overlapping"):
            review(self.config, self.trades, "2026-09")
        self.trades[1]["entry_date"] = "2026-09-14"
        self.trades[1]["id"] = self.trades[0]["id"]
        with self.assertRaisesRegex(ValueError, "unique"):
            review(self.config, self.trades, "2026-09")

    def test_empty_journal_and_input_not_mutated(self):
        result = review(self.config, [], "2026-10")
        self.assertEqual(result["equity"], Decimal("50000"))
        self.assertIsNone(result["mean_net_per_trade"])
        original = copy.deepcopy(self.trades)
        review(self.config, self.trades, "2026-09")
        self.assertEqual(self.trades, original)

    def test_live_config_and_zero_capital_rejected(self):
        self.config["mode"] = "live"
        with self.assertRaises(ValueError):
            funding(self.config, "2026-10")
        self.config["mode"] = "paper"
        self.config["capital_ceiling"] = "0"
        with self.assertRaises(ValueError):
            funding(self.config, "2026-10")

    def test_total_loss_limit_includes_fees_and_does_not_reset_monthly(self):
        trades = copy.deepcopy(self.trades[:2])
        trades[0].update(exit_price="75", costs="0")
        trades[1].update(entry_date="2026-10-01", exit_date="2026-10-02", exit_price="150.40", costs="20")
        result = review(self.config, trades, "2026-10")
        self.assertEqual(result["net"], Decimal("-5000"))
        self.assertTrue(result["loss_limit_ever_breached"])
        self.assertEqual(result["month_net"], Decimal("-2500"))

    def test_breach_persists_after_recovery(self):
        self.trades[0].update(exit_price="50", costs="0")
        self.trades[1].update(exit_price="320", costs="0")
        result = review(self.config, self.trades[:2], "2026-09")
        self.assertEqual(result["net"], Decimal("1000"))
        self.assertEqual(result["max_closed_trade_loss_from_start"], Decimal("5000"))
        self.assertTrue(result["loss_limit_ever_breached"])

    def test_below_limit_does_not_flag(self):
        self.trades[0].update(exit_price="50.01", costs="0")
        result = review(self.config, self.trades[:1], "2026-09")
        self.assertEqual(result["net"], Decimal("-4999"))
        self.assertFalse(result["loss_limit_ever_breached"])

    def test_invalid_loss_limits_rejected(self):
        for value in ("-1", "NaN", "50001"):
            self.config["affordable_total_loss"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                funding(self.config, "2026-10")


if __name__ == "__main__":
    unittest.main()
