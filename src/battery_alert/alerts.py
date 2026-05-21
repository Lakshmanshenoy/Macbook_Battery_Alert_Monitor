# mypy: ignore-errors
import os
import subprocess
import sys
from datetime import datetime
from typing import Dict, Optional, Union

from .constants import UPDATE_CHANNEL
from .legacy_app import BatteryAlertApp as LegacyBatteryAlertApp


class AlertManager:
    """Alert orchestration facade."""

    def __init__(self, app: "LegacyBatteryAlertApp") -> None:
        self.app = app

    def _rumps_module(self):
        gui_module = sys.modules.get("battery_alert_gui")
        rumps = getattr(gui_module, "rumps", None)
        if rumps is None:
            import rumps as imported_rumps

            rumps = imported_rumps
        return rumps

    def should_trigger_alert(
        self,
        battery_info: Dict[str, Union[int, bool]],
        now: Optional[datetime] = None,
    ) -> bool:
        now = now or datetime.now()

        if not battery_info["is_discharging"]:
            self.app._below_threshold_prev = False
            return False

        level = battery_info["level"]
        below_threshold = level <= self.app.settings["battery_threshold"]
        if not below_threshold:
            self.app._below_threshold_prev = False
            return False

        crossed_threshold = not self.app._below_threshold_prev
        cooldown_seconds = self.app.settings["alert_cooldown_seconds"]
        cooldown_elapsed = (
            self.app._last_alert_time is None
            or (now - self.app._last_alert_time).total_seconds() >= cooldown_seconds
        )

        self.app._below_threshold_prev = True
        return crossed_threshold or cooldown_elapsed

    def trigger_alert(self, battery_level: int, now: Optional[datetime] = None) -> None:
        now = now or datetime.now()
        self.app._last_alert_time = now
        alert_time = now.strftime("%Y-%m-%d %H:%M:%S")

        self.app.alert_history.append({
            "time": alert_time,
            "battery_level": battery_level,
        })
        self.app.save_alert_history()

        self.app.log_runtime(f"Alert triggered at {battery_level}% ({alert_time})", level="warning")

        if self.app.settings["enable_sound"]:
            try:
                sound_files = [
                    "/System/Library/Sounds/Alarm.aiff",
                    "/System/Library/Sounds/Glass.aiff",
                    "/System/Library/Sounds/Ping.aiff",
                ]
                for sound_file in sound_files:
                    if os.path.exists(sound_file):
                        subprocess.Popen(["afplay", sound_file])
                        self.app.log_runtime(f"Playing: {sound_file}")
                        break
            except Exception as exc:
                self.app.log_runtime(f"Sound alert failed: {exc}", level="error")

        if self.app.settings["enable_notifications"]:
            try:
                apple_script = (
                    f'display notification "Battery at {battery_level}%! Please charge your device." '
                    'with title "Low Battery Alert"'
                )
                result = subprocess.run(["osascript", "-e", apple_script], capture_output=True, text=True)
                if result.returncode != 0:
                    self.app.log_runtime(f"Notification failed: {result.stderr}", level="error")
                else:
                    self.app.log_runtime("Sent successfully")
            except Exception as exc:
                self.app.log_runtime(f"Notification alert failed: {exc}", level="error")

        if self.app.settings["enable_voice"]:
            try:
                subprocess.Popen(["say", f"Battery low at {battery_level} percent. Please charge your device."])
                self.app.log_runtime("Alert triggered")
            except Exception as exc:
                self.app.log_runtime(f"Voice alert failed: {exc}", level="error")

    def update_boolean_setting(self, key, sender, label, enabled_text: str = "ON", disabled_text: str = "OFF") -> None:
        self.app.settings[key] = not self.app.settings[key]
        self.app.save_config()
        sender.title = f"{label}: {enabled_text if self.app.settings[key] else disabled_text}"

    def prompt_for_integer_setting(
        self,
        key,
        title: str,
        prompt: str,
        minimum: int,
        maximum: int,
        success_message: str,
    ) -> bool:
        rumps = self._rumps_module()

        current = self.app.settings[key]
        window = rumps.Window(
            f"Current value: {current}\n\n{prompt}",
            title=title,
            default_text=str(current),
            ok="OK",
            cancel="Cancel",
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
            rumps.alert(f"Please enter a number between {minimum}-{maximum}", title="Error")
            return False

        self.app.settings[key] = value
        self.app.save_config()
        rumps.alert(success_message.format(value=value), title="Success")
        return True

    def format_settings_summary(self) -> str:
        """Return a human-readable summary of the active preferences."""
        alert_modes = []
        if self.app.settings["enable_sound"]:
            alert_modes.append("sound")
        if self.app.settings["enable_voice"]:
            alert_modes.append("voice")
        if self.app.settings["enable_notifications"]:
            alert_modes.append("notifications")

        modes_text = ", ".join(alert_modes) if alert_modes else "none"
        autolaunch_text = "enabled" if self.app.settings["auto_launch"] else "disabled"
        updates_text = "enabled" if self.app.settings["enable_update_checks"] else "disabled"
        update_channel = self.app.settings.get("update_channel", UPDATE_CHANNEL)

        return (
            f"Battery threshold: {self.app.settings['battery_threshold']}%\n"
            f"Check interval: {self.app.settings['check_interval']} seconds\n"
            f"Alert cooldown: {self.app.settings['alert_cooldown_seconds']} seconds\n"
            f"Alert modes: {modes_text}\n"
            f"Launch at startup: {autolaunch_text}\n"
            f"Update checks: {updates_text}\n"
            f"Update channel: {update_channel}"
        )

    def show_preferences(self, _) -> None:
        """Show a summary of current user preferences."""
        try:
            self._rumps_module().alert("Preferences", self.format_settings_summary())
        except Exception as exc:
            self.app.log_runtime(f"Error in show_preferences: {exc}", level="error")

    def update_menu_labels(self) -> None:
        """Update menu item labels to reflect current settings."""
        try:
            self.app.setup_menu()
        except Exception as exc:
            self.app.log_runtime(f"Failed to update menu: {exc}", level="error")

    def set_threshold(self, _) -> None:
        """Set battery threshold using a dialog."""
        try:
            self.prompt_for_integer_setting(
                "battery_threshold",
                "Battery Threshold",
                "Enter new threshold (1-100):",
                1,
                100,
                "Battery threshold set to {value}%",
            )
        except Exception as exc:
            self.app.log_runtime(f"Error in set_threshold: {exc}", level="error")
            self._rumps_module().alert(f"Error: {exc}", title="Error")

    def set_interval(self, _) -> None:
        """Set check interval using a dialog."""
        try:
            self.prompt_for_integer_setting(
                "check_interval",
                "Check Interval",
                "Enter new interval (10-3600 seconds):",
                10,
                3600,
                "Check interval set to {value} seconds",
            )
        except Exception as exc:
            self.app.log_runtime(f"Error in set_interval: {exc}", level="error")
            self._rumps_module().alert(f"Error: {exc}", title="Error")

    def set_cooldown(self, _) -> None:
        """Set alert cooldown using a dialog."""
        try:
            self.prompt_for_integer_setting(
                "alert_cooldown_seconds",
                "Alert Cooldown",
                "Enter alert cooldown (30-86400 seconds):",
                30,
                86400,
                "Alert cooldown set to {value} seconds",
            )
        except Exception as exc:
            self.app.log_runtime(f"Error in set_cooldown: {exc}", level="error")
            self._rumps_module().alert(f"Error: {exc}", title="Error")

    def toggle_sound(self, sender) -> None:
        try:
            self.update_boolean_setting("enable_sound", sender, "🔊 Sound Alerts")
            self.app.log_runtime(f"Sound alerts: {'ON' if self.app.settings['enable_sound'] else 'OFF'}")
        except Exception as exc:
            self.app.log_runtime(f"Error toggling sound: {exc}", level="error")

    def toggle_voice(self, sender) -> None:
        try:
            self.update_boolean_setting("enable_voice", sender, "🎤 Voice Alerts")
            self.app.log_runtime(f"Voice alerts: {'ON' if self.app.settings['enable_voice'] else 'OFF'}")
        except Exception as exc:
            self.app.log_runtime(f"Error toggling voice: {exc}", level="error")

    def toggle_notifications(self, sender) -> None:
        try:
            self.update_boolean_setting("enable_notifications", sender, "🔔 Notifications")
            self.app.log_runtime(f"Notifications: {'ON' if self.app.settings['enable_notifications'] else 'OFF'}")
        except Exception as exc:
            self.app.log_runtime(f"Error toggling notifications: {exc}", level="error")

    def toggle_autolaunch(self, sender) -> None:
        try:
            self.update_boolean_setting("auto_launch", sender, "🚀 Launch at Startup")
            self.app.setup_autolaunch()
            status = "enabled" if self.app.settings["auto_launch"] else "disabled"
            self.app.log_runtime(f"Auto-launch: {status}")
            self._rumps_module().alert(f"Launch at Startup {status.capitalize()}", title="Success")
        except Exception as exc:
            self.app.log_runtime(f"Error toggling auto-launch: {exc}", level="error")
            self._rumps_module().alert(f"Error: {exc}", title="Error")

    def toggle_update_checks(self, sender) -> None:
        try:
            self.update_boolean_setting("enable_update_checks", sender, "🆕 Update Checks")
            status = "enabled" if self.app.settings["enable_update_checks"] else "disabled"
            self.app.log_runtime(f"Automatic update checks {status}")
        except Exception as exc:
            self.app.log_runtime(f"Error toggling update checks: {exc}", level="error")
            self._rumps_module().alert(f"Error: {exc}", title="Error")

    def toggle_update_channel(self, sender) -> None:
        current = self.app.settings.get("update_channel", UPDATE_CHANNEL)
        self.app.settings["update_channel"] = "beta" if current == "stable" else "stable"
        self.app.save_config()
        sender.title = f"🧭 Update Channel: {self.app.settings['update_channel'].upper()}"
        self.app.show_maintenance_status(f"Update channel set to {self.app.settings['update_channel']}.")

    def update_menu_icon(self) -> None:
        """Update menu bar icon with battery status."""
        try:
            battery_info = self.app.get_battery_info()
            level = battery_info["level"]

            if battery_info["is_charging"]:
                icon = "🔌"
                self.app.log_runtime("Charging detected - using 🔌")
            elif level > 50:
                icon = "🔋"
            elif level > 20:
                icon = "🪫"
            else:
                icon = "⚠️"

            title = f"{icon} {level}%"
            old_title = self.app.title
            self.app.title = title

            if old_title != title:
                self.app.log_runtime(f"{old_title} → {title}")
        except Exception as exc:
            self.app.log_runtime(f"Failed to update menu icon: {exc}", level="error")

    def update_icon_loop(self) -> None:
        """Continuously update menu bar icon every 5 seconds."""
        while self.app.monitoring and not self.app.stop_event.is_set():
            try:
                self.app.update_menu_icon()
                self.app.stop_event.wait(5)
            except Exception as exc:
                self.app.log_runtime(f"Error in update_icon_loop: {exc}", level="error")
                self.app.stop_event.wait(5)

    def monitor_battery(self) -> None:
        """Monitor battery in background thread."""
        while self.app.monitoring and not self.app.stop_event.is_set():
            try:
                battery_info = self.app.get_battery_info()
                level = battery_info["level"]

                current_power_state = "charging" if battery_info["is_charging"] else "discharging"
                if self.app._last_power_state and self.app._last_power_state != current_power_state:
                    self.app._last_power_transition = (
                        f"{self.app._last_power_state} -> {current_power_state} at {level}% "
                        f"on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    self.app.log_runtime(
                        f"Power source changed: {self.app._last_power_state} -> {current_power_state} at {level}%"
                    )
                self.app._last_power_state = current_power_state

                now = datetime.now()
                if self.app.should_trigger_alert(battery_info, now=now):
                    self.app.trigger_alert(level, now=now)

                self.app.stop_event.wait(self.app.settings["check_interval"])
            except Exception as exc:
                self.app.log_runtime(f"Error in monitor_battery: {exc}", level="error")
                self.app.stop_event.wait(10)
