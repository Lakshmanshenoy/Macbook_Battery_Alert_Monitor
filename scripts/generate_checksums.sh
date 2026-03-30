#!/usr/bin/env bash
# Generate SHA256 checksums for release artifacts
set -euo pipefail

OUT=checksums.txt
echo "Generating SHA256 checksums into $OUT"
rm -f "$OUT"
for f in "$@"; do
  if [ -f "$f" ]; then
    shasum -a 256 "$f" >> "$OUT"
  else
    echo "Warning: $f not found, skipping" >&2
  fi
done
echo "Checksums written to $OUT"
