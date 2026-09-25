"""Chronology and sizing checks for the separate retrospective screen."""

import unittest
from datetime import date, timedelta
from decimal import Decimal

from scripts.compare_daily_strategies import decision, quantity, simulate
from tradinglab.research import Bar, fees, money

D = Decimal


class StrategyScreenTests(unittest.TestCase):
    def bars(self):
        first = date(2026, 1, 1)
        bars = [Bar(first + timedelta(days=i), D(100), D(101), D(99), D(100), 1000)
                for i in range(20)]
        bars.append(Bar(first + timedelta(days=20), D(100), D(121), D(99), D(120), 1000))
        bars.append(Bar(first + timedelta(days=21), D(130), D(132), D(128), D(130), 1000))
        return bars

    def test_close_signal_fills_only_at_next_open(self):
        bars = self.bars()
        self.assertEqual(decision(bars, 20, "sma_cross_10_20"), (True, False))
        result = simulate(bars, "sma_cross_10_20", 21, 21)
        self.assertEqual(result["closed_trades"], 1)
        self.assertEqual(result["trades"][0]["entry_day"], str(bars[21].day))
        self.assertEqual(result["trades"][0]["reason"], "evaluation_end")
        self.assertLess(D(result["net"]), 0)  # next-open gap and round-trip costs

    def test_mean_reversion_threshold_can_produce_no_trade(self):
        result = simulate(self.bars(), "mean_reversion_20_10pct", 21, 21)
        self.assertEqual(result["closed_trades"], 0)
        self.assertEqual(D(result["net"]), 0)

    def test_backtrader_10_30_cross_uses_thirty_prior_closes(self):
        first = date(2026, 1, 1)
        bars = [Bar(first + timedelta(days=i), D(100), D(101), D(99), D(100), 1000)
                for i in range(30)]
        bars.append(Bar(first + timedelta(days=30), D(100), D(121), D(99), D(120), 1000))
        self.assertEqual(decision(bars, 30, "sma_cross_10_30"), (True, False))

    def test_planned_stop_risk_includes_fees_and_slippage(self):
        entry = D("300")
        qty, stop = quantity(entry, D("28000"))
        value = qty * entry
        stop_proceeds = qty * money(stop * D("0.999"))
        risk = value + fees(value, "buy") - stop_proceeds + fees(stop_proceeds, "sell")
        self.assertLessEqual(risk, D("250"))
        self.assertLessEqual(value + fees(value, "buy"), D("28000"))


if __name__ == "__main__":
    unittest.main()
