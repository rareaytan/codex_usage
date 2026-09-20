import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from codex_usage_history import record_sample, read_samples


class UsageHistoryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "history.sqlite3"
        self.now = datetime(2026, 9, 20, 12)

    def record(self, when, value, account="a"):
        record_sample({"timestamp": when.strftime("%Y-%m-%d %H:%M:%S"),
                       "status": {"weekly_left_percent": value, "account": account}},
                      self.path)

    def test_persists_samples_and_deduplicates_timestamp(self):
        self.record(self.now, 73)
        self.record(self.now, 73)
        self.assertEqual(read_samples("a", self.now, self.path), [(self.now, 73)])

    def test_seven_day_window_and_account_isolation(self):
        self.record(self.now - timedelta(days=8), 90)
        self.record(self.now - timedelta(days=7), 80)
        self.record(self.now, 73)
        self.record(self.now, 20, "b")
        self.assertEqual(read_samples("a", self.now, self.path),
                         [(self.now - timedelta(days=7), 80), (self.now, 73)])

    def test_invalid_values_are_not_recorded(self):
        for value in (None, -1, 101, "N/A", True, float("nan")):
            self.record(self.now, value)
        self.assertEqual(read_samples("a", self.now, self.path), [])

    def test_missing_history_is_empty(self):
        self.assertEqual(read_samples("a", self.now, self.path), [])


if __name__ == "__main__":
    unittest.main()
