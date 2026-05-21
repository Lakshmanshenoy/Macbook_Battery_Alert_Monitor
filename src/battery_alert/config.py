# mypy: ignore-errors
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .constants import (
    APP_STATE_SCHEMA_VERSION,
    CONFIG_SCHEMA_VERSION,
    UPDATE_CHANNEL,
    UPDATE_STATE_SCHEMA_VERSION,
)
from .legacy_app import BatteryAlertApp as LegacyBatteryAlertApp


class ConfigManager:
    """Configuration/state persistence facade used by the thin app orchestrator."""

    def __init__(self, app: "LegacyBatteryAlertApp") -> None:
        self.app = app

    def _rumps_module(self) -> Any:
        gui_module = sys.modules.get("battery_alert_gui")
        rumps = getattr(gui_module, "rumps", None)
        if rumps is not None:
            return rumps

        import rumps as imported_rumps

        return imported_rumps

    def _subprocess_module(self) -> Any:
        gui_module = sys.modules.get("battery_alert_gui")
        return getattr(gui_module, "subprocess", subprocess)

    def default_settings_payload(self) -> Dict[str, Any]:
        return self.app.default_settings_payload()

    def default_app_state_payload(self) -> Dict[str, Any]:
        return self.app.default_app_state_payload()

    def default_update_state_payload(self) -> Dict[str, Any]:
        return self.app.default_update_state_payload()

    def migrate_config_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        merged = self.default_settings_payload()
        if not isinstance(payload, dict):
            return merged
        merged.update(payload)
        merged["config_schema_version"] = CONFIG_SCHEMA_VERSION
        return merged

    def migrate_app_state_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        merged = self.default_app_state_payload()
        if not isinstance(payload, dict):
            return merged
        merged.update(payload)
        merged["app_state_schema_version"] = APP_STATE_SCHEMA_VERSION
        return merged

    def migrate_update_state_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        merged = self.default_update_state_payload()
        if not isinstance(payload, dict):
            return merged
        merged.update(payload)
        merged["update_state_schema_version"] = UPDATE_STATE_SCHEMA_VERSION
        return merged

    def validate_settings(self) -> None:
        settings = self.app.settings
        threshold = settings.get("battery_threshold", 20)
        interval = settings.get("check_interval", 10)
        cooldown = settings.get("alert_cooldown_seconds", 900)

        try:
            threshold = int(threshold)
        except (TypeError, ValueError):
            threshold = 20

        try:
            interval = int(interval)
        except (TypeError, ValueError):
            interval = 10

        try:
            cooldown = int(cooldown)
        except (TypeError, ValueError):
            cooldown = 900

        settings["battery_threshold"] = max(1, min(100, threshold))
        settings["check_interval"] = max(10, min(3600, interval))
        settings["alert_cooldown_seconds"] = max(30, min(86400, cooldown))
        settings["enable_sound"] = bool(settings.get("enable_sound", True))
        settings["enable_voice"] = bool(settings.get("enable_voice", True))
        settings["enable_notifications"] = bool(settings.get("enable_notifications", True))
        settings["auto_launch"] = bool(settings.get("auto_launch", False))
        settings["enable_update_checks"] = bool(settings.get("enable_update_checks", True))
        update_channel = str(settings.get("update_channel", UPDATE_CHANNEL)).strip().lower()
        if update_channel not in {"stable", "beta"}:
            update_channel = UPDATE_CHANNEL
        settings["update_channel"] = update_channel
        settings["config_schema_version"] = CONFIG_SCHEMA_VERSION

    def load_config(self) -> None:
        if self.app.config_file.exists():
            try:
                with open(self.app.config_file) as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    self.app.settings = self.migrate_config_payload(loaded)
                else:
                    self.app.settings = self.default_settings_payload()
                self.validate_settings()
            except Exception as exc:
                self.app.log_runtime(f"Failed to load config: {exc}", level="error")
                self.app.settings = self.default_settings_payload()
                self.validate_settings()
                self.recover_corrupted_json_file(self.app.config_file, self.app.settings, "config")
        else:
            self.save_config()

    def save_config(self) -> None:
        try:
            self.validate_settings()
            self.write_json_atomic(self.app.config_file, self.app.settings)
        except Exception as exc:
            self.app.log_runtime(f"Failed to save config: {exc}", level="error")

    def load_alert_history(self) -> None:
        if self.app.log_file.exists():
            try:
                with open(self.app.log_file) as handle:
                    loaded_history = json.load(handle)
                if isinstance(loaded_history, list):
                    self.app.alert_history = [
                        alert
                        for alert in loaded_history
                        if isinstance(alert, dict)
                        and "time" in alert
                        and "battery_level" in alert
                    ][-50:]
                else:
                    self.app.alert_history = []
            except Exception as exc:
                self.app.log_runtime(f"Failed to load history: {exc}", level="error")
                self.app.alert_history = []
                self.recover_corrupted_json_file(self.app.log_file, [], "alert history")

    def save_alert_history(self) -> None:
        try:
            self.write_json_atomic(self.app.log_file, self.app.alert_history[-100:])
        except Exception as exc:
            self.app.log_runtime(f"Failed to save history: {exc}", level="error")

    def load_app_state(self) -> None:
        if not self.app.app_state_file.exists():
            self.save_app_state()
            return

        try:
            with open(self.app.app_state_file) as handle:
                loaded_state = json.load(handle)
            if isinstance(loaded_state, dict):
                self.app.app_state = self.migrate_app_state_payload(loaded_state)
            else:
                self.app.app_state = self.default_app_state_payload()
                self.save_app_state()
        except Exception as exc:
            self.app.log_runtime(f"Failed to load app state: {exc}", level="error")
            self.app.app_state = self.default_app_state_payload()
            self.recover_corrupted_json_file(self.app.app_state_file, self.app.app_state, "app state")

    def save_app_state(self) -> None:
        try:
            self.app.app_state["app_state_schema_version"] = APP_STATE_SCHEMA_VERSION
            self.write_json_atomic(self.app.app_state_file, self.app.app_state)
        except Exception as exc:
            self.app.log_runtime(f"Failed to save app state: {exc}", level="error")

    def load_update_state(self) -> None:
        if not self.app.update_state_file.exists():
            self.save_update_state()
            return

        try:
            with open(self.app.update_state_file) as handle:
                loaded_state = json.load(handle)
            if isinstance(loaded_state, dict):
                self.app.update_state = self.migrate_update_state_payload(loaded_state)
            else:
                self.app.update_state = self.default_update_state_payload()
                self.save_update_state()
        except Exception as exc:
            self.app.log_runtime(f"Failed to load update state: {exc}", level="error")
            self.app.update_state = self.default_update_state_payload()
            self.recover_corrupted_json_file(self.app.update_state_file, self.app.update_state, "update state")

    def save_update_state(self) -> None:
        try:
            self.app.update_state["update_state_schema_version"] = UPDATE_STATE_SCHEMA_VERSION
            self.write_json_atomic(self.app.update_state_file, self.app.update_state)
        except Exception as exc:
            self.app.log_runtime(f"Failed to save update state: {exc}", level="error")

    def recover_corrupted_json_file(self, path: Path, fallback_payload: Any, context_label: str) -> None:
        try:
            if path.exists():
                quarantine_name = f"{path.name}.corrupt.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                quarantine_path = path.with_name(quarantine_name)
                path.replace(quarantine_path)
                self.app.log_runtime(
                    f"Recovered corrupted {context_label} file by quarantining to {quarantine_path.name}",
                    level="warning",
                )
            self.write_json_atomic(path, fallback_payload)
        except Exception as exc:
            self.app.log_runtime(f"Failed to recover corrupted {context_label} file: {exc}", level="error")

    def write_json_atomic(self, destination: Path, payload: Any) -> None:
        tmp_path = destination.with_suffix(destination.suffix + ".tmp")
        with open(tmp_path, "w") as handle:
            json.dump(payload, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, destination)

    def record_app_state_event(self, key: str, value: Any = None) -> None:
        """Record lightweight app usage metrics for post-release support."""
        if not hasattr(self.app, "app_state") or not isinstance(self.app.app_state, dict):
            self.app.app_state = self.default_app_state_payload()

        if key not in self.app.app_state:
            return

        if isinstance(self.app.app_state.get(key), int):
            self.app.app_state[key] = int(self.app.app_state[key]) + (1 if value is None else value)
        else:
            self.app.app_state[key] = value
        self.app.save_app_state()

    def onboarding_summary(self) -> str:
        """Return a short onboarding summary for new users."""
        return (
            "Welcome to Battery Alert Monitor.\n\n"
            "Quick start:\n"
            "1. Set Battery Threshold and Alert Cooldown from the menu.\n"
            "2. Use Check for Updates or Run Release Check from the maintenance menu.\n"
            "3. Export a Support Bundle if you need help troubleshooting.\n\n"
            "You can reopen this message from the menu anytime."
        )

    def show_getting_started(self, _ : Any = None) -> None:
        """Show onboarding guidance on demand."""
        try:
            self._rumps_module().alert("Getting Started", self.onboarding_summary())
        except Exception as exc:
            self.app.log_runtime(f"Error in show_getting_started: {exc}", level="error")

    def maybe_show_first_run_onboarding(self) -> None:
        """Show a one-time onboarding tip on first launch."""
        if self.app.app_state.get("first_launch_completed"):
            return

        self.app.app_state["first_launch_completed"] = True
        self.app.app_state["onboarding_shown_at"] = datetime.now().isoformat()
        self.app.save_app_state()
        self.app.show_non_blocking_feedback(
            "Welcome",
            "Battery Alert is ready. Open Getting Started for a short tour of the main settings.",
        )

    def is_process_running(self, pid: int) -> bool:
        """Check if a process with the given PID exists."""
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except Exception:
            return False

    def ensure_single_instance(self) -> None:
        """Prevent multiple app instances and clean stale PID files."""
        if not self.app.pid_file.exists():
            return

        try:
            existing_pid_raw = self.app.pid_file.read_text().strip()
            if not existing_pid_raw:
                self.app.pid_file.unlink(missing_ok=True)
                return

            existing_pid = int(existing_pid_raw)
            if existing_pid == os.getpid():
                return

            if self.app._is_process_running(existing_pid):
                raise RuntimeError("Battery Alert is already running.")

            self.app.pid_file.unlink(missing_ok=True)
        except ValueError:
            self.app.pid_file.unlink(missing_ok=True)

    def setup_autolaunch(self) -> None:
        """Setup or remove autolaunch using LaunchAgent."""
        launch_agent_dir = Path.home() / "Library/LaunchAgents"
        plist_file = launch_agent_dir / "com.batteryalert.app.plist"

        try:
            launch_agent_dir.mkdir(exist_ok=True)

            if self.app.settings["auto_launch"]:
                plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.batteryalert.background</string>
    <key>Program</key>
    <string>/usr/bin/open</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/open</string>
        <string>-a</string>
        <string>Battery Alert</string>
        <string>--background</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardInPath</key>
    <string>/dev/null</string>
    <key>StandardOutPath</key>
    <string>/dev/null</string>
    <key>StandardErrorPath</key>
    <string>/dev/null</string>
</dict>
</plist>"""

                with open(plist_file, "w") as handle:
                    handle.write(plist_content)

                self._subprocess_module().run(["launchctl", "unload", str(plist_file)], capture_output=True)
                self._subprocess_module().run(["launchctl", "load", str(plist_file)], capture_output=True)
                self.app.log_runtime(f"Enabled - LaunchAgent plist: {plist_file}")
                self.app.log_runtime(
                    "To see it with app name in login items, add Battery Alert.app to System Settings > General > Login Items"
                )
            elif plist_file.exists():
                self._subprocess_module().run(["launchctl", "unload", str(plist_file)], capture_output=True)
                plist_file.unlink()
                self.app.log_runtime("Disabled - LaunchAgent removed")
        except Exception as exc:
            self.app.log_runtime(f"Failed to setup autolaunch: {exc}", level="error")
