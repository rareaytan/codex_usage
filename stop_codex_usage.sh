#!/usr/bin/env bash
set -euo pipefail

JSON_PATH="/tmp/codex_status.json"
WATCH_LOG="/tmp/codex_status_watch.log"
TMUX_SESSION="codex_quota_watch"
SERVICE="codex-usage-watcher.service"

echo "Stopping Codex usage tools..."

# 同时停止服务和旧版脚本直接启动的进程，避免匹配到 shell 命令文本。
systemctl --user stop "$SERVICE" 2>/dev/null || true
PYTHON_PROCESS='^([^[:space:]]*/)?python3([.][0-9]+)?[[:space:]]+'
PROCESS_PATTERN="${PYTHON_PROCESS}([^[:space:]]*/)?(codex_tmux_status_watch|codex_float_ui|show_codex_usage_chart)[.]py([[:space:]]|$)|^([^[:space:]]*/)?codex-usage-chart([[:space:]]|$)"
for OLD_PID in $(pgrep -u "$(id -u)" -f "$PROCESS_PATTERN" 2>/dev/null || true); do
  echo "Stopping usage process: $OLD_PID"
  kill "$OLD_PID" 2>/dev/null || true
done
sleep 1

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
rm -f "$JSON_PATH" /tmp/codex_status_watch.pid

echo
echo "Stopped."
echo "Logs kept:"
echo "  $WATCH_LOG"
