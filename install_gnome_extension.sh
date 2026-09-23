#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UUID="codex-usage@local"
SOURCE_DIR="$SCRIPT_DIR/gnome-extension/$UUID"
TARGET_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/gnome-shell/extensions/$UUID"
BIN_DIR="$HOME/.local/bin"

if ! command -v gnome-extensions >/dev/null 2>&1; then
  echo "ERROR: gnome-extensions not found; this installer requires GNOME Shell."
  exit 1
fi

mkdir -p "$TARGET_DIR" "$BIN_DIR"
cp -a "$SOURCE_DIR/." "$TARGET_DIR/"
ln -sfn "$SCRIPT_DIR/show_codex_usage_chart.py" "$BIN_DIR/codex-usage-chart"
chmod +x "$SCRIPT_DIR/show_codex_usage_chart.py"

echo "Installed extension: $TARGET_DIR"
echo "Installed chart launcher: $BIN_DIR/codex-usage-chart"

if gnome-extensions enable "$UUID" 2>/dev/null; then
  echo "Enabled extension: $UUID"
else
  echo
  echo "The running GNOME Shell has not discovered the new extension yet."
  echo "Log out and back in, then run:"
  echo "  gnome-extensions enable $UUID"
fi
