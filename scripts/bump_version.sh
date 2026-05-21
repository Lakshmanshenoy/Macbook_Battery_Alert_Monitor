#!/usr/bin/env bash
set -euo pipefail

# Usage: bump_version.sh <bump> [explicit_version]
# bump: major|minor|patch

BUMP=${1:-patch}
EXPLICIT=${2:-}

repo_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo_root"

git fetch --tags

if [ -n "$EXPLICIT" ]; then
  NEW_VERSION="$EXPLICIT"
else
  if git describe --tags --abbrev=0 >/dev/null 2>&1; then
    CUR_TAG=$(git describe --tags --abbrev=0)
  else
    CUR_TAG="v0.0.0"
  fi
  # strip leading v
  CUR_VER=${CUR_TAG#v}
  IFS='.' read -r MAJ MIN PAT <<<"$CUR_VER"
  MAJ=${MAJ:-0}; MIN=${MIN:-0}; PAT=${PAT:-0}
  case "$BUMP" in
    major)
      MAJ=$((MAJ+1)); MIN=0; PAT=0;;
    minor)
      MIN=$((MIN+1)); PAT=0;;
    patch)
      PAT=$((PAT+1));;
    *)
      echo "Unknown bump type: $BUMP"; exit 2;;
  esac
  NEW_VERSION="${MAJ}.${MIN}.${PAT}"
fi

NEW_TAG="v${NEW_VERSION}"
echo "Creating tag $NEW_TAG"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

git tag -a "$NEW_TAG" -m "Release $NEW_TAG"
git push origin "$NEW_TAG"

echo "Pushed tag $NEW_TAG"
