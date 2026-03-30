# How to verify downloaded releases

Provide these steps to users so they can confirm file integrity and provenance.

1) Check SHA256 checksum
- After downloading `Battery Alert.dmg`, compare its SHA256 checksum with the value published in the release notes.

macOS:
```bash
shasum -a 256 Battery\ Alert.dmg
```

2) Verify code signature and notarization
- After copying the app to `/Applications`, run:

```bash
spctl --assess --type execute --verbose=4 "/Applications/Battery Alert.app"
```

- Check the codesign information:

```bash
codesign -dv --verbose=4 "/Applications/Battery Alert.app"
```

- Check stapler (optional):

```bash
xcrun stapler validate "/Applications/Battery Alert.app"
```

3) Verify GPG signature (optional)
- If a GPG-signed checksum or signature file is provided, import the maintainer's public key and verify:

```bash
gpg --import maintainer_public_key.asc
gpg --verify checksums.txt.sig checksums.txt
```

4) Reproducible builds
- For advanced users, provide build instructions (see `RELEASE_TEMPLATE.md`) and compare the produced artifact checksum with the published one.

If anything looks suspicious, do not open the file and open an issue in the repository or contact support (see `SUPPORT.md`).
