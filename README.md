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
- Toggle sound, voice, and notifications independently
- Auto-launch at system startup
- Configuration automatically saved

🎯 **Professional Features**
- Runs in background after launching
- Real-time battery percentage in menu bar
- Detailed alert history
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

### Menu Options

- **Battery Threshold** - Set when to get alerts
- **Check Interval** - Configure how often to check battery
- **Sound Alerts** - Toggle sound notifications
- **Voice Alerts** - Toggle voice notifications
- **Notifications** - Toggle macOS notifications
- **Launch at Startup** - Enable auto-start
- **Check Status** - View current battery information
- **View Alert History** - See recent low battery alerts
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

## License

This project is open-source and available for personal use.

## Version History

**v1.0** (Current)
- Initial release with GUI
- Menu bar integration
- Interactive settings
- Alert history
- Auto-launch support
