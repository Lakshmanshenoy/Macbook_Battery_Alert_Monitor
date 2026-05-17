#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

print_step() {
  echo "[checks] $1"
}

run_syntax_check() {
  print_step "Running Python syntax check"
  python3 - <<'PY'
from pathlib import Path
import py_compile
import sys

root = Path('.')
targets = []
if (root / 'battery_alert_gui.py').exists():
    targets.append(root / 'battery_alert_gui.py')
for folder in ('scripts', 'tests'):
    base = root / folder
    if base.exists():
        targets.extend(sorted(base.rglob('*.py')))

failed = []
for path in targets:
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as exc:
        failed.append((path, exc.msg))

if failed:
    for path, msg in failed:
        print(f"[syntax] FAIL {path}: {msg}")
    sys.exit(1)

print(f"[syntax] PASS ({len(targets)} files)")
PY
}

run_fixers() {
  print_step "Running indentation/conflict auto-fixer"
  python3 scripts/fix_indentation_and_conflicts.py
}

run_tests() {
  print_step "Running pytest"
  pytest -q

  print_step "Running release smoke test"
  python3 scripts/release_smoke_test.py

  print_step "Running synthetic artifact verification"
  python3 scripts/run_pre_release_checks.py --skip-tests
}

print_step "Starting project checks"
run_fixers

if ! run_syntax_check; then
  print_step "Syntax check failed, retrying once after fixer"
  run_fixers
  run_syntax_check
fi

if ! run_tests; then
  print_step "Tests failed, retrying once after fixer"
  run_fixers
  run_syntax_check
  run_tests
fi

print_step "All checks passed"
