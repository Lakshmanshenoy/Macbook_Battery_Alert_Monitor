# mypy: ignore-errors
from typing import Any, Dict

from .legacy_app import BatteryAlertApp as LegacyBatteryAlertApp


class ConfigManager:
    """Configuration/state persistence facade used by the thin app orchestrator."""

    def __init__(self, app: "LegacyBatteryAlertApp") -> None:
        self.app = app

    def default_settings_payload(self) -> Dict[str, Any]:
        return LegacyBatteryAlertApp.default_settings_payload()

    def default_app_state_payload(self) -> Dict[str, Any]:
        return LegacyBatteryAlertApp.default_app_state_payload()

    def default_update_state_payload(self) -> Dict[str, Any]:
        return LegacyBatteryAlertApp.default_update_state_payload()

    def migrate_config_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return LegacyBatteryAlertApp.migrate_config_payload(self.app, payload)

    def migrate_app_state_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return LegacyBatteryAlertApp.migrate_app_state_payload(self.app, payload)

    def migrate_update_state_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return LegacyBatteryAlertApp.migrate_update_state_payload(self.app, payload)

    def validate_settings(self) -> None:
        LegacyBatteryAlertApp.validate_settings(self.app)

    def load_config(self) -> None:
        LegacyBatteryAlertApp.load_config(self.app)

    def save_config(self) -> None:
        LegacyBatteryAlertApp.save_config(self.app)

    def load_alert_history(self) -> None:
        LegacyBatteryAlertApp.load_alert_history(self.app)

    def save_alert_history(self) -> None:
        LegacyBatteryAlertApp.save_alert_history(self.app)

    def load_app_state(self) -> None:
        LegacyBatteryAlertApp.load_app_state(self.app)

    def save_app_state(self) -> None:
        LegacyBatteryAlertApp.save_app_state(self.app)

    def load_update_state(self) -> None:
        LegacyBatteryAlertApp.load_update_state(self.app)

    def save_update_state(self) -> None:
        LegacyBatteryAlertApp.save_update_state(self.app)

    def recover_corrupted_json_file(self, path, fallback_payload, context_label: str) -> None:
        LegacyBatteryAlertApp.recover_corrupted_json_file(self.app, path, fallback_payload, context_label)

    def write_json_atomic(self, destination, payload) -> None:
        LegacyBatteryAlertApp._write_json_atomic(self.app, destination, payload)
