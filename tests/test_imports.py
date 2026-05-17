import importlib
import sys
import types


def _install_rumps_stub():
    rumps_stub = types.ModuleType("rumps")

    class DummyApp:
        def __init__(self, *args, **kwargs):
            self.title = ""
            self.menu = []

        def run(self):
            return None

    class DummyMenuItem:
        def __init__(self, title, callback=None):
            self.title = title
            self.callback = callback

    class DummyWindow:
        def __init__(self, *args, **kwargs):
            pass

        def run(self):
            return types.SimpleNamespace(clicked=False, text="")

    rumps_stub.App = DummyApp
    rumps_stub.MenuItem = DummyMenuItem
    rumps_stub.Window = DummyWindow
    rumps_stub.alert = lambda *args, **kwargs: None
    rumps_stub.quit_application = lambda: None

    sys.modules["rumps"] = rumps_stub


def test_can_import_main_module():
    # Sanity check: importing the main module should succeed
    # Sanity check: importing the main module should succeed
    _install_rumps_stub()
    mod = importlib.import_module('battery_alert_gui')
    assert mod is not None
