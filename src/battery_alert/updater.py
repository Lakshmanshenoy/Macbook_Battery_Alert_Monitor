# mypy: ignore-errors
import hashlib
import json
import ssl
import subprocess
import sys
import tempfile
import threading
import urllib
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import certifi
except Exception:  # pragma: no cover - fallback is tested via runtime behavior
    certifi = None

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
        self._ssl_context = None

    def _subprocess_module(self) -> Any:
        gui_module = sys.modules.get("battery_alert_gui")
        return getattr(gui_module, "subprocess", subprocess)

    def _threading_module(self) -> Any:
        gui_module = sys.modules.get("battery_alert_gui")
        return getattr(gui_module, "threading", threading)

    def _urlopen(self, request_or_url: Any, timeout: int = 6) -> Any:
        gui_module = sys.modules.get("battery_alert_gui")
        urllib_module = getattr(gui_module, "urllib", urllib)
        ssl_context = self._get_ssl_context()
        if ssl_context is not None:
            return urllib_module.request.urlopen(request_or_url, timeout=timeout, context=ssl_context)
        return urllib_module.request.urlopen(request_or_url, timeout=timeout)

    def _get_ssl_context(self) -> Any:
        if self._ssl_context is not None:
            return self._ssl_context

        try:
            if certifi is not None:
                self._ssl_context = ssl.create_default_context(cafile=certifi.where())
            else:
                self._ssl_context = ssl.create_default_context()
        except Exception as exc:
            self.app.log_runtime(f"Unable to initialize SSL context: {exc}", level="warning")
            self._ssl_context = None

        return self._ssl_context

    def _rumps_module(self) -> Any:
        gui_module = sys.modules.get("battery_alert_gui")
        rumps = getattr(gui_module, "rumps", None)
        if rumps is not None:
            return rumps

        import rumps as imported_rumps

        return imported_rumps

    def _http_headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "User-Agent": "battmon-macos",
        }

    def _release_api_url(self, update_channel: Optional[str] = None) -> str:
        channel = (update_channel or self.app.settings.get("update_channel", UPDATE_CHANNEL) or UPDATE_CHANNEL).strip().lower()
        return LATEST_STABLE_RELEASE_API if channel == "stable" else RELEASES_API

    def _fetch_release_payload(self, update_channel: Optional[str] = None) -> Dict[str, Any]:
        channel = (update_channel or self.app.settings.get("update_channel", UPDATE_CHANNEL) or UPDATE_CHANNEL).strip().lower()
        request = urllib.request.Request(
            self._release_api_url(channel),
            headers=self._http_headers(),
        )
        with self._urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if channel == "stable":
            return payload if isinstance(payload, dict) else {}

        release_payload: Dict[str, Any] = {}
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
        return release_payload

    def _release_info_from_payload(self, release_payload: Dict[str, Any]) -> Dict[str, str]:
        return {
            "version": str(release_payload.get("tag_name", "")).lstrip("v"),
            "url": str(release_payload.get("html_url", "")) or RELEASES_PAGE_URL,
        }

    def _find_release_asset_url(self, release_payload: Dict[str, Any], file_name: str) -> str:
        assets = release_payload.get("assets")
        if not isinstance(assets, list):
            return ""
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            if str(asset.get("name", "")) == file_name:
                return str(asset.get("browser_download_url", ""))
        return ""

    def _download_file(self, url: str, destination: Path) -> None:
        request = urllib.request.Request(url, headers=self._http_headers())
        with self._urlopen(request, timeout=30) as response:
            destination.write_bytes(response.read())

    def _sha256_file(self, path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _checksum_from_manifest(self, checksums_text: str, target_name: str) -> str:
        for line in checksums_text.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            parts = cleaned.split()
            if len(parts) < 2:
                continue
            digest = parts[0].strip().lower()
            file_token = parts[-1].strip().lstrip("*")
            if file_token == target_name:
                return digest
        return ""

    def record_update_check_result(
        self,
        status: str,
        latest_version: Optional[str] = None,
        latest_url: Optional[str] = None,
        checked_at: Optional[datetime] = None,
    ) -> None:
        """Persist update-check metadata for visibility and support diagnostics."""
        if not hasattr(self.app, "app_state") or not isinstance(self.app.app_state, dict):
            self.app.app_state = self.app.default_app_state_payload()

        if checked_at is not None:
            self.app.app_state["last_update_check_at"] = checked_at.isoformat()
        self.app.app_state["last_update_status"] = status
        if latest_version:
            self.app.app_state["last_known_release_version"] = latest_version
        if latest_url:
            self.app.app_state["last_known_release_url"] = latest_url
        self.app.save_app_state()

    def _version_tuple(self, version: str) -> Tuple[int, int, int]:
        """Normalize semantic-ish version strings for comparison."""
        cleaned = version.lower().strip().lstrip("v")
        cleaned = cleaned.split("-")[0]
        parts = []
        for token in cleaned.split("."):
            try:
                parts.append(int(token))
            except ValueError:
                parts.append(0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])

    def is_newer_version(self, latest_version: str, current_version: str) -> bool:
        """Return True when latest_version is greater than current_version."""
        return self._version_tuple(latest_version) > self._version_tuple(current_version)

    def _read_last_update_check(self) -> Optional[datetime]:
        """Read last update-check timestamp from disk."""
        if not hasattr(self.app, "update_state") or not isinstance(self.app.update_state, dict):
            self.app.update_state = self.app.default_update_state_payload()

        timestamp = self.app.update_state.get("last_checked")
        if not timestamp:
            return None

        try:
            return datetime.fromisoformat(timestamp)
        except Exception:
            self.app.update_state = self.app.default_update_state_payload()
            self.app.save_update_state()
            return None

    def _write_last_update_check(self, timestamp: datetime) -> None:
        """Persist last update-check timestamp."""
        if not hasattr(self.app, "update_state") or not isinstance(self.app.update_state, dict):
            self.app.update_state = self.app.default_update_state_payload()

        self.app.update_state["last_checked"] = timestamp.isoformat()
        self.app.save_update_state()

    def should_check_for_updates(self, now: Optional[datetime] = None, minimum_hours: int = 24) -> bool:
        """Throttle automatic update checks to avoid network chatter."""
        now = now or datetime.now()
        previous = self._read_last_update_check()
        if previous is None:
            return True
        return (now - previous).total_seconds() >= minimum_hours * 3600

    def check_for_updates(self, manual: bool = False) -> Dict[str, str]:
        if not manual and not self.app.settings.get("enable_update_checks", True):
            return {"status": "disabled", "message": "Automatic update checks are disabled."}

        if not manual and not self.should_check_for_updates():
            return {"status": "throttled", "message": "Automatic update check throttled."}

        checked_at = datetime.now()
        try:
            latest_release = self.app.get_latest_release()
            latest = latest_release.get("version", "")
            latest_url = latest_release.get("url", RELEASES_PAGE_URL)
            self._write_last_update_check(checked_at)

            if not latest:
                self.record_update_check_result("unknown", checked_at=checked_at)
                return {
                    "status": "unknown",
                    "message": "Could not determine the latest release version right now. Please try again shortly.",
                }

            if self.is_newer_version(latest, APP_VERSION):
                message = f"Version {latest} is available. You are on {APP_VERSION}."
                self.record_update_check_result(
                    "update_available",
                    latest_version=latest,
                    latest_url=latest_url,
                    checked_at=checked_at,
                )
                self.app.log_runtime(message)
                return {"status": "update_available", "message": message}

            self.record_update_check_result(
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
            self.record_update_check_result("failed", checked_at=checked_at)
            self.app.log_runtime(f"Update check failed: {exc}", level="warning")
            return {
                "status": "failed",
                "message": "Unable to check updates right now. Please try again later.",
            }
        except Exception as exc:
            self.record_update_check_result("failed", checked_at=checked_at)
            self.app.log_runtime(f"Unexpected update check error: {exc}", level="warning")
            return {
                "status": "failed",
                "message": "Unable to check updates right now. Please try again later.",
            }

    def _run_manual_update_check(self) -> None:
        """Run update check in background and send non-blocking completion feedback."""
        try:
            result = self.app.check_for_updates(manual=True)
            status = result.get("status", "failed")
            message = result.get("message", "Unable to check updates right now. Please try again later.")

            if status == "update_available":
                self.app.show_maintenance_status(f"Update check complete: {message}")
                prompt = self._rumps_module().Window(
                    message + "\n\nOpen the release page now?",
                    title="Update Available",
                    default_text="",
                    ok="Open",
                    cancel="Later",
                )
                response = prompt.run()
                if response.clicked:
                    self.open_releases_page(None)
            elif status == "up_to_date":
                self.app.show_maintenance_status("Update check complete: no updates found.")
            elif status == "unknown":
                self.app.show_maintenance_status(f"Update check complete: {message}")
            else:
                self.app.show_maintenance_status(f"Update check failed: {message}")
        finally:
            self.app._update_check_in_progress = False

    def check_for_updates_now(self, _: Any) -> None:
        """Manual update check entrypoint for menu action."""
        if self.app._update_check_in_progress:
            self.app.show_maintenance_status("Update check already in progress.")
            return

        self.app._update_check_in_progress = True
        self.app.show_maintenance_status("Update check started.")
        self._threading_module().Thread(target=self._run_manual_update_check, daemon=True).start()

    def show_version_and_updates(self, _: Any = None) -> None:
        """Show the current version and tracked update state."""
        try:
            self._rumps_module().alert("Version & Updates", self.app.build_release_visibility_summary())
        except Exception as exc:
            self.app.log_runtime(f"Error in show_version_and_updates: {exc}", level="error")

    def open_releases_page(self, _: Any = None) -> None:
        """Open the GitHub releases page for self-service downloads and notes."""
        try:
            self._subprocess_module().run(["open", RELEASES_PAGE_URL], check=False)
            self.app.show_maintenance_status("Opened releases page.")
        except Exception as exc:
            self.app.log_runtime(f"Error opening releases page: {exc}", level="error")
            self._rumps_module().alert(f"Error: {exc}", title="Error")

    def get_latest_release(self) -> Dict[str, str]:
        """Fetch latest release details according to selected update channel."""
        release_payload = self._fetch_release_payload()
        return self._release_info_from_payload(release_payload)

    def _run_guided_update_download(self) -> None:
        downloads_dir = Path.home() / "Downloads"
        downloads_dir.mkdir(parents=True, exist_ok=True)

        try:
            release_payload = self._fetch_release_payload()
            release_info = self._release_info_from_payload(release_payload)
            latest_version = release_info.get("version", "")

            if not latest_version:
                self.app.show_maintenance_status("Guided update failed: latest version unavailable.")
                return

            if not self.is_newer_version(latest_version, APP_VERSION):
                self.app.show_maintenance_status("Guided update: you are already on the latest version.")
                return

            dmg_url = self._find_release_asset_url(release_payload, "BattMon.dmg")
            if not dmg_url:
                self.app.show_maintenance_status("Guided update failed: BattMon.dmg was not found in release assets.")
                return

            dmg_destination = downloads_dir / f"BattMon-{latest_version}.dmg"
            self.app.show_maintenance_status("Guided update: downloading installer…")
            self._download_file(dmg_url, dmg_destination)

            checksums_url = self._find_release_asset_url(release_payload, "checksums.txt")
            if checksums_url:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
                    temp_path = Path(temp_file.name)
                try:
                    self._download_file(checksums_url, temp_path)
                    expected_digest = self._checksum_from_manifest(temp_path.read_text(encoding="utf-8", errors="replace"), "BattMon.dmg")
                    if expected_digest:
                        actual_digest = self._sha256_file(dmg_destination)
                        if actual_digest != expected_digest:
                            self.app.show_maintenance_status("Guided update failed: checksum verification mismatch.")
                            return
                finally:
                    temp_path.unlink(missing_ok=True)

            self._subprocess_module().run(["open", str(dmg_destination)], check=False)
            self.app.show_maintenance_status(
                f"Guided update ready: installer downloaded to {dmg_destination.name} and opened."
            )
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            self.app.log_runtime(f"Guided update download failed: {exc}", level="warning")
            self.app.show_maintenance_status("Guided update failed: unable to download release assets.")
        except Exception as exc:
            self.app.log_runtime(f"Guided update failed: {exc}", level="warning")
            self.app.show_maintenance_status("Guided update failed: unexpected error.")
        finally:
            self.app._guided_update_in_progress = False

    def download_and_open_latest_installer(self, _: Any = None) -> None:
        if getattr(self.app, "_guided_update_in_progress", False):
            self.app.show_maintenance_status("Guided update is already in progress.")
            return

        self.app._guided_update_in_progress = True
        self.app.show_maintenance_status("Guided update started.")
        self._threading_module().Thread(target=self._run_guided_update_download, daemon=True).start()

    def download_latest_release(self, _: Any = None) -> None:
        try:
            release_url = self.app.app_state.get("last_known_release_url") or RELEASES_PAGE_URL
            self._subprocess_module().run(["open", release_url], check=False)
            self.app.show_maintenance_status("Opened latest release download page.")
        except Exception as exc:
            self.app.log_runtime(f"Error downloading latest release: {exc}", level="error")
            self._rumps_module().alert(f"Error: {exc}", title="Error")

    def build_release_validation_command(self) -> List[str]:
        """Build the command used to run the release smoke test."""
        smoke_test_script = Path(__file__).resolve().parent / "scripts" / "release_smoke_test.py"
        return [sys.executable, str(smoke_test_script)]

    def _run_release_validation(self) -> None:
        """Run the release smoke test and report the outcome."""
        try:
            command = self.app.build_release_validation_command()
            result = self._subprocess_module().run(command, capture_output=True, text=True)
            self.app.record_app_state_event("release_checks_run")
            self.app.app_state["last_release_validation_at"] = datetime.now().isoformat()
            self.app.save_app_state()

            if result.returncode == 0:
                self.app.show_maintenance_status("Release check complete: passed.")
                self.app.log_runtime("Release smoke test completed successfully")
            else:
                message = (result.stderr or result.stdout or "Release smoke test failed.").strip()
                self.app.show_maintenance_status(f"Release check failed: {message[:160]}")
                self.app.log_runtime(f"Release smoke test failed: {message}", level="warning")
        except Exception as exc:
            self.app.log_runtime(f"Release validation error: {exc}", level="warning")
            self.app.show_maintenance_status("Release check failed: unable to run smoke test.")
        finally:
            self.app._release_validation_in_progress = False

    def run_release_validation_now(self, _: Any) -> None:
        """Run the release smoke test in the background."""
        if self.app._release_validation_in_progress:
            self.app.show_maintenance_status("Release check already in progress.")
            return

        self.app._release_validation_in_progress = True
        self.app.show_maintenance_status("Release check started.")
        self._threading_module().Thread(target=self._run_release_validation, daemon=True).start()
