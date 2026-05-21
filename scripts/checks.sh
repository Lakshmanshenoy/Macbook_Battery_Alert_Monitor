#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

MODE="${1:-local}"
if [[ "$MODE" == "--ci" ]]; then
  MODE="ci"
fi

if [[ "$MODE" != "local" && "$MODE" != "ci" ]]; then
  echo "Usage: bash scripts/checks.sh [local|ci|--ci]"
  exit 2
fi

CHECK_ONLY=false
if [[ "$MODE" == "ci" || "${CI:-}" == "true" ]]; then
  CHECK_ONLY=true
fi

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
  if [[ "$CHECK_ONLY" == "true" ]]; then
    print_step "Checking indentation/conflict issues (non-mutating CI mode)"
    python3 scripts/fix_indentation_and_conflicts.py --check
  else
    print_step "Running indentation/conflict auto-fixer"
    python3 scripts/fix_indentation_and_conflicts.py
  fi
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
  if [[ "$CHECK_ONLY" == "true" ]]; then
    print_step "Syntax check failed in CI mode"
    exit 1
  fi
  print_step "Syntax check failed, retrying once after fixer"
  run_fixers
  run_syntax_check
fi

if ! run_tests; then
  if [[ "$CHECK_ONLY" == "true" ]]; then
    print_step "Tests failed in CI mode"
    exit 1
  fi
  print_step "Tests failed, retrying once after fixer"
  run_fixers
  run_syntax_check
  run_tests
fi

print_step "All checks passed"
