#!/usr/bin/env bash
set -euo pipefail

WATCH_PID="/tmp/codex_status_watch.pid"
UI_PID="/tmp/codex_float_ui.pid"
JSON_PATH="/tmp/codex_status.json"
WATCH_LOG="/tmp/codex_status_watch.log"
UI_LOG="/tmp/codex_float_ui.log"
TMUX_SESSION="codex_quota_watch"

echo "Stopping Codex usage tools..."

# 停止 watcher
if [ -f "$WATCH_PID" ]; then
  PID="$(cat "$WATCH_PID" || true)"
  if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
    echo "Stopping watcher pid: $PID"
    kill "$PID" 2>/dev/null || true
    sleep 1

    if kill -0 "$PID" 2>/dev/null; then
      echo "Force killing watcher pid: $PID"
      kill -9 "$PID" 2>/dev/null || true
    fi
  else
    echo "Watcher not running."
  fi
  rm -f "$WATCH_PID"
else
  echo "Watcher pid file not found."
fi

# 停止 UI
if [ -f "$UI_PID" ]; then
  PID="$(cat "$UI_PID" || true)"
  if [ -n "${PID:-}" ] && kill -0 "$PID" 2>/dev/null; then
    echo "Stopping UI pid: $PID"
    kill "$PID" 2>/dev/null || true
    sleep 1

    if kill -0 "$PID" 2>/dev/null; then
      echo "Force killing UI pid: $PID"
      kill -9 "$PID" 2>/dev/null || true
    fi
  else
    echo "UI not running."
  fi
  rm -f "$UI_PID"
else
  echo "UI pid file not found."
fi

# 关闭 tmux 中的 Codex 会话
if command -v tmux >/dev/null 2>&1; then
  if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    echo "Killing tmux session: $TMUX_SESSION"
    tmux kill-session -t "$TMUX_SESSION" || true
  else
    echo "tmux session not found: $TMUX_SESSION"
  fi
fi

# 可选：清理 JSON
rm -f "$JSON_PATH"

echo
echo "Stopped."
echo "Logs kept:"
echo "  $WATCH_LOG"
echo "  $UI_LOG"
