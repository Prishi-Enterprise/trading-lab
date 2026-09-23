"""Run: python -m unittest discover -s tests -v   (stdlib only, no network)"""
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from goldtracker import learn, sources, tracker
from goldtracker.notify import MetaCloudNotifier
from goldtracker.timeutil import IST, inr

FIX = Path(__file__).parent / "fixtures"


def page(name):
    return (FIX / name).read_text()


class Recorder:
    name = "recorder"

    def __init__(self):
        self.sent = []

    def send(self, alert):
        self.sent.append(alert)


class ParserTests(unittest.TestCase):
    def test_bullions(self):
        q = sources.parse_bullions(page("bullions_ahmedabad.html"))
        self.assertEqual(q["gold24k_10g"].price, 154090)
        self.assertEqual(q["gold22k_10g"].price, 141249)
        self.assertEqual(q["gold24k_10g"].as_of, datetime(2026, 9, 18, 10, 40, tzinfo=IST))
        m = q["mcx_gold_10g"]
        self.assertEqual(m.price, 153503)
        self.assertEqual(m.extra, {"high": 153637, "low": 152171, "prev_close": 152981})
        self.assertEqual(m.as_of, datetime(2026, 9, 18, 10, 40, tzinfo=IST))

    def test_bullions_24h_pm_quirk(self):
        html = page("bullions_ahmedabad.html").replace("18 Sep 2026 10:40 AM", "17 Sep 2026 21:05 PM")
        q = sources.parse_bullions(html)
        self.assertEqual(q["gold24k_10g"].as_of, datetime(2026, 9, 17, 21, 5, tzinfo=IST))

    def test_aib(self):
        q = sources.parse_aib(page("aib_ahmedabad.html"))
        self.assertEqual(q["retail_999_10g"].price, 151119)
        self.assertEqual(q["rtgs_999_10g"].price, 153692)
        self.assertEqual(q["retail_995_10g"].price, 150094)
        self.assertEqual(q["retail_999_10g"].as_of, datetime(2026, 9, 18, 10, 39, 14, 605000, tzinfo=IST))
        self.assertNotIn(235474, [x.price for x in q.values()])  # silver ignored

    def test_empty_page_raises(self):
        with self.assertRaises(sources.SourceError):
            sources.parse_bullions("<html>cloudflare challenge</html>")
        with self.assertRaises(sources.SourceError):
            sources.parse_aib("<html></html>")

    def test_inr(self):
        self.assertEqual(inr(153470), "₹1,53,470")
        self.assertEqual(inr(999), "₹999")
        self.assertEqual(inr(15403000), "₹1,54,03,000")


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["GOLD_STATE"] = str(Path(self.tmp.name) / "state.json")
        self.cfg = json.loads((tracker.ROOT / "config.json").read_text())
        self.cfg["watch"] = [{"metric": "bullions:gold24k_10g", "label": "24K"}]
        self.cfg["interval"] = {"mode": "fixed", "minutes": 10, "min": 5, "max": 30}
        self.base = page("bullions_ahmedabad.html")

    def tearDown(self):
        os.environ.pop("GOLD_STATE", None)
        self.tmp.cleanup()

    def getter_for(self, price_24k):
        html = self.base.replace(">154,090<", f">{price_24k:,}<")
        return lambda url: html

    def tick(self, price, at="2026-09-18T11:00:00", rec=None):
        rec = rec or Recorder()
        now = datetime.fromisoformat(at).replace(tzinfo=IST)
        rc = tracker.run(self.cfg, rec, now=now, getter=self.getter_for(price), log=lambda *_: None)
        return rc, rec

    def test_open_then_alert_tiers_once(self):
        rec = Recorder()
        self.tick(154090, "2026-09-18T10:41:00", rec)                    # sets open
        self.assertEqual(rec.sent, [])
        self.tick(150000, "2026-09-18T10:51:00", rec)                    # -2.65% -> -2 fires
        self.assertEqual(len(rec.sent), 1)
        self.assertIn("threshold -2%", rec.sent[0].text)
        self.tick(149000, "2026-09-18T11:01:00", rec)                    # still only -2 zone -> nothing
        self.assertEqual(len(rec.sent), 1)
        self.tick(138000, "2026-09-18T11:11:00", rec)                    # -10.4% -> -5 & -10 at once, one msg
        self.assertEqual(len(rec.sent), 2)
        self.assertIn("threshold -10%", rec.sent[1].text)
        self.tick(137000, "2026-09-18T11:21:00", rec)
        self.assertEqual(len(rec.sent), 2)

    def test_rise_alert(self):
        rec = Recorder()
        self.tick(154090, "2026-09-18T10:41:00", rec)
        self.tick(157500, "2026-09-18T10:51:00", rec)                    # +2.2%
        self.assertEqual(len(rec.sent), 1)
        self.assertTrue(rec.sent[0].text.startswith("🔺"))

    def test_stale_quote_not_used_as_open(self):
        html = self.base.replace("18 Sep 2026 10:40 AM", "17 Sep 2026 21:05 PM")
        now = datetime(2026, 9, 18, 9, 5, tzinfo=IST)
        tracker.run(self.cfg, Recorder(), now=now, getter=lambda u: html, log=lambda *_: None)
        st = json.loads(Path(os.environ["GOLD_STATE"]).read_text())
        self.assertEqual(st["open"], {})

    def test_new_day_resets(self):
        rec = Recorder()
        self.tick(154090, "2026-09-18T10:41:00", rec)
        self.tick(150000, "2026-09-18T10:51:00", rec)
        html = self.base.replace("18 Sep 2026 10:40 AM", "19 Sep 2026 10:40 AM").replace(">154,090<", ">150,000<")
        tracker.run(self.cfg, rec, now=datetime(2026, 9, 19, 10, 41, tzinfo=IST),
                    getter=lambda u: html, log=lambda *_: None)
        st = json.loads(Path(os.environ["GOLD_STATE"]).read_text())
        self.assertEqual(st["open"]["bullions:gold24k_10g"]["price"], 150000)
        self.assertEqual(st["alerts_sent"], {})

    def test_outside_window_and_sunday(self):
        rc, rec = self.tick(1, "2026-09-18T03:00:00")
        self.assertEqual((rc, rec.sent), (0, []))
        rc, rec = self.tick(1, "2026-09-20T12:00:00")   # Sunday
        self.assertFalse(Path(os.environ["GOLD_STATE"]).exists())

    def test_all_sources_down_alerts_once(self):
        self.cfg["failure_alert_after"] = 2
        rec = Recorder()
        bad = lambda u: (_ for _ in ()).throw(sources.SourceError("403"))  # noqa: E731
        for i in range(4):
            rc = tracker.run(self.cfg, rec, now=datetime(2026, 9, 18, 11, i * 10, tzinfo=IST),
                             getter=bad, log=lambda *_: None)
            self.assertEqual(rc, 2)
        self.assertEqual(len(rec.sent), 1)

    def test_adaptive_skip(self):
        self.cfg["interval"] = {"mode": "adaptive", "minutes": 10, "min": 5, "max": 30}
        rec = Recorder()
        self.tick(154090, "2026-09-18T10:41:00", rec)
        # 3 min later: learned interval (no history for the hour yet -> 10) not elapsed -> skip
        self.tick(100000, "2026-09-18T10:44:00", rec)
        self.assertEqual(rec.sent, [])

    def test_dashboard_payload_is_sanitized(self):
        self.tick(154090, "2026-09-18T10:41:00")
        state = json.loads(Path(os.environ["GOLD_STATE"]).read_text())
        payload = tracker.dashboard_payload(self.cfg, state)
        self.assertEqual(payload["status"], "verified")
        self.assertEqual(payload["observed_on"], "2026-09-18")
        self.assertEqual(payload["metrics"][0]["price"], 154090)
        self.assertEqual(payload["metrics"][0]["open_price"], 154090)
        self.assertEqual(payload["metrics"][0]["change_pct"], 0.0)
        self.assertNotIn("alerts_sent", payload)

    def test_run_creates_nested_state_directory(self):
        nested = Path(self.tmp.name) / "nested" / "state.json"
        os.environ["GOLD_STATE"] = str(nested)
        self.tick(154090, "2026-09-18T10:41:00")
        self.assertTrue(nested.exists())
        self.assertTrue((nested.parent / "history.csv").exists())


class LearnTests(unittest.TestCase):
    def test_suggest(self):
        self.assertEqual(learn.suggest_minutes(3, 3, 10, 5, 30), 10)      # too few samples
        self.assertEqual(learn.suggest_minutes(12, 12, 10, 5, 30), 5)     # always changing -> fastest
        self.assertEqual(learn.suggest_minutes(12, 0, 10, 5, 30), 30)     # never changing -> slowest

    def test_hourly_rate(self):
        t = lambda h, m: datetime(2026, 9, 18, h, m, tzinfo=IST)  # noqa: E731
        rows = [(t(10, 0), "a", 1), (t(10, 10), "a", 1), (t(10, 20), "a", 2), (t(11, 0), "a", 2)]
        self.assertEqual(learn.hourly_change_rate(rows), {10: (2, 1), 11: (1, 0)})


class NotifierTests(unittest.TestCase):
    def test_meta_template_payload(self):
        os.environ.update(WA_TOKEN="t", WA_PHONE_NUMBER_ID="1", WA_TO="+919800000000", WA_TEMPLATE="gold_alert")
        try:
            n = MetaCloudNotifier()
            from goldtracker.notify import Alert
            p = n.payload("919800000000", Alert("24K", "₹1", -2.5, "₹2", "18 Sep", "x"))
            self.assertEqual(p["template"]["name"], "gold_alert")
            self.assertEqual(len(p["template"]["components"][0]["parameters"]), 5)
            self.assertEqual(n.to, ["919800000000"])
        finally:
            for k in ("WA_TOKEN", "WA_PHONE_NUMBER_ID", "WA_TO", "WA_TEMPLATE"):
                os.environ.pop(k, None)


if __name__ == "__main__":
    unittest.main()
