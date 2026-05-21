from pathlib import Path

from scripts.run_pre_release_checks import build_command_plan

def test_build_command_plan_includes_core_release_checks():
    plan = build_command_plan()
    assert ["pytest", "-q"] in plan
    assert ["python3", "scripts/release_smoke_test.py"] in plan

def test_pre_release_script_exists():
    script_path = Path("scripts/run_pre_release_checks.py")
    assert script_path.exists()

def test_phase9_release_helper_scripts_exist():
    assert Path("scripts/generate_release_manifest.py").exists()
    assert Path("scripts/generate_release_notes.py").exists()
    assert Path("scripts/verify_published_release.py").exists()
    assert Path("scripts/ship_checklist.py").exists()

def test_phase10_quality_gate_scripts_exist():
    assert Path("scripts/checks.sh").exists()
    assert Path("scripts/fix_indentation_and_conflicts.py").exists()


def test_checks_script_supports_ci_mode_flag():
    checks_script = Path("scripts/checks.sh")
    content = checks_script.read_text(encoding="utf-8")

    assert "--ci" in content
    assert "Usage: bash scripts/checks.sh [local|ci|--ci]" in content
