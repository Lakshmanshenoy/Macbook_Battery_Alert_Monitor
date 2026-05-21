"""Unit tests for AlertManager.should_trigger_alert()."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import src.battery_alert.alerts as alerts_module
from src.battery_alert.alerts import AlertManager


class _FakeApp:
    def __init__(self, threshold: int = 20, cooldown: int = 900) -> None:
        self.settings = {
            "battery_threshold": threshold,
            "alert_cooldown_seconds": cooldown,
            "enable_sound": False,
            "enable_voice": False,
            "enable_notifications": False,
        }
        self._below_threshold_prev = False
        self._last_alert_time = None
        self.alert_history = []
        self.log_runtime = lambda *args, **kwargs: None
        self.save_alert_history = lambda: None
        self.save_config = lambda: None
        self.setup_autolaunch = lambda: None
        self.show_maintenance_status = lambda message: None
        self.show_non_blocking_feedback = lambda title, message: None
        self.preferences_window = SimpleNamespace(present=lambda: False)
        self.get_battery_info = lambda: {"level": 55, "is_charging": False, "is_discharging": True}
        self.icon_renderer = SimpleNamespace(apply=lambda level, is_charging: False)
        self.title = "🔋"
        self._last_power_state = None
        self._last_power_transition = None


class _Sender:
    def __init__(self) -> None:
        self.title = ""


def _make_manager(threshold: int = 20, cooldown: int = 900) -> AlertManager:
    return AlertManager(_FakeApp(threshold=threshold, cooldown=cooldown))


def test_no_alert_when_charging() -> None:
    manager = _make_manager()
    info = {"level": 10, "is_charging": True, "is_discharging": False}
    assert manager.should_trigger_alert(info) is False


def test_no_alert_above_threshold() -> None:
    manager = _make_manager(threshold=20)
    info = {"level": 50, "is_charging": False, "is_discharging": True}
    assert manager.should_trigger_alert(info) is False


def test_alert_on_first_threshold_crossing() -> None:
    manager = _make_manager(threshold=20)
    info = {"level": 15, "is_charging": False, "is_discharging": True}
    assert manager.should_trigger_alert(info) is True


def test_no_alert_within_cooldown() -> None:
    manager = _make_manager(cooldown=900)
    info = {"level": 15, "is_charging": False, "is_discharging": True}
    now = datetime(2026, 1, 1, 12, 0, 0)

    assert manager.should_trigger_alert(info, now=now) is True
    manager.app._last_alert_time = now
    later = now + timedelta(seconds=400)

    assert manager.should_trigger_alert(info, now=later) is False


def test_alert_after_cooldown_expires() -> None:
    manager = _make_manager(cooldown=900)
    info = {"level": 15, "is_charging": False, "is_discharging": True}
    now = datetime(2026, 1, 1, 12, 0, 0)

    manager.app._below_threshold_prev = True
    manager.app._last_alert_time = now
    later = now + timedelta(seconds=901)

    assert manager.should_trigger_alert(info, now=later) is True


def test_threshold_boundary_exact() -> None:
    manager = _make_manager(threshold=20)
    info = {"level": 20, "is_charging": False, "is_discharging": True}
    assert manager.should_trigger_alert(info) is True


def test_threshold_boundary_one_above() -> None:
    manager = _make_manager(threshold=20)
    info = {"level": 21, "is_charging": False, "is_discharging": True}
    assert manager.should_trigger_alert(info) is False


def test_resets_below_threshold_flag_on_charging() -> None:
    manager = _make_manager()
    info_low = {"level": 10, "is_charging": False, "is_discharging": True}

    assert manager.should_trigger_alert(info_low) is True
    assert manager.app._below_threshold_prev is True

    info_charging = {"level": 10, "is_charging": True, "is_discharging": False}
    assert manager.should_trigger_alert(info_charging) is False
    assert manager.app._below_threshold_prev is False


def test_trigger_alert_records_history_and_time() -> None:
    manager = _make_manager()
    now = datetime(2026, 1, 1, 12, 0, 0)

    manager.trigger_alert(15, now=now)

    assert manager.app._last_alert_time == now
    assert manager.app.alert_history[-1]["battery_level"] == 15


def test_update_boolean_setting_updates_sender_and_value() -> None:
    manager = _make_manager()
    sender = _Sender()

    manager.update_boolean_setting("enable_sound", sender, "Sound")

    assert manager.app.settings["enable_sound"] is True
    assert sender.title == "Sound: ON"


def test_toggle_update_channel_switches_value() -> None:
    manager = _make_manager()
    sender = _Sender()

    manager.toggle_update_channel(sender)

    assert manager.app.settings["update_channel"] == "beta"
    assert sender.title == "🧭 Update Channel: BETA"


def test_prompt_for_integer_setting_success(monkeypatch) -> None:
    manager = _make_manager()
    alerts = []

    class _Window:
        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            return SimpleNamespace(clicked=True, text="45")

    rumps_stub = SimpleNamespace(Window=_Window, alert=lambda message, title=None: alerts.append((message, title)))
    monkeypatch.setattr(manager, "_rumps_module", lambda: rumps_stub)

    changed = manager.prompt_for_integer_setting(
        "battery_threshold",
        "Battery Threshold",
        "Enter",
        1,
        100,
        "Set to {value}",
    )

    assert changed is True
    assert manager.app.settings["battery_threshold"] == 45
    assert alerts == [("Set to 45", "Success")]


def test_prompt_for_integer_setting_rejects_invalid_number(monkeypatch) -> None:
    manager = _make_manager()
    alerts = []

    class _Window:
        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            return SimpleNamespace(clicked=True, text="invalid")

    rumps_stub = SimpleNamespace(Window=_Window, alert=lambda message, title=None: alerts.append((message, title)))
    monkeypatch.setattr(manager, "_rumps_module", lambda: rumps_stub)

    changed = manager.prompt_for_integer_setting(
        "battery_threshold",
        "Battery Threshold",
        "Enter",
        1,
        100,
        "Set to {value}",
    )

    assert changed is False
    assert alerts == [("Please enter a valid number", "Error")]


def test_update_menu_icon_uses_charging_symbol() -> None:
    manager = _make_manager()
    manager.app.get_battery_info = lambda: {"level": 88, "is_charging": True, "is_discharging": False}

    manager.update_menu_icon()

    assert manager.app.title == "🔌 88%"


def test_update_menu_icon_uses_medium_symbol() -> None:
    manager = _make_manager()
    manager.app.get_battery_info = lambda: {"level": 35, "is_charging": False, "is_discharging": True}

    manager.update_menu_icon()

    assert manager.app.title == "🪫 35%"


def test_trigger_alert_uses_sound_and_notification_paths(monkeypatch) -> None:
    manager = _make_manager()
    manager.app.settings["enable_sound"] = True
    manager.app.settings["enable_notifications"] = True
    manager.app.settings["enable_voice"] = True
    popen_calls = []
    run_calls = []

    monkeypatch.setattr(alerts_module.os.path, "exists", lambda path: True)
    monkeypatch.setattr(alerts_module.subprocess, "Popen", lambda args: popen_calls.append(args))
    monkeypatch.setattr(
        alerts_module.subprocess,
        "run",
        lambda args, capture_output=True, text=True: run_calls.append(args) or SimpleNamespace(returncode=0, stderr=""),
    )

    manager.trigger_alert(12, now=datetime(2026, 1, 1, 9, 0, 0))

    assert ["afplay", "/System/Library/Sounds/Alarm.aiff"] in popen_calls
    assert ["say", "Battery low at 12 percent. Please charge your device."] in popen_calls
    assert run_calls and run_calls[0][0:2] == ["osascript", "-e"]


def test_set_threshold_calls_prompt(monkeypatch) -> None:
    manager = _make_manager()
    calls = []

    monkeypatch.setattr(
        manager,
        "prompt_for_integer_setting",
        lambda *args, **kwargs: calls.append(args) or True,
    )

    manager.set_threshold(None)

    assert calls and calls[0][0] == "battery_threshold"


def test_toggle_sound_updates_setting_and_sender() -> None:
    manager = _make_manager()
    sender = _Sender()
    manager.app.settings["enable_sound"] = False

    manager.toggle_sound(sender)

    assert manager.app.settings["enable_sound"] is True
    assert sender.title == "🔊 Sound Alerts: ON"


def test_toggle_autolaunch_success(monkeypatch) -> None:
    manager = _make_manager()
    sender = _Sender()
    notices = []
    manager.app.settings["auto_launch"] = False

    monkeypatch.setattr(manager, "_rumps_module", lambda: SimpleNamespace(alert=lambda msg, title=None: notices.append((msg, title))))
    manager.toggle_autolaunch(sender)

    assert manager.app.settings["auto_launch"] is True
    assert sender.title == "🚀 Launch at Startup: ON"
    assert notices and notices[-1] == ("Launch at Startup Enabled", "Success")


def test_toggle_update_checks_updates_setting() -> None:
    manager = _make_manager()
    sender = _Sender()
    manager.app.settings["enable_update_checks"] = False

    manager.toggle_update_checks(sender)

    assert manager.app.settings["enable_update_checks"] is True
    assert sender.title == "🆕 Update Checks: ON"


def test_monitor_battery_triggers_alert_once() -> None:
    manager = _make_manager(cooldown=10)
    triggered = []

    class _StopEvent:
        def __init__(self) -> None:
            self.calls = 0

        def is_set(self) -> bool:
            return self.calls > 0

        def wait(self, _seconds: int) -> None:
            self.calls += 1

    manager.app.stop_event = _StopEvent()
    manager.app.monitoring = True
    manager.app.settings["check_interval"] = 1
    manager.app.get_battery_info = lambda: {"level": 15, "is_charging": False, "is_discharging": True}
    manager.app.should_trigger_alert = lambda info, now=None: True
    manager.app.trigger_alert = lambda level, now=None: triggered.append((level, now is not None))

    manager.monitor_battery()

    assert triggered == [(15, True)]
