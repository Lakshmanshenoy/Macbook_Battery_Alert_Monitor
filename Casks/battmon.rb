cask "battmon" do
  version "1.1.3"
  sha256 "REPLACE_WITH_SHA256_OF_DMG"

  url "https://github.com/Lakshmanshenoy/battmon-macos/releases/download/v#{version}/BattMon.dmg"
  name "BattMon"
  desc "Lightweight battery alert monitor for macOS"
  homepage "https://github.com/Lakshmanshenoy/battmon-macos"

  app "BattMon.app"

  zap trash: [
    "~/.battery_alert",
    "~/Library/LaunchAgents/com.shenoylabs.batteryalert.plist",
  ]
end