# mypy: ignore-errors
from pathlib import Path
from typing import Dict, Optional, Union

from .legacy_app import BatteryAlertApp as LegacyBatteryAlertApp


class DiagnosticsManager:
    """Diagnostics/logging/support-bundle facade."""

    def __init__(self, app: "LegacyBatteryAlertApp") -> None:
        self.app = app

    def setup_runtime_logging(self) -> None:
        LegacyBatteryAlertApp.setup_runtime_logging(self.app)

    def install_exception_hooks(self) -> None:
        LegacyBatteryAlertApp.install_exception_hooks(self.app)

    def write_crash_report(
        self,
        exc_type: type,
        exc_value: Exception,
        exc_traceback,
        thread_name: str = "main",
    ) -> Optional[Path]:
        return LegacyBatteryAlertApp.write_crash_report(
            self.app,
            exc_type,
            exc_value,
            exc_traceback,
            thread_name,
        )

    def build_diagnostics_report(
        self,
        battery_info: Optional[Dict[str, Union[int, bool]]] = None,
    ) -> str:
        return LegacyBatteryAlertApp.build_diagnostics_report(self.app, battery_info)

    def export_support_bundle(self, preset: str = "full") -> Optional[Path]:
        return LegacyBatteryAlertApp.create_support_bundle_archive(self.app, preset)
