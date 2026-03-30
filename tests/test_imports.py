import importlib


def test_can_import_main_module():
    # Sanity check: importing the main module should succeed
    mod = importlib.import_module('battery_alert_gui')
    assert mod is not None
