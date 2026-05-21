# mypy: ignore-errors
from datetime import datetime
from typing import Dict, Optional, Union

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
        return LegacyBatteryAlertApp.should_trigger_alert(self.app, battery_info, now)

    def trigger_alert(self, battery_level: int, now: Optional[datetime] = None) -> None:
        LegacyBatteryAlertApp.trigger_alert(self.app, battery_level, now)
