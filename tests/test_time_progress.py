import unittest
from datetime import datetime

from codex_float_ui import (
    BAR_WIDTH,
    CodexFloatingUI,
    SEGMENTS,
    SEG_GAP,
    current_day_quota_threshold,
    format_reset_text,
    snap_position,
    status_is_stale,
    time_remaining_percent,
)


class FakeCanvas:
    def __init__(self, width=BAR_WIDTH):
        self.width = width
        self.rectangles = []

    def delete(self, tag):
        self.rectangles.clear()

    def winfo_width(self):
        return self.width

    def create_rectangle(self, *coords, **kwargs):
        self.rectangles.append((coords, kwargs))

    def create_line(self, *coords, **kwargs):
        pass


class TimeRemainingPercentTest(unittest.TestCase):
    def test_weekly_progress_uses_remaining_time_until_reset(self):
        now = datetime(2026, 6, 18, 12, 0, 0)

        self.assertEqual(time_remaining_percent("Jun 22 00:00", 7 * 24 * 60, now), 50)

    def test_weekly_progress_parses_codex_time_on_day_month_format(self):
        now = datetime(2026, 6, 21, 22, 4, 0)

        self.assertEqual(time_remaining_percent("10:04 on 25 Jun", 7 * 24 * 60, now), 50)

    def test_weekly_progress_floors_nearly_full_window(self):
        now = datetime(2026, 7, 13, 20, 57, 53)

        self.assertEqual(time_remaining_percent("20:56 on 20 Jul", 7 * 24 * 60, now), 99)

    def test_unparseable_reset_has_no_progress(self):
        now = datetime(2026, 6, 18, 12, 0, 0)

        self.assertIsNone(time_remaining_percent("N/A", 5 * 60, now))

    def test_past_day_month_reset_has_no_remaining_progress(self):
        now = datetime(2026, 8, 20, 16, 5, 0)

        self.assertIsNone(time_remaining_percent("11:32 on 20 Aug", 7 * 24 * 60, now))

    def test_segmented_quota_fill_uses_drawable_width_without_gaps(self):
        ui = object.__new__(CodexFloatingUI)
        ui.quota_vs_time_color = lambda left_percent, time_percent: "#5aa9ff"
        canvas = FakeCanvas()

        CodexFloatingUI.draw_weekly_segmented_bar(ui, canvas, 73, None)

        filled_width = sum(
            coords[2] - coords[0]
            for coords, kwargs in canvas.rectangles
            if kwargs.get("fill") == "#5aa9ff"
        )
        drawable_width = BAR_WIDTH - (SEGMENTS - 1) * SEG_GAP
        self.assertAlmostEqual(filled_width, drawable_width * 0.73)

    def test_current_day_quota_threshold_uses_day_bucket_floor(self):
        self.assertAlmostEqual(current_day_quota_threshold(73), 500 / 7)

    def test_current_day_quota_threshold_does_not_warn_at_precise_time_point(self):
        threshold = current_day_quota_threshold(73)

        self.assertGreaterEqual(73, threshold)

    def test_current_day_quota_threshold_caps_full_window_to_first_day_floor(self):
        self.assertAlmostEqual(current_day_quota_threshold(100), 600 / 7)

    def test_weekly_reset_shows_month_day_when_not_today(self):
        now = datetime(2026, 7, 2, 8, 0, 0)

        self.assertEqual(format_reset_text("weekly", "10:53 on 7 Jul", now), "7.7 10:53")

    def test_weekly_reset_shows_time_when_today(self):
        now = datetime(2026, 7, 7, 8, 0, 0)

        self.assertEqual(format_reset_text("weekly", "10:53 on 7 Jul", now), "10:53")

    def test_spark_reset_shows_month_day_when_not_today(self):
        now = datetime(2026, 7, 2, 8, 0, 0)

        self.assertEqual(format_reset_text("spark", "10:53 on 7 Jul", now), "7.7 10:53")

    def test_spark_reset_shows_time_when_today(self):
        now = datetime(2026, 7, 7, 8, 0, 0)

        self.assertEqual(format_reset_text("spark", "10:53 on 7 Jul", now), "10:53")

    def test_status_is_stale_after_more_than_three_minutes(self):
        now = datetime(2026, 7, 2, 8, 4, 1)

        self.assertTrue(status_is_stale("2026-07-02 08:01:00", now))

    def test_status_is_not_stale_at_three_minutes(self):
        now = datetime(2026, 7, 2, 8, 4, 0)

        self.assertFalse(status_is_stale("2026-07-02 08:01:00", now))

    def test_invalid_status_timestamp_is_stale(self):
        now = datetime(2026, 7, 2, 8, 4, 0)

        self.assertTrue(status_is_stale("bad timestamp", now))

    def test_snap_position_snaps_to_top_edge(self):
        self.assertEqual(
            snap_position(120, 10, 200, 80, 1000, 800, 24),
            (120, 0),
        )

    def test_snap_position_snaps_to_right_edge(self):
        self.assertEqual(
            snap_position(785, 120, 200, 80, 1000, 800, 24),
            (800, 120),
        )

    def test_snap_position_keeps_position_outside_threshold(self):
        self.assertEqual(
            snap_position(120, 40, 200, 80, 1000, 800, 24),
            (120, 40),
        )

    def test_snap_position_can_ignore_top_edge_when_dragging_away(self):
        self.assertEqual(
            snap_position(120, 10, 200, 80, 1000, 800, 24, ignored_edges={"top"}),
            (120, 10),
        )


if __name__ == "__main__":
    unittest.main()
