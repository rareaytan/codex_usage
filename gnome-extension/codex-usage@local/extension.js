import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';

import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const STATUS_PATH = '/tmp/codex_status.json';
const REFRESH_SECONDS = 5;
const STALE_SECONDS = 180;
const MONTHS = {
    Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5,
    Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11,
};

const COLORS = {
    normal: '#ffffff',
    warning: '#f0b35a',
    stale: '#ff6b6b',
    unavailable: '#aaaaaa',
};

const CodexUsageIndicator = GObject.registerClass(
class CodexUsageIndicator extends PanelMenu.Button {
    _init() {
        super._init(0.0, 'Codex Usage', false);

        this._decoder = new TextDecoder();
        this._timerId = 0;

        this._label = new St.Label({
            text: 'codex:--% time:--%',
            y_align: Clutter.ActorAlign.CENTER,
            style_class: 'codex-usage-label',
        });
        this.add_child(this._label);

        this._accountItem = this._makeInfoItem('账户', 'N/A');
        this._fiveHourItem = this._makeInfoItem('5h 额度', 'N/A');
        this._fiveHourResetItem = this._makeInfoItem('5h 重置', 'N/A');
        this._quotaItem = this._makeInfoItem('7 天额度', 'N/A');
        this._timeItem = this._makeInfoItem('时间额度', 'N/A');
        this._resetItem = this._makeInfoItem('重置时间', 'N/A');
        this._updatedItem = this._makeInfoItem('更新时间', 'N/A');

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        const chartItem = new PopupMenu.PopupMenuItem('打开额度曲线');
        chartItem.connect('activate', () => this._openChart());
        this.menu.addMenuItem(chartItem);

        const refreshItem = new PopupMenu.PopupMenuItem('立即刷新显示');
        refreshItem.connect('activate', () => this._refresh());
        this.menu.addMenuItem(refreshItem);

        this._refresh();
        this._timerId = GLib.timeout_add_seconds(
            GLib.PRIORITY_DEFAULT,
            REFRESH_SECONDS,
            () => {
                this._refresh();
                return GLib.SOURCE_CONTINUE;
            }
        );
    }

    _makeInfoItem(name, value) {
        const item = new PopupMenu.PopupBaseMenuItem({reactive: false});
        const nameLabel = new St.Label({
            text: name,
            style_class: 'codex-usage-info-name',
        });
        const valueLabel = new St.Label({
            text: value,
            x_expand: true,
            x_align: Clutter.ActorAlign.END,
            style_class: 'codex-usage-info-value',
        });
        item.add_child(nameLabel);
        item.add_child(valueLabel);
        item._nameLabel = nameLabel;
        item._valueLabel = valueLabel;
        this.menu.addMenuItem(item);
        return item;
    }

    _setUnavailable(message = '等待数据') {
        this._label.text = 'codex:--% time:--%';
        this._label.set_style(`color: ${COLORS.unavailable};`);
        this._accountItem._valueLabel.text = message;
        this._fiveHourItem._valueLabel.text = 'N/A';
        this._fiveHourResetItem._valueLabel.text = 'N/A';
        this._quotaItem._valueLabel.text = 'N/A';
        this._timeItem._valueLabel.text = 'N/A';
        this._resetItem._valueLabel.text = 'N/A';
        this._updatedItem._valueLabel.text = 'N/A';
        this._fiveHourItem.hide();
        this._fiveHourResetItem.hide();
    }

    _isStale(timestamp) {
        if (!timestamp)
            return true;

        const parsed = new Date(timestamp.replace(' ', 'T'));
        if (Number.isNaN(parsed.getTime()))
            return true;

        return Date.now() - parsed.getTime() > STALE_SECONDS * 1000;
    }

    _remainingTimePercent(resetText) {
        // Codex may emit either "17:58 on 29 Sep" or
        // "10:35 AM on 4 Oct" depending on the client version.
        const match = resetText.match(
            /^(\d{1,2}):(\d{2})(?:\s+(AM|PM))?\s+on\s+(\d{1,2})\s+([A-Za-z]{3})$/i
        );
        if (!match)
            return null;

        const monthName = match[5][0].toUpperCase() + match[5].slice(1).toLowerCase();
        const month = MONTHS[monthName];
        if (month === undefined)
            return null;

        let hour = Number(match[1]);
        const meridiem = match[3]?.toUpperCase();
        if (meridiem === 'AM')
            hour %= 12;
        else if (meridiem === 'PM')
            hour = hour % 12 + 12;

        const now = new Date();
        let reset = new Date(
            now.getFullYear(), month, Number(match[4]),
            hour, Number(match[2]), 0, 0
        );
        if (reset <= now)
            reset.setFullYear(reset.getFullYear() + 1);

        return Math.trunc(Math.max(0, Math.min(100,
            (reset.getTime() - now.getTime()) / (7 * 24 * 60 * 60 * 1000) * 100)));
    }

    _isBehindTime(leftPercent, timePercent) {
        if (timePercent === null)
            return false;

        const remainingPercent = timePercent;
        const currentDayFloor = Math.floor(remainingPercent / (100 / 7)) * (100 / 7);
        return leftPercent < currentDayFloor;
    }

    _render(data) {
        const status = data.status ?? {};
        if (status.weekly_left_percent === null ||
            status.weekly_left_percent === undefined) {
            this._setUnavailable('额度尚未就绪');
            return;
        }
        const left = Number(status.weekly_left_percent);
        if (!Number.isFinite(left)) {
            this._setUnavailable('额度尚未就绪');
            return;
        }

        const percent = Math.max(0, Math.min(100, Math.trunc(left)));
        const reset = status.weekly_reset || 'N/A';
        const rawFiveHour = status.five_hour_left_percent;
        const parsedFiveHour = Number(rawFiveHour);
        const hasFiveHour = rawFiveHour !== null && rawFiveHour !== undefined &&
            Number.isFinite(parsedFiveHour);
        const plusMode = hasFiveHour || /\bplus\b/i.test(status.account || '');
        const fiveHourPercent = hasFiveHour
            ? Math.max(0, Math.min(100, Math.trunc(parsedFiveHour)))
            : null;
        const timePercent = this._remainingTimePercent(reset);
        const stale = this._isStale(data.timestamp);
        const warning = this._isBehindTime(percent, timePercent);
        const color = stale ? COLORS.stale : warning ? COLORS.warning : COLORS.normal;

        const timeText = timePercent === null ? '--' : timePercent;
        if (plusMode) {
            const fiveHourText = fiveHourPercent === null ? '--' : fiveHourPercent;
            this._label.text = `5h:${fiveHourText}% week:${percent}%`;
            this._fiveHourItem.show();
            this._fiveHourResetItem.show();
            this._timeItem.hide();
            this._fiveHourItem._valueLabel.text = fiveHourPercent === null
                ? 'N/A' : `${fiveHourPercent}%`;
            this._fiveHourResetItem._valueLabel.text = status.five_hour_reset || 'N/A';
            this._quotaItem._nameLabel.text = '1 周额度';
            this._resetItem._nameLabel.text = '1 周重置';
        } else {
            this._label.text = `codex:${percent}% time:${timeText}%`;
            this._fiveHourItem.hide();
            this._fiveHourResetItem.hide();
            this._timeItem.show();
            this._quotaItem._nameLabel.text = '7 天额度';
            this._resetItem._nameLabel.text = '重置时间';
        }
        this._label.set_style(`color: ${color};`);
        this._accountItem._valueLabel.text = status.account || 'N/A';
        this._quotaItem._valueLabel.text = stale ? `${percent}%（数据过期）` : `${percent}%`;
        this._timeItem._valueLabel.text = timePercent === null ? 'N/A' : `${timePercent}%`;
        this._resetItem._valueLabel.text = reset;
        this._updatedItem._valueLabel.text = data.timestamp || 'N/A';
    }

    _refresh() {
        try {
            const file = Gio.File.new_for_path(STATUS_PATH);
            const [ok, contents] = file.load_contents(null);
            if (!ok) {
                this._setUnavailable();
                return;
            }
            this._render(JSON.parse(this._decoder.decode(contents)));
        } catch (error) {
            this._setUnavailable('无法读取数据');
        }
    }

    _openChart() {
        const launcher = GLib.build_filenamev([
            GLib.get_home_dir(), '.local', 'bin', 'codex-usage-chart',
        ]);
        try {
            Gio.Subprocess.new([launcher], Gio.SubprocessFlags.NONE);
        } catch (error) {
            Main.notify('Codex Usage', '曲线启动失败，请重新运行 install_gnome_extension.sh');
        }
    }

    destroy() {
        if (this._timerId) {
            GLib.source_remove(this._timerId);
            this._timerId = 0;
        }
        super.destroy();
    }
});

export default class CodexUsageExtension extends Extension {
    enable() {
        this._indicator = new CodexUsageIndicator();
        Main.panel.addToStatusArea(this.uuid, this._indicator, 1, 'left');
    }

    disable() {
        this._indicator?.destroy();
        this._indicator = null;
    }
}
