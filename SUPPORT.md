# Support & Verification

How to get help
- Open an issue on the repository for bugs or feature requests.
- For urgent support, include your OS version and app version in the issue.

Verifying downloads
- Check the SHA256 checksum provided in the release assets before opening downloaded files.
- Verify the app is signed by running:

  spctl --assess --type execute --verbose=4 /Applications/\"Battery Alert.app\"

- Or check codesign details:

  codesign -dv --verbose=4 /Applications/\"Battery Alert.app\"

Reporting security issues
- Please open an issue or email the maintainer with steps to reproduce. Sensitive security reports may be handled privately on request.
