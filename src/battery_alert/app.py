# mypy: ignore-errors
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .alerts import AlertManager
from .battery import BatteryService
from .config import ConfigManager
from .constants import APP_VERSION
from .diagnostics import DiagnosticsManager
from .icon_renderer import StatusIconRenderer
from .legacy_app import BatteryAlertApp as LegacyBatteryAlertApp
from .preferences_window import PreferencesWindowController
from .updater import UpdateChecker

BUILD_TYPE = os.environ.get("BATTERY_ALERT_BUILD", "release").strip().lower()


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
        if not hasattr(self, "preferences_window"):
            self.preferences_window = PreferencesWindowController(self)
        if not hasattr(self, "icon_renderer"):
            self.icon_renderer = StatusIconRenderer(self)

    def _rumps_module(self) -> Any:
        gui_module = sys.modules.get("battery_alert_gui")
        rumps = getattr(gui_module, "rumps", None)
        if rumps is None:
            import rumps as imported_rumps

            rumps = imported_rumps
        return rumps

    def setup_menu(self) -> None:
        rumps = self._rumps_module()
        menu_items = [
            rumps.MenuItem("Getting Started", self.show_getting_started),
            rumps.MenuItem("Show Preferences", self.show_preferences),
            rumps.MenuItem("Battery Threshold", self.set_threshold),
            rumps.MenuItem("Check Interval", self.set_interval),
            rumps.MenuItem("Alert Cooldown", self.set_cooldown),
            None,
            rumps.MenuItem("🔊 Sound Alerts: " + ("ON" if self.settings["enable_sound"] else "OFF"), self.toggle_sound),
            rumps.MenuItem("🎤 Voice Alerts: " + ("ON" if self.settings["enable_voice"] else "OFF"), self.toggle_voice),
            rumps.MenuItem("🔔 Notifications: " + ("ON" if self.settings["enable_notifications"] else "OFF"), self.toggle_notifications),
            rumps.MenuItem("🆕 Update Checks: " + ("ON" if self.settings["enable_update_checks"] else "OFF"), self.toggle_update_checks),
            rumps.MenuItem("🧭 Update Channel: " + self.settings.get("update_channel", "stable").upper(), self.toggle_update_channel),
            None,
            rumps.MenuItem("🚀 Launch at Startup: " + ("ON" if self.settings["auto_launch"] else "OFF"), self.toggle_autolaunch),
            None,
            rumps.MenuItem("View System Status", self.check_status),
            rumps.MenuItem("Version & Updates", self.show_version_and_updates),
            rumps.MenuItem("Run Update Check", self.check_for_updates_now),
            rumps.MenuItem("Download Latest Release", self.download_latest_release),
            rumps.MenuItem("Guided Update (Download & Open DMG)", self.download_and_open_latest_installer),
            rumps.MenuItem("Open Releases Page", self.open_releases_page),
            rumps.MenuItem("Run Test Alert", self.test_alert),
            rumps.MenuItem("View Alert History", self.view_alert_history),
            rumps.MenuItem("Copy Support Diagnostics", self.copy_diagnostics),
            rumps.MenuItem("Export Support Bundle", self.export_support_bundle),
            rumps.MenuItem("Open Support Folder", self.open_config_folder),
            None,
            rumps.MenuItem("About", self.show_about),
            rumps.MenuItem("Quit", self.quit_app),
        ]

        if BUILD_TYPE == "dev":
            menu_items[24:24] = [
                None,
                rumps.MenuItem("- Developer -", None),
                rumps.MenuItem("Run Release Validation", self.run_release_validation_now),
                rumps.MenuItem("Export Diagnostics-Only Bundle", self.export_diagnostics_bundle),
            ]

        self.menu = menu_items

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

    def update_boolean_setting(self, key: str, sender: Any, label: str, enabled_text: str = "ON", disabled_text: str = "OFF") -> None:
        self._ensure_managers()
        self.alert_manager.update_boolean_setting(key, sender, label, enabled_text, disabled_text)

    def prompt_for_integer_setting(
        self,
        key: str,
        title: str,
        prompt: str,
        minimum: int,
        maximum: int,
        success_message: str,
    ) -> bool:
        self._ensure_managers()
        return self.alert_manager.prompt_for_integer_setting(
            key,
            title,
            prompt,
            minimum,
            maximum,
            success_message,
        )

    def toggle_update_channel(self, sender: Any) -> None:
        self._ensure_managers()
        self.alert_manager.toggle_update_channel(sender)

    def format_settings_summary(self) -> str:
        self._ensure_managers()
        return self.alert_manager.format_settings_summary()

    def show_preferences(self, _: Any) -> None:
        self._ensure_managers()
        self.alert_manager.show_preferences(_)

    def update_menu_labels(self) -> None:
        self._ensure_managers()
        self.alert_manager.update_menu_labels()

    def set_threshold(self, _: Any) -> None:
        self._ensure_managers()
        self.alert_manager.set_threshold(_)

    def set_interval(self, _: Any) -> None:
        self._ensure_managers()
        self.alert_manager.set_interval(_)

    def set_cooldown(self, _: Any) -> None:
        self._ensure_managers()
        self.alert_manager.set_cooldown(_)

    def toggle_sound(self, sender: Any) -> None:
        self._ensure_managers()
        self.alert_manager.toggle_sound(sender)

    def toggle_voice(self, sender: Any) -> None:
        self._ensure_managers()
        self.alert_manager.toggle_voice(sender)

    def toggle_notifications(self, sender: Any) -> None:
        self._ensure_managers()
        self.alert_manager.toggle_notifications(sender)

    def toggle_autolaunch(self, sender: Any) -> None:
        self._ensure_managers()
        self.alert_manager.toggle_autolaunch(sender)

    def setup_autolaunch(self) -> None:
        self._ensure_managers()
        self.config_manager.setup_autolaunch()

    def toggle_update_checks(self, sender: Any) -> None:
        self._ensure_managers()
        self.alert_manager.toggle_update_checks(sender)

    def update_menu_icon(self) -> None:
        self._ensure_managers()
        self.alert_manager.update_menu_icon()

    def update_icon_loop(self) -> None:
        self._ensure_managers()
        self.alert_manager.update_icon_loop()

    def monitor_battery(self) -> None:
        self._ensure_managers()
        self.alert_manager.monitor_battery()

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
        fallback_payload: Any,
        context_label: str,
    ) -> None:
        self._ensure_managers()
        self.config_manager.recover_corrupted_json_file(path, fallback_payload, context_label)

    def _write_json_atomic(self, destination: Path, payload: Any) -> None:
        self._ensure_managers()
        self.config_manager.write_json_atomic(destination, payload)

    def record_app_state_event(self, key: str, value: Any = None) -> None:
        self._ensure_managers()
        self.config_manager.record_app_state_event(key, value)

    def onboarding_summary(self) -> str:
        self._ensure_managers()
        return self.config_manager.onboarding_summary()

    def show_getting_started(self, _: Any = None) -> None:
        self._ensure_managers()
        self.config_manager.show_getting_started(_)

    def maybe_show_first_run_onboarding(self) -> None:
        self._ensure_managers()
        self.config_manager.maybe_show_first_run_onboarding()

    def _is_process_running(self, pid: int) -> bool:
        self._ensure_managers()
        return self.config_manager.is_process_running(pid)

    def ensure_single_instance(self) -> None:
        self._ensure_managers()
        self.config_manager.ensure_single_instance()

    def setup_runtime_logging(self) -> None:
        self._ensure_managers()
        self.diagnostics_manager.setup_runtime_logging()

    def check_runtime_dependencies(self) -> None:
        self._ensure_managers()
        self.diagnostics_manager.check_runtime_dependencies()

    def log_runtime(self, message: str, level: str = "info") -> None:
        self._ensure_managers()
        self.diagnostics_manager.log_runtime(message, level)

    def install_exception_hooks(self) -> None:
        self._ensure_managers()
        self.diagnostics_manager.install_exception_hooks()

    def handle_uncaught_exception(self, exc_type: type, exc_value: Exception, exc_traceback: Any) -> None:
        self._ensure_managers()
        self.diagnostics_manager.handle_uncaught_exception(exc_type, exc_value, exc_traceback)

    def handle_thread_exception(self, args: Any) -> None:
        self._ensure_managers()
        self.diagnostics_manager.handle_thread_exception(args)

    def write_crash_report(
        self,
        exc_type: type,
        exc_value: Exception,
        exc_traceback: Any,
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

    def show_maintenance_status(self, message: str) -> None:
        self._ensure_managers()
        self.diagnostics_manager.show_maintenance_status(message)

    def build_usage_summary(self) -> str:
        self._ensure_managers()
        return self.diagnostics_manager.build_usage_summary()

    def build_release_visibility_summary(self) -> str:
        self._ensure_managers()
        return self.diagnostics_manager.build_release_visibility_summary()

    def build_status_summary(self, battery_info: Optional[Dict[str, Union[int, bool]]] = None) -> str:
        self._ensure_managers()
        return self.diagnostics_manager.build_status_summary(battery_info)

    def redact_text_for_support_share(self, text: str) -> str:
        self._ensure_managers()
        return self.diagnostics_manager.redact_text_for_support_share(text)

    def cleanup_old_support_artifacts(self, keep_bundles: int = 10, keep_crash_reports: int = 10) -> None:
        self._ensure_managers()
        self.diagnostics_manager.cleanup_old_support_artifacts(keep_bundles, keep_crash_reports)

    def get_latest_crash_report_path(self) -> Optional[Path]:
        self._ensure_managers()
        return self.diagnostics_manager.get_latest_crash_report_path()

    def show_feedback(self, title: str, message: str) -> None:
        self._ensure_managers()
        self.diagnostics_manager.show_feedback(title, message)

    def show_non_blocking_feedback(self, title: str, message: str) -> None:
        self._ensure_managers()
        self.diagnostics_manager.show_non_blocking_feedback(title, message)

    def create_support_bundle_archive(self, preset: str = "full") -> Optional[Path]:
        self._ensure_managers()
        return self.diagnostics_manager.create_support_bundle_archive(preset)

    def check_status(self, _: Any) -> None:
        self._ensure_managers()
        self.diagnostics_manager.check_status(_)

    def test_alert(self, _: Any) -> None:
        self._ensure_managers()
        self.diagnostics_manager.test_alert(_)

    def view_alert_history(self, _: Any) -> None:
        self._ensure_managers()
        self.diagnostics_manager.view_alert_history(_)

    def copy_diagnostics(self, _: Any) -> None:
        self._ensure_managers()
        self.diagnostics_manager.copy_diagnostics(_)

    def export_support_bundle(self, _: Any) -> None:
        self._ensure_managers()
        self.diagnostics_manager.export_support_bundle(_)

    def export_diagnostics_bundle(self, _: Any) -> None:
        self._ensure_managers()
        self.diagnostics_manager.export_diagnostics_bundle(_)

    def open_config_folder(self, _: Any) -> None:
        self._ensure_managers()
        self.diagnostics_manager.open_config_folder(_)

    def show_about(self, _: Any) -> None:
        self._ensure_managers()
        self.diagnostics_manager.show_about(_)

    def quit_app(self, _: Any) -> None:
        self._ensure_managers()
        self.diagnostics_manager.quit_app(_)

    def check_for_updates(self, manual: bool = False) -> Dict[str, str]:
        self._ensure_managers()
        return self.update_checker.check_for_updates(manual)

    def record_update_check_result(
        self,
        status: str,
        latest_version: Optional[str] = None,
        latest_url: Optional[str] = None,
        checked_at: Optional[datetime] = None,
    ) -> None:
        self._ensure_managers()
        self.update_checker.record_update_check_result(status, latest_version, latest_url, checked_at)

    def _version_tuple(self, version: str) -> Tuple[int, int, int]:
        self._ensure_managers()
        return self.update_checker._version_tuple(version)

    def is_newer_version(self, latest_version: str, current_version: str) -> bool:
        self._ensure_managers()
        return self.update_checker.is_newer_version(latest_version, current_version)

    def _read_last_update_check(self) -> Optional[datetime]:
        self._ensure_managers()
        return self.update_checker._read_last_update_check()

    def _write_last_update_check(self, timestamp: datetime) -> None:
        self._ensure_managers()
        self.update_checker._write_last_update_check(timestamp)

    def should_check_for_updates(self, now: Optional[datetime] = None, minimum_hours: int = 24) -> bool:
        self._ensure_managers()
        return self.update_checker.should_check_for_updates(now, minimum_hours)

    def _run_manual_update_check(self) -> None:
        self._ensure_managers()
        self.update_checker._run_manual_update_check()

    def check_for_updates_now(self, _: Any) -> None:
        self._ensure_managers()
        self.update_checker.check_for_updates_now(_)

    def show_version_and_updates(self, _: Any = None) -> None:
        self._ensure_managers()
        self.update_checker.show_version_and_updates(_)

    def open_releases_page(self, _: Any = None) -> None:
        self._ensure_managers()
        self.update_checker.open_releases_page(_)

    def get_latest_release(self) -> Dict[str, str]:
        self._ensure_managers()
        return self.update_checker.get_latest_release()

    def download_latest_release(self, _: Any = None) -> None:
        self._ensure_managers()
        self.update_checker.download_latest_release(_)

    def download_and_open_latest_installer(self, _: Any = None) -> None:
        self._ensure_managers()
        self.update_checker.download_and_open_latest_installer(_)

    def build_release_validation_command(self) -> List[str]:
        self._ensure_managers()
        return self.update_checker.build_release_validation_command()

    def _run_release_validation(self) -> None:
        self._ensure_managers()
        self.update_checker._run_release_validation()

    def run_release_validation_now(self, _: Any) -> None:
        self._ensure_managers()
        self.update_checker.run_release_validation_now(_)


__all__ = ["APP_VERSION", "BatteryAlertApp"]
