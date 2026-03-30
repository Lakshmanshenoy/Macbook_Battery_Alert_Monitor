# Privacy Policy — Battery Alert Monitor

Short summary
- This app does not collect or transmit personal data by default.
- Local configuration (thresholds, alert history) is stored only on the user's machine in `~/.battery_alert/`.

Data minimization
- The app stores only the minimal state required to operate: `config.json` (settings) and `alert_history.json` (last 100 alerts). No network calls are made by default.

Opt-in features
- If you later add telemetry or crash reporting, make it explicit and opt-in. Document what is collected and provide a way to opt-out and to delete local data.

Telemetry
- No telemetry, analytics, or crash reporting is collected unless explicitly added and opt‑in is provided.

Permissions
- The app requests only the permissions required for local notifications and text‑to‑speech (system notifications and sound). If additional permissions are required by macOS, they will be requested at runtime with a clear explanation.

Data retention & deletion
- Alert history is kept locally and limited to the last 100 events. Users can delete the `~/.battery_alert/` folder to remove local data.

Contact
- For privacy questions or data removal requests, contact the maintainer via the repository issue tracker or the support contact in SUPPORT.md.
