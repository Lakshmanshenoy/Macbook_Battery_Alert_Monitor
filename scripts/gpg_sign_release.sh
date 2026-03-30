#!/usr/bin/env bash
# Sign release checksums with GPG and export the maintainer public key.
# Run this AFTER scripts/generate_checksums.sh has produced checksums.txt
#
# Prerequisites:
#   brew install gnupg   (or OS GPG install)
#   gpg --full-generate-key   (run once to create your key if you don't have one)
#
# Usage:
#   bash scripts/gpg_sign_release.sh [GPG_KEY_ID]
#   e.g.  bash scripts/gpg_sign_release.sh hello@example.com
#   If no key ID is provided, GPG will use your default key.

set -euo pipefail

CHECKSUMS_FILE="checksums.txt"
SIG_FILE="${CHECKSUMS_FILE}.asc"
PUBKEY_FILE="maintainer_public_key.asc"
KEY_ID="${1:-}"

if [ ! -f "$CHECKSUMS_FILE" ]; then
  echo "Error: $CHECKSUMS_FILE not found. Run scripts/generate_checksums.sh first."
  exit 1
fi

# Sign the checksums file
echo "Signing $CHECKSUMS_FILE..."
if [ -n "$KEY_ID" ]; then
  gpg --armor --detach-sign --local-user "$KEY_ID" --output "$SIG_FILE" "$CHECKSUMS_FILE"
else
  gpg --armor --detach-sign --output "$SIG_FILE" "$CHECKSUMS_FILE"
fi
echo "Signature written to $SIG_FILE"

# Export the public key
echo "Exporting public key to $PUBKEY_FILE..."
if [ -n "$KEY_ID" ]; then
  gpg --armor --export "$KEY_ID" > "$PUBKEY_FILE"
else
  gpg --armor --export > "$PUBKEY_FILE"
fi
echo "Public key written to $PUBKEY_FILE"

echo ""
echo "Done. Include the following files in your GitHub Release:"
echo "  - $CHECKSUMS_FILE"
echo "  - $SIG_FILE"
echo "  - $PUBKEY_FILE (first release only — users import this once)"
