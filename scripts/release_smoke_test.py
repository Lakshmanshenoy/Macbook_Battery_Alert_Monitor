#!/usr/bin/env python3
"""Non-interactive release smoke test for BattMon.

This checks the release-critical behavior without launching the GUI:
- settings validation
- support bundle creation
- manual update-check result handling
"""

from __future__ import annotations

import importlib
import json
import sys
import tempfile
import types
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def next_patch_version(version: str) -> str:
    cleaned = version.lower().strip().lstrip("v").split("-")[0]
    parts = []
    for token in cleaned.split("."):
        try:
            parts.append(int(token))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    parts[2] += 1
    return f"{parts[0]}.{parts[1]}.{parts[2]}"


def install_rumps_stub() -> None:
    """Install a minimal rumps stub so the app can be imported off-macOS or headless."""
    if "rumps" in sys.modules:
        return

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
        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            return types.SimpleNamespace(clicked=False, text="")

    rumps_stub.App = DummyApp
    rumps_stub.MenuItem = DummyMenuItem
    rumps_stub.Window = DummyWindow
    rumps_stub.alert = lambda *args, **kwargs: None
    rumps_stub.quit_application = lambda: None
    sys.modules["rumps"] = rumps_stub


def new_app():
    install_rumps_stub()
    module = importlib.import_module("battery_alert_gui")
    module = importlib.reload(module)
    app_cls = module.BatteryAlertApp

    temp_dir = Path(tempfile.mkdtemp(prefix="battmon-smoke-"))
    app = app_cls.__new__(app_cls)
    app.config_dir = temp_dir
    app.config_file = temp_dir / "config.json"
    app.log_file = temp_dir / "alert_history.json"
    app.pid_file = temp_dir / "app.pid"
    app.runtime_log_file = temp_dir / "logs" / "battery_alert.log"
    app.update_state_file = temp_dir / "update_state.json"
    app.app_state_file = temp_dir / "app_state.json"
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
        "update_channel": "stable",
    }
    app.alert_history = []
    app.app_state = {
        "app_state_schema_version": 4,
        "first_launch_completed": False,
        "onboarding_shown_at": None,
        "release_checks_run": 0,
        "support_bundle_exports": 0,
        "last_support_bundle_export_at": None,
        "last_update_check_at": None,
        "last_update_status": None,
        "last_known_release_version": None,
        "last_known_release_url": None,
        "last_crash_report_at": None,
        "last_release_validation_at": None,
    }
    app.crash_reports_dir = temp_dir / "crash_reports"
    app._last_power_transition = None
    app._below_threshold_prev = False
    app._last_alert_time = None
    app._last_power_state = None
    app._update_check_in_progress = False
    app._release_validation_in_progress = False
    app.logger = None
    app.runtime_health = {"missing_tools": [], "is_degraded": False, "checked_at": None}
    return module, app


def main() -> int:
    module, app = new_app()

    app.validate_settings()
    if app.settings["battery_threshold"] != 20:
        print("Smoke test failed: settings validation did not normalize defaults.")
        return 1

    app.config_file.write_text(json.dumps(app.settings, indent=2))
    app.log_file.write_text("[]")
    app.runtime_log_file.parent.mkdir(parents=True, exist_ok=True)
    app.runtime_log_file.write_text("runtime log line")

    bundle_path = app.create_support_bundle_archive()
    if not bundle_path.exists():
        print("Smoke test failed: support bundle was not created.")
        return 1

    with zipfile.ZipFile(bundle_path, "r") as archive:
        names = set(archive.namelist())
    required = {
        "diagnostics.txt",
        "safe_share_guide.txt",
        "manifest.json",
        "config.json",
        "alert_history.json",
        "logs/battery_alert.log",
    }
    if not required.issubset(names):
        print(f"Smoke test failed: support bundle missing files: {sorted(required - names)}")
        return 1

    next_version = next_patch_version(module.APP_VERSION)
    app.get_latest_release = lambda: {
        "version": next_version,
        "url": f"https://example.com/release/{next_version}",
    }
    result = app.check_for_updates(manual=True)
    if result["status"] != "update_available":
        print("Smoke test failed: update check did not return update_available.")
        return 1

    print("Release smoke test passed.")
    print(f"Support bundle: {bundle_path}")
    print(f"Latest release status: {result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())