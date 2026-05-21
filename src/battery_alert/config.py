# mypy: ignore-errors
import json
import os
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

    def recover_corrupted_json_file(self, path: Path, fallback_payload: Dict[str, Any], context_label: str) -> None:
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

    def write_json_atomic(self, destination: Path, payload: Dict[str, Any]) -> None:
        tmp_path = destination.with_suffix(destination.suffix + ".tmp")
        with open(tmp_path, "w") as handle:
            json.dump(payload, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, destination)
