# Release Runbook

Use this runbook when preparing a Battery Alert Monitor release.

## Local preparation

1. Ensure the working tree is clean.
2. Run `bash scripts/checks.sh` as the primary local quality gate.
3. Optionally run `bash scripts/checks.sh --ci` to emulate non-mutating CI behavior.
4. Run `python3 scripts/run_pre_release_checks.py`.
5. Run `python3 scripts/generate_release_notes.py --to-ref HEAD` and review generated notes.
6. Run `python3 scripts/ship_checklist.py --version X.Y.Z --skip-checks` for final ship guidance.
7. Run `bash build.sh` and `bash create_dmg.sh` if you want a local packaging sanity check before tagging.
8. Confirm `RELEASE_DRAFT.md` is up to date.
9. Verify support export contains rotated runtime logs when present (`logs/battery_alert.log.*`).

## Dry run

1. Trigger the release workflow with `workflow_dispatch`.
2. Confirm build, checksum generation, artifact upload, and verification steps all pass.
3. Confirm `release_manifest.json` is generated and uploaded with release artifacts.
4. Download the uploaded workflow artifact and inspect `Battery Alert.dmg`, `checksums.txt`, and signing outputs.

## Tagged release

1. Create and push a tag in the form `vX.Y.Z`.
2. Watch the release workflow for build, signing, notarization, checksum, and upload steps.
3. Confirm the published GitHub release contains the DMG, checksums, signature, maintainer public key, and `release_manifest.json`.
4. Confirm the post-release verification workflow passes for the published tag.
5. Optionally run `python3 scripts/verify_published_release.py --owner <owner> --repo <repo> --tag vX.Y.Z --token <token>` locally.

## Rollback

1. If the workflow fails before publish, fix the branch and rerun the dry run.
2. If a bad release is published, delete the GitHub release, delete the tag, and cut a replacement tag after fixing the issue.
3. If signing or notarization breaks, ship an unsigned dry-run artifact only for internal validation until secrets are corrected.
