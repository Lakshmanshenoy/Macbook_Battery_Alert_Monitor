# mypy: ignore-errors
from __future__ import annotations

import sys
from typing import Any, Dict, Optional

try:
    import objc  # type: ignore
    from AppKit import (  # type: ignore
        NSApp,
        NSButton,
        NSControlStateValueOff,
        NSControlStateValueOn,
        NSFont,
        NSMakeRect,
        NSPanel,
        NSPopUpButton,
        NSSwitch,
        NSTextField,
        NSView,
        NSVisualEffectBlendingModeBehindWindow,
        NSVisualEffectMaterialSidebar,
        NSVisualEffectStateActive,
        NSVisualEffectView,
        NSWindowStyleMaskClosable,
        NSWindowStyleMaskTitled,
        NSWindowStyleMaskUtilityWindow,
    )
    from Foundation import NSObject  # type: ignore

    APPKIT_AVAILABLE = True
except Exception:  # pragma: no cover - exercised indirectly via fallback tests
    APPKIT_AVAILABLE = False


if APPKIT_AVAILABLE:

    class _PanelActionBridge(NSObject):
        def initWithController_(self, controller: "PreferencesWindowController") -> "_PanelActionBridge":
            self = objc.super(_PanelActionBridge, self).init()
            if self is None:
                return None
            self.controller = controller
            return self

        @objc.typedSelector(b"v@:@")
        def save_(self, _sender: Any) -> None:
            self.controller._save_and_close()

        @objc.typedSelector(b"v@:@")
        def cancel_(self, _sender: Any) -> None:
            self.controller._close_panel()


class PreferencesWindowController:
    """Native AppKit preferences editor with safe fallback behavior."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self._panel = None
        self._controls: Dict[str, Any] = {}
        self._action_bridge = None

    def is_available(self) -> bool:
        return APPKIT_AVAILABLE

    def present(self) -> bool:
        if not self.is_available():
            return False

        if self._panel is None:
            self._panel = self._build_panel()

        if self._panel is None:
            return False

        self._refresh_controls()
        self._panel.center()
        self._panel.makeKeyAndOrderFront_(None)
        if NSApp() is not None:
            NSApp().activateIgnoringOtherApps_(True)
        return True

    def _close_panel(self) -> None:
        if self._panel is not None:
            self._panel.orderOut_(None)

    def _refresh_controls(self) -> None:
        if not self._controls:
            return

        self._controls["battery_threshold"].setIntValue_(int(self.app.settings.get("battery_threshold", 20)))
        self._controls["check_interval"].setIntValue_(int(self.app.settings.get("check_interval", 10)))
        self._controls["alert_cooldown_seconds"].setIntValue_(int(self.app.settings.get("alert_cooldown_seconds", 900)))
        self._controls["enable_sound"].setState_(NSControlStateValueOn if self.app.settings.get("enable_sound", True) else NSControlStateValueOff)
        self._controls["enable_voice"].setState_(NSControlStateValueOn if self.app.settings.get("enable_voice", True) else NSControlStateValueOff)
        self._controls["enable_notifications"].setState_(NSControlStateValueOn if self.app.settings.get("enable_notifications", True) else NSControlStateValueOff)
        self._controls["auto_launch"].setState_(NSControlStateValueOn if self.app.settings.get("auto_launch", False) else NSControlStateValueOff)
        self._controls["enable_update_checks"].setState_(NSControlStateValueOn if self.app.settings.get("enable_update_checks", True) else NSControlStateValueOff)

        selected_channel = str(self.app.settings.get("update_channel", "stable")).strip().lower()
        if selected_channel not in {"stable", "beta"}:
            selected_channel = "stable"
        self._controls["update_channel"].selectItemWithTitle_(selected_channel)

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

    def _save_and_close(self) -> None:
        payload = self._read_payload(self._controls)
        if payload is None:
            return

        self.app.settings.update(payload)
        self.app.save_config()
        self.app.update_menu_labels()
        self.app.show_non_blocking_feedback("Preferences", "Updated successfully.")
        self._close_panel()

    def _build_panel(self) -> Optional[Any]:
        try:
            style = (
                NSWindowStyleMaskTitled
                | NSWindowStyleMaskClosable
                | NSWindowStyleMaskUtilityWindow
            )
            panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(0, 0, 420, 440),
                style,
                2,
                False,
            )
            panel.setTitle_("BattMon Preferences")
            panel.setFloatingPanel_(True)

            effect_view = NSVisualEffectView.alloc().initWithFrame_(NSMakeRect(0, 0, 420, 440))
            effect_view.setMaterial_(NSVisualEffectMaterialSidebar)
            effect_view.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
            effect_view.setState_(NSVisualEffectStateActive)
            panel.setContentView_(effect_view)

            container = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 420, 440))
            effect_view.addSubview_(container)
            self._action_bridge = _PanelActionBridge.alloc().initWithController_(self)

            def add_label(text: str, y: float) -> Any:
                label = NSTextField.labelWithString_(text)
                label.setFrame_(NSMakeRect(20, y, 180, 22))
                label.setFont_(NSFont.systemFontOfSize_(13))
                container.addSubview_(label)
                return label

            def add_input(default: Any, y: float) -> Any:
                field = NSTextField.alloc().initWithFrame_(NSMakeRect(260, y, 120, 24))
                field.setStringValue_(str(default))
                container.addSubview_(field)
                return field

            def add_switch(label: str, checked: bool, y: float) -> Any:
                switch = NSSwitch.alloc().initWithFrame_(NSMakeRect(320, y, 44, 24))
                switch.setState_(NSControlStateValueOn if checked else NSControlStateValueOff)
                container.addSubview_(switch)
                add_label(label, y + 2)
                return switch

            def add_header(text: str, y: float) -> None:
                header = NSTextField.labelWithString_(text.upper())
                header.setFrame_(NSMakeRect(20, y, 220, 18))
                header.setFont_(NSFont.boldSystemFontOfSize_(11))
                container.addSubview_(header)

            add_header("Alerts", 396)
            add_label("Battery threshold (%)", 364)
            battery_threshold = add_input(self.app.settings.get("battery_threshold", 20), 360)

            add_label("Check interval (seconds)", 330)
            check_interval = add_input(self.app.settings.get("check_interval", 10), 326)

            add_label("Alert cooldown (seconds)", 296)
            alert_cooldown_seconds = add_input(self.app.settings.get("alert_cooldown_seconds", 900), 292)

            add_header("Notifications", 244)
            enable_sound = add_switch("Enable sound alerts", bool(self.app.settings.get("enable_sound", True)), 212)
            enable_voice = add_switch("Enable voice alerts", bool(self.app.settings.get("enable_voice", True)), 182)
            enable_notifications = add_switch("Enable notifications", bool(self.app.settings.get("enable_notifications", True)), 152)

            add_header("General", 118)
            auto_launch = add_switch("Launch at startup", bool(self.app.settings.get("auto_launch", False)), 86)
            enable_update_checks = add_switch(
                "Enable automatic update checks",
                bool(self.app.settings.get("enable_update_checks", True)),
                56,
            )

            add_label("Update channel", 26)
            update_channel = NSPopUpButton.alloc().initWithFrame_pullsDown_(NSMakeRect(260, 22, 120, 26), False)
            update_channel.addItemsWithTitles_(["stable", "beta"])
            selected_channel = str(self.app.settings.get("update_channel", "stable")).strip().lower()
            if selected_channel not in {"stable", "beta"}:
                selected_channel = "stable"
            update_channel.selectItemWithTitle_(selected_channel)
            container.addSubview_(update_channel)

            save_button = NSButton.alloc().initWithFrame_(NSMakeRect(310, 10, 90, 28))
            save_button.setTitle_("Save")
            save_button.setTarget_(self._action_bridge)
            save_button.setAction_(objc.selector(self._action_bridge.save_, signature=b"v@:@"))
            container.addSubview_(save_button)

            cancel_button = NSButton.alloc().initWithFrame_(NSMakeRect(210, 10, 90, 28))
            cancel_button.setTitle_("Cancel")
            cancel_button.setTarget_(self._action_bridge)
            cancel_button.setAction_(objc.selector(self._action_bridge.cancel_, signature=b"v@:@"))
            container.addSubview_(cancel_button)

            self._controls = {
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
            return panel
        except Exception as exc:
            self.app.log_runtime(f"Failed to open native preferences: {exc}", level="warning")
            return None
