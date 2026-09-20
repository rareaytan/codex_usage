import os
import tkinter as tk
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from codex_float_ui import CodexFloatingUI
from codex_usage_chart import midnight_ticks


class MidnightTicksTest(unittest.TestCase):
    def test_chart_period_uses_reset_time_at_sample_timestamp(self):
        ui = object.__new__(CodexFloatingUI)
        ui.read_status = lambda: ({"timestamp": "2026-09-20 10:00:00",
                                  "weekly_reset": "11:32 on 24 Sep"}, None)
        self.assertEqual(ui.chart_period(), (datetime(2026, 9, 17, 11, 32),
                                             datetime(2026, 9, 24, 11, 32)))

    def test_ticks_are_calendar_midnights_inside_period(self):
        start = datetime(2026, 9, 17, 11, 32)
        end = start + timedelta(days=7)
        ticks = midnight_ticks(start, end)
        self.assertEqual(ticks, [datetime(2026, 9, day) for day in range(18, 25)])

    def test_midnight_endpoints_are_not_duplicated(self):
        start = datetime(2026, 12, 29)
        end = datetime(2027, 1, 5)
        self.assertEqual(midnight_ticks(start, end),
                         [start + timedelta(days=i) for i in range(1, 7)])


@unittest.skipUnless(os.environ.get("DISPLAY"), "Requires a graphical display")
class UsageChartTest(unittest.TestCase):
    def setUp(self):
        now = datetime.now()
        status = {"account": "test", "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                  "weekly_left": 75,
                  "weekly_reset": (now + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")}
        status_patch = patch.object(CodexFloatingUI, "read_status", return_value=(status, None))
        status_patch.start()
        self.addCleanup(status_patch.stop)
        self.ui = CodexFloatingUI()
        self.addCleanup(self.close_ui)
        self.ui.root.update()

    def close_ui(self):
        for timer in self.ui.root.tk.call("after", "info"):
            self.ui.root.after_cancel(timer)
        self.ui.root.destroy()

    def test_reset_sets_axis_range_and_excludes_previous_cycle(self):
        end = datetime.now() + timedelta(days=2)
        start = end - timedelta(days=7)
        with patch.object(self.ui, "chart_period", return_value=(start, end)), \
                patch("codex_usage_chart.read_samples", return_value=[
                    (start - timedelta(seconds=1), 10), (start, 100)]):
            self.ui.show_chart()
            self.ui.root.update()
            canvas = self.ui.chart.canvas
            points = canvas.find_withtag("quota-point")
            self.assertEqual(len(points), 1)
            self.assertAlmostEqual(canvas.coords(points[-1])[0] + 1, 52)
            self.assertEqual(len(canvas.find_withtag("midnight-grid")), 7)

    def test_missing_reset_shows_no_invented_period(self):
        with patch.object(self.ui, "chart_period", return_value=None):
            self.ui.show_chart()
            self.ui.root.update()
            canvas = self.ui.chart.canvas
            self.assertEqual(len(canvas.find_withtag("quota-line")), 0)
            self.assertTrue(canvas.find_withtag("period-unavailable"))

    def test_double_click_opens_and_outside_click_closes(self):
        label = self.ui.weekly_label
        for stamp in (1000, 1100):
            label.event_generate("<ButtonPress-1>", x=5, y=5, time=stamp)
            label.event_generate("<ButtonRelease-1>", x=5, y=5, time=stamp + 10)
        self.ui.root.update()
        self.assertIsNotNone(self.ui.chart)
        self.assertTrue(self.ui.chart.window.winfo_exists())
        self.ui.weekly_value.event_generate("<ButtonPress-1>")
        self.ui.root.update()
        self.assertFalse(self.ui.chart.window.winfo_exists())

    def test_line_and_gap_rendering_and_escape(self):
        now = datetime.now()
        samples = [(now - timedelta(minutes=10), 90),
                   (now - timedelta(minutes=9), 80), (now, 70)]
        with patch("codex_usage_chart.read_samples", return_value=samples):
            self.ui.show_chart()
            self.ui.root.update()
            self.assertEqual(len(self.ui.chart.canvas.find_withtag("quota-line")), 1)
            self.assertEqual(len(self.ui.chart.canvas.find_withtag("quota-point")), 2)
            self.ui.chart.window.event_generate("<Escape>")
            self.ui.root.update()
            self.assertFalse(self.ui.chart.window.winfo_exists())

    def test_focus_to_another_window_closes_chart(self):
        self.ui.show_chart()
        self.ui.root.update()
        other = tk.Toplevel(self.ui.root)
        other.focus_force()
        self.ui.root.update()
        self.assertFalse(self.ui.chart.window.winfo_exists())

    def test_empty_and_single_sample(self):
        for samples in ([], [(datetime.now(), 75)]):
            with patch("codex_usage_chart.read_samples", return_value=samples):
                self.ui.show_chart()
                self.ui.root.update()
                self.assertEqual(len(self.ui.chart.canvas.find_withtag("quota-line")), 0)
                self.assertEqual(bool(self.ui.chart.canvas.find_withtag("quota-point")), bool(samples))
