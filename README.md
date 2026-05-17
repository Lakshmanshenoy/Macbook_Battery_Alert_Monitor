# 🔋 Battery Alert Monitor for Macbook

A professional, user-friendly battery monitoring application for macOS. Get alerts when your battery is running low, with real-time status updates and comprehensive settings.

## Features

✨ **User-Friendly Interface**
- Native macOS menu bar icon showing current battery percentage
- Beautiful, intuitive settings window
- System-integrated notifications

🔔 **Smart Alerts**
- Sound alerts when battery drops below threshold
- Voice notifications (customizable)
- Desktop notifications
- Alert history log

⚙️ **Customizable Settings**
- Adjustable battery threshold (1-100%)
- Configurable check interval
- Configurable alert cooldown
- Toggle sound, voice, and notifications independently
- Auto-launch at system startup
- Configuration automatically saved

🎯 **Professional Features**
- Runs in background after launching
- Real-time battery percentage in menu bar
- Detailed alert history
- Built-in diagnostics copy and config-folder access
- One-click support bundle export (diagnostics + logs + config)
- Structured crash reports for uncaught runtime failures
- Rotating runtime logs for easier troubleshooting
- Manual test alert for validating notifications
- In-app update check against latest GitHub release
- In-app version and update visibility panel
- One-click access to the GitHub releases page
- Lightweight and efficient
- No additional dependencies for end-users

## Installation

### For Users (Easiest Way)

1. Download `Battery Alert.dmg`
2. Open the DMG file
3. Drag **Battery Alert.app** to your **Applications** folder
4. Done! Launch from Applications folder

### For Developers

#### Prerequisites
- macOS 10.13+
- Python 3.8+ (if building from source)
- 50MB free disk space

#### Build from Source

1. **Setup the project:**
   ```bash
   bash setup.sh
   ```

2. **Test the app (optional):**
   ```bash
   source venv/bin/activate
   python3 battery_alert_gui.py
   ```

3. **Build the macOS app:**
   ```bash
   bash build.sh
   ```

4. **Create DMG installer (optional):**
   ```bash
   bash create_dmg.sh
   ```

The built app will be in `dist/Battery Alert.app`

## Usage

### Getting Started

1. Launch **Battery Alert** from Applications
2. The app will appear in your menu bar (🔋 icon)
3. Click the icon to access the menu

On first launch, the app shows a short onboarding tip and keeps a persistent record so it only appears once.

### Menu Options

- **Battery Threshold** - Set when to get alerts
- **Check Interval** - Configure how often to check battery
- **Alert Cooldown** - Control how often repeated alerts can fire
- **Show Preferences** - Review all active settings in one place
- **Sound Alerts** - Toggle sound notifications
- **Voice Alerts** - Toggle voice notifications
- **Notifications** - Toggle macOS notifications
- **Launch at Startup** - Enable auto-start
- **Check Status** - View current battery information
- **Version & Updates** - View app version, update channel, and latest known release state
- **Test Alert Now** - Send a manual test notification
- **View Alert History** - See recent low battery alerts
- **Copy Diagnostics** - Copy support-friendly diagnostics to the clipboard
- **Export Support Bundle** - Create a zipped bundle for issue reporting
- **Check for Updates** - Check latest release availability
<<<<<<< HEAD
- **Update Channel** - Switch between stable and beta release checks
- **Download Latest Release** - Open the last known release URL directly
=======
>>>>>>> origin/main
- **Open Releases Page** - Open the project releases page in your browser
- **Run Release Check** - Run the release smoke test in the background
- **Open Config Folder** - Open the settings folder in Finder
- **About** - App information
- **Quit** - Close the application

### Settings

**Battery Threshold**
- Battery level that triggers alerts
- Default: **20%**
- Adjustable: 1-100%
- Example: Set to 30% to get alerts when battery reaches 30%

**Check Interval**
- How often to check battery level
- Default: **10 seconds**
- Adjustable: 10-3600 seconds (10s to 1 hour)
- Lower = more responsive, slightly more battery usage
- Higher = saves battery, less responsive

**Alert Cooldown**
- Minimum time between repeated low-battery alerts while still below threshold
- Default: **900 seconds**
- Adjustable: 30-86400 seconds
- Helps reduce alert spam during extended low-battery sessions

**Alert Types**
- 🔊 Sound Alerts - Play a sound when alert triggers
- 🎤 Voice Alerts - Get a voice notification
- 🔔 Notifications - Show macOS notification

**Auto-Launch**
- 🚀 Launch at Startup - Automatically start with your Mac

### Menu Bar Icon

The icon dynamically changes to show battery status:
- 🔌 Charging
- 🔋 Battery good (>50%)
- 🪫 Battery medium (20-50%)
- ⚠️ Battery low (<20%)

## Configuration Files

Settings are stored in `~/.battery_alert/` directory:
- `config.json` - Your preferences
- `alert_history.json` - Log of recent alerts
- `app.pid` - Process ID file
- `logs/battery_alert.log` - Rotating runtime log file
- `support_bundle_*.zip` - Exported troubleshooting bundles

Support actions in the menu can also copy a diagnostics snapshot and open this folder directly.

## Maintenance

- Use **Getting Started** if you want to reopen the onboarding tips.
- Use **Version & Updates** to inspect the last check time and latest known release without starting a new network request.
<<<<<<< HEAD
- Use **Update Channel** to toggle between stable and beta checks.
- Use **Download Latest Release** to open the latest known release directly in your browser.
=======
>>>>>>> origin/main
- Use **Run Release Check** to run the release smoke test from inside the app.
- Use **Export Support Bundle** and choose **Diagnostics only** when support only needs lightweight metadata.
- The release smoke test script is still available directly at `python3 scripts/release_smoke_test.py`.
- Run `python3 scripts/run_pre_release_checks.py` for a one-command local pre-release validation pass.
<<<<<<< HEAD
- Generate release metadata with `python3 scripts/generate_release_manifest.py --help`.
- Generate release-note drafts with `python3 scripts/generate_release_notes.py --help`.
- Run the compact ship checklist with `python3 scripts/ship_checklist.py --version X.Y.Z`.
- Verify published GitHub release assets with `python3 scripts/verify_published_release.py --help`.
=======
>>>>>>> origin/main

## Release Security (Phase 3)

The release workflow now supports optional signing and notarization for macOS artifacts.

Add these repository secrets to enable signed releases:
- `MACOS_SIGNING_CERT_BASE64` - Base64-encoded `.p12` Developer ID certificate
- `MACOS_SIGNING_CERT_PASSWORD` - Password for the `.p12` certificate
- `MACOS_SIGNING_IDENTITY` - Codesign identity (for example: `Developer ID Application: Your Name (TEAMID)`)

Add these repository secrets to enable notarization:
- `APPLE_ID`
- `APPLE_APP_SPECIFIC_PASSWORD`
- `APPLE_TEAM_ID`

If these secrets are not set, the workflow still produces unsigned release artifacts.

## Reliability Hardening (Phase 6)

- Config and app-state payloads now include schema versions and migration defaults.
- Support bundles include `manifest.json` and `safe_share_guide.txt`.
- Diagnostics in support bundles redact your home-directory path (`/Users/...` -> `~`).
- The release workflow supports `workflow_dispatch` dry runs that build and verify artifacts without publishing a GitHub release.

## Validation and Support Polish (Phase 7)

- Startup now recovers from corrupted config, app-state, alert-history, and update-state JSON files by quarantining unreadable files and restoring safe defaults.
- Support diagnostics redaction now also masks email addresses and obvious username markers.
- Diagnostics now include `Last update check` and `Last support bundle export` timestamps.
- CI now lints GitHub workflows with `actionlint` before running tests.
- CI and release workflows both exercise `scripts/verify_release_artifacts.py` for post-build artifact integrity checks.

## Distribution and Observability (Phase 8)

- The app now stores structured crash reports for uncaught exceptions under `~/.battery_alert/crash_reports/`.
- Support bundles include the latest crash report when one is available.
- The menu now includes **Version & Updates** and **Open Releases Page** for clearer self-service update handling.
- `View System Status` now includes power-source transition history, support export counts, and tracked update state.
- CI now verifies an uploaded/downloaded artifact pair instead of only checking a locally generated file.
- Maintainers can run `python3 scripts/run_pre_release_checks.py` to execute the pre-release validation sequence locally.

<<<<<<< HEAD
## Release Trust and Maintainability (Phase 9)

- Update checks now support stable/beta channels and track the latest known release URL for direct downloads.
- Support export now supports a diagnostics-only preset and retention cleanup for old bundles/reports.
- Runtime dependency health is tracked so maintainers can quickly identify degraded environments.
- Release workflow now publishes `release_manifest.json` alongside checksum artifacts.
- A post-release verification workflow validates published release assets from GitHub Releases.
- New maintainer scripts are available for release manifest generation, release note drafting, ship checklist execution, and published-asset verification.

=======
>>>>>>> origin/main
## System Requirements

- **OS:** macOS 10.13 or later
- **Processor:** Intel or Apple Silicon (M1/M2/M3)
- **RAM:** 50MB minimum
- **Disk Space:** 100MB for installation

## Troubleshooting

**App won't launch?**
- Try restarting your Mac
- Check System Preferences > Security & Privacy > General

**Notifications not appearing?**
- Check macOS notifications settings for Battery Alert
- System Preferences > Notifications > Battery Alert

**Sound alerts not playing?**
- Check volume settings
- Verify "Sound Alerts" is enabled in settings

**Auto-launch not working?**
- Try enabling it again in settings
- Restart your Mac

## Uninstallation

1. Drag **Battery Alert** from Applications to Trash
2. Empty Trash
3. (Optional) Delete `~/.battery_alert/` folder to remove saved settings

## Development

### Project Structure

```
Battery_Low_Alert/
├── battery_alert_gui.py      # Main application (~450 lines)
├── requirements.txt          # Python dependencies
├── setup.sh                  # Setup script
├── build.sh                  # Build script
├── create_dmg.sh             # DMG creation script
├── BatteryAlert.icns         # Custom app icon
├── BatteryAlert.iconset/     # Icon source files
└── dist/                     # Built application output
```

### Building a Newer Version

1. Update `battery_alert_gui.py` with changes
2. Run `bash build.sh` to create new app bundle
3. Optionally run `bash create_dmg.sh` for distribution

## Support

For issues or feature requests, please check:
- Configuration files in `~/.battery_alert/`
- Console messages in `/tmp/battery_alert.log`

## Release Validation

Before cutting a tagged release, run:
- `pytest -q`
- `python3 scripts/release_smoke_test.py`
- `python3 scripts/run_pre_release_checks.py`

The manual release checklist lives in [docs/release-qa-checklist.md](docs/release-qa-checklist.md).
The step-by-step maintainer flow lives in [docs/release-runbook.md](docs/release-runbook.md).
The support-handling guide lives in [docs/support-triage-guide.md](docs/support-triage-guide.md).

## License

This project is open-source and available for personal use.

## Version History

**v1.0.0** (Current)
- Initial release with GUI
- Menu bar integration
- Interactive settings
- Alert history
- Auto-launch support
