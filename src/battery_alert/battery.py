import subprocess
import time
from typing import Callable, Dict, Union

BatteryInfo = Dict[str, Union[int, bool]]


class BatteryService:
    """Battery information provider with short-lived result caching."""

    def __init__(self, logger: Callable[[str, str], None]) -> None:
        self._log = logger
        self._cache: Dict[str, Union[int, bool, float]] = {
            "level": 100,
            "is_charging": False,
            "is_discharging": False,
            "fetched_at": 0.0,
        }

    def get_battery_info(self) -> BatteryInfo:
        now = time.time()
        fetched_at = float(self._cache.get("fetched_at", 0.0))
        if now - fetched_at < 3.0:
            return {
                "level": int(self._cache["level"]),
                "is_charging": bool(self._cache["is_charging"]),
                "is_discharging": bool(self._cache["is_discharging"]),
            }

        try:
            result = subprocess.run(
                ["pmset", "-g", "batt"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            battery_output = result.stdout

            import re

            percentage_match = re.search(r"(\d+)%", battery_output)
            battery_level = int(percentage_match.group(1)) if percentage_match else 100
            lower = battery_output.lower()
            is_charging = "charging" in lower
            is_discharging = "discharging" in lower

            self._cache.update(
                {
                    "level": battery_level,
                    "is_charging": is_charging,
                    "is_discharging": is_discharging,
                    "fetched_at": now,
                }
            )

            self._log(
                "Battery level: {}%, charging: {}, discharging: {}".format(
                    battery_level,
                    is_charging,
                    is_discharging,
                ),
                "info",
            )
            return {
                "level": battery_level,
                "is_charging": is_charging,
                "is_discharging": is_discharging,
            }
        except Exception as exc:  # pragma: no cover - defensive fallback
            self._log("Failed to get battery info: {}".format(exc), "error")
            return {
                "level": int(self._cache.get("level", 100)),
                "is_charging": bool(self._cache.get("is_charging", False)),
                "is_discharging": bool(self._cache.get("is_discharging", False)),
            }
