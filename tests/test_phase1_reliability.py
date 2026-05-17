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
    app.app_state_file = Path(tmp_path) / "app_state.json"
    app.settings = {
        "config_schema_version": 2,
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
    app.app_state = {
        "app_state_schema_version": 3,
        "first_launch_completed": False,
        "onboarding_shown_at": None,
        "release_checks_run": 0,
        "support_bundle_exports": 0,
        "last_support_bundle_export_at": None,
        "last_update_check_at": None,
        "last_update_status": None,
        "last_known_release_version": None,
        "last_crash_report_at": None,
        "last_release_validation_at": None,
    }
    app.crash_reports_dir = Path(tmp_path) / "crash_reports"
    app._below_threshold_prev = False
    app._last_alert_time = None
    app._last_power_state = None
    app._last_power_transition = None
    app.logger = None
    app._release_validation_in_progress = False
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
    assert "safe_share_guide.txt" in names
    assert "manifest.json" in names
    assert "config.json" in names
    assert "alert_history.json" in names
    assert "logs/battery_alert.log" in names


def test_create_support_bundle_archive_includes_latest_crash_report(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    app.config_file.write_text('{"battery_threshold": 20}')
    app.log_file.write_text('[]')
    app.runtime_log_file.parent.mkdir(parents=True, exist_ok=True)
    app.runtime_log_file.write_text('runtime log line')
    app.crash_reports_dir.mkdir(parents=True, exist_ok=True)
    crash_report = app.crash_reports_dir / "crash_report_20260101_120000.json"
    crash_report.write_text('{"user": "lakshman", "contact": "person@example.com"}', encoding="utf-8")

    bundle_path = app.create_support_bundle_archive()

    with zipfile.ZipFile(bundle_path, "r") as zf:
        names = set(zf.namelist())
        crash_text = zf.read("crash_reports/latest_crash_report.json").decode("utf-8")

    assert "crash_reports/latest_crash_report.json" in names
    assert "person@example.com" not in crash_text


def test_migrate_config_payload_adds_schema_and_defaults(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    migrated = app.migrate_config_payload({"battery_threshold": 35})

    assert migrated["config_schema_version"] == battery_alert_module.CONFIG_SCHEMA_VERSION
    assert migrated["battery_threshold"] == 35
    assert migrated["enable_update_checks"] is True


def test_migrate_app_state_payload_adds_schema_and_defaults(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    migrated = app.migrate_app_state_payload({"release_checks_run": 7})

    assert migrated["app_state_schema_version"] == battery_alert_module.APP_STATE_SCHEMA_VERSION
    assert migrated["release_checks_run"] == 7
    assert migrated["support_bundle_exports"] == 0
    assert migrated["last_update_check_at"] is None
    assert migrated["last_support_bundle_export_at"] is None
    assert migrated["last_update_status"] is None
    assert migrated["last_known_release_version"] is None
    assert migrated["last_crash_report_at"] is None


def test_build_release_visibility_summary_includes_update_state(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    app.app_state["last_update_check_at"] = "2026-01-01T12:00:00"
    app.app_state["last_update_status"] = "up_to_date"
    app.app_state["last_known_release_version"] = "1.1.0"

    summary = app.build_release_visibility_summary()

    assert "Current version: 1.1.0" in summary
    assert "Update channel: stable" in summary
    assert "Last result: up_to_date" in summary
    assert "Latest known release: 1.1.0" in summary


def test_build_status_summary_includes_power_and_support_context(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    app._last_power_transition = "charging -> discharging at 45% on 2026-01-01 12:00:00"
    app.app_state["support_bundle_exports"] = 2
    app.app_state["last_update_status"] = "update_available"

    summary = app.build_status_summary({"level": 45, "is_charging": False, "is_discharging": True})

    assert "Battery level: 45%" in summary
    assert "Last power transition: charging -> discharging" in summary
    assert "Support bundles exported: 2" in summary
    assert "Last update result: update_available" in summary


def test_write_crash_report_persists_latest_timestamp(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        exc_type, exc_value, exc_traceback = sys.exc_info()

    report_path = app.write_crash_report(exc_type, exc_value, exc_traceback, thread_name="worker")

    assert report_path is not None
    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["thread_name"] == "worker"
    assert payload["exception_type"] == "RuntimeError"
    assert app.app_state["last_crash_report_at"] is not None


def test_redact_text_for_support_share_masks_home_path(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    text = (
        f"config path: {Path.home()}/.battery_alert/config.json\n"
        "user: lakshman\n"
        "contact: person@example.com\n"
        "fallback path: /Users/alice/Documents"
    )

    redacted = app.redact_text_for_support_share(text)

    assert str(Path.home()) not in redacted
    assert "~/.battery_alert/config.json" in redacted
    assert "person@example.com" not in redacted
    assert "<redacted-email>" in redacted
    assert "user: <redacted-user>" in redacted
    assert "/Users/<redacted-user>/Documents" in redacted


def test_load_config_migrates_pre_schema_payload(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    app.config_file.write_text(json.dumps({"battery_threshold": 33}, indent=2))

    app.load_config()

    assert app.settings["battery_threshold"] == 33
    assert app.settings["config_schema_version"] == battery_alert_module.CONFIG_SCHEMA_VERSION
    assert app.settings["enable_update_checks"] is True


def test_load_app_state_migrates_pre_schema_payload(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    app.app_state_file.write_text(json.dumps({"support_bundle_exports": 2}, indent=2))

    app.load_app_state()

    assert app.app_state["support_bundle_exports"] == 2
    assert app.app_state["app_state_schema_version"] == battery_alert_module.APP_STATE_SCHEMA_VERSION
    assert app.app_state["last_update_check_at"] is None
    assert app.app_state["last_update_status"] is None


def test_load_config_recovers_corrupted_json(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    app.config_file.write_text("{broken")

    app.load_config()

    assert app.settings["config_schema_version"] == battery_alert_module.CONFIG_SCHEMA_VERSION
    quarantined = list(app.config_dir.glob("config.json.corrupt.*"))
    assert quarantined


def test_load_alert_history_recovers_corrupted_json(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    app.log_file.write_text("[broken")

    app.load_alert_history()

    assert app.alert_history == []
    quarantined = list(app.config_dir.glob("alert_history.json.corrupt.*"))
    assert quarantined


def test_first_run_onboarding_marks_state_and_is_idempotent(tmp_path, monkeypatch):
    app = _new_app_for_unit_tests(tmp_path)
    shown = []

    monkeypatch.setattr(app, "show_non_blocking_feedback", lambda title, message: shown.append((title, message)))

    app.maybe_show_first_run_onboarding()
    app.maybe_show_first_run_onboarding()

    assert shown == [
        (
            "Welcome",
            "Battery Alert is ready. Open Getting Started for a short tour of the main settings."
        )
    ]
    assert app.app_state["first_launch_completed"] is True
    assert app.app_state["onboarding_shown_at"] is not None
    assert app.app_state_file.exists()


def test_run_release_validation_now_runs_in_background(tmp_path, monkeypatch):
    app = _new_app_for_unit_tests(tmp_path)
    shown = []
    commands = []
    started = []

    monkeypatch.setattr(app, "show_non_blocking_feedback", lambda title, message: shown.append((title, message)))
    monkeypatch.setattr(app, "build_release_validation_command", lambda: ["python3", "scripts/release_smoke_test.py"])
    monkeypatch.setattr(
        battery_alert_module.subprocess,
        "run",
        lambda command, capture_output, text: commands.append(command) or types.SimpleNamespace(returncode=0, stdout="ok", stderr="")
    )

    class FakeThread:
        def __init__(self, target, daemon=False):
            self.target = target
            self.daemon = daemon

        def start(self):
            started.append(True)
            self.target()

    monkeypatch.setattr(battery_alert_module.threading, "Thread", FakeThread)

    app.run_release_validation_now(None)

    assert commands == [["python3", "scripts/release_smoke_test.py"]]
    assert started == [True]
    assert shown[0] == ("Maintenance", "Release check started.")
    assert shown[-1] == ("Maintenance", "Release check complete: passed.")
    assert app.app_state["release_checks_run"] == 1
    assert app.app_state["last_release_validation_at"] is not None


def test_build_release_validation_command_points_to_script(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)

    command = app.build_release_validation_command()

    assert command[0] == sys.executable
    assert command[1].endswith("scripts/release_smoke_test.py")


def test_check_for_updates_manual_empty_latest_shows_feedback(tmp_path, monkeypatch):
    app = _new_app_for_unit_tests(tmp_path)

    monkeypatch.setattr(app, "get_latest_release_version", lambda: "")
    result = app.check_for_updates(manual=True)

    assert result["status"] == "unknown"
    assert "Could not determine" in result["message"]
    assert app.app_state["last_update_status"] == "unknown"


def test_export_support_bundle_shows_feedback(tmp_path, monkeypatch):
    app = _new_app_for_unit_tests(tmp_path)
    shown = []

    app.config_file.write_text('{"battery_threshold": 20}')
    app.log_file.write_text('[]')
    app.runtime_log_file.parent.mkdir(parents=True, exist_ok=True)
    app.runtime_log_file.write_text('runtime log line')

    monkeypatch.setattr(app, "show_feedback", lambda title, message: shown.append((title, message)))
    monkeypatch.setattr(battery_alert_module.subprocess, "run", lambda *args, **kwargs: None)

    app.export_support_bundle(None)

    assert shown
    assert shown[0][0] == "Support Bundle Exported"
    assert "Support bundle created at:" in shown[0][1]


def test_run_manual_update_check_sends_non_blocking_feedback(tmp_path, monkeypatch):
    app = _new_app_for_unit_tests(tmp_path)
    shown = []

    monkeypatch.setattr(
        app,
        "check_for_updates",
        lambda manual=False: {"status": "up_to_date", "message": "You are up to date on version 1.1.0."}
    )
    monkeypatch.setattr(app, "show_non_blocking_feedback", lambda title, message: shown.append((title, message)))
    app._update_check_in_progress = True

    app._run_manual_update_check()

    assert shown == [("Maintenance", "Update check complete: no updates found.")]
    assert app._update_check_in_progress is False


def test_open_releases_page_sends_feedback(tmp_path, monkeypatch):
    app = _new_app_for_unit_tests(tmp_path)
    shown = []
    commands = []

    monkeypatch.setattr(app, "show_non_blocking_feedback", lambda title, message: shown.append((title, message)))
    monkeypatch.setattr(battery_alert_module.subprocess, "run", lambda command, check=False: commands.append(command))

    app.open_releases_page(None)

    assert commands == [["open", battery_alert_module.RELEASES_PAGE_URL]]
    assert shown == [("Maintenance", "Opened releases page.")]


def test_support_bundle_diagnostics_do_not_leak_home_path(tmp_path):
    app = _new_app_for_unit_tests(tmp_path)
    app.config_file.write_text('{"battery_threshold": 20}')
    app.log_file.write_text('[]')
    app.runtime_log_file.parent.mkdir(parents=True, exist_ok=True)
    app.runtime_log_file.write_text("runtime log line")

    bundle_path = app.create_support_bundle_archive()
    with zipfile.ZipFile(bundle_path, "r") as zf:
        diagnostics = zf.read("diagnostics.txt").decode("utf-8")

    assert str(Path.home()) not in diagnostics
