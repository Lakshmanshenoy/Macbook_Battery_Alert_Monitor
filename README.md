# 🔋 BattMon

Lightweight battery alert monitor for macOS.

[![Semantic Release](https://github.com/Lakshmanshenoy/battmon-macos/actions/workflows/semantic-release.yml/badge.svg?branch=main)](https://github.com/Lakshmanshenoy/battmon-macos/actions/workflows/semantic-release.yml)
[![Semantic Release Dry Run](https://github.com/Lakshmanshenoy/battmon-macos/actions/workflows/semantic-release-dry-run.yml/badge.svg?branch=main)](https://github.com/Lakshmanshenoy/battmon-macos/actions/workflows/semantic-release-dry-run.yml)
[![Commit Message Lint](https://github.com/Lakshmanshenoy/battmon-macos/actions/workflows/commitlint.yml/badge.svg?branch=main)](https://github.com/Lakshmanshenoy/battmon-macos/actions/workflows/commitlint.yml)

Lightweight battery alert monitor for macOS. Get alerts when your battery is running low, with real-time status updates and configurable settings.

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

1. Download `BattMon.dmg`
2. Open the DMG file
3. Drag **BattMon.app** to your **Applications** folder
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

The built app will be in `dist/BattMon.app`

## Usage

### Getting Started

1. Launch **BattMon** from Applications
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
- **Update Channel** - Switch between stable and beta release checks
- **Download Latest Release** - Open the last known release URL directly
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

- Use **Version & Updates** to inspect the last check time and latest known release without starting a new network request.
- Use **Update Channel** to toggle between stable and beta checks.
- Use **Download Latest Release** to open the latest known release directly in your browser.
- Use **Run Release Check** to run the release smoke test from inside the app.
- Use **Export Support Bundle** and choose **Diagnostics only** when support only needs lightweight metadata.
- The release smoke test script is still available directly at `python3 scripts/release_smoke_test.py`.
- Run `python3 scripts/run_pre_release_checks.py` for a one-command local pre-release validation pass.
- Generate release metadata with `python3 scripts/generate_release_manifest.py --help`.
- Generate release-note drafts with `python3 scripts/generate_release_notes.py --help`.
- Run the compact ship checklist with `python3 scripts/ship_checklist.py --version X.Y.Z`.
- Verify published GitHub release assets with `python3 scripts/verify_published_release.py --help`.

## Release Signing (Optional)

The release workflow supports optional code signing and notarization. Without these secrets the workflow still produces unsigned artifacts.

Add these repository secrets to enable **signing**:
- `MACOS_SIGNING_CERT_BASE64` — Base64-encoded `.p12` Developer ID certificate
- `MACOS_SIGNING_CERT_PASSWORD` — Password for the `.p12` certificate
- `MACOS_SIGNING_IDENTITY` — Codesign identity (e.g. `Developer ID Application: Your Name (TEAMID)`)

Add these secrets to enable **notarization**:
- `APPLE_ID`
- `APPLE_APP_SPECIFIC_PASSWORD`
- `APPLE_TEAM_ID`

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
- Check macOS notifications settings for BattMon
- System Preferences > Notifications > BattMon

**Sound alerts not playing?**
- Check volume settings
- Verify "Sound Alerts" is enabled in settings

**Auto-launch not working?**
- Try enabling it again in settings
- Restart your Mac

## Uninstallation

1. Drag **BattMon** from Applications to Trash
2. Empty Trash
3. (Optional) Delete `~/.battery_alert/` folder to remove saved settings

## Development

### Project Structure

```
battmon-macos/
├── battery_alert_gui.py          # Entry point shim
├── src/
│   └── battery_alert/
│       ├── __init__.py
│       ├── constants.py          # App-wide constants and paths
│       ├── battery.py            # pmset polling with TTL caching
│       ├── config.py             # JSON persistence and migration
│       ├── alerts.py             # Alert decision and firing logic
│       ├── updater.py            # GitHub release update checks
│       ├── diagnostics.py        # Crash reports and support bundles
│       └── app.py                # rumps orchestration layer
├── tests/                        # pytest test suite
├── scripts/                      # Maintainer and release scripts
├── requirements.txt              # Python dependencies
├── pyproject.toml                # Build metadata and tool config
├── setup.sh                      # Dev environment setup
├── build.sh                      # PyInstaller build script
└── create_dmg.sh                 # DMG creation script
```

### Building a Newer Version

1. Make changes in `src/battery_alert/`
2. Run `bash build.sh` to create new app bundle
3. Optionally run `bash create_dmg.sh` for distribution

## Support

For issues or feature requests, please check:
- Configuration files in `~/.battery_alert/`
- Runtime logs in `~/.battery_alert/logs/battery_alert.log`
- Use **Export Support Bundle** from the menu bar to create a shareable diagnostics zip

## Release Validation

Before cutting a tagged release, run:
- `bash scripts/checks.sh`
- `bash scripts/checks.sh --ci` (optional preview of CI behavior)
- `pytest -q`
- `python3 scripts/release_smoke_test.py`
- `python3 scripts/run_pre_release_checks.py`

The manual release checklist lives in [docs/release-qa-checklist.md](docs/release-qa-checklist.md).
The step-by-step maintainer flow lives in [docs/release-runbook.md](docs/release-runbook.md).
The support-handling guide lives in [docs/support-triage-guide.md](docs/support-triage-guide.md).

## License

MIT License - see [LICENSE](./LICENSE).

## Version History

**v1.1.0** (Current)
- Modular package: logic split into `src/battery_alert/` (battery, config, alerts, updater, diagnostics)
- MIT License added
- Automated semantic versioning via Conventional Commits
- Structured crash reports and rotating runtime logs
- Stable/beta update channels
- One-click support bundle export with redaction
- Fixed `is_charging` false-positive when battery is discharging

**v1.0.0**
- Initial release
- Menu bar integration with live battery percentage
- Sound, voice, and macOS notification alerts
- Configurable threshold, interval, and cooldown
- Alert history and auto-launch support
