import json
import subprocess
import sys
import urllib.request
from pathlib import Path

from scripts.dispatch_release_build import dispatch_workflow, parse_repository
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


def test_parse_repository_rejects_invalid_value():
    try:
        parse_repository("invalid-repo")
    except ValueError as exc:
        assert "Invalid GitHub repository" in str(exc)
    else:
        raise AssertionError("Expected parse_repository to reject invalid owner/repo input")


def test_dispatch_workflow_posts_workflow_dispatch(monkeypatch):
    captured: dict[str, object] = {}

    class FakeResponse:
        status = 204

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

    def fake_urlopen(request: urllib.request.Request, timeout: int) -> FakeResponse:
        captured["url"] = request.full_url
        captured["data"] = request.data
        captured["method"] = request.get_method()
        captured["timeout"] = timeout
        captured["headers"] = {key.lower(): value for key, value in request.header_items()}
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    dispatch_workflow(
        owner="Lakshmanshenoy",
        repo="battmon-macos",
        workflow="release.yml",
        ref="main",
        token="test-token",
        inputs={"tag_name": "v1.2.6"},
    )

    assert captured["url"] == (
        "https://api.github.com/repos/Lakshmanshenoy/battmon-macos/"
        "actions/workflows/release.yml/dispatches"
    )
    assert json.loads(captured["data"].decode("utf-8")) == {
        "ref": "main",
        "inputs": {"tag_name": "v1.2.6"},
    }
    assert captured["method"] == "POST"
    assert captured["timeout"] == 30
    assert captured["headers"]["authorization"] == "Bearer test-token"
