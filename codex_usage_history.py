import math
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


HISTORY_PATH = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "codex_usage/history.sqlite3"


def record_sample(payload, path=HISTORY_PATH):
    status = payload.get("status") or {}
    value = status.get("weekly_left_percent")
    if (type(value) not in (int, float) or not math.isfinite(value)
            or not 0 <= value <= 100):
        return
    try:
        when = datetime.strptime(payload["timestamp"], "%Y-%m-%d %H:%M:%S")
    except (KeyError, TypeError, ValueError):
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=1) as db:
        db.execute("CREATE TABLE IF NOT EXISTS samples ("
                   "account TEXT, timestamp TEXT, remaining REAL, "
                   "PRIMARY KEY (account, timestamp))")
        db.execute("INSERT OR REPLACE INTO samples VALUES (?, ?, ?)",
                   (status.get("account") or "", when.isoformat(), value))
        db.execute("DELETE FROM samples WHERE timestamp < ?",
                   ((when - timedelta(days=7)).isoformat(),))


def read_samples(account, now=None, path=HISTORY_PATH):
    now = now or datetime.now()
    path = Path(path)
    if not path.exists():
        return []
    with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=1) as db:
        rows = db.execute(
            "SELECT timestamp, remaining FROM samples "
            "WHERE account = ? AND timestamp >= ? AND timestamp <= ? ORDER BY timestamp",
            (account, (now - timedelta(days=7)).isoformat(), now.isoformat()),
        ).fetchall()
    return [(datetime.fromisoformat(timestamp), value) for timestamp, value in rows]
