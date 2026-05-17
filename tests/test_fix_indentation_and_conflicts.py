from pathlib import Path

from scripts.fix_indentation_and_conflicts import clean_merge_markers, fix_missing_block_after_defs, process_file


def test_clean_merge_markers_removes_only_marker_lines():
    lines = [
        "print('ok')\n",
        "<<<<<<< HEAD\n",
        "x = 1\n",
        "=======\n",
        "y = 2\n",
        ">>>>>>> branch\n",
    ]

    cleaned, removed = clean_merge_markers(lines)

    assert removed == 3
    assert cleaned == ["print('ok')\n", "x = 1\n", "y = 2\n"]


def test_fix_missing_block_after_defs_inserts_pass_for_empty_body():
    lines = [
        "def demo():\n",
        "print('after')\n",
    ]

    fixed, fixes = fix_missing_block_after_defs(lines)

    assert fixes == 1
    assert fixed == [
        "def demo():\n",
        "    pass\n",
        "print('after')\n",
    ]


def test_process_file_check_mode_reports_without_writing(tmp_path):
    target = Path(tmp_path) / "sample.py"
    target.write_text("def demo():\nprint('x')\n", encoding="utf-8")

    changed, fix_count = process_file(target, apply=False)

    assert changed is True
    assert fix_count == 1
    assert target.read_text(encoding="utf-8") == "def demo():\nprint('x')\n"


def test_process_file_apply_mode_writes_fixes(tmp_path):
    target = Path(tmp_path) / "sample.py"
    target.write_text("def demo():\nprint('x')\n", encoding="utf-8")

    changed, fix_count = process_file(target, apply=True)

    assert changed is True
    assert fix_count == 1
    assert target.read_text(encoding="utf-8") == "def demo():\n    pass\nprint('x')\n"
