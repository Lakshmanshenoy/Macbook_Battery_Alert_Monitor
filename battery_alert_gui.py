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
from datetime import datetime
from pathlib import Path
import rumps


APP_VERSION = "1.1.0"
LATEST_RELEASE_API = "https://api.github.com/repos/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/releases/latest"


class BatteryAlertApp(rumps.App):
    """Main application class with menu bar integration"""
    
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
        
        # Create config directory
        self.config_dir.mkdir(exist_ok=True)
        
        # Default settings
        self.settings = {
            "battery_threshold": 20,
            "check_interval": 10,
            "alert_cooldown_seconds": 900,
            "enable_sound": True,
            "enable_voice": True,
            "enable_notifications": True,
            "auto_launch": False,
            "enable_update_checks": True
        }

        self._below_threshold_prev = False
        self._last_alert_time = None
        self._last_power_state = None
        self._update_check_in_progress = False
        self.stop_event = threading.Event()
        
        # Alert history
        self.alert_history = []
        self.logger = None

        # Logging should start before other runtime operations.
        self.setup_runtime_logging()
        
        # Load configuration
        self.load_config()
        self.load_alert_history()

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

        # Non-blocking update check on startup.
        self.check_for_updates(manual=False)
    
    def load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.settings.update(loaded)
                self.validate_settings()
            except Exception as e:
                print(f"[ERROR] Failed to load config: {e}")
        else:
            self.save_config()

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
            except Exception as e:
                print(f"[ERROR] Failed to load history: {e}")
    
    def save_alert_history(self):
        """Save alert history to file"""
        try:
            self._write_json_atomic(self.log_file, self.alert_history[-100:])  # Keep up to 100 alerts
        except Exception as e:
            print(f"[ERROR] Failed to save history: {e}")

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
                print(f"[ICON] Charging detected - using 🔌")
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
            None,
            rumps.MenuItem("🚀 Launch at Startup: " + ("ON" if self.settings["auto_launch"] else "OFF"), 
                          self.toggle_autolaunch),
            None,
            rumps.MenuItem("Check Status", self.check_status),
            rumps.MenuItem("Check for Updates", self.check_for_updates_now),
            rumps.MenuItem("Test Alert Now", self.test_alert),
            rumps.MenuItem("View Alert History", self.view_alert_history),
            rumps.MenuItem("Copy Diagnostics", self.copy_diagnostics),
            rumps.MenuItem("Export Support Bundle", self.export_support_bundle),
            rumps.MenuItem("Open Config Folder", self.open_config_folder),
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

        return (
            f"Battery threshold: {self.settings['battery_threshold']}%\n"
            f"Check interval: {self.settings['check_interval']} seconds\n"
            f"Alert cooldown: {self.settings['alert_cooldown_seconds']} seconds\n"
            f"Alert modes: {modes_text}\n"
            f"Launch at startup: {autolaunch_text}\n"
            f"Update checks: {updates_text}"
        )

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
            f"app_version: {APP_VERSION}\n"
            f"alert_history_entries: {len(self.alert_history)}\n"
            f"last_alert: {last_alert}\n"
            f"config_file: {self.config_file}\n"
            f"log_file: {self.log_file}\n"
            f"runtime_log_file: {self.runtime_log_file}"
        )

    def create_support_bundle_archive(self):
        """Create a zip bundle with config, history, diagnostics, and logs."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        bundle_path = self.config_dir / f"support_bundle_{timestamp}.zip"
        diagnostics_text = self.build_diagnostics_report()

        with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("diagnostics.txt", diagnostics_text)

            if self.config_file.exists():
                zf.write(self.config_file, arcname="config.json")
            if self.log_file.exists():
                zf.write(self.log_file, arcname="alert_history.json")
            if self.runtime_log_file.exists():
                zf.write(self.runtime_log_file, arcname="logs/battery_alert.log")

            for rotated_log in self.runtime_log_file.parent.glob("battery_alert.log.*"):
                zf.write(rotated_log, arcname=f"logs/{rotated_log.name}")

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

    def get_latest_release_version(self):
        """Fetch latest release tag from GitHub releases API."""
        request = urllib.request.Request(
            LATEST_RELEASE_API,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "battery-alert-monitor"}
        )
        with urllib.request.urlopen(request, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return str(payload.get("tag_name", "")).lstrip("v")

    def _read_last_update_check(self):
        """Read last update-check timestamp from disk."""
        if not self.update_state_file.exists():
            return None
        try:
            with open(self.update_state_file) as f:
                payload = json.load(f)
            timestamp = payload.get("last_checked")
            if not timestamp:
                return None
            return datetime.fromisoformat(timestamp)
        except Exception:
            return None

    def _write_last_update_check(self, timestamp):
        """Persist last update-check timestamp."""
        self._write_json_atomic(self.update_state_file, {"last_checked": timestamp.isoformat()})

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

        try:
            latest = self.get_latest_release_version()
            self._write_last_update_check(datetime.now())

            if not latest:
                return {
                    "status": "unknown",
                    "message": "Could not determine the latest release version right now. Please try again shortly."
                }

            if self.is_newer_version(latest, APP_VERSION):
                message = f"Version {latest} is available. You are on {APP_VERSION}."
                self.log_runtime(message)
                return {"status": "update_available", "message": message}

            return {
                "status": "up_to_date",
                "message": f"You are up to date on version {APP_VERSION}."
            }
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            self.log_runtime(f"Update check failed: {e}", level="warning")
            return {
                "status": "failed",
                "message": "Unable to check updates right now. Please try again later."
            }
        except Exception as e:
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
                self.show_non_blocking_feedback("Update Available", message)
            elif status == "up_to_date":
                self.show_non_blocking_feedback("No Updates", message)
            elif status == "unknown":
                self.show_non_blocking_feedback("Update Check", message)
            else:
                self.show_non_blocking_feedback("Update Check Failed", message)
        finally:
            self._update_check_in_progress = False

    def check_for_updates_now(self, _):
        """Manual update check entrypoint for menu action."""
        if self._update_check_in_progress:
            self.show_non_blocking_feedback("Update Check", "An update check is already in progress.")
            return

        self._update_check_in_progress = True
        self.show_non_blocking_feedback("Update Check", "Checking for updates in the background...")
        threading.Thread(target=self._run_manual_update_check, daemon=True).start()
    
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
                print(f"[TIP] To see it with app name in login items, add Battery Alert.app to System Settings > General > Login Items")
            else:
                # Remove autolaunch
                if plist_file.exists():
                    subprocess.run(['launchctl', 'unload', str(plist_file)], 
                                 capture_output=True)
                    plist_file.unlink()
                    print(f"[AUTOLAUNCH] Disabled - LaunchAgent removed")
        except Exception as e:
            print(f"[ERROR] Failed to setup autolaunch: {e}")
    
    def check_status(self, _):
        """Check and display current battery status"""
        try:
            battery_info = self.get_battery_info()
            level = battery_info["level"]
            charging = "Charging 🔌" if battery_info["is_charging"] else "Discharging 🔋"
            
            message = f"""Battery Level: {level}%
Status: {charging}
Threshold: {self.settings['battery_threshold']}%
Check Interval: {self.settings['check_interval']} seconds
Alert Cooldown: {self.settings['alert_cooldown_seconds']} seconds"""
            
            rumps.alert("Battery Status", message)
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
            bundle_path = self.create_support_bundle_archive()
            self.log_runtime(f"Support bundle exported to {bundle_path}")
            subprocess.run(["open", "-R", str(bundle_path)], check=False)
            self.show_feedback("Support Bundle Exported", f"Support bundle created at:\n{bundle_path}")
        except Exception as e:
            self.log_runtime(f"Failed to export support bundle: {e}", level="warning")
            self.show_feedback("Error", f"Failed to export support bundle: {e}")

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
