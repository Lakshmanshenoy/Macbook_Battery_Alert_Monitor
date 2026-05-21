cask "battery-alert" do
  version "1.1.0"
  sha256 "REPLACE_WITH_SHA256_OF_DMG"

  url "https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor/releases/download/v#{version}/Battery.Alert.dmg"
  name "Battery Alert Monitor"
  desc "Menu bar battery monitoring app for macOS"
  homepage "https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor"

  app "Battery Alert.app"

  zap trash: [
    "~/.battery_alert",
    "~/Library/LaunchAgents/com.shenoylabs.batteryalert.plist",
  ]
end
