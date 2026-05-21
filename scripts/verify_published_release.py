#!/usr/bin/env python3
"""Download published GitHub release assets and verify checksums."""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

from scripts.verify_release_artifacts import verify_artifact


API_ROOT = "https://api.github.com/repos"


def fetch_release(owner: str, repo: str, tag: str, token: str = "") -> dict:
    """Fetch release metadata by tag."""
    url = f"{API_ROOT}/{owner}/{repo}/releases/tags/{tag}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "battmon-macos"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def download_asset(asset_url: str, output_path: Path, token: str = "") -> None:
    """Download one GitHub release asset."""
    headers = {"Accept": "application/octet-stream", "User-Agent": "battmon-macos"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(asset_url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        output_path.write_bytes(response.read())


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify published release assets.")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--download-dir", default="downloaded_release_assets")
    parser.add_argument("--token", default="")
    args = parser.parse_args()

    download_dir = Path(args.download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)

    release = fetch_release(args.owner, args.repo, args.tag, token=args.token)
    assets = release.get("assets", [])

    dmg_asset = next((a for a in assets if str(a.get("name", "")).endswith(".dmg")), None)
    checksums_asset = next((a for a in assets if a.get("name") == "checksums.txt"), None)
    if dmg_asset is None or checksums_asset is None:
        print("Required release assets not found (DMG/checksums.txt).")
        return 1

    dmg_path = download_dir / str(dmg_asset["name"])
    checksums_path = download_dir / "checksums.txt"
    download_asset(dmg_asset["url"], dmg_path, token=args.token)
    download_asset(checksums_asset["url"], checksums_path, token=args.token)

    ok, message = verify_artifact(dmg_path, checksums_path)
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
