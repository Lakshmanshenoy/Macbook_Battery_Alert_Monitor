#!/bin/bash
# Create DMG installer for Battery Alert

echo "🖼️  Creating DMG installer..."

APP_NAME="Battery Alert"
DIST_DIR="dist"
DMG_NAME="${APP_NAME}.dmg"
TEMP_DMG="/tmp/${APP_NAME}_temp.dmg"
MOUNT_POINT="/tmp/${APP_NAME}_mount"

# Check if app exists
if [ ! -d "${DIST_DIR}/${APP_NAME}.app" ]; then
    echo "❌ Error: App not found at ${DIST_DIR}/${APP_NAME}.app"
    echo "💡 Please run './build.sh' first"
    exit 1
fi

# Clean old DMG
rm -f "${DMG_NAME}" "${TEMP_DMG}"

# Create temporary DMG
hdiutil create -volname "${APP_NAME}" -srcfolder "${DIST_DIR}/${APP_NAME}.app" -ov -format UDZO -imagekey zlib-level=9 "${TEMP_DMG}"

# Move to current directory
mv "${TEMP_DMG}" "${DMG_NAME}"

echo ""
echo "✅ DMG created successfully!"
echo "📁 Location: $(pwd)/${DMG_NAME}"
echo ""
echo "📤 Now you can share this DMG file with others!"
echo "📥 Users can double-click to mount, then drag Battery Alert.app to Applications"
echo ""
