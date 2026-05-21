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
        gui_module = sys.modules.get("battery_alert_gui")
        rumps = getattr(gui_module, "rumps", None)
        if rumps is None:
            import rumps as imported_rumps

            rumps = imported_rumps

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

    def toggle_update_channel(self, sender) -> None:
        current = self.app.settings.get("update_channel", UPDATE_CHANNEL)
        self.app.settings["update_channel"] = "beta" if current == "stable" else "stable"
        self.app.save_config()
        sender.title = f"🧭 Update Channel: {self.app.settings['update_channel'].upper()}"
        self.app.show_maintenance_status(f"Update channel set to {self.app.settings['update_channel']}.")
