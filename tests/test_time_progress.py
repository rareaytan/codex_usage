import unittest
from datetime import datetime

from codex_float_ui import time_remaining_percent


class TimeRemainingPercentTest(unittest.TestCase):
    def test_5h_progress_uses_remaining_time_until_reset(self):
        now = datetime(2026, 6, 18, 12, 0, 0)

        self.assertEqual(time_remaining_percent("2:30 PM", 5 * 60, now), 50)


    def test_5h_progress_represents_remaining_time_not_elapsed_time(self):
        now = datetime(2026, 6, 18, 12, 0, 0)

        self.assertEqual(time_remaining_percent("1:00 PM", 5 * 60, now), 20)

    def test_weekly_progress_uses_remaining_time_until_reset(self):
        now = datetime(2026, 6, 18, 12, 0, 0)

        self.assertEqual(time_remaining_percent("Jun 22 00:00", 7 * 24 * 60, now), 50)

    def test_unparseable_reset_has_no_progress(self):
        now = datetime(2026, 6, 18, 12, 0, 0)

        self.assertIsNone(time_remaining_percent("N/A", 5 * 60, now))


if __name__ == "__main__":
    unittest.main()
