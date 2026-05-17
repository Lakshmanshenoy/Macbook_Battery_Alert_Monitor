#!/usr/bin/env python3
"""
Battery Alert Monitor - macOS GUI Application
A professional battery monitoring tool for macOS users
"""

import os
import json
import threading
import subprocess
import sys
import platform
import logging
from logging.handlers import RotatingFileHandler
import urllib.request
import urllib.error
import zipfile
import re
import traceback
import shutil
from datetime import datetime
from pathlib import Path
import rumps


APP_VERSION = "1.1.0"
LATEST_STABLE_RELEASE_API = "https://api.github.com/repos/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/releases/latest"
RELEASES_API = "https://api.github.com/repos/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/releases"
RELEASES_PAGE_URL = "https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/releases"
UPDATE_CHANNEL = "stable"
CONFIG_SCHEMA_VERSION = 2
APP_STATE_SCHEMA_VERSION = 4
SUPPORT_BUNDLE_SCHEMA_VERSION = 4
CRASH_REPORT_SCHEMA_VERSION = 1
UPDATE_STATE_SCHEMA_VERSION = 1
REQUIRED_RUNTIME_TOOLS = {
    "pmset": "battery monitoring",
    "osascript": "notifications",
    "afplay": "sound alerts",
    "say": "voice alerts",
}


class BatteryAlertApp(rumps.App):
    """Main application class with menu bar integration"""

    @staticmethod
    def default_settings_payload():
        """Default persisted settings payload."""
        return {
            "config_schema_version": CONFIG_SCHEMA_VERSION,
            "battery_threshold": 20,
            "check_interval": 10,
            "alert_cooldown_seconds": 900,
            "enable_sound": True,
            "enable_voice": True,
            "enable_notifications": True,
            "auto_launch": False,
            "enable_update_checks": True,
            "update_channel": UPDATE_CHANNEL,
        }

    @staticmethod
    def default_app_state_payload():
        """Default persisted application state payload."""
        return {
            "app_state_schema_version": APP_STATE_SCHEMA_VERSION,
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

    @staticmethod
    def default_update_state_payload():
        """Default persisted update-state payload."""
        return {
            "update_state_schema_version": UPDATE_STATE_SCHEMA_VERSION,
            "last_checked": None,
        }
    
    def __init__(self):
        """Initialize the application"""
        super(BatteryAlertApp, self).__init__("🔋", quit_button=None)
        
        # Configuration
        self.config_dir = Path.home() / ".battery_alert"
        self.config_file = self.config_dir / "config.json"
        self.log_file = self.config_dir / "alert_history.json"
        self.pid_file = self.config_dir / "app.pid"
        self.runtime_log_file = self.config_dir / "logs" / "battery_alert.log"
        self.update_state_file = self.config_dir / "update_state.json"
        self.app_state_file = self.config_dir / "app_state.json"
        self.crash_reports_dir = self.config_dir / "crash_reports"
        
        # Create config directory
        self.config_dir.mkdir(exist_ok=True)
        
        # Default settings
        self.settings = self.default_settings_payload()

        self._below_threshold_prev = False
        self._last_alert_time = None
        self._last_power_state = None
        self._last_power_transition = None
        self._update_check_in_progress = False
        self._release_validation_in_progress = False
        self._previous_excepthook = None
        self._previous_threading_excepthook = None
        self.runtime_health = {
            "missing_tools": [],
            "is_degraded": False,
            "checked_at": None,
        }
        self.stop_event = threading.Event()
        
        # Alert history
        self.alert_history = []
        self.app_state = self.default_app_state_payload()
        self.update_state = self.default_update_state_payload()
        self.logger = None

        # Logging should start before other runtime operations.
        self.setup_runtime_logging()
        self.install_exception_hooks()
        self.check_runtime_dependencies()
        
        # Load configuration
        self.load_config()
        self.load_alert_history()
        self.load_app_state()
        self.load_update_state()

        # Ensure single-instance behavior before writing our PID
        self.ensure_single_instance()
        
        # Save PID
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
        # Start monitoring thread
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self.monitor_battery, daemon=True)
        self.monitor_thread.start()
        
        # Start icon update thread (updates every 5 seconds for dynamic display)
        self.icon_update_thread = threading.Thread(target=self.update_icon_loop, daemon=True)
        self.icon_update_thread.start()
        
        # Setup menu
        self.setup_menu()
        
        # Update icon with battery level immediately
        self.update_menu_icon()

        # Show a lightweight first-run tip once, then remember that onboarding was shown.
        self.maybe_show_first_run_onboarding()

        # Non-blocking update check on startup.
        self.check_for_updates(manual=False)
    
    def load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.settings = self.migrate_config_payload(loaded)
                    else:
                        self.settings = self.default_settings_payload()
                self.validate_settings()
            except Exception as e:
                print(f"[ERROR] Failed to load config: {e}")
                self.settings = self.default_settings_payload()
                self.validate_settings()
                self.recover_corrupted_json_file(
                    self.config_file,
                    self.settings,
                    "config"
                )
        else:
            self.save_config()

    def migrate_config_payload(self, payload):
        """Migrate persisted config payloads from older schema versions."""
        merged = self.default_settings_payload()
        if not isinstance(payload, dict):
            return merged

        merged.update(payload)
        merged["config_schema_version"] = CONFIG_SCHEMA_VERSION
        return merged

    def validate_settings(self):
        """Validate and normalize settings read from disk."""
        threshold = self.settings.get("battery_threshold", 20)
        interval = self.settings.get("check_interval", 10)
        cooldown = self.settings.get("alert_cooldown_seconds", 900)

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

        self.settings["battery_threshold"] = max(1, min(100, threshold))
        self.settings["check_interval"] = max(10, min(3600, interval))
        self.settings["alert_cooldown_seconds"] = max(30, min(86400, cooldown))
        self.settings["enable_sound"] = bool(self.settings.get("enable_sound", True))
        self.settings["enable_voice"] = bool(self.settings.get("enable_voice", True))
        self.settings["enable_notifications"] = bool(self.settings.get("enable_notifications", True))
        self.settings["auto_launch"] = bool(self.settings.get("auto_launch", False))
        self.settings["enable_update_checks"] = bool(self.settings.get("enable_update_checks", True))
        update_channel = str(self.settings.get("update_channel", UPDATE_CHANNEL)).strip().lower()
        if update_channel not in {"stable", "beta"}:
            update_channel = UPDATE_CHANNEL
        self.settings["update_channel"] = update_channel
        self.settings["config_schema_version"] = CONFIG_SCHEMA_VERSION

    def check_runtime_dependencies(self):
        """Check required tools and track degraded runtime states."""
        missing_tools = []
        for tool_name, capability in REQUIRED_RUNTIME_TOOLS.items():
            if shutil.which(tool_name) is None:
                missing_tools.append(f"{tool_name} ({capability})")

        self.runtime_health = {
            "missing_tools": missing_tools,
            "is_degraded": bool(missing_tools),
            "checked_at": datetime.now().isoformat(),
        }

        if missing_tools:
            self.log_runtime(
                f"Runtime degraded; missing tools: {', '.join(missing_tools)}",
                level="warning",
            )

    def setup_runtime_logging(self):
        """Create a rotating runtime log for support and diagnostics."""
        try:
            self.runtime_log_file.parent.mkdir(parents=True, exist_ok=True)
            logger = logging.getLogger("battery_alert")
            logger.setLevel(logging.INFO)
            logger.propagate = False

            if not logger.handlers:
                handler = RotatingFileHandler(
                    self.runtime_log_file,
                    maxBytes=1_000_000,
                    backupCount=3,
                    encoding="utf-8"
                )
                handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
                logger.addHandler(handler)

            self.logger = logger
            self.log_runtime("Runtime logging initialized")
        except Exception as e:
            print(f"[ERROR] Failed to initialize runtime logging: {e}")

    def log_runtime(self, message, level="info"):
        """Log runtime messages to both console and rotating log file."""
        print(f"[RUNTIME] {message}")
        if not self.logger:
            return

        log_method = getattr(self.logger, level, self.logger.info)
        log_method(message)

    def install_exception_hooks(self):
        """Capture uncaught exceptions into crash reports for later support analysis."""
        self._previous_excepthook = sys.excepthook
        sys.excepthook = self.handle_uncaught_exception

        if hasattr(threading, "excepthook"):
            self._previous_threading_excepthook = threading.excepthook
            threading.excepthook = self.handle_thread_exception

    def handle_uncaught_exception(self, exc_type, exc_value, exc_traceback):
        """Persist an uncaught exception raised on the main thread."""
        if issubclass(exc_type, KeyboardInterrupt):
            if self._previous_excepthook:
                self._previous_excepthook(exc_type, exc_value, exc_traceback)
            return

        self.write_crash_report(exc_type, exc_value, exc_traceback, thread_name="main")
        self.log_runtime(f"Captured uncaught exception: {exc_type.__name__}: {exc_value}", level="warning")

    def handle_thread_exception(self, args):
        """Persist an uncaught exception raised on a background thread."""
        thread_name = getattr(getattr(args, "thread", None), "name", "background")
        self.write_crash_report(args.exc_type, args.exc_value, args.exc_traceback, thread_name=thread_name)
        self.log_runtime(
            f"Captured background exception in {thread_name}: {args.exc_type.__name__}: {args.exc_value}",
            level="warning",
        )

        if self._previous_threading_excepthook:
            self._previous_threading_excepthook(args)

    def write_crash_report(self, exc_type, exc_value, exc_traceback, thread_name="main"):
        """Write a structured crash report for diagnostics and support bundles."""
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
            crash_reports_dir = getattr(self, "crash_reports_dir", self.config_dir / "crash_reports")
            self.crash_reports_dir = crash_reports_dir
            crash_reports_dir.mkdir(parents=True, exist_ok=True)
            report_path = crash_reports_dir / f"crash_report_{report_timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            self._write_json_atomic(report_path, payload)
            self.record_app_state_event("last_crash_report_at", report_timestamp.isoformat())
            return report_path
        except Exception as e:
            print(f"[ERROR] Failed to write crash report: {e}")
            return None

    def get_latest_crash_report_path(self):
        """Return the newest crash report on disk, if present."""
        crash_reports_dir = getattr(self, "crash_reports_dir", self.config_dir / "crash_reports")
        self.crash_reports_dir = crash_reports_dir
        if not crash_reports_dir.exists():
            return None

        reports = sorted(crash_reports_dir.glob("crash_report_*.json"))
        return reports[-1] if reports else None

    def show_feedback(self, title, message):
        """Show user-facing feedback reliably across rumps versions."""
        try:
            rumps.alert(title, message)
            return
        except TypeError:
            # Some versions can prefer keyword title ordering.
            try:
                rumps.alert(message, title=title)
                return
            except Exception:
                pass
        except Exception:
            pass

        # Last-resort fallback so user still gets context in logs.
        self.log_runtime(f"{title}: {message}")

    def show_non_blocking_feedback(self, title, message):
        """Show non-blocking user feedback via macOS notification."""
        try:
            safe_title = title.replace('"', "'")
            safe_message = message.replace('"', "'")
            apple_script = f'display notification "{safe_message}" with title "{safe_title}"'
            subprocess.run(["osascript", "-e", apple_script], capture_output=True, text=True)
        except Exception as e:
            self.log_runtime(f"Notification fallback failed: {e}", level="warning")
        self.log_runtime(f"{title}: {message}")

    def _write_json_atomic(self, file_path, payload):
        """Write JSON atomically to avoid corruption from interrupted writes."""
        temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
        with open(temp_path, 'w') as f:
            json.dump(payload, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, file_path)

    def recover_corrupted_json_file(self, file_path, default_payload, context_label):
        """Quarantine unreadable JSON and replace it with a safe default payload."""
        try:
            if file_path.exists():
                quarantine_name = f"{file_path.name}.corrupt.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                quarantine_path = file_path.with_name(quarantine_name)
                file_path.replace(quarantine_path)
                self.log_runtime(
                    f"Recovered corrupted {context_label} file by quarantining to {quarantine_path.name}",
                    level="warning"
                )
            self._write_json_atomic(file_path, default_payload)
        except Exception as e:
            print(f"[ERROR] Failed to recover corrupted {context_label} file: {e}")
    
    def save_config(self):
        """Save configuration to file"""
        try:
            self.validate_settings()
            self._write_json_atomic(self.config_file, self.settings)
        except Exception as e:
            print(f"[ERROR] Failed to save config: {e}")
    
    def load_alert_history(self):
        """Load alert history from file"""
        if self.log_file.exists():
            try:
                with open(self.log_file) as f:
                    loaded_history = json.load(f)
                    if isinstance(loaded_history, list):
                        self.alert_history = [
                            alert for alert in loaded_history
                            if isinstance(alert, dict)
                            and "time" in alert
                            and "battery_level" in alert
                        ][-50:]  # Keep last 50 alerts
                    else:
                        self.alert_history = []
            except Exception as e:
                print(f"[ERROR] Failed to load history: {e}")
                self.alert_history = []
                self.recover_corrupted_json_file(self.log_file, [], "alert history")
    
    def save_alert_history(self):
        """Save alert history to file"""
        try:
            self._write_json_atomic(self.log_file, self.alert_history[-100:])  # Keep up to 100 alerts
        except Exception as e:
            print(f"[ERROR] Failed to save history: {e}")

    def load_app_state(self):
        """Load persistent app state used for onboarding and maintenance metrics."""
        if not self.app_state_file.exists():
            self.save_app_state()
            return

        try:
            with open(self.app_state_file) as f:
                loaded_state = json.load(f)
            if isinstance(loaded_state, dict):
                self.app_state = self.migrate_app_state_payload(loaded_state)
            else:
                self.app_state = self.default_app_state_payload()
                self.save_app_state()
        except Exception as e:
            print(f"[ERROR] Failed to load app state: {e}")
            self.app_state = self.default_app_state_payload()
            self.recover_corrupted_json_file(
                self.app_state_file,
                self.app_state,
                "app state"
            )

    def migrate_app_state_payload(self, payload):
        """Migrate persisted app-state payloads from older schema versions."""
        merged = self.default_app_state_payload()
        if not isinstance(payload, dict):
            return merged

        merged.update(payload)
        merged["app_state_schema_version"] = APP_STATE_SCHEMA_VERSION
        return merged

    def save_app_state(self):
        """Persist app state used for onboarding and maintenance metrics."""
        try:
            self.app_state["app_state_schema_version"] = APP_STATE_SCHEMA_VERSION
            self._write_json_atomic(self.app_state_file, self.app_state)
        except Exception as e:
            print(f"[ERROR] Failed to save app state: {e}")

    def migrate_update_state_payload(self, payload):
        """Migrate persisted update-state payloads from older schema versions."""
        merged = self.default_update_state_payload()
        if not isinstance(payload, dict):
            return merged

        merged.update(payload)
        merged["update_state_schema_version"] = UPDATE_STATE_SCHEMA_VERSION
        return merged

    def load_update_state(self):
        """Load update throttle state used by automatic checks."""
        if not self.update_state_file.exists():
            self.save_update_state()
            return

        try:
            with open(self.update_state_file) as f:
                loaded_state = json.load(f)
            if isinstance(loaded_state, dict):
                self.update_state = self.migrate_update_state_payload(loaded_state)
            else:
                self.update_state = self.default_update_state_payload()
                self.save_update_state()
        except Exception as e:
            print(f"[ERROR] Failed to load update state: {e}")
            self.update_state = self.default_update_state_payload()
            self.recover_corrupted_json_file(
                self.update_state_file,
                self.update_state,
                "update state"
            )

    def save_update_state(self):
        """Persist update throttle state."""
        try:
            self.update_state["update_state_schema_version"] = UPDATE_STATE_SCHEMA_VERSION
            self._write_json_atomic(self.update_state_file, self.update_state)
        except Exception as e:
            print(f"[ERROR] Failed to save update state: {e}")

    def record_app_state_event(self, key, value=None):
        """Record lightweight app usage metrics for post-release support."""
        if not hasattr(self, "app_state") or not isinstance(self.app_state, dict):
            self.app_state = self.default_app_state_payload()

        if key not in self.app_state:
            return

        if isinstance(self.app_state.get(key), int):
            self.app_state[key] = int(self.app_state[key]) + (1 if value is None else value)
        else:
            self.app_state[key] = value
        self.save_app_state()

    def onboarding_summary(self):
        """Return a short onboarding summary for new users."""
        return (
            "Welcome to Battery Alert Monitor.\n\n"
            "Quick start:\n"
            "1. Set Battery Threshold and Alert Cooldown from the menu.\n"
            "2. Use Check for Updates or Run Release Check from the maintenance menu.\n"
            "3. Export a Support Bundle if you need help troubleshooting.\n\n"
            "You can reopen this message from the menu anytime."
        )

    def show_getting_started(self, _=None):
        """Show onboarding guidance on demand."""
        try:
            rumps.alert("Getting Started", self.onboarding_summary())
        except Exception as e:
            print(f"[ERROR] Error in show_getting_started: {e}")

    def maybe_show_first_run_onboarding(self):
        """Show a one-time onboarding tip on first launch."""
        if self.app_state.get("first_launch_completed"):
            return

        self.app_state["first_launch_completed"] = True
        self.app_state["onboarding_shown_at"] = datetime.now().isoformat()
        self.save_app_state()
        self.show_non_blocking_feedback(
            "Welcome",
            "Battery Alert is ready. Open Getting Started for a short tour of the main settings."
        )

    def _is_process_running(self, pid):
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

    def ensure_single_instance(self):
        """Prevent multiple app instances and clean stale PID files."""
        if not self.pid_file.exists():
            return

        try:
            existing_pid_raw = self.pid_file.read_text().strip()
            if not existing_pid_raw:
                self.pid_file.unlink(missing_ok=True)
                return

            existing_pid = int(existing_pid_raw)
            if existing_pid == os.getpid():
                return

            if self._is_process_running(existing_pid):
                raise RuntimeError("Battery Alert is already running.")

            # Stale pid file
            self.pid_file.unlink(missing_ok=True)
        except ValueError:
            self.pid_file.unlink(missing_ok=True)
    
    def get_battery_info(self):
        """Get current battery information"""
        try:
            battery_output = subprocess.check_output(
                ['pmset', '-g', 'batt'],
                universal_newlines=True
            )
            
            # Parse battery level
            import re
            battery_match = re.search(r'(\d+)%', battery_output)
            battery_level = int(battery_match.group(1)) if battery_match else 0
            
            # Parse charger status - improved detection
            # Check for AC Power or charging indicators
            is_charging = ("AC Power" in battery_output and "connected" in battery_output) or \
                         ("charging" in battery_output.lower() and "discharging" not in battery_output.lower())
            is_discharging = "discharging" in battery_output.lower()
            
            # Debug output
            print(f"[BATTERY] Level: {battery_level}%, Charging: {is_charging}, Discharging: {is_discharging}")
            print(f"[BATTERY] Raw: {battery_output.strip()[:100]}")
            
            return {
                "level": battery_level,
                "is_charging": is_charging,
                "is_discharging": is_discharging
            }
        except Exception as e:
            print(f"[ERROR] Failed to get battery info: {e}")
            return {"level": 0, "is_charging": False, "is_discharging": False}
    
    def update_menu_icon(self):
        """Update menu bar icon with battery status"""
        try:
            battery_info = self.get_battery_info()
            level = battery_info["level"]
            
            # Icon selection based on battery level
            if battery_info["is_charging"]:
                icon = "🔌"
                print("[ICON] Charging detected - using 🔌")
            elif level > 50:
                icon = "🔋"
            elif level > 20:
                icon = "🪫"
            else:
                icon = "⚠️"
            
            title = f"{icon} {level}%"
            old_title = self.title
            self.title = title
            
            if old_title != title:
                print(f"[ICON UPDATE] {old_title} → {title}")
            
        except Exception as e:
            print(f"[ERROR] Failed to update menu icon: {e}")
    
    def update_icon_loop(self):
        """Continuously update menu bar icon every 5 seconds"""
        while self.monitoring and not self.stop_event.is_set():
            try:
                self.update_menu_icon()
                self.stop_event.wait(5)  # Update every 5 seconds
            except Exception as e:
                print(f"[ERROR] Error in update_icon_loop: {e}")
                self.stop_event.wait(5)

    def should_trigger_alert(self, battery_info, now=None):
        """Decide whether an alert should be triggered using edge + cooldown logic."""
        now = now or datetime.now()

        if not battery_info["is_discharging"]:
            self._below_threshold_prev = False
            return False

        level = battery_info["level"]
        below_threshold = level <= self.settings["battery_threshold"]
        if not below_threshold:
            self._below_threshold_prev = False
            return False

        crossed_threshold = not self._below_threshold_prev
        cooldown_seconds = self.settings["alert_cooldown_seconds"]
        cooldown_elapsed = (
            self._last_alert_time is None
            or (now - self._last_alert_time).total_seconds() >= cooldown_seconds
        )

        self._below_threshold_prev = True
        return crossed_threshold or cooldown_elapsed
    
    def trigger_alert(self, battery_level, now=None):
        """Trigger alert for low battery"""
        now = now or datetime.now()
        self._last_alert_time = now
        alert_time = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Add to history
        self.alert_history.append({
            "time": alert_time,
            "battery_level": battery_level
        })
        self.save_alert_history()
        
        print(f"\n[ALERT TRIGGERED] Battery at {battery_level}% - {alert_time}")
        
        # Play sound
        if self.settings["enable_sound"]:
            try:
                # Try multiple sound files in order of preference
                sound_files = [
                    '/System/Library/Sounds/Alarm.aiff',
                    '/System/Library/Sounds/Glass.aiff',
                    '/System/Library/Sounds/Ping.aiff',
                ]
                for sound_file in sound_files:
                    if os.path.exists(sound_file):
                        subprocess.Popen(['afplay', sound_file])
                        print(f"[SOUND] Playing: {sound_file}")
                        break
            except Exception as e:
                print(f"[ERROR] Sound alert failed: {e}")
        
        # Show notification
        if self.settings["enable_notifications"]:
            try:
                # Use proper AppleScript syntax without line breaks
                apple_script = f'display notification "Battery at {battery_level}%! Please charge your device." with title "Low Battery Alert"'
                result = subprocess.run(['osascript', '-e', apple_script], capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"[ERROR] Notification failed: {result.stderr}")
                else:
                    print("[NOTIFICATION] Sent successfully")
            except Exception as e:
                print(f"[ERROR] Notification alert failed: {e}")
        
        # Voice alert
        if self.settings["enable_voice"]:
            try:
                subprocess.Popen(['say', f'Battery low at {battery_level} percent. Please charge your device.'])
                print("[VOICE] Alert triggered")
            except Exception as e:
                print(f"[ERROR] Voice alert failed: {e}")
    
    def monitor_battery(self):
        """Monitor battery in background thread"""
        while self.monitoring and not self.stop_event.is_set():
            try:
                battery_info = self.get_battery_info()
                level = battery_info["level"]

                current_power_state = "charging" if battery_info["is_charging"] else "discharging"
                if self._last_power_state and self._last_power_state != current_power_state:
                    self._last_power_transition = (
                        f"{self._last_power_state} -> {current_power_state} at {level}% "
                        f"on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    self.log_runtime(
                        f"Power source changed: {self._last_power_state} -> {current_power_state} at {level}%"
                    )
                self._last_power_state = current_power_state

                now = datetime.now()
                if self.should_trigger_alert(battery_info, now=now):
                    self.trigger_alert(level, now=now)

                # Wait before next check
                self.stop_event.wait(self.settings["check_interval"])
            except Exception as e:
                print(f"[ERROR] Error in monitor_battery: {e}")
                self.stop_event.wait(10)
    
    def setup_menu(self):
        """Setup the menu bar items"""
        self.menu = [
            rumps.MenuItem("Getting Started", self.show_getting_started),
            rumps.MenuItem("Show Preferences", self.show_preferences),
            rumps.MenuItem("Battery Threshold", self.set_threshold),
            rumps.MenuItem("Check Interval", self.set_interval),
            rumps.MenuItem("Alert Cooldown", self.set_cooldown),
            None,
            rumps.MenuItem("🔊 Sound Alerts: " + ("ON" if self.settings["enable_sound"] else "OFF"), 
                          self.toggle_sound),
            rumps.MenuItem("🎤 Voice Alerts: " + ("ON" if self.settings["enable_voice"] else "OFF"), 
                          self.toggle_voice),
            rumps.MenuItem("🔔 Notifications: " + ("ON" if self.settings["enable_notifications"] else "OFF"), 
                          self.toggle_notifications),
            rumps.MenuItem("🆕 Update Checks: " + ("ON" if self.settings["enable_update_checks"] else "OFF"),
                          self.toggle_update_checks),
            rumps.MenuItem("🧭 Update Channel: " + self.settings.get("update_channel", UPDATE_CHANNEL).upper(),
                          self.toggle_update_channel),
            None,
            rumps.MenuItem("🚀 Launch at Startup: " + ("ON" if self.settings["auto_launch"] else "OFF"), 
                          self.toggle_autolaunch),
            None,
            rumps.MenuItem("View System Status", self.check_status),
            rumps.MenuItem("Version & Updates", self.show_version_and_updates),
            rumps.MenuItem("Run Update Check", self.check_for_updates_now),
            rumps.MenuItem("Download Latest Release", self.download_latest_release),
            rumps.MenuItem("Run Release Validation", self.run_release_validation_now),
            rumps.MenuItem("Open Releases Page", self.open_releases_page),
            rumps.MenuItem("Run Test Alert", self.test_alert),
            rumps.MenuItem("View Alert History", self.view_alert_history),
            rumps.MenuItem("Copy Support Diagnostics", self.copy_diagnostics),
            rumps.MenuItem("Export Support Bundle", self.export_support_bundle),
            rumps.MenuItem("Export Diagnostics-Only Bundle", self.export_diagnostics_bundle),
            rumps.MenuItem("Open Support Folder", self.open_config_folder),
            None,
            rumps.MenuItem("About", self.show_about),
            rumps.MenuItem("Quit", self.quit_app)
        ]

    def show_preferences(self, _):
        """Show a summary of current user preferences."""
        try:
            rumps.alert("Preferences", self.format_settings_summary())
        except Exception as e:
            print(f"[ERROR] Error in show_preferences: {e}")
    
    def update_menu_labels(self):
        """Update menu item labels to reflect current settings"""
        try:
            # Rebuild menu with updated labels
            self.setup_menu()
        except Exception as e:
            print(f"[ERROR] Failed to update menu: {e}")

    def format_settings_summary(self):
        """Return a human-readable summary of the active preferences."""
        alert_modes = []
        if self.settings["enable_sound"]:
            alert_modes.append("sound")
        if self.settings["enable_voice"]:
            alert_modes.append("voice")
        if self.settings["enable_notifications"]:
            alert_modes.append("notifications")

        modes_text = ", ".join(alert_modes) if alert_modes else "none"
        autolaunch_text = "enabled" if self.settings["auto_launch"] else "disabled"
        updates_text = "enabled" if self.settings["enable_update_checks"] else "disabled"
        update_channel = self.settings.get("update_channel", UPDATE_CHANNEL)

        return (
            f"Battery threshold: {self.settings['battery_threshold']}%\n"
            f"Check interval: {self.settings['check_interval']} seconds\n"
            f"Alert cooldown: {self.settings['alert_cooldown_seconds']} seconds\n"
            f"Alert modes: {modes_text}\n"
            f"Launch at startup: {autolaunch_text}\n"
            f"Update checks: {updates_text}\n"
            f"Update channel: {update_channel}"
        )

    def build_usage_summary(self):
        """Return a short summary of onboarding and maintenance metrics."""
        state = self.app_state if hasattr(self, "app_state") and isinstance(self.app_state, dict) else {
            **self.default_app_state_payload(),
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

    def build_release_visibility_summary(self):
        """Return a concise version and update visibility summary."""
        state = self.app_state if hasattr(self, "app_state") and isinstance(self.app_state, dict) else {
            **self.default_app_state_payload(),
        }

        return (
            f"Current version: {APP_VERSION}\n"
            f"Update channel: {self.settings.get('update_channel', UPDATE_CHANNEL)}\n"
            f"Last checked: {state.get('last_update_check_at') or 'never'}\n"
            f"Last result: {state.get('last_update_status') or 'unknown'}\n"
            f"Latest known release: {state.get('last_known_release_version') or 'unknown'}\n"
            f"Latest known release URL: {state.get('last_known_release_url') or 'unknown'}"
        )

    def build_status_summary(self, battery_info=None):
        """Return a rich operational status snapshot."""
        battery_info = battery_info or self.get_battery_info()
        power_source = "Charging" if battery_info["is_charging"] else "Discharging"
        transition = self._last_power_transition or "No power transition observed yet"

        return (
            f"Battery level: {battery_info['level']}%\n"
            f"Power source: {power_source}\n"
            f"Last power transition: {transition}\n"
            f"Threshold: {self.settings['battery_threshold']}%\n"
            f"Check interval: {self.settings['check_interval']} seconds\n"
            f"Alert cooldown: {self.settings['alert_cooldown_seconds']} seconds\n"
            f"Last update check: {self.app_state.get('last_update_check_at') or 'never'}\n"
            f"Last update result: {self.app_state.get('last_update_status') or 'unknown'}\n"
            f"Latest known release: {self.app_state.get('last_known_release_version') or 'unknown'}\n"
            f"Support bundles exported: {self.app_state.get('support_bundle_exports', 0)}\n"
            f"Last crash report: {self.app_state.get('last_crash_report_at') or 'never'}\n"
            f"Runtime degraded: {'yes' if self.runtime_health.get('is_degraded') else 'no'}\n"
            f"Missing tools: {', '.join(self.runtime_health.get('missing_tools', [])) or 'none'}"
        )

    def redact_text_for_support_share(self, text):
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

    def show_maintenance_status(self, message):
        """Show concise non-blocking status for maintenance actions."""
        self.show_non_blocking_feedback("Maintenance", message)

    def build_diagnostics_report(self, battery_info=None):
        """Build a support-friendly diagnostics snapshot."""
        battery_info = battery_info or self.get_battery_info()
        last_alert = self.alert_history[-1]["time"] if self.alert_history else "never"

        return (
            "Battery Alert Diagnostics\n"
            f"timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"python: {sys.version.split()[0]}\n"
            f"platform: {platform.platform()}\n"
            f"battery_level: {battery_info['level']}\n"
            f"charging: {battery_info['is_charging']}\n"
            f"discharging: {battery_info['is_discharging']}\n"
            f"threshold: {self.settings['battery_threshold']}\n"
            f"check_interval: {self.settings['check_interval']}\n"
            f"alert_cooldown_seconds: {self.settings['alert_cooldown_seconds']}\n"
            f"sound_enabled: {self.settings['enable_sound']}\n"
            f"voice_enabled: {self.settings['enable_voice']}\n"
            f"notifications_enabled: {self.settings['enable_notifications']}\n"
            f"auto_launch: {self.settings['auto_launch']}\n"
            f"update_checks_enabled: {self.settings['enable_update_checks']}\n"
            f"update_channel: {self.settings.get('update_channel', UPDATE_CHANNEL)}\n"
            f"runtime_degraded: {self.runtime_health.get('is_degraded')}\n"
            f"missing_runtime_tools: {', '.join(self.runtime_health.get('missing_tools', [])) or 'none'}\n"
            f"app_version: {APP_VERSION}\n"
            f"alert_history_entries: {len(self.alert_history)}\n"
            f"last_alert: {last_alert}\n"
            f"config_file: {self.config_file}\n"
            f"log_file: {self.log_file}\n"
            f"runtime_log_file: {self.runtime_log_file}\n"
            f"\nusage_summary:\n{self.build_usage_summary()}"
        )

    def cleanup_old_support_artifacts(self, keep_bundles=10, keep_crash_reports=10):
        """Remove older support bundles and crash reports to keep support storage tidy."""
        bundles = sorted(self.config_dir.glob("support_bundle_*.zip"))
        for old_bundle in bundles[:-keep_bundles]:
            old_bundle.unlink(missing_ok=True)

        crash_reports_dir = getattr(self, "crash_reports_dir", self.config_dir / "crash_reports")
        reports = sorted(crash_reports_dir.glob("crash_report_*.json")) if crash_reports_dir.exists() else []
        for old_report in reports[:-keep_crash_reports]:
            old_report.unlink(missing_ok=True)

    def create_support_bundle_archive(self, preset="full"):
        """Create a zip bundle with config, history, diagnostics, and logs."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        preset_suffix = "diag" if preset == "diagnostics" else "full"
        bundle_path = self.config_dir / f"support_bundle_{preset_suffix}_{timestamp}.zip"
        diagnostics_text = self.build_diagnostics_report()
        redacted_diagnostics = self.redact_text_for_support_share(diagnostics_text)
        latest_crash_report = self.get_latest_crash_report_path()

        manifest = {
            "support_bundle_schema_version": SUPPORT_BUNDLE_SCHEMA_VERSION,
            "app_version": APP_VERSION,
            "created_at": datetime.now().isoformat(),
            "config_schema_version": self.settings.get("config_schema_version", CONFIG_SCHEMA_VERSION),
            "app_state_schema_version": self.app_state.get("app_state_schema_version", APP_STATE_SCHEMA_VERSION),
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
            rotated_logs = sorted(self.runtime_log_file.parent.glob("battery_alert.log.*"))
            for rotated_log in rotated_logs:
                manifest["included_files"].append(f"logs/{rotated_log.name}")

        safe_share_guide = (
            "Support Bundle Safe-Share Guide\n"
            "- Review diagnostics.txt before sharing externally.\n"
            "- Redacted diagnostics replace your home directory with '~'.\n"
            "- Crash reports are included when available and may mention code paths or thread names.\n"
            "- Remove files you do not want to share before sending.\n"
        )

        with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("diagnostics.txt", redacted_diagnostics)
            zf.writestr("safe_share_guide.txt", safe_share_guide)
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            if preset != "diagnostics":
                if self.config_file.exists():
                    zf.write(self.config_file, arcname="config.json")
                if self.log_file.exists():
                    zf.write(self.log_file, arcname="alert_history.json")
                if self.runtime_log_file.exists():
                    zf.write(self.runtime_log_file, arcname="logs/battery_alert.log")

            if latest_crash_report is not None and latest_crash_report.exists():
                zf.writestr(
                    "crash_reports/latest_crash_report.json",
                    self.redact_text_for_support_share(latest_crash_report.read_text(encoding="utf-8")),
                )

            if preset != "diagnostics":
                for rotated_log in self.runtime_log_file.parent.glob("battery_alert.log.*"):
                    zf.write(rotated_log, arcname=f"logs/{rotated_log.name}")

        self.cleanup_old_support_artifacts()

        return bundle_path

    def update_boolean_setting(self, key, sender, label, enabled_text="ON", disabled_text="OFF"):
        """Toggle a boolean setting and update the menu label."""
        self.settings[key] = not self.settings[key]
        self.save_config()
        sender.title = f"{label}: {enabled_text if self.settings[key] else disabled_text}"

    def prompt_for_integer_setting(self, key, title, prompt, minimum, maximum, success_message):
        """Prompt the user to update a numeric setting."""
        current = self.settings[key]
        window = rumps.Window(
            f"Current value: {current}\n\n{prompt}",
            title=title,
            default_text=str(current),
            ok="OK",
            cancel="Cancel"
        )
        response = window.run()

        if response.clicked is False:
            return False

        if not response.text:
            return False

        try:
            value = int(response.text)
        except ValueError:
            rumps.alert("Please enter a valid number", title="Error")
            return False

        if not minimum <= value <= maximum:
            rumps.alert(
                f"Please enter a number between {minimum}-{maximum}",
                title="Error"
            )
            return False

        self.settings[key] = value
        self.save_config()
        rumps.alert(success_message.format(value=value), title="Success")
        return True
    
    def set_threshold(self, _):
        """Set battery threshold using rumps dialog"""
        try:
            self.prompt_for_integer_setting(
                "battery_threshold",
                "Battery Threshold",
                "Enter new threshold (1-100):",
                1,
                100,
                "Battery threshold set to {value}%"
            )
        except Exception as e:
            print(f"[ERROR] Error in set_threshold: {e}")
            rumps.alert(f"Error: {e}", title="Error")
    
    def set_interval(self, _):
        """Set check interval using rumps dialog"""
        try:
            self.prompt_for_integer_setting(
                "check_interval",
                "Check Interval",
                "Enter new interval (10-3600 seconds):",
                10,
                3600,
                "Check interval set to {value} seconds"
            )
        except Exception as e:
            print(f"[ERROR] Error in set_interval: {e}")
            rumps.alert(f"Error: {e}", title="Error")

    def set_cooldown(self, _):
        """Set alert cooldown using rumps dialog."""
        try:
            self.prompt_for_integer_setting(
                "alert_cooldown_seconds",
                "Alert Cooldown",
                "Enter alert cooldown (30-86400 seconds):",
                30,
                86400,
                "Alert cooldown set to {value} seconds"
            )
        except Exception as e:
            print(f"[ERROR] Error in set_cooldown: {e}")
            rumps.alert(f"Error: {e}", title="Error")
    
    def toggle_sound(self, sender):
        """Toggle sound alerts"""
        try:
            self.update_boolean_setting("enable_sound", sender, "🔊 Sound Alerts")
            print(f"[SETTINGS] Sound alerts: {'ON' if self.settings['enable_sound'] else 'OFF'}")
        except Exception as e:
            print(f"[ERROR] Error toggling sound: {e}")
    
    def toggle_voice(self, sender):
        """Toggle voice alerts"""
        try:
            self.update_boolean_setting("enable_voice", sender, "🎤 Voice Alerts")
            print(f"[SETTINGS] Voice alerts: {'ON' if self.settings['enable_voice'] else 'OFF'}")
        except Exception as e:
            print(f"[ERROR] Error toggling voice: {e}")
    
    def toggle_notifications(self, sender):
        """Toggle notifications"""
        try:
            self.update_boolean_setting("enable_notifications", sender, "🔔 Notifications")
            print(f"[SETTINGS] Notifications: {'ON' if self.settings['enable_notifications'] else 'OFF'}")
        except Exception as e:
            print(f"[ERROR] Error toggling notifications: {e}")
    
    def toggle_autolaunch(self, sender):
        """Toggle launch at startup"""
        try:
            self.update_boolean_setting("auto_launch", sender, "🚀 Launch at Startup")
            self.setup_autolaunch()
            status = "enabled" if self.settings["auto_launch"] else "disabled"
            print(f"[SETTINGS] Auto-launch: {status}")
            rumps.alert(f"Launch at Startup {status.capitalize()}", title="Success")
        except Exception as e:
            print(f"[ERROR] Error toggling auto-launch: {e}")
            rumps.alert(f"Error: {e}", title="Error")

    def toggle_update_checks(self, sender):
        """Toggle automatic update checks."""
        try:
            self.update_boolean_setting("enable_update_checks", sender, "🆕 Update Checks")
            status = "enabled" if self.settings["enable_update_checks"] else "disabled"
            self.log_runtime(f"Automatic update checks {status}")
        except Exception as e:
            print(f"[ERROR] Error toggling update checks: {e}")
            rumps.alert(f"Error: {e}", title="Error")

    def toggle_update_channel(self, sender):
        """Toggle update channel between stable and beta releases."""
        try:
            current = self.settings.get("update_channel", UPDATE_CHANNEL)
            self.settings["update_channel"] = "beta" if current == "stable" else "stable"
            self.save_config()
            sender.title = f"🧭 Update Channel: {self.settings['update_channel'].upper()}"
            self.show_maintenance_status(f"Update channel set to {self.settings['update_channel']}.")
        except Exception as e:
            print(f"[ERROR] Error toggling update channel: {e}")
            rumps.alert(f"Error: {e}", title="Error")

    def record_update_check_result(self, status, latest_version=None, latest_url=None, checked_at=None):
        """Persist update-check metadata for visibility and support diagnostics."""
        if not hasattr(self, "app_state") or not isinstance(self.app_state, dict):
            self.app_state = self.default_app_state_payload()

        if checked_at is not None:
            self.app_state["last_update_check_at"] = checked_at.isoformat()
        self.app_state["last_update_status"] = status
        if latest_version:
            self.app_state["last_known_release_version"] = latest_version
        if latest_url:
            self.app_state["last_known_release_url"] = latest_url
        self.save_app_state()

    def _version_tuple(self, version):
        """Normalize semantic-ish version strings for comparison."""
        cleaned = version.lower().strip().lstrip("v")
        cleaned = cleaned.split("-")[0]
        parts = []
        for token in cleaned.split("."):
            try:
                parts.append(int(token))
            except ValueError:
                parts.append(0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])

    def is_newer_version(self, latest_version, current_version):
        """Return True when latest_version is greater than current_version."""
        return self._version_tuple(latest_version) > self._version_tuple(current_version)

    def get_latest_release(self):
        """Fetch latest release details according to selected update channel."""
        update_channel = self.settings.get("update_channel", UPDATE_CHANNEL)
        api_url = LATEST_STABLE_RELEASE_API if update_channel == "stable" else RELEASES_API
        request = urllib.request.Request(
            api_url,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "battery-alert-monitor"}
        )
        with urllib.request.urlopen(request, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if update_channel == "stable":
            release_payload = payload
        else:
            release_payload = {}
            if isinstance(payload, list):
                for candidate in payload:
                    if isinstance(candidate, dict) and candidate.get("prerelease"):
                        release_payload = candidate
                        break
                if not release_payload:
                    for candidate in payload:
                        if isinstance(candidate, dict):
                            release_payload = candidate
                            break

        return {
            "version": str(release_payload.get("tag_name", "")).lstrip("v"),
            "url": str(release_payload.get("html_url", "")) or RELEASES_PAGE_URL,
        }

    def _read_last_update_check(self):
        """Read last update-check timestamp from disk."""
        if not hasattr(self, "update_state") or not isinstance(self.update_state, dict):
            self.update_state = self.default_update_state_payload()

        timestamp = self.update_state.get("last_checked")
        if not timestamp:
            return None

        try:
            return datetime.fromisoformat(timestamp)
        except Exception:
            self.update_state = self.default_update_state_payload()
            self.save_update_state()
            return None

    def _write_last_update_check(self, timestamp):
        """Persist last update-check timestamp."""
        if not hasattr(self, "update_state") or not isinstance(self.update_state, dict):
            self.update_state = self.default_update_state_payload()

        self.update_state["last_checked"] = timestamp.isoformat()
        self.save_update_state()

    def should_check_for_updates(self, now=None, minimum_hours=24):
        """Throttle automatic update checks to avoid network chatter."""
        now = now or datetime.now()
        previous = self._read_last_update_check()
        if previous is None:
            return True
        return (now - previous).total_seconds() >= minimum_hours * 3600

    def check_for_updates(self, manual=False):
        """Check whether a newer release is available on GitHub."""
        if not manual and not self.settings.get("enable_update_checks", True):
            return {"status": "disabled", "message": "Automatic update checks are disabled."}

        if not manual and not self.should_check_for_updates():
            return {"status": "throttled", "message": "Automatic update check throttled."}

        checked_at = datetime.now()
        try:
            latest_release = self.get_latest_release()
            latest = latest_release.get("version", "")
            latest_url = latest_release.get("url", RELEASES_PAGE_URL)
            self._write_last_update_check(checked_at)

            if not latest:
                self.record_update_check_result("unknown", checked_at=checked_at)
                return {
                    "status": "unknown",
                    "message": "Could not determine the latest release version right now. Please try again shortly."
                }

            if self.is_newer_version(latest, APP_VERSION):
                message = f"Version {latest} is available. You are on {APP_VERSION}."
                self.record_update_check_result(
                    "update_available",
                    latest_version=latest,
                    latest_url=latest_url,
                    checked_at=checked_at,
                )
                self.log_runtime(message)
                return {"status": "update_available", "message": message}

            self.record_update_check_result(
                "up_to_date",
                latest_version=latest,
                latest_url=latest_url,
                checked_at=checked_at,
            )

            return {
                "status": "up_to_date",
                "message": f"You are up to date on version {APP_VERSION}."
            }
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            self.record_update_check_result("failed", checked_at=checked_at)
            self.log_runtime(f"Update check failed: {e}", level="warning")
            return {
                "status": "failed",
                "message": "Unable to check updates right now. Please try again later."
            }
        except Exception as e:
            self.record_update_check_result("failed", checked_at=checked_at)
            self.log_runtime(f"Unexpected update check error: {e}", level="warning")
            return {
                "status": "failed",
                "message": "Unable to check updates right now. Please try again later."
            }

    def _run_manual_update_check(self):
        """Run update check in background and send non-blocking completion feedback."""
        try:
            result = self.check_for_updates(manual=True)
            status = result.get("status", "failed")
            message = result.get("message", "Unable to check updates right now. Please try again later.")

            if status == "update_available":
                self.show_maintenance_status(f"Update check complete: {message}")
            elif status == "up_to_date":
                self.show_maintenance_status("Update check complete: no updates found.")
            elif status == "unknown":
                self.show_maintenance_status(f"Update check complete: {message}")
            else:
                self.show_maintenance_status(f"Update check failed: {message}")
        finally:
            self._update_check_in_progress = False

    def check_for_updates_now(self, _):
        """Manual update check entrypoint for menu action."""
        if self._update_check_in_progress:
            self.show_maintenance_status("Update check already in progress.")
            return

        self._update_check_in_progress = True
        self.show_maintenance_status("Update check started.")
        threading.Thread(target=self._run_manual_update_check, daemon=True).start()

    def show_version_and_updates(self, _=None):
        """Show the current version and tracked update state."""
        try:
            rumps.alert("Version & Updates", self.build_release_visibility_summary())
        except Exception as e:
            print(f"[ERROR] Error in show_version_and_updates: {e}")

    def open_releases_page(self, _=None):
        """Open the GitHub releases page for self-service downloads and notes."""
        try:
            subprocess.run(["open", RELEASES_PAGE_URL], check=False)
            self.show_maintenance_status("Opened releases page.")
        except Exception as e:
            print(f"[ERROR] Error opening releases page: {e}")
            rumps.alert(f"Error: {e}", title="Error")

    def download_latest_release(self, _=None):
        """Open the best known release URL for quick update handoff."""
        try:
            release_url = self.app_state.get("last_known_release_url") or RELEASES_PAGE_URL
            subprocess.run(["open", release_url], check=False)
            self.show_maintenance_status("Opened latest release download page.")
        except Exception as e:
            print(f"[ERROR] Error downloading latest release: {e}")
            rumps.alert(f"Error: {e}", title="Error")
    
    def setup_autolaunch(self):
        """Setup or remove autolaunch using LaunchAgent"""
        launch_agent_dir = Path.home() / "Library/LaunchAgents"
        plist_file = launch_agent_dir / "com.batteryalert.app.plist"
        
        try:
            launch_agent_dir.mkdir(exist_ok=True)
            
            if self.settings["auto_launch"]:
                # Use a minimal plist configuration that launches the app properly
                # The key is to use the app bundle ID and let macOS resolve the app
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
                
                with open(plist_file, 'w') as f:
                    f.write(plist_content)
                
                # Unload if already loaded, then load
                subprocess.run(['launchctl', 'unload', str(plist_file)], 
                             capture_output=True)
                subprocess.run(['launchctl', 'load', str(plist_file)], 
                             capture_output=True)
                print(f"[AUTOLAUNCH] Enabled - LaunchAgent plist: {plist_file}")
                print("[TIP] To see it with app name in login items, add Battery Alert.app to System Settings > General > Login Items")
            else:
                # Remove autolaunch
                if plist_file.exists():
                    subprocess.run(['launchctl', 'unload', str(plist_file)], 
                                 capture_output=True)
                    plist_file.unlink()
                    print("[AUTOLAUNCH] Disabled - LaunchAgent removed")
        except Exception as e:
            print(f"[ERROR] Failed to setup autolaunch: {e}")
    
    def check_status(self, _):
        """Check and display current battery status"""
        try:
            battery_info = self.get_battery_info()
            rumps.alert("System Status", self.build_status_summary(battery_info))
        except Exception as e:
            print(f"[ERROR] Error in check_status: {e}")

    def test_alert(self, _):
        """Trigger a manual test alert using the current battery level."""
        try:
            battery_level = self.get_battery_info()["level"]
            self.trigger_alert(battery_level)
            rumps.alert(
                "Test alert sent using your current battery status.",
                title="Test Alert"
            )
        except Exception as e:
            print(f"[ERROR] Error in test_alert: {e}")
            rumps.alert(f"Error: {e}", title="Error")
    
    def view_alert_history(self, _):
        """View alert history"""
        try:
            if self.alert_history:
                history_text = "Recent Alerts:\n\n"
                for alert in reversed(self.alert_history[-20:]):
                    history_text += f"{alert['time']} - {alert['battery_level']}%\n"
            else:
                history_text = "No alerts recorded yet. Your battery is healthy! ✅"
            
            rumps.alert("Alert History", history_text)
        except Exception as e:
            print(f"[ERROR] Error in view_alert_history: {e}")

    def copy_diagnostics(self, _):
        """Copy diagnostics information to the clipboard."""
        try:
            diagnostics = self.build_diagnostics_report()
            subprocess.run(["pbcopy"], input=diagnostics, text=True, check=True)
            rumps.alert(
                "Diagnostics copied to the clipboard.",
                title="Diagnostics"
            )
        except Exception as e:
            print(f"[ERROR] Error in copy_diagnostics: {e}")
            rumps.alert(f"Error: {e}", title="Error")

    def export_support_bundle(self, _):
        """Generate a support zip bundle for troubleshooting."""
        try:
            bundle_path = self.create_support_bundle_archive(preset="full")
            self.record_app_state_event("support_bundle_exports")
            self.record_app_state_event("last_support_bundle_export_at", datetime.now().isoformat())
            self.log_runtime(f"Support bundle exported to {bundle_path}")
            subprocess.run(["open", "-R", str(bundle_path)], check=False)
            self.show_maintenance_status("Support bundle export complete.")
            self.show_feedback(
                "Support Bundle Exported",
                f"Support bundle created at:\n{bundle_path}\n\n"
                "Tip: Review safe_share_guide.txt in the bundle before sharing."
            )
        except Exception as e:
            self.log_runtime(f"Failed to export support bundle: {e}", level="warning")
            self.show_feedback("Error", f"Failed to export support bundle: {e}")

    def export_diagnostics_bundle(self, _):
        """Generate a diagnostics-only support bundle for lightweight triage."""
        try:
            bundle_path = self.create_support_bundle_archive(preset="diagnostics")
            self.record_app_state_event("support_bundle_exports")
            self.record_app_state_event("last_support_bundle_export_at", datetime.now().isoformat())
            self.log_runtime(f"Diagnostics-only bundle exported to {bundle_path}")
            subprocess.run(["open", "-R", str(bundle_path)], check=False)
            self.show_maintenance_status("Diagnostics-only bundle export complete.")
        except Exception as e:
            self.log_runtime(f"Failed to export diagnostics-only bundle: {e}", level="warning")
            self.show_feedback("Error", f"Failed to export diagnostics-only bundle: {e}")

    def build_release_validation_command(self):
        """Build the command used to run the release smoke test."""
        smoke_test_script = Path(__file__).resolve().parent / "scripts" / "release_smoke_test.py"
        return [sys.executable, str(smoke_test_script)]

    def _run_release_validation(self):
        """Run the release smoke test and report the outcome."""
        try:
            command = self.build_release_validation_command()
            result = subprocess.run(command, capture_output=True, text=True)
            self.record_app_state_event("release_checks_run")
            self.app_state["last_release_validation_at"] = datetime.now().isoformat()
            self.save_app_state()

            if result.returncode == 0:
                self.show_maintenance_status("Release check complete: passed.")
                self.log_runtime("Release smoke test completed successfully")
            else:
                message = (result.stderr or result.stdout or "Release smoke test failed.").strip()
                self.show_maintenance_status(f"Release check failed: {message[:160]}")
                self.log_runtime(f"Release smoke test failed: {message}", level="warning")
        except Exception as e:
            self.log_runtime(f"Release validation error: {e}", level="warning")
            self.show_maintenance_status("Release check failed: unable to run smoke test.")
        finally:
            self._release_validation_in_progress = False

    def run_release_validation_now(self, _):
        """Run the release smoke test in the background."""
        if self._release_validation_in_progress:
            self.show_maintenance_status("Release check already in progress.")
            return

        self._release_validation_in_progress = True
        self.show_maintenance_status("Release check started.")
        threading.Thread(target=self._run_release_validation, daemon=True).start()

    def open_config_folder(self, _):
        """Open the configuration directory in Finder."""
        try:
            subprocess.run(["open", str(self.config_dir)], check=True)
        except Exception as e:
            print(f"[ERROR] Error in open_config_folder: {e}")
            rumps.alert(f"Error: {e}", title="Error")
    
    def show_about(self, _):
        """Show about dialog"""
        try:
            about_text = f"""Battery Alert Monitor v{APP_VERSION}

A professional battery monitoring tool for macOS.

Keep your device powered and healthy! 🔋

© 2024"""
            rumps.alert("About Battery Alert", about_text)
        except Exception as e:
            print(f"[ERROR] Error in show_about: {e}")
    
    def quit_app(self, _):
        """Quit the application"""
        try:
            self.log_runtime("Application shutdown requested")
            self.monitoring = False
            self.stop_event.set()

            if hasattr(self, "monitor_thread") and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=2)
            if hasattr(self, "icon_update_thread") and self.icon_update_thread.is_alive():
                self.icon_update_thread.join(timeout=2)

            self.pid_file.unlink(missing_ok=True)
            rumps.quit_application()
        except Exception as e:
            print(f"[ERROR] Error quitting: {e}")
            rumps.quit_application()


def main():
    """Main entry point"""
    try:
        app = BatteryAlertApp()
        app.run()
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
