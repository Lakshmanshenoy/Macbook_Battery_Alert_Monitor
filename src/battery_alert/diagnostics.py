# mypy: ignore-errors
import logging
import platform
import shutil
import subprocess
import sys
import traceback
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Optional, Union

from .constants import APP_VERSION, CRASH_REPORT_SCHEMA_VERSION, REQUIRED_RUNTIME_TOOLS
from .legacy_app import BatteryAlertApp as LegacyBatteryAlertApp


class DiagnosticsManager:
    """Diagnostics/logging/support-bundle facade."""

    def __init__(self, app: "LegacyBatteryAlertApp") -> None:
        self.app = app

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

    def handle_uncaught_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """Persist uncaught exceptions raised on the main thread."""
        if issubclass(exc_type, KeyboardInterrupt):
            if self.app._previous_excepthook:
                self.app._previous_excepthook(exc_type, exc_value, exc_traceback)
            return

        self.write_crash_report(exc_type, exc_value, exc_traceback, thread_name="main")
        self.log_runtime(f"Captured uncaught exception: {exc_type.__name__}: {exc_value}", level="warning")

    def handle_thread_exception(self, args) -> None:
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
        exc_traceback,
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
            subprocess.run(["osascript", "-e", apple_script], capture_output=True, text=True)
        except Exception as exc:
            self.log_runtime(f"Notification fallback failed: {exc}", level="warning")
        self.log_runtime(f"{title}: {message}")

    def build_diagnostics_report(
        self,
        battery_info: Optional[Dict[str, Union[int, bool]]] = None,
    ) -> str:
        return LegacyBatteryAlertApp.build_diagnostics_report(self.app, battery_info)

    def export_support_bundle(self, preset: str = "full") -> Optional[Path]:
        return LegacyBatteryAlertApp.create_support_bundle_archive(self.app, preset)
