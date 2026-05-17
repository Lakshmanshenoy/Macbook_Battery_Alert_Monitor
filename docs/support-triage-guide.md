# Support Triage Guide

Use this guide when a user shares diagnostics or a support bundle.

## Bundle contents

1. Read `diagnostics.txt` first for current settings, battery state, update status, and maintenance history.
2. Check `manifest.json` to confirm bundle schema version and included files.
3. Review `logs/battery_alert.log` for runtime warnings, update-check failures, or power-source transitions.
4. Review `crash_reports/latest_crash_report.json` when present for uncaught exception details.
5. If only metadata is needed, request a diagnostics-only support export to minimize shared files.

## Common patterns

1. Repeated low-battery complaints: compare battery threshold, cooldown, and alert-history timestamps.
2. Update-check complaints: inspect `Last update check`, `Last update result`, and `Latest known release` fields.
3. Runtime environment complaints: inspect diagnostics for missing tool markers (`say`, `afplay`, or notification support) and degraded status.
4. Startup/reset complaints: look for quarantined `.corrupt.*` files in the support folder.
5. Crash complaints: inspect `exception_type`, `exception_message`, and traceback frames in the crash report.

## Safe sharing

1. Diagnostics and crash reports redact home-directory paths, obvious usernames, and email addresses.
2. Users should still review the bundle before sharing externally.
3. If a user is uncomfortable sharing logs, ask for `diagnostics.txt` first and escalate only when needed.
