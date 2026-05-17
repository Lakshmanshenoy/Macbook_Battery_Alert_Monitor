#!/usr/bin/env python3
"""Verify release artifact integrity against SHA256 checksums."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


def parse_checksums_file(checksums_path: Path) -> dict[str, str]:
    """Parse a shasum-style checksums file into filename -> sha256 hash."""
    mapping: dict[str, str] = {}
    for raw_line in checksums_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^([A-Fa-f0-9]{64})\s+\*?(.+)$", line)
        if not match:
            raise ValueError(f"Invalid checksum line: {raw_line}")
        digest = match.group(1).lower()
        filename = match.group(2).strip()
        mapping[filename] = digest
    return mapping


def compute_sha256(file_path: Path) -> str:
    """Compute SHA256 hash for the given file."""
    digest = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_artifact(artifact_path: Path, checksums_path: Path) -> tuple[bool, str]:
    """Validate one artifact against the checksums file."""
    if not artifact_path.exists():
        return False, f"Artifact not found: {artifact_path}"

    if not checksums_path.exists():
        return False, f"Checksums file not found: {checksums_path}"

    checksums = parse_checksums_file(checksums_path)
    expected = checksums.get(artifact_path.name)
    if not expected:
        return False, f"No checksum entry for {artifact_path.name} in {checksums_path}"

    actual = compute_sha256(artifact_path)
    if actual != expected:
        return (
            False,
            f"Checksum mismatch for {artifact_path.name}: expected {expected}, got {actual}",
        )

    return True, f"Checksum verified for {artifact_path.name}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify release artifact integrity.")
    parser.add_argument("--artifact", required=True, help="Path to artifact file")
    parser.add_argument("--checksums", required=True, help="Path to checksums.txt")
    args = parser.parse_args()

    ok, message = verify_artifact(Path(args.artifact), Path(args.checksums))
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
