# mypy: ignore-errors
import json
import logging
import platform
import re
import shutil
import subprocess
import sys
import traceback
import zipfile
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional, Union

from .constants import (
    APP_STATE_SCHEMA_VERSION,
    APP_VERSION,
    CONFIG_SCHEMA_VERSION,
    CRASH_REPORT_SCHEMA_VERSION,
    REQUIRED_RUNTIME_TOOLS,
    SUPPORT_BUNDLE_SCHEMA_VERSION,
    UPDATE_CHANNEL,
)
from .legacy_app import BatteryAlertApp as LegacyBatteryAlertApp


class DiagnosticsManager:
    """Diagnostics/logging/support-bundle facade."""

    def __init__(self, app: "LegacyBatteryAlertApp") -> None:
        self.app = app

    def _subprocess_module(self) -> Any:
        gui_module = sys.modules.get("battery_alert_gui")
        return getattr(gui_module, "subprocess", subprocess)

    def _rumps_module(self) -> Any:
        gui_module = sys.modules.get("battery_alert_gui")
        rumps = getattr(gui_module, "rumps", None)
        if rumps is not None:
            return rumps

        import rumps as imported_rumps

        return imported_rumps

    def check_runtime_dependencies(self) -> None:
        """Check required tools and track degraded runtime states."""
        missing_tools = []
        for tool_name, capability in REQUIRED_RUNTIME_TOOLS.items():
            if shutil.which(tool_name) is None:
                missing_tools.append(f"{tool_name} ({capability})")

        self.app.runtime_health = {
            "missing_tools": missing_tools,
            "is_degraded": bool(missing_tools),
            "checked_at": datetime.now().isoformat(),
        }

        if missing_tools:
            self.log_runtime(
                f"Runtime degraded; missing tools: {', '.join(missing_tools)}",
                level="warning",
            )

    def setup_runtime_logging(self) -> None:
        try:
            self.app.runtime_log_file.parent.mkdir(parents=True, exist_ok=True)
            logger = logging.getLogger("battery_alert")
            logger.setLevel(logging.INFO)
            logger.propagate = False

            if not logger.handlers:
                handler = RotatingFileHandler(
                    self.app.runtime_log_file,
                    maxBytes=1_000_000,
                    backupCount=3,
                    encoding="utf-8",
                )
                handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
                logger.addHandler(handler)

            self.app.logger = logger
            self.log_runtime("Runtime logging initialized")
        except Exception as exc:
            self.log_runtime(f"Failed to initialize runtime logging: {exc}", level="error")

    def log_runtime(self, message: str, level: str = "info") -> None:
        """Log runtime messages to rotating file with fallback logger."""
        if self.app.logger:
            log_method = getattr(self.app.logger, level, self.app.logger.info)
            log_method(message)
            return

        fallback_logger = logging.getLogger("battery_alert")
        fallback_method = getattr(fallback_logger, level, fallback_logger.info)
        fallback_method(message)

    def install_exception_hooks(self) -> None:
        self.app._previous_excepthook = sys.excepthook
        sys.excepthook = self.handle_uncaught_exception

        if hasattr(__import__("threading"), "excepthook"):
            import threading

            self.app._previous_threading_excepthook = threading.excepthook
            threading.excepthook = self.handle_thread_exception

    def handle_uncaught_exception(self, exc_type: type, exc_value: Exception, exc_traceback: Any) -> None:
        """Persist uncaught exceptions raised on the main thread."""
        if issubclass(exc_type, KeyboardInterrupt):
            if self.app._previous_excepthook:
                self.app._previous_excepthook(exc_type, exc_value, exc_traceback)
            return

        self.write_crash_report(exc_type, exc_value, exc_traceback, thread_name="main")
        self.log_runtime(f"Captured uncaught exception: {exc_type.__name__}: {exc_value}", level="warning")

    def handle_thread_exception(self, args: Any) -> None:
        """Persist uncaught exceptions raised on background threads."""
        thread_name = getattr(getattr(args, "thread", None), "name", "background")
        self.write_crash_report(args.exc_type, args.exc_value, args.exc_traceback, thread_name=thread_name)
        self.log_runtime(
            f"Captured background exception in {thread_name}: {args.exc_type.__name__}: {args.exc_value}",
            level="warning",
        )

        if self.app._previous_threading_excepthook:
            self.app._previous_threading_excepthook(args)

    def write_crash_report(
        self,
        exc_type: type,
        exc_value: Exception,
        exc_traceback: Any,
        thread_name: str = "main",
    ) -> Optional[Path]:
        report_timestamp = datetime.now()
        payload = {
            "crash_report_schema_version": CRASH_REPORT_SCHEMA_VERSION,
            "created_at": report_timestamp.isoformat(),
            "app_version": APP_VERSION,
            "thread_name": thread_name,
            "exception_type": getattr(exc_type, "__name__", str(exc_type)),
            "exception_message": str(exc_value),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "traceback": traceback.format_exception(exc_type, exc_value, exc_traceback),
        }

        try:
            crash_reports_dir = getattr(self.app, "crash_reports_dir", self.app.config_dir / "crash_reports")
            self.app.crash_reports_dir = crash_reports_dir
            crash_reports_dir.mkdir(parents=True, exist_ok=True)
            report_path = crash_reports_dir / f"crash_report_{report_timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            self.app._write_json_atomic(report_path, payload)
            self.app.record_app_state_event("last_crash_report_at", report_timestamp.isoformat())
            return report_path
        except Exception as exc:
            self.log_runtime(f"Failed to write crash report: {exc}", level="error")
            return None

    def get_latest_crash_report_path(self) -> Optional[Path]:
        """Return latest crash report path, if available."""
        crash_reports_dir = getattr(self.app, "crash_reports_dir", self.app.config_dir / "crash_reports")
        self.app.crash_reports_dir = crash_reports_dir
        if not crash_reports_dir.exists():
            return None

        reports = sorted(crash_reports_dir.glob("crash_report_*.json"))
        return reports[-1] if reports else None

    def show_feedback(self, title: str, message: str) -> None:
        """Show user-facing feedback reliably across rumps versions."""
        try:
            import rumps

            rumps.alert(title, message)
            return
        except TypeError:
            try:
                import rumps

                rumps.alert(message, title=title)
                return
            except Exception:
                pass
        except Exception:
            pass

        self.log_runtime(f"{title}: {message}")

    def show_non_blocking_feedback(self, title: str, message: str) -> None:
        """Show non-blocking feedback via macOS notification fallback."""
        try:
            safe_title = title.replace('"', "'")
            safe_message = message.replace('"', "'")
            apple_script = f'display notification "{safe_message}" with title "{safe_title}"'
            self._subprocess_module().run(["osascript", "-e", apple_script], capture_output=True, text=True)
        except Exception as exc:
            self.log_runtime(f"Notification fallback failed: {exc}", level="warning")
        self.log_runtime(f"{title}: {message}")

    def show_maintenance_status(self, message: str) -> None:
        """Show concise non-blocking status for maintenance actions."""
        self.app.show_non_blocking_feedback("Maintenance", message)

    def build_usage_summary(self) -> str:
        """Return a short summary of onboarding and maintenance metrics."""
        state = self.app.app_state if hasattr(self.app, "app_state") and isinstance(self.app.app_state, dict) else {
            **self.app.default_app_state_payload(),
        }

        return (
            f"First launch completed: {state.get('first_launch_completed')}\n"
            f"Onboarding shown at: {state.get('onboarding_shown_at') or 'never'}\n"
            f"Release checks run: {state.get('release_checks_run', 0)}\n"
            f"Support bundles exported: {state.get('support_bundle_exports', 0)}\n"
            f"Last support bundle export: {state.get('last_support_bundle_export_at') or 'never'}\n"
            f"Last update check: {state.get('last_update_check_at') or 'never'}\n"
            f"Last update result: {state.get('last_update_status') or 'unknown'}\n"
            f"Latest known release: {state.get('last_known_release_version') or 'unknown'}\n"
            f"Latest known release URL: {state.get('last_known_release_url') or 'unknown'}\n"
            f"Last crash report: {state.get('last_crash_report_at') or 'never'}\n"
            f"Last release validation: {state.get('last_release_validation_at') or 'never'}"
        )

    def build_release_visibility_summary(self) -> str:
        """Return a concise version and update visibility summary."""
        state = self.app.app_state if hasattr(self.app, "app_state") and isinstance(self.app.app_state, dict) else {
            **self.app.default_app_state_payload(),
        }

        return (
            f"Current version: {APP_VERSION}\n"
            f"Update channel: {self.app.settings.get('update_channel', UPDATE_CHANNEL)}\n"
            f"Last checked: {state.get('last_update_check_at') or 'never'}\n"
            f"Last result: {state.get('last_update_status') or 'unknown'}\n"
            f"Latest known release: {state.get('last_known_release_version') or 'unknown'}\n"
            f"Latest known release URL: {state.get('last_known_release_url') or 'unknown'}"
        )

    def build_status_summary(self, battery_info: Optional[Dict[str, Union[int, bool]]] = None) -> str:
        """Return a rich operational status snapshot."""
        battery_info = battery_info or self.app.get_battery_info()
        power_source = "Charging" if battery_info["is_charging"] else "Discharging"
        transition = self.app._last_power_transition or "No power transition observed yet"

        return (
            f"Battery level: {battery_info['level']}%\n"
            f"Power source: {power_source}\n"
            f"Last power transition: {transition}\n"
            f"Threshold: {self.app.settings['battery_threshold']}%\n"
            f"Check interval: {self.app.settings['check_interval']} seconds\n"
            f"Alert cooldown: {self.app.settings['alert_cooldown_seconds']} seconds\n"
            f"Last update check: {self.app.app_state.get('last_update_check_at') or 'never'}\n"
            f"Last update result: {self.app.app_state.get('last_update_status') or 'unknown'}\n"
            f"Latest known release: {self.app.app_state.get('last_known_release_version') or 'unknown'}\n"
            f"Support bundles exported: {self.app.app_state.get('support_bundle_exports', 0)}\n"
            f"Last crash report: {self.app.app_state.get('last_crash_report_at') or 'never'}\n"
            f"Runtime degraded: {'yes' if self.app.runtime_health.get('is_degraded') else 'no'}\n"
            f"Missing tools: {', '.join(self.app.runtime_health.get('missing_tools', [])) or 'none'}"
        )

    def check_status(self, _: Any) -> None:
        """Check and display current battery status."""
        try:
            battery_info = self.app.get_battery_info()
            self._rumps_module().alert("System Status", self.app.build_status_summary(battery_info))
        except Exception as exc:
            self.app.log_runtime(f"Error in check_status: {exc}", level="error")

    def test_alert(self, _: Any) -> None:
        """Trigger a manual test alert using the current battery level."""
        try:
            battery_level = self.app.get_battery_info()["level"]
            self.app.trigger_alert(battery_level)
            self._rumps_module().alert(
                "Test alert sent using your current battery status.",
                title="Test Alert",
            )
        except Exception as exc:
            self.app.log_runtime(f"Error in test_alert: {exc}", level="error")
            self._rumps_module().alert(f"Error: {exc}", title="Error")

    def view_alert_history(self, _: Any) -> None:
        """View alert history."""
        try:
            if self.app.alert_history:
                history_text = "Recent Alerts:\n\n"
                for alert in reversed(self.app.alert_history[-20:]):
                    history_text += f"{alert['time']} - {alert['battery_level']}%\n"
            else:
                history_text = "No alerts recorded yet. Your battery is healthy! ✅"

            self._rumps_module().alert("Alert History", history_text)
        except Exception as exc:
            self.app.log_runtime(f"Error in view_alert_history: {exc}", level="error")

    def copy_diagnostics(self, _: Any) -> None:
        """Copy diagnostics information to the clipboard."""
        try:
            diagnostics = self.app.build_diagnostics_report()
            self._subprocess_module().run(["pbcopy"], input=diagnostics, text=True, check=True)
            self._rumps_module().alert("Diagnostics copied to the clipboard.", title="Diagnostics")
        except Exception as exc:
            self.app.log_runtime(f"Error in copy_diagnostics: {exc}", level="error")
            self._rumps_module().alert(f"Error: {exc}", title="Error")

    def redact_text_for_support_share(self, text: str) -> str:
        """Redact obvious local path/user information from shared diagnostics."""
        if not isinstance(text, str):
            return ""
        redacted = text.replace(str(Path.home()), "~")
        redacted = re.sub(r"/Users/[^/\s]+", "/Users/<redacted-user>", redacted)
        redacted = re.sub(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            "<redacted-email>",
            redacted,
        )
        redacted = re.sub(
            r"(?im)^(\s*(?:username|user|account)\s*[:=]\s*).+$",
            r"\1<redacted-user>",
            redacted,
        )
        return redacted

    def build_diagnostics_report(
        self,
        battery_info: Optional[Dict[str, Union[int, bool]]] = None,
    ) -> str:
        battery_info = battery_info or self.app.get_battery_info()
        last_alert = self.app.alert_history[-1]["time"] if self.app.alert_history else "never"

        return (
            "Battery Alert Diagnostics\n"
            f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"python: {sys.version.split()[0]}\n"
            f"platform: {platform.platform()}\n"
            f"battery_level: {battery_info['level']}\n"
            f"charging: {battery_info['is_charging']}\n"
            f"discharging: {battery_info['is_discharging']}\n"
            f"threshold: {self.app.settings['battery_threshold']}\n"
            f"check_interval: {self.app.settings['check_interval']}\n"
            f"alert_cooldown_seconds: {self.app.settings['alert_cooldown_seconds']}\n"
            f"sound_enabled: {self.app.settings['enable_sound']}\n"
            f"voice_enabled: {self.app.settings['enable_voice']}\n"
            f"notifications_enabled: {self.app.settings['enable_notifications']}\n"
            f"auto_launch: {self.app.settings['auto_launch']}\n"
            f"update_checks_enabled: {self.app.settings['enable_update_checks']}\n"
            f"update_channel: {self.app.settings.get('update_channel', UPDATE_CHANNEL)}\n"
            f"runtime_degraded: {self.app.runtime_health.get('is_degraded')}\n"
            f"missing_runtime_tools: {', '.join(self.app.runtime_health.get('missing_tools', [])) or 'none'}\n"
            f"app_version: {APP_VERSION}\n"
            f"alert_history_entries: {len(self.app.alert_history)}\n"
            f"last_alert: {last_alert}\n"
            f"config_file: {self.app.config_file}\n"
            f"log_file: {self.app.log_file}\n"
            f"runtime_log_file: {self.app.runtime_log_file}\n"
            f"\nusage_summary:\n{self.app.build_usage_summary()}"
        )

    def _battery_info_for_support_bundle(self) -> Dict[str, Union[int, bool]]:
        """Build a non-throwing battery snapshot for support bundle generation."""
        try:
            service = getattr(self.app, "battery_service", None)
            cache = getattr(service, "_cache", {}) if service is not None else {}
            return {
                "level": int(cache.get("level", 100)),
                "is_charging": bool(cache.get("is_charging", False)),
                "is_discharging": bool(cache.get("is_discharging", False)),
            }
        except Exception:
            return {
                "level": 100,
                "is_charging": False,
                "is_discharging": False,
            }

    def cleanup_old_support_artifacts(self, keep_bundles: int = 10, keep_crash_reports: int = 10) -> None:
        """Remove older support bundles and crash reports to keep storage tidy."""
        bundles = sorted(self.app.config_dir.glob("support_bundle_*.zip"))
        for old_bundle in bundles[:-keep_bundles]:
            old_bundle.unlink(missing_ok=True)

        crash_reports_dir = getattr(self.app, "crash_reports_dir", self.app.config_dir / "crash_reports")
        reports = sorted(crash_reports_dir.glob("crash_report_*.json")) if crash_reports_dir.exists() else []
        for old_report in reports[:-keep_crash_reports]:
            old_report.unlink(missing_ok=True)

    def create_support_bundle_archive(self, preset: str = "full") -> Optional[Path]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        preset_suffix = "diag" if preset == "diagnostics" else "full"
        bundle_path = self.app.config_dir / f"support_bundle_{preset_suffix}_{timestamp}.zip"

        try:
            diagnostics_text = self.build_diagnostics_report(self._battery_info_for_support_bundle())
        except Exception as exc:
            self.app.log_runtime(f"Falling back to minimal diagnostics report: {exc}", level="warning")
            diagnostics_text = (
                "Battery Alert Diagnostics\n"
                f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"app_version: {APP_VERSION}\n"
                "note: diagnostics fallback used due report generation error\n"
            )

        redacted_diagnostics = self.redact_text_for_support_share(diagnostics_text)
        latest_crash_report = self.get_latest_crash_report_path()

        manifest = {
            "support_bundle_schema_version": SUPPORT_BUNDLE_SCHEMA_VERSION,
            "app_version": APP_VERSION,
            "created_at": datetime.now().isoformat(),
            "config_schema_version": self.app.settings.get("config_schema_version", CONFIG_SCHEMA_VERSION),
            "app_state_schema_version": self.app.app_state.get("app_state_schema_version", APP_STATE_SCHEMA_VERSION),
            "crash_report_schema_version": CRASH_REPORT_SCHEMA_VERSION,
            "included_files": [
                "diagnostics.txt",
                "safe_share_guide.txt",
                "manifest.json",
            ],
            "preset": preset,
        }

        if preset != "diagnostics":
            manifest["included_files"].extend([
                "config.json",
                "alert_history.json",
                "logs/battery_alert.log",
            ])

        if latest_crash_report is not None:
            manifest["included_files"].append("crash_reports/latest_crash_report.json")

        if preset != "diagnostics":
            rotated_logs = sorted(self.app.runtime_log_file.parent.glob("battery_alert.log.*"))
            for rotated_log in rotated_logs:
                manifest["included_files"].append(f"logs/{rotated_log.name}")

        safe_share_guide = (
            "Support Bundle Safe-Share Guide\n"
            "- Review diagnostics.txt before sharing externally.\n"
            "- Redacted diagnostics replace your home directory with '~'.\n"
            "- Crash reports are included when available and may mention code paths or thread names.\n"
            "- Remove files you do not want to share before sending.\n"
        )

        with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("diagnostics.txt", redacted_diagnostics)
            archive.writestr("safe_share_guide.txt", safe_share_guide)
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))

            if preset != "diagnostics":
                if self.app.config_file.exists():
                    archive.write(self.app.config_file, arcname="config.json")
                if self.app.log_file.exists():
                    archive.write(self.app.log_file, arcname="alert_history.json")
                if self.app.runtime_log_file.exists():
                    archive.write(self.app.runtime_log_file, arcname="logs/battery_alert.log")

            if latest_crash_report is not None and latest_crash_report.exists():
                archive.writestr(
                    "crash_reports/latest_crash_report.json",
                    self.redact_text_for_support_share(latest_crash_report.read_text(encoding="utf-8")),
                )

            if preset != "diagnostics":
                for rotated_log in self.app.runtime_log_file.parent.glob("battery_alert.log.*"):
                    archive.write(rotated_log, arcname=f"logs/{rotated_log.name}")

        self.cleanup_old_support_artifacts()
        return bundle_path

    def export_support_bundle(self, _: Any) -> None:
        """Generate a support zip bundle for troubleshooting."""
        try:
            bundle_path = self.create_support_bundle_archive(preset="full")
            self.app.record_app_state_event("support_bundle_exports")
            self.app.record_app_state_event("last_support_bundle_export_at", datetime.now().isoformat())
            self.app.log_runtime(f"Support bundle exported to {bundle_path}")

            try:
                self._subprocess_module().run(["open", "-R", str(bundle_path)], check=False)
            except Exception as exc:
                self.app.log_runtime(f"Unable to reveal support bundle in Finder: {exc}", level="warning")

            try:
                self.app.show_maintenance_status("Support bundle export complete.")
            except Exception as exc:
                self.app.log_runtime(f"Unable to show maintenance status: {exc}", level="warning")

            self.app.show_feedback(
                "Support Bundle Exported",
                f"Support bundle created at:\n{bundle_path}\n\n"
                "Tip: Review safe_share_guide.txt in the bundle before sharing.",
            )
        except Exception as exc:
            self.app.log_runtime(f"Failed to export support bundle: {exc}", level="warning")
            self.app.show_feedback("Error", f"Failed to export support bundle: {exc}")

    def export_diagnostics_bundle(self, _: Any) -> None:
        """Generate a diagnostics-only support bundle for lightweight triage."""
        try:
            bundle_path = self.create_support_bundle_archive(preset="diagnostics")
            self.app.record_app_state_event("support_bundle_exports")
            self.app.record_app_state_event("last_support_bundle_export_at", datetime.now().isoformat())
            self.app.log_runtime(f"Diagnostics-only bundle exported to {bundle_path}")

            try:
                self._subprocess_module().run(["open", "-R", str(bundle_path)], check=False)
            except Exception as exc:
                self.app.log_runtime(f"Unable to reveal diagnostics bundle in Finder: {exc}", level="warning")

            try:
                self.app.show_maintenance_status("Diagnostics-only bundle export complete.")
            except Exception as exc:
                self.app.log_runtime(f"Unable to show maintenance status: {exc}", level="warning")
        except Exception as exc:
            self.app.log_runtime(f"Failed to export diagnostics-only bundle: {exc}", level="warning")
            self.app.show_feedback("Error", f"Failed to export diagnostics-only bundle: {exc}")

    def open_config_folder(self, _: Any) -> None:
        """Open the configuration directory in Finder."""
        try:
            self._subprocess_module().run(["open", str(self.app.config_dir)], check=True)
        except Exception as exc:
            self.app.log_runtime(f"Error in open_config_folder: {exc}", level="error")
            self._rumps_module().alert(f"Error: {exc}", title="Error")

    def show_about(self, _: Any) -> None:
        """Show about dialog."""
        try:
            about_text = f"""Battery Alert Monitor v{APP_VERSION}

A professional battery monitoring tool for macOS.

Keep your device powered and healthy! 🔋

© 2024"""
            self._rumps_module().alert("About Battery Alert", about_text)
        except Exception as exc:
            self.app.log_runtime(f"Error in show_about: {exc}", level="error")

    def quit_app(self, _: Any) -> None:
        """Quit the application gracefully."""
        try:
            self.app.log_runtime("Application shutdown requested")
            self.app.monitoring = False
            self.app.stop_event.set()

            if hasattr(self.app, "monitor_thread") and self.app.monitor_thread.is_alive():
                self.app.monitor_thread.join(timeout=2)
            if hasattr(self.app, "icon_update_thread") and self.app.icon_update_thread.is_alive():
                self.app.icon_update_thread.join(timeout=2)

            self.app.pid_file.unlink(missing_ok=True)
            self._rumps_module().quit_application()
        except Exception as exc:
            self.app.log_runtime(f"Error quitting: {exc}", level="error")
            self._rumps_module().quit_application()
