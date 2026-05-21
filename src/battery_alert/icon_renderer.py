# mypy: ignore-errors
from __future__ import annotations

from typing import Any, Optional

try:
    from AppKit import NSImage  # type: ignore

    APPKIT_AVAILABLE = True
except Exception:  # pragma: no cover
    APPKIT_AVAILABLE = False


class StatusIconRenderer:
    """Render status bar symbols via AppKit when available."""

    def __init__(self, app: Any) -> None:
        self.app = app

    def is_available(self) -> bool:
        return APPKIT_AVAILABLE

    def _symbol_name(self, level: int, is_charging: bool) -> str:
        if is_charging:
            return "battery.100.bolt"
        if level > 80:
            return "battery.100"
        if level > 40:
            return "battery.50"
        if level > 20:
            return "battery.25"
        return "exclamationmark.triangle.fill"

    def _status_button(self) -> Optional[Any]:
        status_item = getattr(self.app, "_nsapp", None)
        if status_item is None:
            return None

        button_fn = getattr(status_item, "button", None)
        if callable(button_fn):
            return button_fn()
        return None

    def apply(self, level: int, is_charging: bool) -> bool:
        if not self.is_available():
            return False

        button = self._status_button()
        if button is None:
            return False

        try:
            symbol_name = self._symbol_name(level, is_charging)
            image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(symbol_name, "Battery status")
            if image is None:
                return False

            image.setTemplate_(True)
            button.setImage_(image)
            button.setTitle_(f" {level}%")
            return True
        except Exception:
            return False
