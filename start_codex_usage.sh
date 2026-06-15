#!/usr/bin/env bash
set -euo pipefail

# 当前脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Codex 进入的工作目录；默认是当前执行命令的目录
WORKDIR="${1:-$PWD}"

# 固定配置
JSON_PATH="/tmp/codex_status.json"
WATCH_LOG="/tmp/codex_status_watch.log"
UI_LOG="/tmp/codex_float_ui.log"
WATCH_PID="/tmp/codex_status_watch.pid"
UI_PID="/tmp/codex_float_ui.pid"
TMUX_SESSION="codex_quota_watch"

WATCH_SCRIPT="$SCRIPT_DIR/codex_tmux_status_watch.py"
UI_SCRIPT="$SCRIPT_DIR/codex_float_ui.py"

echo "Starting Codex usage watcher..."
echo "Script dir : $SCRIPT_DIR"
echo "Workdir    : $WORKDIR"
echo "JSON       : $JSON_PATH"
echo

# 基础检查
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found"
  exit 1
fi

if ! command -v tmux >/dev/null 2>&1; then
  echo "ERROR: tmux not found. Install with:"
  echo "  sudo apt install -y tmux"
  exit 1
fi

if [ ! -f "$WATCH_SCRIPT" ]; then
  echo "ERROR: watcher script not found: $WATCH_SCRIPT"
  exit 1
fi

if [ ! -f "$UI_SCRIPT" ]; then
  echo "ERROR: UI script not found: $UI_SCRIPT"
  exit 1
fi

# 如果旧 watcher 还在，先杀掉
if [ -f "$WATCH_PID" ]; then
  OLD_WATCH_PID="$(cat "$WATCH_PID" || true)"
  if [ -n "${OLD_WATCH_PID:-}" ] && kill -0 "$OLD_WATCH_PID" 2>/dev/null; then
    echo "Stopping old watcher pid: $OLD_WATCH_PID"
    kill "$OLD_WATCH_PID" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$WATCH_PID"
fi

# 如果旧 UI 还在，先杀掉
if [ -f "$UI_PID" ]; then
  OLD_UI_PID="$(cat "$UI_PID" || true)"
  if [ -n "${OLD_UI_PID:-}" ] && kill -0 "$OLD_UI_PID" 2>/dev/null; then
    echo "Stopping old UI pid: $OLD_UI_PID"
    kill "$OLD_UI_PID" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$UI_PID"
fi

# 清理旧 JSON，避免 UI 读到旧数据
rm -f "$JSON_PATH"

# 启动 watcher
nohup python3 "$WATCH_SCRIPT" "$WORKDIR" \
  --auto-trust \
  --interval 60 \
  --json-out "$JSON_PATH" \
  > "$WATCH_LOG" 2>&1 &

WATCHER_PID=$!
echo "$WATCHER_PID" > "$WATCH_PID"

echo "Watcher PID: $WATCHER_PID"
echo "Waiting for JSON..."

# 等待 JSON 生成
for i in $(seq 1 20); do
  if [ -f "$JSON_PATH" ]; then
    echo "JSON ready."
    break
  fi

  if ! kill -0 "$WATCHER_PID" 2>/dev/null; then
    echo "ERROR: watcher exited early. Log:"
    cat "$WATCH_LOG"
    exit 1
  fi

  sleep 1
done

if [ ! -f "$JSON_PATH" ]; then
  echo "WARNING: JSON not generated yet, UI will show waiting state."
  echo "Check watcher log:"
  echo "  cat $WATCH_LOG"
fi

# 启动悬浮 UI
nohup python3 "$UI_SCRIPT" > "$UI_LOG" 2>&1 &

FLOAT_UI_PID=$!
echo "$FLOAT_UI_PID" > "$UI_PID"

echo
echo "Started."
echo "Watcher PID : $WATCHER_PID"
echo "UI PID      : $FLOAT_UI_PID"
echo "tmux session: $TMUX_SESSION"
echo
echo "Logs:"
echo "  watcher: $WATCH_LOG"
echo "  UI     : $UI_LOG"
echo
echo "Attach Codex session:"
echo "  tmux attach -t $TMUX_SESSION"
echo
echo "Stop:"
echo "  $SCRIPT_DIR/stop_codex_usage.sh"
