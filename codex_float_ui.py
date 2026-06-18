#!/usr/bin/env python3
import json
import os
import re
import tkinter as tk
from datetime import datetime, timedelta


JSON_PATH = "/tmp/codex_status.json"
REFRESH_MS = 5000

BAR_WIDTH = 155
BAR_HEIGHT = 8
TIME_BAR_HEIGHT = 3
H5_WINDOW_MINUTES = 5 * 60
WEEKLY_WINDOW_MINUTES = 7 * 24 * 60
TIME_WINDOWS = {
    "h5": H5_WINDOW_MINUTES,
    "weekly": WEEKLY_WINDOW_MINUTES,
}


def parse_reset_datetime(reset_text: str, now: datetime | None = None):
    if now is None:
        now = datetime.now()

    if not reset_text:
        return None

    text = reset_text.strip()
    if not text or text.upper() == "N/A":
        return None

    low = text.lower()
    if low.startswith("in "):
        total_minutes = 0
        matches = re.findall(
            r"(\d+)\s*(d|day|days|h|hr|hrs|hour|hours|m|min|mins|minute|minutes)",
            low,
        )
        for amount, unit in matches:
            amount = int(amount)
            if unit.startswith("d"):
                total_minutes += amount * 24 * 60
            elif unit.startswith("h"):
                total_minutes += amount * 60
            else:
                total_minutes += amount
        if total_minutes > 0:
            return now + timedelta(minutes=total_minutes)

    normalized = re.sub(r"\bat\b", "", text, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip().rstrip(".")

    year_formats = (
        ("%Y-%m-%d %H:%M:%S", normalized),
        ("%Y-%m-%d %H:%M", normalized),
        ("%Y %b %d %H:%M", f"{now.year} {normalized}"),
        ("%Y %b %d, %H:%M", f"{now.year} {normalized}"),
        ("%Y %b %d %I:%M %p", f"{now.year} {normalized}"),
        ("%Y %b %d, %I:%M %p", f"{now.year} {normalized}"),
    )
    for fmt, value in year_formats:
        try:
            parsed = datetime.strptime(value, fmt)
            if not normalized.startswith(str(now.year)) and parsed <= now:
                parsed = parsed.replace(year=now.year + 1)
            return parsed
        except ValueError:
            pass

    time_formats = ("%I:%M %p", "%H:%M")
    for fmt in time_formats:
        try:
            parsed_time = datetime.strptime(normalized, fmt).time()
            parsed = datetime.combine(now.date(), parsed_time)
            if parsed <= now:
                parsed += timedelta(days=1)
            return parsed
        except ValueError:
            pass

    return None


def time_remaining_percent(
    reset_text: str,
    window_minutes: int,
    now: datetime | None = None,
):
    if now is None:
        now = datetime.now()

    reset_dt = parse_reset_datetime(reset_text, now)
    if reset_dt is None or window_minutes <= 0:
        return None

    remaining_minutes = (reset_dt - now).total_seconds() / 60
    if remaining_minutes < 0:
        return None

    remaining_ratio = remaining_minutes / window_minutes
    remaining_percent = round(max(0, min(1, remaining_ratio)) * 100)
    return remaining_percent


class CodexFloatingUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Codex Usage")

        # 悬浮、半透明、无边框
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.94)
        self.root.overrideredirect(True)

        # 初始位置
        self.root.geometry("+1180+80")

        self.drag_x = 0
        self.drag_y = 0

        self.build_ui()
        self.bind_drag_events()
        self.update_ui()

    def build_ui(self):
        self.frame = tk.Frame(
            self.root,
            bg="#111111",
            padx=11,
            pady=8,
            highlightthickness=1,
            highlightbackground="#2c2c2c",
        )
        self.frame.pack()

        # Header
        self.header = tk.Frame(self.frame, bg="#111111")
        self.header.pack(fill="x")

        self.title_label = tk.Label(
            self.header,
            text="Codex Usage",
            bg="#111111",
            fg="#f5f5f5",
            font=("Ubuntu Mono", 10, "bold"),
        )
        self.title_label.pack(side="left")

        self.close_label = tk.Label(
            self.header,
            text="×",
            bg="#111111",
            fg="#9a9a9a",
            font=("Ubuntu Mono", 11, "bold"),
            cursor="hand2",
            padx=4,
        )
        self.close_label.pack(side="right")
        self.close_label.bind("<Button-1>", lambda e: self.root.destroy())

        tk.Label(self.frame, text="", bg="#111111", height=1).pack()

        self.build_section("5H", "h5")
        self.build_section("Weekly", "weekly")

        self.footer = tk.Label(
            self.frame,
            text="updated: N/A",
            bg="#111111",
            fg="#6f6f6f",
            font=("Ubuntu Mono", 8),
            anchor="w",
            justify="left",
        )
        self.footer.pack(fill="x", pady=(3, 0))

    def build_section(self, name, attr_prefix):
        container = tk.Frame(self.frame, bg="#111111")
        container.pack(fill="x", pady=(0, 5))

        # 第一行：名称 + 百分比
        top_row = tk.Frame(container, bg="#111111")
        top_row.pack(fill="x")

        label = tk.Label(
            top_row,
            text=name,
            bg="#111111",
            fg="#b0b0b0",
            font=("Ubuntu Mono", 10),
            anchor="w",
        )
        label.pack(side="left")

        value = tk.Label(
            top_row,
            text="N/A",
            bg="#111111",
            fg="#ffffff",
            font=("Ubuntu Mono", 10, "bold"),
            anchor="e",
        )
        value.pack(side="right")

        # 第二行：额度进度条
        bar_canvas = tk.Canvas(
            container,
            width=BAR_WIDTH,
            height=BAR_HEIGHT,
            bg="#111111",
            highlightthickness=0,
            bd=0,
        )
        # fill="x" 保证进度条右侧和百分比右侧对齐
        bar_canvas.pack(fill="x", pady=(3, 0))

        # 第三行：时间进度条
        time_bar_canvas = tk.Canvas(
            container,
            width=BAR_WIDTH,
            height=TIME_BAR_HEIGHT,
            bg="#111111",
            highlightthickness=0,
            bd=0,
        )
        time_bar_canvas.pack(fill="x", pady=(0, 1))

        # 第四行：reset
        reset = tk.Label(
            container,
            text="reset N/A",
            bg="#111111",
            fg="#8a8a8a",
            font=("Ubuntu Mono", 8),
            anchor="w",
        )
        reset.pack(fill="x")

        setattr(self, f"{attr_prefix}_container", container)
        setattr(self, f"{attr_prefix}_label", label)
        setattr(self, f"{attr_prefix}_value", value)
        setattr(self, f"{attr_prefix}_bar", bar_canvas)
        setattr(self, f"{attr_prefix}_time_bar", time_bar_canvas)
        setattr(self, f"{attr_prefix}_reset", reset)

    def bind_drag_events(self):
        widgets = [
            self.frame,
            self.header,
            self.title_label,
            self.footer,
            self.h5_container,
            self.h5_label,
            self.h5_value,
            self.h5_bar,
            self.h5_time_bar,
            self.h5_reset,
            self.weekly_container,
            self.weekly_label,
            self.weekly_value,
            self.weekly_bar,
            self.weekly_time_bar,
            self.weekly_reset,
        ]

        for widget in widgets:
            widget.bind("<ButtonPress-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.drag)

    def start_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def drag(self, event):
        x = self.root.winfo_pointerx() - self.drag_x
        y = self.root.winfo_pointery() - self.drag_y
        self.root.geometry(f"+{x}+{y}")

    def read_status(self):
        if not os.path.exists(JSON_PATH):
            return None, f"JSON not found:\n{JSON_PATH}"

        try:
            with open(JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            status = data.get("status") or {}
            timestamp = data.get("timestamp") or ""

            return {
                "timestamp": timestamp,
                "h5_left": status.get("limit_5h_left_percent"),
                "h5_reset": status.get("limit_5h_reset") or "N/A",
                "weekly_left": status.get("weekly_left_percent"),
                "weekly_reset": status.get("weekly_reset") or "N/A",
            }, None

        except Exception as e:
            return None, f"Read error:\n{e}"

    def color_by_left(self, left_percent):
        if left_percent is None:
            return "#5a5a5a"

        try:
            left_percent = int(left_percent)
        except Exception:
            return "#5a5a5a"

        if left_percent <= 10:
            return "#ff6b6b"   # red
        if left_percent <= 30:
            return "#f0b35a"   # orange
        return "#5aa9ff"       # blue

    def draw_progress_bar(self, canvas, left_percent):
        canvas.delete("all")

        # 使用实际 canvas 宽度，保证右侧和百分比右侧对齐
        width = max(canvas.winfo_width(), BAR_WIDTH)
        height = BAR_HEIGHT
        pad = 1

        # 背景
        canvas.create_rectangle(
            0,
            0,
            width,
            height,
            fill="#262626",
            outline="#262626",
        )

        if left_percent is None:
            return

        try:
            left_percent = int(left_percent)
        except Exception:
            return

        left_percent = max(0, min(100, left_percent))
        fill_width = int((left_percent / 100) * width)
        fill_color = self.color_by_left(left_percent)

        if fill_width > 0:
            canvas.create_rectangle(
                pad,
                pad,
                fill_width,
                height - pad,
                fill=fill_color,
                outline=fill_color,
            )

    def draw_time_bar(self, canvas, remaining_percent):
        canvas.delete("all")

        width = max(canvas.winfo_width(), BAR_WIDTH)
        height = TIME_BAR_HEIGHT
        pad = 1

        canvas.create_rectangle(
            0,
            0,
            width,
            height,
            fill="#1f1f1f",
            outline="#1f1f1f",
        )

        if remaining_percent is None:
            return

        try:
            remaining_percent = int(remaining_percent)
        except Exception:
            return

        remaining_percent = max(0, min(100, remaining_percent))
        fill_width = int((remaining_percent / 100) * width)

        if fill_width > 0:
            canvas.create_rectangle(
                pad,
                0,
                fill_width,
                height,
                fill="#7a7a7a",
                outline="#7a7a7a",
            )

    def format_time(self, timestamp: str) -> str:
        if not timestamp:
            return "updated: N/A"

        try:
            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            return f"updated: {dt.strftime('%H:%M:%S')}"
        except Exception:
            return f"updated: {timestamp}"

    def update_section(self, prefix, left_value, reset_text):
        value_label = getattr(self, f"{prefix}_value")
        bar_canvas = getattr(self, f"{prefix}_bar")
        time_bar_canvas = getattr(self, f"{prefix}_time_bar")
        reset_label = getattr(self, f"{prefix}_reset")

        if left_value is None:
            value_label.config(text="N/A", fg="#ffcc66")
            reset_label.config(text="reset N/A")
            self.draw_progress_bar(bar_canvas, None)
            self.draw_time_bar(time_bar_canvas, None)
            return

        try:
            left_value = int(left_value)
        except Exception:
            value_label.config(text="N/A", fg="#ffcc66")
            reset_label.config(text="reset N/A")
            self.draw_progress_bar(bar_canvas, None)
            self.draw_time_bar(time_bar_canvas, None)
            return

        value_label.config(
            text=f"{left_value}%",
            fg=self.color_by_left(left_value),
        )

        reset_label.config(text=f"reset {reset_text}")

        # 等布局完成后再绘制，确保 canvas 宽度正确
        self.root.after(10, lambda: self.draw_progress_bar(bar_canvas, left_value))
        time_percent = time_remaining_percent(reset_text, TIME_WINDOWS.get(prefix, 0))
        self.root.after(10, lambda: self.draw_time_bar(time_bar_canvas, time_percent))

    def update_ui(self):
        data, error = self.read_status()

        if error:
            self.update_section("h5", None, "N/A")
            self.update_section("weekly", None, "N/A")
            self.footer.config(text=error)
        else:
            self.update_section("h5", data["h5_left"], data["h5_reset"])
            self.update_section("weekly", data["weekly_left"], data["weekly_reset"])
            self.footer.config(text=self.format_time(data["timestamp"]))

        self.root.after(REFRESH_MS, self.update_ui)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    CodexFloatingUI().run()
