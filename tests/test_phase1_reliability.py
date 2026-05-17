import importlib
from datetime import datetime, timedelta
from pathlib import Path
import json
import zipfile
import sys
import types


def _install_rumps_stub():
    rumps_stub = types.ModuleType("rumps")

    class DummyApp:
        def __init__(self, *args, **kwargs):
            self.title = ""
            self.menu = []

        def run(self):
            return None

    class DummyMenuItem:
        def __init__(self, title, callback=None):
            self.title = title
            self.callback = callback

    class DummyWindow:
        next_response = types.SimpleNamespace(clicked=False, text="")

        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            return DummyWindow.next_response

    rumps_stub.App = DummyApp
    rumps_stub.MenuItem = DummyMenuItem
    rumps_stub.Window = DummyWindow
    rumps_stub.alert = lambda *args, **kwargs: None
    rumps_stub.quit_application = lambda: None

    sys.modules["rumps"] = rumps_stub


_install_rumps_stub()
battery_alert_module = importlib.import_module("battery_alert_gui")
battery_alert_module = importlib.reload(battery_alert_module)
BatteryAlertApp = battery_alert_module.BatteryAlertApp


def _new_app_for_unit_tests(tmp_path):
    app = BatteryAlertApp.__new__(BatteryAlertApp)
    app.config_dir = Path(tmp_path)
    app.config_file = Path(tmp_path) / "config.json"
    app.log_file = Path(tmp_path) / "alert_history.json"
    app.pid_file = Path(tmp_path) / "app.pid"
    app.runtime_log_file = Path(tmp_path) / "logs" / "battery_alert.log"
    app.update_state_file = Path(tmp_path) / "update_state.json"
    app.settings = {
        "battery_threshold": 20,
        "check_interval": 10,
        "alert_cooldown_seconds": 60,
        "enable_sound": True,
        "enable_voice": True,
        "enable_notifications": True,
        "auto_launch": False,
        "enable_update_checks": True,
    }
    app.alert_history = []
    app._below_threshold_prev = False
    app._last_alert_time = None
    app._last_power_state = None
    app.logger = None
    return app


def test_validate_settings_clamps_invalid_values(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    app.settings.update(
        {
            "battery_threshold": "bad",
            "check_interval": 1,
            "alert_cooldown_seconds": 1,
            "enable_sound": 0,
            "enable_voice": "",
            "enable_notifications": 1,
            "auto_launch": "yes",
        }
    )

    app.validate_settings()

    assert app.settings["battery_threshold"] == 20
    assert app.settings["check_interval"] == 10
    assert app.settings["alert_cooldown_seconds"] == 30
    assert app.settings["enable_sound"] is False
    assert app.settings["enable_voice"] is False
    assert app.settings["enable_notifications"] is True
    assert app.settings["auto_launch"] is True


def test_should_trigger_alert_uses_edge_and_cooldown(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    info = {"level": 15, "is_discharging": True, "is_charging": False}

    now = datetime(2026, 1, 1, 10, 0, 0)
    assert app.should_trigger_alert(info, now=now) is True

    app._last_alert_time = now
    assert app.should_trigger_alert(info, now=now + timedelta(seconds=10)) is False
    assert app.should_trigger_alert(info, now=now + timedelta(seconds=61)) is True


def test_atomic_write_replaces_file_content(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    payload = {"battery_threshold": 35}

    app._write_json_atomic(app.config_file, payload)

    assert app.config_file.exists()
    with open(app.config_file) as f:
        loaded = json.load(f)
    assert loaded == payload


def test_ensure_single_instance_cleans_stale_pid(tmp_path, monkeypatch):
    app = _new_app_for_unit_tests(tmp_path)
    app.pid_file.write_text("999999")

    monkeypatch.setattr(app, "_is_process_running", lambda pid: False)
    app.ensure_single_instance()

    assert not app.pid_file.exists()


def test_format_settings_summary_includes_phase2_fields(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    app.settings["alert_cooldown_seconds"] = 120
    app.settings["enable_voice"] = False
    app.settings["auto_launch"] = True

    summary = app.format_settings_summary()

    assert "Battery threshold: 20%" in summary
    assert "Alert cooldown: 120 seconds" in summary
    assert "Alert modes: sound, notifications" in summary
    assert "Launch at startup: enabled" in summary
    assert "Update checks: enabled" in summary


def test_build_diagnostics_report_includes_support_context(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    app.alert_history.append({"time": "2026-01-01 10:00:00", "battery_level": 19})

    report = app.build_diagnostics_report(
        {"level": 18, "is_charging": False, "is_discharging": True}
    )

    assert "Battery Alert Diagnostics" in report
    assert "battery_level: 18" in report
    assert "alert_history_entries: 1" in report
    assert "last_alert: 2026-01-01 10:00:00" in report
    assert f"config_file: {app.config_file}" in report
    assert "app_version:" in report


def test_prompt_for_integer_setting_updates_value_and_persists(tmp_path, monkeypatch):
    app = _new_app_for_unit_tests(tmp_path)
    alert_messages = []

    battery_alert_module.rumps.Window.next_response = types.SimpleNamespace(clicked=True, text="45")
    monkeypatch.setattr(
        battery_alert_module.rumps,
        "alert",
        lambda message, title=None: alert_messages.append((message, title))
    )

    changed = app.prompt_for_integer_setting(
        "battery_threshold",
        "Battery Threshold",
        "Enter new threshold (1-100):",
        1,
        100,
        "Battery threshold set to {value}%"
    )

    assert changed is True
    assert app.settings["battery_threshold"] == 45
    assert app.config_file.exists()
    assert alert_messages == [("Battery threshold set to 45%", "Success")]


def test_update_boolean_setting_updates_label_and_value(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    sender = types.SimpleNamespace(title="")

    app.update_boolean_setting("enable_sound", sender, "🔊 Sound Alerts")

    assert app.settings["enable_sound"] is False
    assert sender.title == "🔊 Sound Alerts: OFF"


def test_is_newer_version_compares_semver_like_values(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)

    assert app.is_newer_version("1.2.0", "1.1.9") is True
    assert app.is_newer_version("v1.1.0", "1.1.0") is False
    assert app.is_newer_version("1.1.0-beta", "1.0.9") is True


def test_should_check_for_updates_throttles_by_last_check(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    now = datetime(2026, 1, 1, 12, 0, 0)

    assert app.should_check_for_updates(now=now, minimum_hours=24) is True

    app._write_last_update_check(now - timedelta(hours=2))
    assert app.should_check_for_updates(now=now, minimum_hours=24) is False

    app._write_last_update_check(now - timedelta(hours=30))
    assert app.should_check_for_updates(now=now, minimum_hours=24) is True


def test_create_support_bundle_archive_contains_core_files(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    app.config_file.write_text('{"battery_threshold": 20}')
    app.log_file.write_text('[]')
    app.runtime_log_file.parent.mkdir(parents=True, exist_ok=True)
    app.runtime_log_file.write_text('runtime log line')

    bundle_path = app.create_support_bundle_archive()

    assert bundle_path.exists()
    with zipfile.ZipFile(bundle_path, "r") as zf:
        names = set(zf.namelist())
    assert "diagnostics.txt" in names
    assert "config.json" in names
    assert "alert_history.json" in names
    assert "logs/battery_alert.log" in names
