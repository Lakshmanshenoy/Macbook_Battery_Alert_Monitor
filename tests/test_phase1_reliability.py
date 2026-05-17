from datetime import datetime, timedelta
from pathlib import Path
import json
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

    rumps_stub.App = DummyApp
    rumps_stub.MenuItem = lambda *args, **kwargs: None
    rumps_stub.Window = lambda *args, **kwargs: None
    rumps_stub.alert = lambda *args, **kwargs: None
    rumps_stub.quit_application = lambda: None

    sys.modules["rumps"] = rumps_stub


_install_rumps_stub()
from battery_alert_gui import BatteryAlertApp  # noqa: E402


def _new_app_for_unit_tests(tmp_path):
    app = BatteryAlertApp.__new__(BatteryAlertApp)
    app.config_dir = Path(tmp_path)
    app.config_file = Path(tmp_path) / "config.json"
    app.log_file = Path(tmp_path) / "alert_history.json"
    app.pid_file = Path(tmp_path) / "app.pid"
    app.settings = {
        "battery_threshold": 20,
        "check_interval": 10,
        "alert_cooldown_seconds": 60,
        "enable_sound": True,
        "enable_voice": True,
        "enable_notifications": True,
        "auto_launch": False,
    }
    app.alert_history = []
    app._below_threshold_prev = False
    app._last_alert_time = None
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
