import json
import subprocess
import sys
from pathlib import Path

from scripts.generate_release_manifest import build_release_manifest
from scripts.generate_release_notes import generate_release_notes


def test_build_release_manifest_matches_checksum(tmp_path):
    artifact = Path(tmp_path) / "BattMon.dmg"
    artifact.write_bytes(b"artifact-bytes")

    checksums = Path(tmp_path) / "checksums.txt"
    checksums.write_text(
        "3b1812672047ec0d1f0f8f1fc016c0fb4f1f1caf9cf8bb291c8ac62df13f2e05  BattMon.dmg\n",
        encoding="utf-8",
    )

    manifest = build_release_manifest(
        version="1.2.0",
        artifact_path=artifact,
        checksums_path=checksums,
        signing_status="optional",
        notarization_status="optional",
    )

    assert manifest["version"] == "1.2.0"
    assert manifest["artifact"]["name"] == "BattMon.dmg"
    assert manifest["artifact"]["expected_sha256"] is not None
    assert manifest["checksums_file"] == "checksums.txt"


def test_generate_release_notes_includes_heading(tmp_path):
    repo = Path(tmp_path) / "repo"
    repo.mkdir(parents=True, exist_ok=True)

    (repo / "README.md").write_text("demo\n", encoding="utf-8")

    import subprocess

    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "tester"], cwd=repo, check=True)
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo, check=True, capture_output=True)

    notes = generate_release_notes(repo, from_ref="", to_ref="HEAD")

    assert "## Release Notes" in notes
    assert "Initial commit" in notes


def test_release_manifest_serializes_to_json(tmp_path):
    artifact = Path(tmp_path) / "BattMon.dmg"
    artifact.write_bytes(b"artifact-bytes")
    checksums = Path(tmp_path) / "checksums.txt"
    checksums.write_text(
        "3b1812672047ec0d1f0f8f1fc016c0fb4f1f1caf9cf8bb291c8ac62df13f2e05  BattMon.dmg\n",
        encoding="utf-8",
    )

    manifest = build_release_manifest(
        version="1.2.0",
        artifact_path=artifact,
        checksums_path=checksums,
        signing_status="optional",
        notarization_status="optional",
    )

    encoded = json.dumps(manifest)
    assert '"version": "1.2.0"' in encoded


def test_generate_release_manifest_cli_runs_outside_repo_root(tmp_path):
    artifact = tmp_path / "BattMon.dmg"
    artifact.write_bytes(b"artifact-bytes")

    checksums = tmp_path / "checksums.txt"
    checksums.write_text(
        "3b1812672047ec0d1f0f8f1fc016c0fb4f1f1caf9cf8bb291c8ac62df13f2e05  BattMon.dmg\n",
        encoding="utf-8",
    )

    output = tmp_path / "release_manifest.json"
    script = Path(__file__).resolve().parents[1] / "scripts" / "generate_release_manifest.py"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--version",
            "1.2.0",
            "--artifact",
            str(artifact),
            "--checksums",
            str(checksums),
            "--signing-status",
            "optional",
            "--notarization-status",
            "optional",
            "--output",
            str(output),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["artifact"]["name"] == "BattMon.dmg"
    assert "Release manifest written to" in result.stdout
