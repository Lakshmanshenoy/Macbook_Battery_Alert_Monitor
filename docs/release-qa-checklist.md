# Release QA Checklist

Use this checklist before cutting a tagged release for Battery Alert Monitor.

## Local Validation

- Run the full test suite with `pytest -q`.
- Run the release smoke check script.
- Run `python3 scripts/run_pre_release_checks.py`.
- Run `python3 scripts/ship_checklist.py --version X.Y.Z --skip-checks` to validate maintainer guidance output.
- Run `python3 scripts/verify_release_artifacts.py --artifact <artifact> --checksums checksums.txt` against a generated artifact/checksum pair.
- Confirm `setup.sh` is executable and completes on a clean checkout.

## App Behavior

- Launch the app and confirm the menu bar icon appears.
- Open `Version & Updates` and confirm it shows current version, channel, and last update state.
- Trigger `Check for Updates` and confirm it shows non-blocking feedback.
- Trigger `Export Support Bundle` and confirm the archive is created and Finder reveals it.
- Confirm `Show Preferences`, `Copy Diagnostics`, and `Open Config Folder` all respond.


## Packaging

- Build the app bundle with `bash build.sh`.
- Build the DMG with `bash create_dmg.sh`.
- Run the release workflow via `workflow_dispatch` as a dry run and confirm artifacts are uploaded.
- Confirm `release_manifest.json` is generated in release artifacts.
- If signing secrets are configured, confirm codesign and notarization steps succeed.


## Release Artifacts

- Confirm the release notes are up to date.
- Confirm the DMG, checksums, and signing artifacts are attached to the release.
- Confirm `release_manifest.json` is attached to the release.
- Confirm the release workflow has no failed jobs.
- Confirm `Post Release Verification` workflow succeeds for the published tag.
- Confirm CI workflow lint (`actionlint`) passes for workflow syntax/semantics.
- Confirm CI verifies the downloaded workflow artifact, not just the locally generated file.

## Support Readiness

- Export a support bundle and verify it contains diagnostics, config, alert history, logs, `manifest.json`, and `safe_share_guide.txt`.
- If a crash report exists, verify the bundle includes `crash_reports/latest_crash_report.json`.
- Confirm the runtime log rotates under `~/.battery_alert/logs/`.