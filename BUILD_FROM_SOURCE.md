# Build Battery Alert Monitor from Source

No Apple Developer account required. These steps produce a runnable app and distributable DMG from source code.

## Requirements
- macOS 10.13 or later
- Python 3.8+ (`python3 --version`)
- ~200 MB free disk space for venv + build artifacts

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor.git
cd Macbook_Battery_Alert_Monitor
```

## Step 2 — Set up the environment (one-time)

```bash
bash setup.sh
```

This creates a Python virtual environment in `venv/` and installs all dependencies.

## Step 3 — Run without building (optional quick test)

```bash
source venv/bin/activate
python3 battery_alert_gui.py
# Ctrl+C to quit
deactivate
```

## Step 4 — Build the macOS app bundle

```bash
bash build.sh
```

This runs the following PyInstaller command under the hood (reproducible):

```bash
pyinstaller \
    --name "Battery Alert" \
    --windowed \
    --icon=BatteryAlert.icns \
    --osx-bundle-identifier="com.batteryalert.app" \
    --python-option=u \
    battery_alert_gui.py
```

Output: `dist/Battery Alert.app`

## Step 5 — Create DMG installer (optional, for sharing)

```bash
bash create_dmg.sh
```

Output: `Battery Alert.dmg` (~10 MB)

---

## Verify your build matches the official release

Generate a SHA256 checksum of your locally built DMG and compare it to the value published in [GitHub Releases](https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/releases):

```bash
shasum -a 256 "Battery Alert.dmg"
```

If the checksums match, your build is byte-for-byte identical to the official one.

---

## Open an unsigned app on macOS

macOS shows a warning for apps that are not notarized. To open anyway:

1. Right-click `Battery Alert.app` → **Open**
2. Click **Open** in the security dialog

Or via System Settings → Privacy & Security → scroll to the blocked app → **Open Anyway**

Or via terminal:

```bash
xattr -dr com.apple.quarantine "/Applications/Battery Alert.app"
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `venv not found` | Run `bash setup.sh` first |
| PyInstaller error | Make sure venv is active: `source venv/bin/activate` |
| App won't open (unsigned warning) | Follow the "Open an unsigned app" steps above |
| Import error at runtime | Verify Python ≥ 3.8 and all dependencies installed |
