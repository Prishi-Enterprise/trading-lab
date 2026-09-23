import copy
import json
import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal as D
from pathlib import Path

from tradinglab.research import Bar, candidate, fees, load_bars, money, run_backtest, size_plan

ROOT = Path(__file__).resolve().parent.parent


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.cfg = json.loads((ROOT/"research-config.json").read_text())
        self.cfg.update(trend_sessions=3, breakout_sessions=2, atr_sessions=2, minimum_average_turnover="0")
        self.bars = [Bar(date(2024,1,1)+timedelta(days=i), D(o), D(h), D(l), D(c), 100000)
                     for i, (o,h,l,c) in enumerate([
                         (100,101,99,100), (100,101,99,100), (100,101,99,100),
                         (101,105,100,104), (104,108,103,107), (107,109,106,108),
                         (108,110,107,109), (109,111,108,110)])]

    def run_window(self, bars=None, cfg=None):
        return run_backtest({"TEST": bars or self.bars}, cfg or self.cfg, date(2024,1,1), date(2024,1,8))

    def test_vendor_binary_float_rounds_to_correct_paisa(self):
        self.assertEqual(money(D("782.3099975585938")), D("782.31"))

    def test_etf_fee_estimate_has_sell_dp_and_stt(self):
        self.assertEqual(fees(D(10000), "buy"), D("13.68"))
        self.assertEqual(fees(D(10000), "sell"), D("35.88"))
        self.assertGreater(fees(D(10000), "sell", same_day=True), fees(D(10000), "sell"))

    def test_previous_high_excludes_signal_bar(self):
        result = candidate(self.bars, 3, self.cfg, D(28000))
        self.assertTrue(result["eligible"])
        self.assertEqual(result["previous_high"], D(101))

    def test_future_prices_do_not_change_signal_or_past_results(self):
        original = candidate(self.bars, 3, self.cfg, D(28000))
        future = self.bars[:4]+[Bar(b.day, D(1000), D(1100), D(900), D(1050), b.volume) for b in self.bars[4:]]
        self.assertEqual(candidate(future, 3, self.cfg, D(28000)), original)
        first = run_backtest({"TEST": self.bars}, self.cfg, date(2024,1,1), date(2024,1,4))
        second = run_backtest({"TEST": future}, self.cfg, date(2024,1,1), date(2024,1,4))
        self.assertEqual(first, second)
        self.assertEqual(first["closed_trades"], 0)

    def test_entry_after_signal_and_costs_reconcile(self):
        result = self.run_window()
        self.assertEqual(result["closed_trades"], 1)
        trade = result["trades"][0]
        self.assertEqual(trade["signal_day"], "2024-01-04")
        self.assertEqual(trade["entry_day"], "2024-01-05")
        self.assertEqual(trade["net"], (trade["exit_price"]-trade["entry_price"])*trade["quantity"]-trade["fees"])
        self.assertEqual(result["net"], trade["net"])
        self.assertEqual(result["ending_equity"], D(28000)+trade["net"])

    def test_open_above_limit_is_skipped(self):
        bars = self.bars[:5]
        bars[-1] = Bar(bars[-1].day, D(120), D(125), D(119), D(123), 100000)
        result = self.run_window(bars)
        self.assertEqual(result["closed_trades"], 0)

    def test_next_open_below_stop_is_skipped(self):
        bars = self.bars[:5]
        bars[-1] = Bar(bars[-1].day, D(80), D(90), D(75), D(85), 100000)
        self.assertEqual(self.run_window(bars)["closed_trades"], 0)

    def test_stop_gap_fills_below_stop_not_at_stop(self):
        bars = self.bars[:6]
        bars[-1] = Bar(bars[-1].day, D(80), D(90), D(75), D(85), 100000)
        trade = self.run_window(bars)["trades"][0]
        self.assertEqual(trade["reason"], "gap_below_stop")
        self.assertEqual(trade["exit_price"], D("79.92"))

    def test_entry_day_stop_is_counted_conservatively(self):
        bars = self.bars[:5]
        bars[-1] = Bar(bars[-1].day, D(104), D(108), D(80), D(90), 100000)
        trade = self.run_window(bars)["trades"][0]
        self.assertEqual(trade["reason"], "entry_day_stop")
        self.assertEqual(trade["entry_day"], trade["exit_day"])
        self.assertLess(trade["net"], 0)

    def test_position_size_includes_costs_and_exit_slippage(self):
        qty = size_plan(D(200), D(190), D(28000), self.cfg)
        self.assertLessEqual(qty*200, D(self.cfg["max_position_value"]))
        stop_fill = D("189.81")
        loss = qty*(200-stop_fill)+fees(qty*D(200), "buy")+fees(qty*stop_fill, "sell")
        self.assertLessEqual(loss, D(250))
        self.assertEqual(size_plan(D(200), D(190), D(1), self.cfg), 0)

    def test_loss_limit_halts_after_gap_loss(self):
        cfg = {**self.cfg, "total_loss_limit": "100"}
        bars = self.bars[:6]
        bars[-1] = Bar(bars[-1].day, D(80), D(90), D(75), D(85), 100000)
        result = self.run_window(bars, cfg)
        self.assertTrue(result["halted_at_loss_limit"])

    def test_calendar_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "calendars"):
            run_backtest({"A": self.bars, "B": self.bars[1:]}, self.cfg, date(2024,1,1), date(2024,1,8))

    def test_missing_data_is_not_silently_dropped(self):
        payload = {"source_url": "https://example.invalid/fixture", "fetched_at_utc": "fixture",
                   "payload": {"chart": {"result": [{"meta": {"currency": "INR", "symbol": "TEST.NS"},
                    "timestamp": [1704080700], "indicators": {"quote": [{
                    "open": [None], "high": [None], "low": [None], "close": [None], "volume": [None]}]}}]}}}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"TEST.NS.json"
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "Missing price"):
                load_bars(path, date(2024,1,2))

    def test_forward_replay_keeps_open_position(self):
        result = run_backtest({"TEST": self.bars}, self.cfg, date(2024,1,1), date(2024,1,8), liquidate_end=False)
        self.assertEqual(result["closed_trades"], 0)
        self.assertIsNotNone(result["open_position"])
        self.assertLess(result["cash"], result["ending_equity"])

    def test_missing_prospective_signal_blocks_replay(self):
        with self.assertRaisesRegex(ValueError, "pre-recorded decision"):
            run_backtest({"TEST": self.bars}, self.cfg, date(2024,1,5), date(2024,1,8), frozen_signals={})

    def test_frozen_no_trade_cannot_be_rewritten_by_historical_signal(self):
        plan = candidate(self.bars, 3, self.cfg, D(28000))
        self.assertTrue(plan["eligible"])
        plan["eligible"] = False
        result = run_backtest({"TEST": self.bars}, self.cfg, date(2024,1,5), date(2024,1,5),
                              liquidate_end=False, frozen_signals={"2024-01-04": {"TEST": plan}})
        self.assertIsNone(result["open_position"])
        self.assertEqual(result["net"], 0)


if __name__ == "__main__":
    unittest.main()
