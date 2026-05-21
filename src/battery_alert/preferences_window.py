# mypy: ignore-errors
from __future__ import annotations

import sys
from typing import Any, Dict, Optional

try:
    from AppKit import (  # type: ignore
        NSAlert,
        NSAlertFirstButtonReturn,
        NSButton,
        NSControlStateValueOff,
        NSControlStateValueOn,
        NSMakeRect,
        NSPopUpButton,
        NSSwitchButton,
        NSTextField,
        NSView,
    )

    APPKIT_AVAILABLE = True
except Exception:  # pragma: no cover - exercised indirectly via fallback tests
    APPKIT_AVAILABLE = False


class PreferencesWindowController:
    """Native AppKit preferences editor with safe fallback behavior."""

    def __init__(self, app: Any) -> None:
        self.app = app

    def is_available(self) -> bool:
        return APPKIT_AVAILABLE

    def present(self) -> bool:
        if not self.is_available():
            return False

        fields = self._build_controls()
        if fields is None:
            return False

        result = fields["alert"].runModal()
        if result != NSAlertFirstButtonReturn:
            return False

        payload = self._read_payload(fields)
        if payload is None:
            return False

        self.app.settings.update(payload)
        self.app.save_config()
        self.app.update_menu_labels()
        self.app.show_non_blocking_feedback("Preferences", "Updated successfully.")
        return True

    def _show_error(self, message: str) -> None:
        gui_module = sys.modules.get("battery_alert_gui")
        rumps = getattr(gui_module, "rumps", None)
        if rumps is not None and hasattr(rumps, "alert"):
            rumps.alert(message, title="Preferences")
            return
        self.app.log_runtime(message, level="warning")

    def _int_from_field(self, fields: Dict[str, Any], key: str, minimum: int, maximum: int, label: str) -> Optional[int]:
        raw = fields[key].stringValue().strip()
        try:
            value = int(raw)
        except ValueError:
            self._show_error(f"{label} must be a number between {minimum}-{maximum}.")
            return None

        if not minimum <= value <= maximum:
            self._show_error(f"{label} must be between {minimum}-{maximum}.")
            return None

        return value

    def _read_payload(self, fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        threshold = self._int_from_field(fields, "battery_threshold", 1, 100, "Battery threshold")
        if threshold is None:
            return None

        interval = self._int_from_field(fields, "check_interval", 10, 3600, "Check interval")
        if interval is None:
            return None

        cooldown = self._int_from_field(fields, "alert_cooldown_seconds", 30, 86400, "Alert cooldown")
        if cooldown is None:
            return None

        channel = fields["update_channel"].titleOfSelectedItem() or "stable"
        channel_value = channel.strip().lower()
        if channel_value not in {"stable", "beta"}:
            channel_value = "stable"

        return {
            "battery_threshold": threshold,
            "check_interval": interval,
            "alert_cooldown_seconds": cooldown,
            "enable_sound": fields["enable_sound"].state() == NSControlStateValueOn,
            "enable_voice": fields["enable_voice"].state() == NSControlStateValueOn,
            "enable_notifications": fields["enable_notifications"].state() == NSControlStateValueOn,
            "auto_launch": fields["auto_launch"].state() == NSControlStateValueOn,
            "enable_update_checks": fields["enable_update_checks"].state() == NSControlStateValueOn,
            "update_channel": channel_value,
        }

    def _build_controls(self) -> Optional[Dict[str, Any]]:
        try:
            alert = NSAlert.alloc().init()
            alert.setMessageText_("Preferences")
            alert.setInformativeText_("Configure Battery Alert Monitor settings.")
            alert.addButtonWithTitle_("Save")
            alert.addButtonWithTitle_("Cancel")

            container = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 420, 330))

            def add_label(text: str, y: float) -> Any:
                label = NSTextField.labelWithString_(text)
                label.setFrame_(NSMakeRect(20, y, 220, 22))
                container.addSubview_(label)
                return label

            def add_input(default: Any, y: float) -> Any:
                field = NSTextField.alloc().initWithFrame_(NSMakeRect(260, y, 120, 24))
                field.setStringValue_(str(default))
                container.addSubview_(field)
                return field

            def add_switch(label: str, checked: bool, y: float) -> Any:
                switch = NSButton.alloc().initWithFrame_(NSMakeRect(20, y, 360, 22))
                switch.setButtonType_(NSSwitchButton)
                switch.setTitle_(label)
                switch.setState_(NSControlStateValueOn if checked else NSControlStateValueOff)
                container.addSubview_(switch)
                return switch

            add_label("Battery threshold (%)", 290)
            battery_threshold = add_input(self.app.settings.get("battery_threshold", 20), 286)

            add_label("Check interval (seconds)", 256)
            check_interval = add_input(self.app.settings.get("check_interval", 10), 252)

            add_label("Alert cooldown (seconds)", 222)
            alert_cooldown_seconds = add_input(self.app.settings.get("alert_cooldown_seconds", 900), 218)

            enable_sound = add_switch("Enable sound alerts", bool(self.app.settings.get("enable_sound", True)), 184)
            enable_voice = add_switch("Enable voice alerts", bool(self.app.settings.get("enable_voice", True)), 158)
            enable_notifications = add_switch("Enable notifications", bool(self.app.settings.get("enable_notifications", True)), 132)
            auto_launch = add_switch("Launch at startup", bool(self.app.settings.get("auto_launch", False)), 106)
            enable_update_checks = add_switch(
                "Enable automatic update checks",
                bool(self.app.settings.get("enable_update_checks", True)),
                80,
            )

            add_label("Update channel", 44)
            update_channel = NSPopUpButton.alloc().initWithFrame_pullsDown_(NSMakeRect(260, 40, 120, 26), False)
            update_channel.addItemsWithTitles_(["stable", "beta"])
            selected_channel = str(self.app.settings.get("update_channel", "stable")).strip().lower()
            if selected_channel not in {"stable", "beta"}:
                selected_channel = "stable"
            update_channel.selectItemWithTitle_(selected_channel)
            container.addSubview_(update_channel)

            alert.setAccessoryView_(container)
            return {
                "alert": alert,
                "battery_threshold": battery_threshold,
                "check_interval": check_interval,
                "alert_cooldown_seconds": alert_cooldown_seconds,
                "enable_sound": enable_sound,
                "enable_voice": enable_voice,
                "enable_notifications": enable_notifications,
                "auto_launch": auto_launch,
                "enable_update_checks": enable_update_checks,
                "update_channel": update_channel,
            }
        except Exception as exc:
            self.app.log_runtime(f"Failed to open native preferences: {exc}", level="warning")
            return None
