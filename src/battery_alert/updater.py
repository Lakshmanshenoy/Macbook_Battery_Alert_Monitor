# mypy: ignore-errors
import json
import urllib.error
import urllib.request
from datetime import datetime

from .constants import (
    APP_VERSION,
    LATEST_STABLE_RELEASE_API,
    RELEASES_API,
    RELEASES_PAGE_URL,
    UPDATE_CHANNEL,
)
from .legacy_app import BatteryAlertApp as LegacyBatteryAlertApp


class UpdateChecker:
    """Release-check and update-channel facade."""

    def __init__(self, app: "LegacyBatteryAlertApp") -> None:
        self.app = app

    def check_for_updates(self, manual: bool = False) -> None:
        if not manual and not self.app.settings.get("enable_update_checks", True):
            return {"status": "disabled", "message": "Automatic update checks are disabled."}

        if not manual and not self.app.should_check_for_updates():
            return {"status": "throttled", "message": "Automatic update check throttled."}

        checked_at = datetime.now()
        try:
            latest_release = self.app.get_latest_release()
            latest = latest_release.get("version", "")
            latest_url = latest_release.get("url", RELEASES_PAGE_URL)
            self.app._write_last_update_check(checked_at)

            if not latest:
                self.app.record_update_check_result("unknown", checked_at=checked_at)
                return {
                    "status": "unknown",
                    "message": "Could not determine the latest release version right now. Please try again shortly.",
                }

            if self.app.is_newer_version(latest, APP_VERSION):
                message = f"Version {latest} is available. You are on {APP_VERSION}."
                self.app.record_update_check_result(
                    "update_available",
                    latest_version=latest,
                    latest_url=latest_url,
                    checked_at=checked_at,
                )
                self.app.log_runtime(message)
                return {"status": "update_available", "message": message}

            self.app.record_update_check_result(
                "up_to_date",
                latest_version=latest,
                latest_url=latest_url,
                checked_at=checked_at,
            )
            return {
                "status": "up_to_date",
                "message": f"You are up to date on version {APP_VERSION}.",
            }
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            self.app.record_update_check_result("failed", checked_at=checked_at)
            self.app.log_runtime(f"Update check failed: {exc}", level="warning")
            return {
                "status": "failed",
                "message": "Unable to check updates right now. Please try again later.",
            }
        except Exception as exc:
            self.app.record_update_check_result("failed", checked_at=checked_at)
            self.app.log_runtime(f"Unexpected update check error: {exc}", level="warning")
            return {
                "status": "failed",
                "message": "Unable to check updates right now. Please try again later.",
            }

    def get_latest_release(self):
        """Fetch latest release details according to selected update channel."""
        update_channel = self.app.settings.get("update_channel", UPDATE_CHANNEL)
        api_url = LATEST_STABLE_RELEASE_API if update_channel == "stable" else RELEASES_API
        request = urllib.request.Request(
            api_url,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "battery-alert-monitor"},
        )
        with urllib.request.urlopen(request, timeout=6) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if update_channel == "stable":
            release_payload = payload
        else:
            release_payload = {}
            if isinstance(payload, list):
                for candidate in payload:
                    if isinstance(candidate, dict) and candidate.get("prerelease"):
                        release_payload = candidate
                        break
                if not release_payload:
                    for candidate in payload:
                        if isinstance(candidate, dict):
                            release_payload = candidate
                            break

        return {
            "version": str(release_payload.get("tag_name", "")).lstrip("v"),
            "url": str(release_payload.get("html_url", "")) or RELEASES_PAGE_URL,
        }

    def download_latest_release(self, _=None) -> None:
        return LegacyBatteryAlertApp.download_latest_release(self.app, _)
