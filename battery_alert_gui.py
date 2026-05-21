#!/usr/bin/env python3
"""
Compatibility entrypoint for BattMon.
Keeps legacy imports working while delegating runtime behavior to src.battery_alert.
"""

import types
import subprocess
import threading
import shutil

try:
    import rumps
except ImportError:
    rumps = types.ModuleType("rumps")

    class _DummyApp:
        def __init__(self, *args, **kwargs):
            self.title = ""
            self.menu = []

        def run(self):
            return None

    class _DummyMenuItem:
        def __init__(self, title, callback=None):
            self.title = title
            self.callback = callback

    class _DummyWindow:
        next_response = types.SimpleNamespace(clicked=False, text="")

        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            return _DummyWindow.next_response

    rumps.App = _DummyApp
    rumps.MenuItem = _DummyMenuItem
    rumps.Window = _DummyWindow
    rumps.alert = lambda *args, **kwargs: None
    rumps.quit_application = lambda: None

from src.battery_alert.app import APP_VERSION, BatteryAlertApp
from src.battery_alert.constants import (
    APP_STATE_SCHEMA_VERSION,
    CONFIG_SCHEMA_VERSION,
    RELEASES_PAGE_URL,
    UPDATE_STATE_SCHEMA_VERSION,
)
from src.battery_alert import legacy_app as _legacy_app

# Keep monkeypatch behavior stable for tests that patch module-level objects.
_legacy_app.subprocess = subprocess
_legacy_app.threading = threading
_legacy_app.shutil = shutil

__all__ = [
    "APP_VERSION",
    "APP_STATE_SCHEMA_VERSION",
    "BatteryAlertApp",
    "CONFIG_SCHEMA_VERSION",
    "RELEASES_PAGE_URL",
    "UPDATE_STATE_SCHEMA_VERSION",
    "main",
]


def main() -> None:
    app = BatteryAlertApp()
    app.run()


if __name__ == "__main__":
    main()
