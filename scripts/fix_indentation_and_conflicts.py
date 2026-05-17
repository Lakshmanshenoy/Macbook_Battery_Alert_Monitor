#!/usr/bin/env python3
"""Conservative auto-fixes for merge markers and simple indentation issues.

This script intentionally limits its scope to project source/test Python files.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re


MERGE_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")
REPO_ROOT = Path(__file__).resolve().parent.parent


def target_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    if (root / "battery_alert_gui.py").exists():
        files.append(root / "battery_alert_gui.py")
    for folder in ("scripts", "tests"):
        base = root / folder
        if base.exists():
            files.extend(sorted(base.rglob("*.py")))
    return files


def clean_merge_markers(lines: list[str]) -> tuple[list[str], int]:
    cleaned: list[str] = []
    removed = 0
    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(marker) for marker in MERGE_MARKERS):
            removed += 1
            continue
        cleaned.append(line)
    return cleaned, removed


def fix_missing_block_after_defs(lines: list[str]) -> tuple[list[str], int]:
    out: list[str] = []
    fixes = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if re.match(r"^(def|class)\s+\w+", stripped) and stripped.rstrip().endswith(":"):
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].lstrip().startswith("#")):
                out.append(lines[j])
                j += 1
            if j < len(lines):
                next_line = lines[j]
                next_stripped = next_line.lstrip()
                next_indent = len(next_line) - len(next_stripped)
                if next_stripped and next_indent <= indent:
                    out.append(" " * (indent + 4) + "pass\n")
                    fixes += 1
            i = j
            continue
        i += 1
    return out, fixes


def process_file(path: Path, apply: bool) -> tuple[bool, int]:
    original = path.read_text(encoding="utf-8").splitlines(keepends=True)
    working = list(original)

    working, marker_fixes = clean_merge_markers(working)
    working, block_fixes = fix_missing_block_after_defs(working)

    total_fixes = marker_fixes + block_fixes
    changed = working != original

    if changed and apply:
        path.write_text("".join(working), encoding="utf-8")
    return changed, total_fixes


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-fix merge markers and simple indentation issues.")
    parser.add_argument("--check", action="store_true", help="Check only; do not write changes.")
    args = parser.parse_args()

    files = target_python_files(REPO_ROOT)
    changed_files: list[str] = []
    total_fixes = 0

    for path in files:
        changed, fix_count = process_file(path, apply=not args.check)
        total_fixes += fix_count
        if changed:
            changed_files.append(str(path.relative_to(REPO_ROOT)))

    mode = "Would fix" if args.check else "Fixed"
    if changed_files:
        print(f"{mode} {len(changed_files)} file(s), {total_fixes} change(s):")
        for item in changed_files:
            print(f"  {item}")
        return 1 if args.check else 0

    print("No merge markers or indentation issues found in target files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
