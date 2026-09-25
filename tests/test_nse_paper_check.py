import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from scripts.run_nse_paper_check import check, should_retire


class NSEPaperCheckTests(unittest.TestCase):
    def test_only_completed_trial_days_run(self):
        ist = ZoneInfo("Asia/Kolkata")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            invoke = lambda *args, **kwargs: self.fail("Unexpected paper execution")
            self.assertEqual(check(datetime(2026, 9, 25, 12, 0, tzinfo=ist), invoke, root)["status"],
                             "market_not_complete")
            self.assertEqual(check(datetime(2026, 10, 2, 19, 0, tzinfo=ist), invoke, root)["status"],
                             "outside_trial")

    def test_check_records_current_day_and_retry_can_skip_frozen_snapshot(self):
        ist = ZoneInfo("Asia/Kolkata")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            calls = []

            def invoke(command, **kwargs):
                calls.append(command)
                return SimpleNamespace(returncode=0, stdout="recorded", stderr="")

            now = datetime(2026, 9, 25, 19, 0, tzinfo=ist)
            self.assertEqual(check(now, invoke, root)["status"], "snapshot_recorded")
            self.assertEqual(calls[0][-1], "2026-09-25")
            snapshot = root / "state/nse-only/snapshots/2026-09-25.json"
            snapshot.parent.mkdir(parents=True)
            snapshot.write_text("{}")
            self.assertEqual(check(now, invoke, root)["status"], "snapshot_already_frozen")
            self.assertEqual(len(calls), 1)

    def test_retirement_after_final_check_or_later_login(self):
        ist = ZoneInfo("Asia/Kolkata")
        self.assertFalse(should_retire(datetime(2026, 10, 1, 18, 30, tzinfo=ist)))
        self.assertTrue(should_retire(datetime(2026, 10, 1, 20, 30, tzinfo=ist)))
        self.assertTrue(should_retire(datetime(2026, 10, 5, 9, 0, tzinfo=ist)))


if __name__ == "__main__":
    unittest.main()
