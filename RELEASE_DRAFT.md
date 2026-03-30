# Battery Alert Monitor — v1.0.0

Never lose work to an unexpected MacBook shutdown again!

Battery Alert Monitor is a lightweight, open-source macOS menu-bar app that watches your battery in real time and alerts you — with sound, voice, and notifications — before it runs out.

---

## What's new in v1.0.0

- Real-time battery monitoring (configurable interval, default 10 s)
- Dynamic menu-bar icon (🔌🔋🪫⚠️)
- Sound, voice, and macOS notification alerts — all independently togglable
- Configurable alert threshold (default 20%)
- Auto-launch at login via LaunchAgent
- Alert history (last 100 events)
- Full open-source release with reproducible builds

---

## Install (easy — download DMG)

1. Download `Battery Alert.dmg` from this release
2. Double-click to mount
3. Drag **Battery Alert.app** to your **Applications** folder
4. Eject the DMG
5. Launch **Battery Alert** from Applications

> macOS may show a security warning because this app is not notarized by Apple.
> To open: **Right-click → Open → Open** (or System Settings → Privacy & Security → Open Anyway).
> This is expected for open-source apps not enrolled in Apple's paid Developer Program.

---

## Install (from source — advanced)

See [BUILD_FROM_SOURCE.md](BUILD_FROM_SOURCE.md) for full instructions:

```bash
git clone https://github.com/Lakshmanshenoy/Macbook_Battery_Alert_Monitor.git
cd Macbook_Battery_Alert_Monitor
bash setup.sh
bash build.sh
```

---

## Verify this release (recommended)

### 1. Check SHA256 checksum

```bash
shasum -a 256 "Battery Alert.dmg"
```

Compare output with the value inside `checksums.txt` attached to this release.

### 2. Verify GPG signature (optional but recommended)

Import the maintainer's public key (one-time):

```bash
gpg --import maintainer_public_key.asc
```

Verify the checksum file signature:

```bash
gpg --verify checksums.txt.asc checksums.txt
```

Expected: `Good signature from "..."`. See [GPG_GUIDE.md](GPG_GUIDE.md) for detailed steps.

---

## Release artifacts

| File | Description |
|---|---|
| `Battery Alert.dmg` | Unsigned macOS installer |
| `checksums.txt` | SHA256 checksums |
| `checksums.txt.asc` | GPG signature of checksums |
| `maintainer_public_key.asc` | Maintainer GPG public key |

---

## Known limitations

- Not notarized (Apple Developer membership not required for open-source use). macOS Gatekeeper will show a warning — see install instructions above.
- Alert history is limited to 100 entries to avoid excessive disk use.

---

## Privacy

This app stores data only locally in `~/.battery_alert/`. No telemetry, no network calls. See [PRIVACY.md](PRIVACY.md).

---

## Questions or issues?

Open an issue or see [SUPPORT.md](SUPPORT.md).

