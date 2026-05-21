# mypy: ignore-errors
from .legacy_app import BatteryAlertApp as LegacyBatteryAlertApp


class UpdateChecker:
    """Release-check and update-channel facade."""

    def __init__(self, app: "LegacyBatteryAlertApp") -> None:
        self.app = app

    def check_for_updates(self, manual: bool = False) -> None:
        return LegacyBatteryAlertApp.check_for_updates(self.app, manual)

    def download_latest_release(self, _=None) -> None:
        return LegacyBatteryAlertApp.download_latest_release(self.app, _)
