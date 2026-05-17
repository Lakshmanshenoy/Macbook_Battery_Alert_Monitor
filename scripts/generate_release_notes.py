#!/usr/bin/env python3
"""Generate draft release notes from git history."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_latest_tag(cwd: Path) -> str:
    """Return latest reachable tag or empty string when none exists."""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def generate_release_notes(cwd: Path, from_ref: str, to_ref: str = "HEAD") -> str:
    """Generate markdown release notes from git log between refs."""
    log_range = f"{from_ref}..{to_ref}" if from_ref else to_ref
    result = subprocess.run(
        ["git", "log", "--pretty=format:- %s (%h)", log_range],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )

    body = result.stdout.strip() or "- No commit messages found for this range."
    heading = f"## Release Notes ({to_ref})"
    if from_ref:
        heading = f"## Release Notes ({from_ref}..{to_ref})"
    return f"{heading}\n\n{body}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate release notes from git history.")
    parser.add_argument("--from-ref", default="", help="Start ref (defaults to latest tag)")
    parser.add_argument("--to-ref", default="HEAD", help="End ref")
    parser.add_argument("--output", default="RELEASE_DRAFT.generated.md", help="Output markdown path")
    args = parser.parse_args()

    from_ref = args.from_ref or get_latest_tag(PROJECT_ROOT)
    notes = generate_release_notes(PROJECT_ROOT, from_ref=from_ref, to_ref=args.to_ref)
    output_path = PROJECT_ROOT / args.output
    output_path.write_text(notes, encoding="utf-8")
    print(f"Release notes written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
