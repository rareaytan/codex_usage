# Codex Usage Monitor

显示 Codex 额度和状态。

![运行效果](docs/images/image.png)

## 依赖安装

- 安装 tmux：
  ```bash
  sudo apt install -y tmux
  ```

- 如果悬浮窗无法启动，安装 tkinter：
  ```bash
  sudo apt install -y python3-tk
  ```

## 使用

启动：

```bash
./start_codex_usage.sh
```

停止：

```bash
./stop_codex_usage.sh
```

## 说明

- `start_codex_usage.sh`：启动后台 watcher 和悬浮窗
- `stop_codex_usage.sh`：关闭相关进程和 `tmux` 会话
- `codex_tmux_status_watch.py`：读取 Codex `/status`
- `codex_float_ui.py`：显示浮窗内容
- 双击 `7days` 打开当前 7 天额度周期的剩余额度折线图（0–100%），点击窗外或按 Esc 关闭。横轴终点为额度重置时间，起点往前推 7 天；每日凌晨 00:00 为分割线并标注日期，未来时段留空。
- 每次成功采集后保存历史数据，默认位于 `~/.local/state/codex_usage/history.sqlite3`（支持 `XDG_STATE_HOME`）。重启后保留最近 7 天数据；首次启用前的数据无法补回，超过 3 分钟的采集空档不连线。
