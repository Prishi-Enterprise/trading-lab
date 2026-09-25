"""NSE source validation that keeps bad inputs out of paper decisions."""

import csv
import io
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from tradinglab.nse_only import load_archive, load_series


class NSEOnlyTests(unittest.TestCase):
    def make_archive(self, folder, day, rows):
        path = folder / f"{day}.zip"
        headers = ("TradDt", "TckrSymb", "SctySrs", "OpnPric", "HghPric", "LwPric", "ClsPric", "TtlTradgVol")
        content = io.StringIO()
        writer = csv.DictWriter(content, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("bhavcopy.csv", content.getvalue())
        return path

    def rows(self, day):
        return [{"TradDt": str(day), "TckrSymb": symbol, "SctySrs": "EQ",
                 "OpnPric": "100", "HghPric": "102", "LwPric": "99",
                 "ClsPric": "101", "TtlTradgVol": "1000"}
                for symbol in ("NIFTYBEES", "JUNIORBEES")]

    def test_both_official_etf_rows_required(self):
        day = date(2026, 9, 24)
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_archive(Path(directory), day, self.rows(day)[:1])
            with self.assertRaisesRegex(ValueError, "Missing or duplicate ETF row"):
                load_archive(path, day)

    def test_bad_date_cannot_be_used_as_fresh_data(self):
        day = date(2026, 9, 24)
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_archive(Path(directory), day, self.rows(date(2026, 9, 23)))
            with self.assertRaisesRegex(ValueError, "Mismatched archive date"):
                load_archive(path, day)

    def test_latest_session_and_minimum_history_required(self):
        day = date(2026, 9, 24)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            self.make_archive(folder, day, self.rows(day))
            with self.assertRaisesRegex(ValueError, "Need 200 official shared sessions"):
                load_series(folder, day)
            series, sources = load_series(folder, day, minimum=1)
            self.assertEqual(len(series["NIFTYBEES.NS"]), 1)
            self.assertEqual(sources[0]["date"], str(day))
            with self.assertRaisesRegex(ValueError, "Need 1 official shared sessions"):
                load_series(folder, date(2026, 9, 25), minimum=1)

    def test_special_sunday_session_cannot_be_skipped(self):
        friday, sunday, monday = date(2026, 1, 30), date(2026, 2, 1), date(2026, 2, 2)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            self.make_archive(folder, friday, self.rows(friday))
            self.make_archive(folder, monday, self.rows(monday))
            with self.assertRaisesRegex(ValueError, "Missing NSE archive for expected trading day 2026-02-01"):
                load_series(folder, monday, minimum=2)
            self.make_archive(folder, sunday, self.rows(sunday))
            self.assertEqual(len(load_series(folder, monday, minimum=3)[1]), 3)


if __name__ == "__main__":
    unittest.main()
