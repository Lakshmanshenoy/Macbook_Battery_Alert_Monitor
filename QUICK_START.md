## 🚀 Quick Start Guide - Battery Alert GUI App

### For Users: Installation & Usage

#### Step 1: Download & Install
1. Get `Battery Alert.dmg` (once built)
2. Double-click to mount the DMG
3. Drag **Battery Alert.app** to Applications
4. Eject the DMG
5. Open Applications and launch **Battery Alert**

#### Step 2: First Launch
- The app will appear as a 🔋 icon in your menu bar
- Click the icon to see menu options
- Your battery percentage is shown in real-time

#### Step 3: Configure Settings
1. Click menu bar icon to open menu
2. Adjust settings:
   - **Battery Threshold**: When to get alerts (default: 20%)
   - **Check Interval**: How often to check (default: 10 seconds)
   - **Sound/Voice/Notifications**: Toggle each independently
   - **Launch at Startup**: Enable auto-launch if desired
3. Settings save automatically

That's it! The app runs in the background automatically.

---

### For Developers: Building from Source

#### Prerequisites
```bash
# Check Python version
python3 --version  # Should be 3.8 or higher
```

#### Build Steps

**1. Setup Environment (First Time Only)**
```bash
cd /Users/lakshmanshenoy/Mac_Projects/Battery_Low_Alert
bash setup.sh
```

This will:
- ✅ Create virtual environment (venv/)
- ✅ Install dependencies (rumps 0.4.0, pyinstaller 6.19.0)
- ✅ Verify Python 3.14 installation

**2. Test the App (Optional)**
```bash
source venv/bin/activate
python3 battery_alert_gui.py
# Ctrl+C to quit
deactivate
```

**3. Build the App Bundle**
```bash
bash build.sh
```

This will:
- ✅ Clean previous builds
- ✅ Generate icon from BatteryAlert.iconset/
- ✅ Run PyInstaller with custom icon
- ✅ Create `dist/Battery Alert.app`

**4. Create DMG for Distribution (Optional)**
```bash
bash create_dmg.sh
```

Creates: `Battery Alert.dmg` (9.8 MB)
- Ready for user distribution
- Includes proper app icon
- Simple drag-to-Applications installation

#### After Building

**For personal use:**
```bash
# Copy to Applications
cp -r dist/Battery\ Alert.app /Applications/
# Or: Drag Battery Alert.app to Applications folder
```

**For distribution:**
- Share the `Battery Alert.dmg` file
- Users just need to download, mount, and drag to Applications

---

### File Structure

```
Battery_Low_Alert/
├── 📄 battery_alert_gui.py       # Main app (GUI logic)
├── 📋 low_battery_alert.sh        # Legacy shell script
├── 📦 requirements.txt            # Python dependencies
├── 🚀 setup.sh                    # Setup script
├── 🔨 build.sh                    # Build app
├── 💿 create_dmg.sh              # Create DMG
├── 📖 README.md                  # Original README
├── 📖 README_GUI.md              # GUI App README
└── 📝 QUICK_START.md            # This file
```

---

### Troubleshooting Build Issues

**Error: "PyInstaller not found"**
```bash
./setup.sh  # Run setup again
```

**Error: "Permission denied" on scripts**
```bash
chmod +x setup.sh build.sh create_dmg.sh
```

**Python 3 not found**
```bash
# Install Python from https://www.python.org/downloads/
# Or use Homebrew:
brew install python3
```

**Build successful but app won't launch**
```bash
# Check permissions
xattr -d com.apple.quarantine dist/Battery\ Alert.app

# Or run directly:
dist/Battery\ Alert.app/Contents/MacOS/Battery\ Alert
```

---

### What Gets Created

**virtual environment/** (venv)
- Isolated Python environment
- Contains rumps and pyinstaller

**build/** and **dist/**
- build/ - Temporary build files
- dist/ - Final app bundle
  - `Battery Alert.app` ← This is what you use!

**Battery Alert.dmg** (after create_dmg.sh)
- Installer file for distribution
- Users double-click to install

---

### Next Steps

1. ✅ Run `./setup.sh` to install dependencies
2. ✅ Run `./build.sh` to create the app
3. ✅ Test it: Open `dist/Battery Alert.app`
4. ✅ (Optional) Run `./create_dmg.sh` to make an installer
5. ✅ Share the `.dmg` or `.app` with friends!

---

### Features Recap

✅ Menu bar icon with battery %  
✅ Beautiful settings window  
✅ Customizable alerts (sound, voice, notifications)  
✅ Auto-launch at startup  
✅ Alert history log  
✅ Saves preferences automatically  
✅ Lightweight & efficient  
✅ Professional macOS integration
