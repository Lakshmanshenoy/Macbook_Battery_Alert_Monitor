#!/bin/bash
# Build script for Battery Alert App

echo "🔨 Building Battery Alert macOS App..."
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Please run ./setup.sh first"
    exit 1
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
pyinstaller \
    --name "Battery Alert" \
    --windowed \
    --icon=BatteryAlert.icns \
    --osx-bundle-identifier="com.batteryalert.app" \
    --python-option=u \
    battery_alert_gui.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ App built successfully!"
    echo ""
    echo "📁 Location: $(pwd)/dist/Battery Alert.app"
    echo ""
    echo "Next steps:"
    echo "1. Copy 'Battery Alert.app' to your Applications folder"
    echo "2. Launch it like any other macOS app"
    echo ""
else
    echo "❌ Build failed. Check the error messages above."
    exit 1
fi
