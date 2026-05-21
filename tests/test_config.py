"""Unit tests for ConfigManager migration and validation behavior."""

from pathlib import Path
from types import SimpleNamespace

import src.battery_alert.config as config_module
from src.battery_alert.config import ConfigManager


class _FakeApp:
    @staticmethod
    def default_settings_payload():
        return {
            "config_schema_version": 2,
            "battery_threshold": 20,
            "check_interval": 10,
            "alert_cooldown_seconds": 900,
            "enable_sound": True,
            "enable_voice": True,
            "enable_notifications": True,
            "auto_launch": False,
            "enable_update_checks": True,
            "update_channel": "stable",
        }

    def __init__(self) -> None:
        self.settings = self.default_settings_payload().copy()
        self.pid_file = Path("/tmp/battery_alert_fake.pid")
        self.log_runtime = lambda *args, **kwargs: None

    def _is_process_running(self, _pid: int) -> bool:
        return False


def _manager() -> ConfigManager:
    app = _FakeApp()
    return ConfigManager(app)


def _validated_settings(payload):
    manager = _manager()
    manager.app.settings = manager.migrate_config_payload(payload)
    manager.validate_settings()
    return manager.app.settings


def test_missing_keys_filled_with_defaults() -> None:
    manager = _manager()
    partial = {"battery_threshold": 30}
    result = manager.migrate_config_payload(partial)

    assert result["check_interval"] == 10
    assert result["alert_cooldown_seconds"] == 900


def test_threshold_clamped_below_minimum() -> None:
    result = _validated_settings({"battery_threshold": 0})
    assert result["battery_threshold"] == 1


def test_threshold_clamped_above_maximum() -> None:
    result = _validated_settings({"battery_threshold": 150})
    assert result["battery_threshold"] == 100


def test_invalid_type_replaced_with_default() -> None:
    result = _validated_settings({"check_interval": "not-a-number"})
    assert result["check_interval"] == 10


def test_update_channel_normalised() -> None:
    result = _validated_settings({"update_channel": "BETA"})
    assert result["update_channel"] == "beta"


def test_invalid_update_channel_falls_back() -> None:
    result = _validated_settings({"update_channel": "nightly"})
    assert result["update_channel"] == "stable"


def test_ensure_single_instance_cleans_invalid_pid(tmp_path) -> None:
    manager = _manager()
    manager.app.pid_file = tmp_path / "app.pid"
    manager.app.pid_file.write_text("not-an-int")

    manager.ensure_single_instance()

    assert not manager.app.pid_file.exists()


def test_ensure_single_instance_raises_when_active(tmp_path, monkeypatch) -> None:
    manager = _manager()
    manager.app.pid_file = tmp_path / "app.pid"
    manager.app.pid_file.write_text("1234")
    monkeypatch.setattr(manager.app, "_is_process_running", lambda pid: True)

    try:
        manager.ensure_single_instance()
        raised = False
    except RuntimeError:
        raised = True

    assert raised is True


def test_setup_autolaunch_enable_writes_plist(tmp_path, monkeypatch) -> None:
    manager = _manager()
    manager.app.settings["auto_launch"] = True
    calls = []

    (tmp_path / "Library").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(
        manager,
        "_subprocess_module",
        lambda: SimpleNamespace(run=lambda args, capture_output=True: calls.append(args)),
    )

    manager.setup_autolaunch()

    plist_file = tmp_path / "Library/LaunchAgents/com.batteryalert.app.plist"
    assert plist_file.exists()
    assert calls and calls[0][0:2] == ["launchctl", "unload"]


def test_setup_autolaunch_disable_removes_plist(tmp_path, monkeypatch) -> None:
    manager = _manager()
    manager.app.settings["auto_launch"] = False
    calls = []

    monkeypatch.setattr(config_module.Path, "home", lambda: tmp_path)
    launch_agent_dir = tmp_path / "Library/LaunchAgents"
    launch_agent_dir.mkdir(parents=True, exist_ok=True)
    plist_file = launch_agent_dir / "com.batteryalert.app.plist"
    plist_file.write_text("plist")

    monkeypatch.setattr(
        manager,
        "_subprocess_module",
        lambda: SimpleNamespace(run=lambda args, capture_output=True: calls.append(args)),
    )

    manager.setup_autolaunch()

    assert not plist_file.exists()
    assert calls and calls[0][0:2] == ["launchctl", "unload"]
