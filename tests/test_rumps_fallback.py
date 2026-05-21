import builtins
import importlib.util
import sys
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parent.parent / "battery_alert_gui.py"


def test_battery_alert_gui_uses_local_rumps_stub_when_import_fails(monkeypatch):
    original_import = builtins.__import__

    def blocked_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "rumps":
            raise ImportError("rumps intentionally unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    sys.modules.pop("battery_alert_gui_fallback_test", None)
    sys.modules.pop("rumps", None)

    spec = importlib.util.spec_from_file_location("battery_alert_gui_fallback_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.rumps.App.__name__ == "_DummyApp"
    assert module.rumps.MenuItem.__name__ == "_DummyMenuItem"
    assert module.rumps.Window.__name__ == "_DummyWindow"
