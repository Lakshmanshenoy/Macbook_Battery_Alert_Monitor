#!/usr/bin/env python3
"""Run the local pre-release validation sequence in one command."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_command(command: list[str], cwd: Path) -> None:
    """Run one command and raise on failure."""
    print(f"[pre-release] running: {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def build_command_plan() -> list[list[str]]:
    """Return the core validation commands for a local pre-release run."""
    return [
        ["pytest", "-q"],
        ["python3", "scripts/release_smoke_test.py"],
    ]


def run_synthetic_artifact_check(cwd: Path) -> None:
    """Create a synthetic artifact and verify checksum tooling end-to-end."""
    with tempfile.TemporaryDirectory(prefix="battery-alert-prerelease-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        artifact_dir = temp_dir / "artifacts"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifact_dir / "BattMon.dmg"
        artifact_path.write_text("pre-release synthetic artifact", encoding="utf-8")

        checksums_path = temp_dir / "checksums.txt"
        result = subprocess.run(
            ["bash", "scripts/generate_checksums.sh", str(artifact_path)],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

        generated_checksums = cwd / "checksums.txt"
        if generated_checksums.exists():
            shutil.move(str(generated_checksums), str(checksums_path))

        print(result.stdout.strip())
        run_command(
            [
                "python3",
                "scripts/verify_release_artifacts.py",
                "--artifact",
                str(artifact_path),
                "--checksums",
                str(checksums_path),
            ],
            cwd,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local pre-release checks.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest execution")
    args = parser.parse_args()

    if not args.skip_tests:
        for command in build_command_plan():
            run_command(command, PROJECT_ROOT)

    run_synthetic_artifact_check(PROJECT_ROOT)
    print("[pre-release] all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
