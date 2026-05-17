#!/usr/bin/env python3
"""Run maintainer ship checklist commands and print next release steps."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def print_next_steps(version: str) -> None:
    """Print concise next steps for maintainers after validations pass."""
    print("\n[ship] next steps")
    print(f"1. Review RELEASE_DRAFT.md and generated notes for v{version}.")
    print(f"2. Create and push tag: git tag v{version} && git push origin v{version}.")
    print("3. Trigger release workflow dry run if needed (workflow_dispatch).")
    print("4. Verify published assets with scripts/verify_published_release.py.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ship checklist for releases.")
    parser.add_argument("--version", required=True, help="Target version number, for example 1.2.0")
    parser.add_argument("--skip-checks", action="store_true", help="Skip automated pre-release checks")
    args = parser.parse_args()

    if not args.skip_checks:
        subprocess.run(["python3", "scripts/run_pre_release_checks.py"], cwd=PROJECT_ROOT, check=True)

    subprocess.run(["python3", "scripts/generate_release_notes.py", "--to-ref", "HEAD"], cwd=PROJECT_ROOT, check=True)
    print_next_steps(args.version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
