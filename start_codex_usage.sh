#!/usr/bin/env bash
set -euo pipefail

# 当前脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Codex 进入的工作目录；默认是当前执行命令的目录
WORKDIR="${1:-$PWD}"

# 固定配置
JSON_PATH="/tmp/codex_status.json"
WATCH_LOG="/tmp/codex_status_watch.log"
WATCH_PID="/tmp/codex_status_watch.pid"
TMUX_SESSION="codex_quota_watch"
SERVICE="codex-usage-watcher.service"

WATCH_SCRIPT="$SCRIPT_DIR/codex_tmux_status_watch.py"
READY_SCRIPT="$SCRIPT_DIR/codex_status_ready.py"

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

if ! command -v codex >/dev/null 2>&1; then
  echo "ERROR: codex not found in PATH"
  exit 1
fi

if ! systemctl --user show-environment >/dev/null 2>&1; then
  echo "ERROR: a running systemd user session is required (Ubuntu 24.04)."
  exit 1
fi

if [ ! -d "$WORKDIR" ]; then
  echo "ERROR: workdir not found: $WORKDIR"
  exit 1
fi
WORKDIR="$(cd "$WORKDIR" && pwd)"

if [ ! -f "$WATCH_SCRIPT" ]; then
  echo "ERROR: watcher script not found: $WATCH_SCRIPT"
  exit 1
fi

if [ ! -f "$READY_SCRIPT" ]; then
  echo "ERROR: status ready script not found: $READY_SCRIPT"
  exit 1
fi

# 停止上一次启动的服务；仅匹配实际 Python 程序，避免误杀编辑器或 shell。
systemctl --user stop "$SERVICE" 2>/dev/null || true
PYTHON_PROCESS='^([^[:space:]]*/)?python3([.][0-9]+)?[[:space:]]+'
PROCESS_PATTERN="${PYTHON_PROCESS}([^[:space:]]*/)?(codex_tmux_status_watch|codex_float_ui|show_codex_usage_chart)[.]py([[:space:]]|$)|^([^[:space:]]*/)?codex-usage-chart([[:space:]]|$)"
for OLD_PID in $(pgrep -u "$(id -u)" -f "$PROCESS_PATTERN" 2>/dev/null || true); do
  echo "Stopping old usage process: $OLD_PID"
  kill "$OLD_PID" 2>/dev/null || true
done
sleep 1

# 清理 PID 文件和旧 JSON
rm -f "$WATCH_PID" "$JSON_PATH"

# 由用户服务管理后台进程，关闭启动终端后继续采集，异常退出时自动重启。
systemd-run --user --unit="$SERVICE" --collect \
  --description="Codex usage quota watcher" \
  --property=Restart=on-failure \
  --property=RestartSec=5 \
  --property="WorkingDirectory=$SCRIPT_DIR" \
  --property="StandardOutput=append:$WATCH_LOG" \
  --property="StandardError=append:$WATCH_LOG" \
  --setenv="PATH=$PATH" \
  "$(command -v python3)" -u "$WATCH_SCRIPT" "$WORKDIR" \
  --auto-trust \
  --no-clear \
  --interval 60 \
  --json-out "$JSON_PATH"

WATCHER_PID="$(systemctl --user show "$SERVICE" --property=MainPID --value)"
echo "$WATCHER_PID" > "$WATCH_PID"

echo "Watcher PID: $WATCHER_PID"
echo "Waiting for quota values..."

# 等待 JSON 中出现有效额度，避免首次冷启动时 UI 先读到空解析结果
for i in $(seq 1 30); do
  if python3 "$READY_SCRIPT" "$JSON_PATH"; then
    echo "Quota values ready."
    break
  fi

  if ! systemctl --user is-active --quiet "$SERVICE"; then
    echo "ERROR: watcher exited early. Log:"
    cat "$WATCH_LOG"
    exit 1
  fi

  sleep 1
done

if ! python3 "$READY_SCRIPT" "$JSON_PATH"; then
  echo "WARNING: quota values not ready yet, UI will show waiting state."
  echo "Check watcher log:"
  echo "  cat $WATCH_LOG"
fi

echo
echo "Started."
echo "Watcher PID : $WATCHER_PID"
echo "User service: $SERVICE"
echo "tmux session: $TMUX_SESSION"
echo
echo "Logs:"
echo "  watcher: $WATCH_LOG"
echo
echo "Attach Codex session:"
echo "  tmux attach -t $TMUX_SESSION"
echo
echo "Stop:"
echo "  $SCRIPT_DIR/stop_codex_usage.sh"
