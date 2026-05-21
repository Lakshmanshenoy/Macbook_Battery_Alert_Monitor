from pathlib import Path

from scripts.verify_release_artifacts import compute_sha256, verify_artifact


def test_verify_artifact_passes_for_matching_checksum(tmp_path):
    artifact = Path(tmp_path) / "BattMon.dmg"
    artifact.write_bytes(b"demo artifact")

    digest = compute_sha256(artifact)
    checksums = Path(tmp_path) / "checksums.txt"
    checksums.write_text(f"{digest}  {artifact.name}\n", encoding="utf-8")

    ok, message = verify_artifact(artifact, checksums)

    assert ok is True
    assert "Checksum verified" in message


def test_verify_artifact_fails_for_mismatch(tmp_path):
    artifact = Path(tmp_path) / "BattMon.dmg"
    artifact.write_bytes(b"demo artifact")

    checksums = Path(tmp_path) / "checksums.txt"
    checksums.write_text(f"{'0' * 64}  {artifact.name}\n", encoding="utf-8")

    ok, message = verify_artifact(artifact, checksums)

    assert ok is False
    assert "Checksum mismatch" in message


def test_verify_artifact_passes_when_checksum_entry_uses_path(tmp_path):
    artifact = Path(tmp_path) / "BattMon.dmg"
    artifact.write_bytes(b"demo artifact")

    digest = compute_sha256(artifact)
    checksums = Path(tmp_path) / "checksums.txt"
    checksums.write_text(f"{digest}  tmp_release/{artifact.name}\n", encoding="utf-8")

    ok, message = verify_artifact(artifact, checksums)

    assert ok is True
    assert "Checksum verified" in message
