#!/usr/bin/env bash
set -euo pipefail

# Usage: update_cask.sh <sha_file> <tag>
SHA_FILE=${1:-}
TAG=${2:-}

if [ -z "$SHA_FILE" ] || [ -z "$TAG" ]; then
  echo "Usage: $0 <sha_file> <tag>" >&2
  exit 2
fi

SHA=$(cat "$SHA_FILE" | awk -F= '{print $2}' 2>/dev/null || cat "$SHA_FILE")
cd "$(dirname "$0")/.."

# Assume cask is at Casks/battmon.rb or Formula/battmon.rb
if [ -f "Casks/battmon.rb" ]; then
  CASK_PATH="Casks/battmon.rb"
elif [ -f "Formula/battmon.rb" ]; then
  CASK_PATH="Formula/battmon.rb"
else
  echo "Cask file not found in tap" >&2
  exit 3
fi

echo "Updating $CASK_PATH with SHA=$SHA and version=$TAG"

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

BRANCH="bump/battmon-${TAG}"
git checkout -b "$BRANCH"

# Update sha and url (assume URL uses tag in path)
perl -0777 -pe 's/sha256\s+"[0-9a-f]{64}"/sha256 "'"$SHA"'"/s' -i "$CASK_PATH"

# If the URL contains a vX.Y.Z tag, replace it with new tag
perl -0777 -pe 's/(releases\/download\/v)[0-9a-zA-Z\.\-]+/\1'"${TAG#v}"'/s' -i "$CASK_PATH" || true

git add "$CASK_PATH"
git commit -m "bump(cask): battmon $TAG"
git push origin "$BRANCH"

# Create PR using GitHub CLI if available
if command -v gh >/dev/null 2>&1; then
  gh pr create --title "bump(cask): battmon $TAG" --body "Automated cask bump for $TAG" --base main --head "$BRANCH"
else
  echo "Created branch $BRANCH. Push complete; please open a PR from this branch in the tap repo."
fi
