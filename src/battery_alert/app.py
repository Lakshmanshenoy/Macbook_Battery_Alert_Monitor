# mypy: ignore-errors
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .alerts import AlertManager
from .battery import BatteryService
from .config import ConfigManager
from .constants import APP_VERSION
from .diagnostics import DiagnosticsManager
from .legacy_app import BatteryAlertApp as LegacyBatteryAlertApp
from .updater import UpdateChecker


class BatteryAlertApp(LegacyBatteryAlertApp):
    """Thin orchestration layer over focused managers."""

    def __init__(self) -> None:
        self._ensure_managers()
        super(BatteryAlertApp, self).__init__()

    def _ensure_managers(self) -> None:
        if not hasattr(self, "config_manager"):
            self.config_manager = ConfigManager(self)
        if not hasattr(self, "alert_manager"):
            self.alert_manager = AlertManager(self)
        if not hasattr(self, "update_checker"):
            self.update_checker = UpdateChecker(self)
        if not hasattr(self, "diagnostics_manager"):
            self.diagnostics_manager = DiagnosticsManager(self)
        if not hasattr(self, "battery_service"):
            self.battery_service = BatteryService(self.log_runtime)

    def get_battery_info(self) -> Dict[str, Union[int, bool]]:
        self._ensure_managers()
        return self.battery_service.get_battery_info()

    def should_trigger_alert(
        self,
        battery_info: Dict[str, Union[int, bool]],
        now: Optional[datetime] = None,
    ) -> bool:
        self._ensure_managers()
        return self.alert_manager.should_trigger_alert(battery_info, now)

    def trigger_alert(self, battery_level: int, now: Optional[datetime] = None) -> None:
        self._ensure_managers()
        self.alert_manager.trigger_alert(battery_level, now)

    def load_config(self) -> None:
        self._ensure_managers()
        self.config_manager.load_config()

    def migrate_config_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_managers()
        return self.config_manager.migrate_config_payload(payload)

    def migrate_app_state_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_managers()
        return self.config_manager.migrate_app_state_payload(payload)

    def migrate_update_state_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_managers()
        return self.config_manager.migrate_update_state_payload(payload)

    def save_config(self) -> None:
        self._ensure_managers()
        self.config_manager.save_config()

    def validate_settings(self) -> None:
        self._ensure_managers()
        self.config_manager.validate_settings()

    def load_alert_history(self) -> None:
        self._ensure_managers()
        self.config_manager.load_alert_history()

    def save_alert_history(self) -> None:
        self._ensure_managers()
        self.config_manager.save_alert_history()

    def load_app_state(self) -> None:
        self._ensure_managers()
        self.config_manager.load_app_state()

    def save_app_state(self) -> None:
        self._ensure_managers()
        self.config_manager.save_app_state()

    def load_update_state(self) -> None:
        self._ensure_managers()
        self.config_manager.load_update_state()

    def save_update_state(self) -> None:
        self._ensure_managers()
        self.config_manager.save_update_state()

    def recover_corrupted_json_file(
        self,
        path: Path,
        fallback_payload: Dict[str, Any],
        context_label: str,
    ) -> None:
        self._ensure_managers()
        self.config_manager.recover_corrupted_json_file(path, fallback_payload, context_label)

    def _write_json_atomic(self, destination: Path, payload: Dict[str, Any]) -> None:
        self._ensure_managers()
        self.config_manager.write_json_atomic(destination, payload)

    def setup_runtime_logging(self) -> None:
        self._ensure_managers()
        self.diagnostics_manager.setup_runtime_logging()

    def install_exception_hooks(self) -> None:
        self._ensure_managers()
        self.diagnostics_manager.install_exception_hooks()

    def write_crash_report(
        self,
        exc_type: type,
        exc_value: Exception,
        exc_traceback,
        thread_name: str = "main",
    ) -> Optional[Path]:
        self._ensure_managers()
        return self.diagnostics_manager.write_crash_report(
            exc_type,
            exc_value,
            exc_traceback,
            thread_name,
        )

    def build_diagnostics_report(
        self,
        battery_info: Optional[Dict[str, Union[int, bool]]] = None,
    ) -> str:
        self._ensure_managers()
        return self.diagnostics_manager.build_diagnostics_report(battery_info)

    def create_support_bundle_archive(self, preset: str = "full") -> Optional[Path]:
        self._ensure_managers()
        return self.diagnostics_manager.export_support_bundle(preset)

    def check_for_updates(self, manual: bool = False) -> None:
        self._ensure_managers()
        return self.update_checker.check_for_updates(manual)

    def get_latest_release(self):
        self._ensure_managers()
        return self.update_checker.get_latest_release()

    def download_latest_release(self, _: Any = None) -> None:
        self._ensure_managers()
        self.update_checker.download_latest_release(_)


__all__ = ["APP_VERSION", "BatteryAlertApp"]
