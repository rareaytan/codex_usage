#!/usr/bin/env python3
"""Open the usage history chart without showing the floating quota window."""

import json
import tkinter as tk
from datetime import datetime, timedelta

from codex_float_ui import parse_reset_datetime
from codex_usage_chart import UsageChart


JSON_PATH = "/tmp/codex_status.json"


def read_period():
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as status_file:
            data = json.load(status_file)
        sampled_at = datetime.strptime(data["timestamp"], "%Y-%m-%d %H:%M:%S")
        reset = parse_reset_datetime(data["status"]["weekly_reset"], sampled_at)
        if reset is None:
            return None
        return reset - timedelta(days=7), reset
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def read_account():
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as status_file:
            return (json.load(status_file).get("status") or {}).get("account") or ""
    except (OSError, ValueError):
        return ""


def main():
    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()
    x = max(0, root.winfo_screenwidth() - 660)
    root.geometry(f"1x1+{x}+32")

    chart = UsageChart(root, read_account(), read_period)

    def exit_when_closed(event):
        if event.widget == chart.window:
            root.after_idle(root.destroy)

    chart.window.bind("<Destroy>", exit_when_closed, add="+")
    root.mainloop()


if __name__ == "__main__":
    main()
