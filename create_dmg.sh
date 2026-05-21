#!/usr/bin/env bash
set -euo pipefail

echo "🖼️  Creating DMG installer..."

APP_NAME="Battery Alert"
APP_BUNDLE="dist/${APP_NAME}.app"
DMG_TEMP="dist/${APP_NAME}_temp.dmg"
DMG_FINAL_DIST="dist/${APP_NAME}.dmg"
DMG_FINAL_ROOT="${APP_NAME}.dmg"
BACKGROUND_SRC="assets/dmg_background@2x.png"
VOLUME_ICON="BatteryAlert.icns"
MOUNT_DIR="/tmp/battery_alert_dmg_mount"

[[ -d "$APP_BUNDLE" ]] || {
    echo "❌ Error: App not found at $APP_BUNDLE"
    echo "💡 Please run './build.sh' first"
    exit 1
}

[[ -f "$BACKGROUND_SRC" ]] || python3 assets/dmg_background.py

STAGING_DIR="$(mktemp -d)"
cleanup() {
    if mount | grep -q "on ${MOUNT_DIR} "; then
        hdiutil detach "$MOUNT_DIR" >/dev/null 2>&1 || true
    fi
    rm -rf "$MOUNT_DIR"
    rm -rf "$STAGING_DIR"
}
trap cleanup EXIT

while IFS= read -r existing_mount; do
    [[ -n "$existing_mount" ]] || continue
    hdiutil detach "$existing_mount" >/dev/null 2>&1 || true
done < <(hdiutil info | awk -v app="$APP_NAME" '$0 ~ "/Volumes/" app {print $NF}')

echo "→ Creating staging area..."
cp -R "$APP_BUNDLE" "$STAGING_DIR/"
mkdir -p "$STAGING_DIR/.background"
cp "$BACKGROUND_SRC" "$STAGING_DIR/.background/background.png"

echo "→ Creating writable DMG..."
rm -f "$DMG_TEMP" "$DMG_FINAL_DIST" "$DMG_FINAL_ROOT"
hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$STAGING_DIR" \
    -ov \
    -format UDRW \
    -size 200m \
    "$DMG_TEMP"

echo "→ Mounting DMG for layout..."
rm -rf "$MOUNT_DIR"
mkdir -p "$MOUNT_DIR"
hdiutil attach "$DMG_TEMP" -readwrite -noverify -noautoopen -mountpoint "$MOUNT_DIR" >/dev/null
BACKGROUND_FILE="$MOUNT_DIR/.background/background.png"

osascript <<APPLESCRIPT
tell application "Finder"
    set dmgFolder to folder (POSIX file "$MOUNT_DIR")
    tell dmgFolder
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set bounds of container window to {220, 140, 700, 440}
        delay 1

        set opts to icon view options of container window
        set arrangement of opts to not arranged
        set icon size of opts to 128
        set background picture of opts to POSIX file "$BACKGROUND_FILE"

        if exists alias file "Applications" then
            delete alias file "Applications"
            delay 0.2
        end if
        make new alias file at dmgFolder to POSIX file "/Applications"
        delay 1

        set position of application file "${APP_NAME}.app" of container window to {120, 150}
        set position of alias file "Applications" of container window to {360, 150}

        close
        open
        update without registering applications
        delay 2
        close
    end tell
end tell
APPLESCRIPT

echo "→ Setting volume icon..."
cp "$VOLUME_ICON" "$MOUNT_DIR/.VolumeIcon.icns"
SetFile -a C "$MOUNT_DIR" 2>/dev/null || true

echo "→ Finalising permissions..."
chmod -Rf go-w "$MOUNT_DIR"
sync

hdiutil detach "$MOUNT_DIR" >/dev/null || hdiutil detach -force "$MOUNT_DIR" >/dev/null

echo "→ Compressing to final DMG..."
hdiutil convert "$DMG_TEMP" -format UDZO -imagekey zlib-level=9 -o "$DMG_FINAL_DIST"
rm -f "$DMG_TEMP"
cp "$DMG_FINAL_DIST" "$DMG_FINAL_ROOT"

echo "✅ DMG ready: $DMG_FINAL_DIST"
echo "✅ Synced root copy: $DMG_FINAL_ROOT"
