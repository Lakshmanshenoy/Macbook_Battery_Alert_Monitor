# Release Runbook

Use this runbook when preparing a Battery Alert Monitor release.

## Local preparation

1. Ensure the working tree is clean.
2. Run `python3 scripts/run_pre_release_checks.py`.
3. Run `bash build.sh` and `bash create_dmg.sh` if you want a local packaging sanity check before tagging.
4. Confirm `RELEASE_DRAFT.md` is up to date.

## Dry run

1. Trigger the release workflow with `workflow_dispatch`.
2. Confirm build, checksum generation, artifact upload, and verification steps all pass.
3. Download the uploaded workflow artifact and inspect `Battery Alert.dmg`, `checksums.txt`, and signing outputs.

## Tagged release

1. Create and push a tag in the form `vX.Y.Z`.
2. Watch the release workflow for build, signing, notarization, checksum, and upload steps.
3. Confirm the published GitHub release contains the DMG, checksums, signature, and maintainer public key.

## Rollback

1. If the workflow fails before publish, fix the branch and rerun the dry run.
2. If a bad release is published, delete the GitHub release, delete the tag, and cut a replacement tag after fixing the issue.
3. If signing or notarization breaks, ship an unsigned dry-run artifact only for internal validation until secrets are corrected.
