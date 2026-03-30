# GPG Signing Guide

This explains how to create a GPG key, sign release artifacts, and allow users to verify them.

---

## One-time setup (maintainer)

### 1. Install GPG

```bash
brew install gnupg
```

### 2. Create a GPG key (one-time)

```bash
gpg --full-generate-key
```

- Key type: RSA and RSA (default)
- Key size: 4096 bits
- Expiry: 2y (recommended)
- Name and email: use the same email as your GitHub account

### 3. Find your key ID

```bash
gpg --list-secret-keys --keyid-format=long
```

Output looks like:
```
sec   rsa4096/ABC1234567890DEF 2024-01-01 [SC]
```

Your key ID is `ABC1234567890DEF`. Your email is also a valid key ID.

### 4. (Optional) Publish your public key

Upload to a keyserver so users can fetch it automatically:

```bash
gpg --keyserver keyserver.ubuntu.com --send-keys ABC1234567890DEF
```

Also export and commit to the repo (run once):

```bash
gpg --armor --export ABC1234567890DEF > maintainer_public_key.asc
```

---

## Sign a release (each release)

After running `scripts/generate_checksums.sh`:

```bash
bash scripts/gpg_sign_release.sh ABC1234567890DEF
```

This produces:
- `checksums.txt.asc` — detached signature
- `maintainer_public_key.asc` — exportable public key

Upload both along with `checksums.txt` and `Battery Alert.dmg` to your GitHub Release.

---

## Verify a release (users)

### 1. Import the maintainer's public key (one-time)

Either from the repo:

```bash
gpg --import maintainer_public_key.asc
```

Or from keyserver:

```bash
gpg --keyserver keyserver.ubuntu.com --recv-keys ABC1234567890DEF
```

### 2. Verify the checksum signature

```bash
gpg --verify checksums.txt.asc checksums.txt
```

Expected output includes `Good signature from "Your Name <email>"`.

### 3. Verify the DMG checksum

```bash
shasum -a 256 "Battery Alert.dmg"
# Compare this output to the line in checksums.txt
```

---

## Trust chain summary

```
Maintainer GPG key (public key published in repo + keyserver)
    ↓ signs
checksums.txt  (SHA256 of each release artifact)
    ↓ verifies
Battery Alert.dmg  (the release artifact)
```

Users who verify this chain can be confident the DMG has not been tampered with.
