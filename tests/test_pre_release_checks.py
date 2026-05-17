from pathlib import Path

from scripts.run_pre_release_checks import build_command_plan


def test_build_command_plan_includes_core_release_checks():
    plan = build_command_plan()

    assert ["pytest", "-q"] in plan
    assert ["python3", "scripts/release_smoke_test.py"] in plan


def test_pre_release_script_exists():
    script_path = Path("scripts/run_pre_release_checks.py")

    assert script_path.exists()
