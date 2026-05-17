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
from datetime import datetime
from pathlib import Path
import rumps


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
            "auto_launch": False
        }

        self._below_threshold_prev = False
        self._last_alert_time = None
        self.stop_event = threading.Event()
        
        # Alert history
        self.alert_history = []
        
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
            rumps.MenuItem("Battery Threshold", self.set_threshold),
            rumps.MenuItem("Check Interval", self.set_interval),
            None,
            rumps.MenuItem("🔊 Sound Alerts: " + ("ON" if self.settings["enable_sound"] else "OFF"), 
                          self.toggle_sound),
            rumps.MenuItem("🎤 Voice Alerts: " + ("ON" if self.settings["enable_voice"] else "OFF"), 
                          self.toggle_voice),
            rumps.MenuItem("🔔 Notifications: " + ("ON" if self.settings["enable_notifications"] else "OFF"), 
                          self.toggle_notifications),
            None,
            rumps.MenuItem("🚀 Launch at Startup: " + ("ON" if self.settings["auto_launch"] else "OFF"), 
                          self.toggle_autolaunch),
            None,
            rumps.MenuItem("Check Status", self.check_status),
            rumps.MenuItem("View Alert History", self.view_alert_history),
            None,
            rumps.MenuItem("About", self.show_about),
            rumps.MenuItem("Quit", self.quit_app)
        ]
    
    def update_menu_labels(self):
        """Update menu item labels to reflect current settings"""
        try:
            # Rebuild menu with updated labels
            self.setup_menu()
        except Exception as e:
            print(f"[ERROR] Failed to update menu: {e}")
    
    def set_threshold(self, _):
        """Set battery threshold using rumps dialog"""
        try:
            current = self.settings["battery_threshold"]
            
            # Use simpledialog-like behavior with rumps
            window = rumps.Window(
                f"Current threshold: {current}%\n\nEnter new threshold (1-100):",
                title="Battery Threshold",
                default_text=str(current),
                ok="OK",
                cancel="Cancel"
            )
            response = window.run()
            
            # Check if Cancel was clicked
            if response.clicked == False:
                return
            
            if response.text:
                try:
                    threshold = int(response.text)
                    if 1 <= threshold <= 100:
                        self.settings["battery_threshold"] = threshold
                        self.save_config()
                        rumps.alert(
                            f"Battery threshold set to {threshold}%",
                            title="Success"
                        )
                    else:
                        rumps.alert(
                            "Please enter a number between 1-100",
                            title="Error"
                        )
                except ValueError:
                    rumps.alert(
                        "Please enter a valid number",
                        title="Error"
                    )
        except Exception as e:
            print(f"[ERROR] Error in set_threshold: {e}")
            rumps.alert(f"Error: {e}", title="Error")
    
    def set_interval(self, _):
        """Set check interval using rumps dialog"""
        try:
            current = self.settings["check_interval"]
            
            # Use simpledialog-like behavior with rumps
            window = rumps.Window(
                f"Current interval: {current}s\n\nEnter new interval (10-3600 seconds):",
                title="Check Interval",
                default_text=str(current),
                ok="OK",
                cancel="Cancel"
            )
            response = window.run()
            
            # Check if Cancel was clicked
            if response.clicked == False:
                return
            
            if response.text:
                try:
                    interval = int(response.text)
                    if 10 <= interval <= 3600:
                        self.settings["check_interval"] = interval
                        self.save_config()
                        rumps.alert(
                            f"Check interval set to {interval} seconds",
                            title="Success"
                        )
                    else:
                        rumps.alert(
                            "Please enter a number between 10-3600",
                            title="Error"
                        )
                except ValueError:
                    rumps.alert(
                        "Please enter a valid number",
                        title="Error"
                    )
        except Exception as e:
            print(f"[ERROR] Error in set_interval: {e}")
            rumps.alert(f"Error: {e}", title="Error")
    
    def toggle_sound(self, sender):
        """Toggle sound alerts"""
        try:
            self.settings["enable_sound"] = not self.settings["enable_sound"]
            self.save_config()
            sender.title = "🔊 Sound Alerts: " + ("ON" if self.settings["enable_sound"] else "OFF")
            print(f"[SETTINGS] Sound alerts: {'ON' if self.settings['enable_sound'] else 'OFF'}")
        except Exception as e:
            print(f"[ERROR] Error toggling sound: {e}")
    
    def toggle_voice(self, sender):
        """Toggle voice alerts"""
        try:
            self.settings["enable_voice"] = not self.settings["enable_voice"]
            self.save_config()
            sender.title = "🎤 Voice Alerts: " + ("ON" if self.settings["enable_voice"] else "OFF")
            print(f"[SETTINGS] Voice alerts: {'ON' if self.settings['enable_voice'] else 'OFF'}")
        except Exception as e:
            print(f"[ERROR] Error toggling voice: {e}")
    
    def toggle_notifications(self, sender):
        """Toggle notifications"""
        try:
            self.settings["enable_notifications"] = not self.settings["enable_notifications"]
            self.save_config()
            sender.title = "🔔 Notifications: " + ("ON" if self.settings["enable_notifications"] else "OFF")
            print(f"[SETTINGS] Notifications: {'ON' if self.settings['enable_notifications'] else 'OFF'}")
        except Exception as e:
            print(f"[ERROR] Error toggling notifications: {e}")
    
    def toggle_autolaunch(self, sender):
        """Toggle launch at startup"""
        try:
            self.settings["auto_launch"] = not self.settings["auto_launch"]
            self.save_config()
            self.setup_autolaunch()
            sender.title = "🚀 Launch at Startup: " + ("ON" if self.settings["auto_launch"] else "OFF")
            status = "enabled" if self.settings["auto_launch"] else "disabled"
            print(f"[SETTINGS] Auto-launch: {status}")
            rumps.alert(f"Launch at Startup {status.capitalize()}", title="Success")
        except Exception as e:
            print(f"[ERROR] Error toggling auto-launch: {e}")
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
Threshold: {self.settings['battery_threshold']}%"""
            
            rumps.alert("Battery Status", message)
        except Exception as e:
            print(f"[ERROR] Error in check_status: {e}")
    
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
    
    def show_about(self, _):
        """Show about dialog"""
        try:
            about_text = """Battery Alert Monitor v1.0

A professional battery monitoring tool for macOS.

Keep your device powered and healthy! 🔋

© 2024"""
            rumps.alert("About Battery Alert", about_text)
        except Exception as e:
            print(f"[ERROR] Error in show_about: {e}")
    
    def quit_app(self, _):
        """Quit the application"""
        try:
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
