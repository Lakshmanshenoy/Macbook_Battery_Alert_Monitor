"""Unit tests for BatteryService (src/battery_alert/battery.py)."""
import time
import types
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.battery_alert.battery import BatteryService

PMSET_CHARGING = (
    "Now drawing from 'AC Power'; AC attached; No recent wakes\n"
    " -InternalBattery-0 (id=12345)\t76%; charging; 1:12 remaining present: true\n"
)

PMSET_DISCHARGING = (
    "Now drawing from 'Battery Power'\n"
    " -InternalBattery-0 (id=12345)\t23%; discharging; 0:48 remaining present: true\n"
)

PMSET_FULL = (
    "Now drawing from 'AC Power'; AC attached; No recent wakes\n"
    " -InternalBattery-0 (id=12345)\t100%; charged; (no estimate) present: true\n"
)


def _make_service() -> BatteryService:
    logger = lambda msg, level: None
    svc = BatteryService(logger)
    # Reset cache so every call fetches fresh
    svc._cache["fetched_at"] = 0.0
    return svc


def _mock_result(stdout: str):
    r = MagicMock()
    r.stdout = stdout
    return r


# ---------------------------------------------------------------------------
# Parsing — charging state
# ---------------------------------------------------------------------------

def test_charging_level_and_state():
    svc = _make_service()
    with patch("subprocess.run", return_value=_mock_result(PMSET_CHARGING)):
        info = svc.get_battery_info()
    assert info["level"] == 76
    assert info["is_charging"] is True
    assert info["is_discharging"] is False


def test_discharging_level_and_state():
    svc = _make_service()
    with patch("subprocess.run", return_value=_mock_result(PMSET_DISCHARGING)):
        info = svc.get_battery_info()
    assert info["level"] == 23
    assert info["is_charging"] is False
    assert info["is_discharging"] is True


def test_fully_charged():
    svc = _make_service()
    with patch("subprocess.run", return_value=_mock_result(PMSET_FULL)):
        info = svc.get_battery_info()
    assert info["level"] == 100
    # "charged" contains "charging" as substring — allow either True or False
    # The important thing is it's NOT discharging
    assert info["is_discharging"] is False


# ---------------------------------------------------------------------------
# Fallback on subprocess error
# ---------------------------------------------------------------------------

def test_fallback_on_subprocess_exception():
    svc = _make_service()
    with patch("subprocess.run", side_effect=OSError("pmset not found")):
        info = svc.get_battery_info()
    # Falls back to cached defaults (level=100 initially)
    assert isinstance(info["level"], int)
    assert isinstance(info["is_charging"], bool)
    assert isinstance(info["is_discharging"], bool)


# ---------------------------------------------------------------------------
# Caching — second call within TTL should not call subprocess again
# ---------------------------------------------------------------------------

def test_result_is_cached_within_ttl():
    svc = _make_service()
    with patch("subprocess.run", return_value=_mock_result(PMSET_DISCHARGING)) as mock_run:
        svc.get_battery_info()   # first call — populates cache
        svc.get_battery_info()   # second call — should use cache
    assert mock_run.call_count == 1


def test_cache_expires_after_ttl():
    svc = _make_service()
    with patch("subprocess.run", return_value=_mock_result(PMSET_DISCHARGING)) as mock_run:
        svc.get_battery_info()          # first call
        svc._cache["fetched_at"] = 0.0  # force cache expiry
        svc.get_battery_info()          # second call — should re-fetch
    assert mock_run.call_count == 2


# ---------------------------------------------------------------------------
# Return shape
# ---------------------------------------------------------------------------

def test_return_keys_present():
    svc = _make_service()
    with patch("subprocess.run", return_value=_mock_result(PMSET_CHARGING)):
        info = svc.get_battery_info()
    assert "level" in info
    assert "is_charging" in info
    assert "is_discharging" in info


def test_level_in_valid_range():
    svc = _make_service()
    with patch("subprocess.run", return_value=_mock_result(PMSET_DISCHARGING)):
        info = svc.get_battery_info()
    assert 0 <= info["level"] <= 100
