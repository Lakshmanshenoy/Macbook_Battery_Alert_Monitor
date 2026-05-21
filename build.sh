#!/bin/bash
# Build script for BattMon App

echo "🔨 Building BattMon macOS App..."
echo ""

# Activate local virtual environment when present; CI can use the runner's
# already-prepared Python environment instead.
if [ -d "venv" ]; then
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
else
    echo "ℹ️ No local virtual environment found. Using current Python environment."
fi

echo ""

# Create icon if it doesn't exist
if [ ! -f "BatteryAlert.icns" ]; then
    echo "🎨 Creating app icon..."
    python3 create_icon.py
    iconutil -c icns BatteryAlert.iconset -o BatteryAlert.icns
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist *.spec

# Build the app with custom icon
echo "📦 Creating macOS app bundle..."
export BATTERY_ALERT_BUILD=release
pyinstaller \
    --name "BattMon" \
    --windowed \
    --icon=BatteryAlert.icns \
    --osx-bundle-identifier="com.batteryalert.app" \
    --python-option=u \
    battery_alert_gui.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ App built successfully!"
    echo ""
    echo "📁 Location: $(pwd)/dist/BattMon.app"
    echo ""
    echo "Next steps:"
    echo "1. Copy 'BattMon.app' to your Applications folder"
    echo "2. Launch it like any other macOS app"
    echo ""
else
    echo "❌ Build failed. Check the error messages above."
    exit 1
fi
