import sqlite3
import tkinter as tk
from datetime import datetime, timedelta

from codex_usage_history import read_samples


def midnight_ticks(start, end):
    tick = start.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    ticks = []
    while tick < end:
        ticks.append(tick)
        tick += timedelta(days=1)
    return ticks


class UsageChart:
    def __init__(self, root, account, get_period):
        self.root = root
        self.account = account
        self.get_period = get_period
        self.timer = None
        self.window = tk.Toplevel(root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        width = min(640, root.winfo_screenwidth())
        height = min(300, root.winfo_screenheight())
        x = min(root.winfo_x(), root.winfo_screenwidth() - width)
        y = root.winfo_y() + root.winfo_height() + 6
        if y + height > root.winfo_screenheight():
            y = root.winfo_y() - height - 6
        self.window.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
        self.canvas = tk.Canvas(self.window, bg="#171717", highlightthickness=1,
                                highlightbackground="#454545")
        self.canvas.pack(fill="both", expand=True)
        self.window.bind("<Escape>", self.close)
        self.window.bind("<FocusOut>", self.on_focus_out)
        self.window.bind("<ButtonPress>", self.on_pointer_press)
        self.window.bind("<Destroy>", self.on_destroy)
        self.canvas.bind("<Configure>", lambda event: self.draw())
        self.window.deiconify()
        self.window.update_idletasks()
        self.window.focus_force()
        # Make the chart behave like a popup: a click anywhere outside it is
        # delivered here so the first outside click can dismiss the window.
        self.window.grab_set_global()
        self.refresh()

    def close(self, event=None):
        if self.window.winfo_exists():
            if self.window.grab_current() == self.window:
                self.window.grab_release()
            self.window.destroy()

    def on_pointer_press(self, event):
        x = self.window.winfo_rootx()
        y = self.window.winfo_rooty()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        if not (x <= event.x_root < x + width and y <= event.y_root < y + height):
            self.close()
            return "break"
        return None

    def on_destroy(self, event):
        if event.widget == self.window and self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None

    def on_focus_out(self, event):
        self.root.after_idle(self.check_focus)

    def check_focus(self):
        if self.window.winfo_exists():
            focused = self.root.focus_get()
            if focused is None or focused.winfo_toplevel() != self.window:
                self.close()

    def refresh(self):
        self.draw()
        self.timer = self.root.after(5000, self.refresh)

    def draw(self):
        canvas = self.canvas
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 100 or height < 100:
            return
        left, right, top, bottom = 52, width - 26, 22, height - 38
        now = datetime.now()
        period = self.get_period()
        if period is None:
            canvas.create_text(width / 2, height / 2, text="暂无重置时间",
                               fill="#aaaaaa", tags="period-unavailable")
            return
        start, end = period
        duration = (end - start).total_seconds()
        for percent in (0, 25, 50, 75, 100):
            y = bottom - percent / 100 * (bottom - top)
            canvas.create_line(left, y, right, y, fill="#303030")
            canvas.create_text(left - 8, y, text=f"{percent}%", anchor="e", fill="#aaaaaa")
        for when in midnight_ticks(start, end):
            x = left + (when - start).total_seconds() / duration * (right - left)
            canvas.create_line(x, top, x, bottom, fill="#3a3a3a", tags="midnight-grid")
            canvas.create_text(x, bottom + 17, text=f"{when.month}.{when.day}", fill="#aaaaaa")
        if start <= now <= end:
            x = left + (now - start).total_seconds() / duration * (right - left)
            canvas.create_line(x, top, x, bottom, fill="#223629", width=1)
        try:
            samples = read_samples(self.account, now)
            samples = [(when, value) for when, value in samples if start <= when <= min(now, end)]
        except (OSError, sqlite3.Error):
            canvas.create_text((left + right) / 2, (top + bottom) / 2,
                               text="历史数据读取失败", fill="#ff6b6b")
            return
        if not samples:
            canvas.create_text((left + right) / 2, (top + bottom) / 2,
                               text="暂无历史数据", fill="#aaaaaa")
            return
        latest_y = bottom - samples[-1][1] / 100 * (bottom - top)
        canvas.create_line(left, latest_y, right, latest_y, fill="#223629", width=1)
        previous = None
        for when, value in samples:
            x = left + (when - start).total_seconds() / duration * (right - left)
            y = bottom - value / 100 * (bottom - top)
            # 停机或采集异常期间留空，避免把缺失数据画成连续走势。
            if previous and (when - previous[0]).total_seconds() <= 180:
                canvas.create_line(previous[1], previous[2], x, y,
                                   fill="#5aa9ff", width=2, tags="quota-line")
            else:
                canvas.create_oval(x - 1, y - 1, x + 1, y + 1,
                                   fill="#5aa9ff", outline="", tags="quota-point")
            previous = (when, x, y)
