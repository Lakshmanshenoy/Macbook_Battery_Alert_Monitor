#!/usr/bin/env python3
"""Generate release manifest metadata for shipped artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from scripts.verify_release_artifacts import compute_sha256, parse_checksums_file


def build_release_manifest(
    version: str,
    artifact_path: Path,
    checksums_path: Path,
    signing_status: str,
    notarization_status: str,
) -> dict:
    """Build a structured manifest for release assets and verification metadata."""
    checksums = parse_checksums_file(checksums_path)
    artifact_sha = compute_sha256(artifact_path)

    expected_sha = checksums.get(artifact_path.name)
    if expected_sha is None:
        for entry_name, digest in checksums.items():
            if Path(entry_name).name == artifact_path.name:
                expected_sha = digest
                break

    return {
        "manifest_schema_version": 1,
        "generated_at": datetime.now().isoformat(),
        "version": version,
        "artifact": {
            "name": artifact_path.name,
            "sha256": artifact_sha,
            "expected_sha256": expected_sha,
            "matches_checksum": expected_sha == artifact_sha,
        },
        "checksums_file": checksums_path.name,
        "signing_status": signing_status,
        "notarization_status": notarization_status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate release manifest metadata.")
    parser.add_argument("--version", required=True, help="Release version (for example 1.2.0)")
    parser.add_argument("--artifact", required=True, help="Path to release artifact")
    parser.add_argument("--checksums", required=True, help="Path to checksums.txt")
    parser.add_argument("--signing-status", default="unknown", help="Signing status label")
    parser.add_argument("--notarization-status", default="unknown", help="Notarization status label")
    parser.add_argument("--output", required=True, help="Path to output JSON file")
    args = parser.parse_args()

    manifest = build_release_manifest(
        version=args.version,
        artifact_path=Path(args.artifact),
        checksums_path=Path(args.checksums),
        signing_status=args.signing_status,
        notarization_status=args.notarization_status,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Release manifest written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
