#!/bin/bash
#
# update.sh - Increment version, commit, push, and reinstall
#
# Usage: ./update.sh [major|minor|patch]
#        Default: patch
#

set -e

# Parse argument (default to patch)
BUMP_TYPE="${1:-patch}"

# Validate argument
if [[ ! "$BUMP_TYPE" =~ ^(major|minor|patch)$ ]]; then
    echo "Error: Invalid argument '$BUMP_TYPE'"
    echo "Usage: ./update.sh [major|minor|patch]"
    exit 1
fi

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep -E '^version = "' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

if [[ -z "$CURRENT_VERSION" ]]; then
    echo "Error: Could not find version in pyproject.toml"
    exit 1
fi

# Parse version components
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Increment based on bump type
case "$BUMP_TYPE" in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"

echo "Bumping version: $CURRENT_VERSION → $NEW_VERSION ($BUMP_TYPE)"

# Update pyproject.toml
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS requires empty string for -i
    sed -i '' "s/^version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
else
    # Linux
    sed -i "s/^version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml
fi

# Verify the change
UPDATED_VERSION=$(grep -E '^version = "' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
if [[ "$UPDATED_VERSION" != "$NEW_VERSION" ]]; then
    echo "Error: Version update failed"
    exit 1
fi

echo "✓ Updated pyproject.toml"

# Commit
git add pyproject.toml
git commit -m "chore: bump version to $NEW_VERSION"
echo "✓ Committed"

# Push
git push
echo "✓ Pushed"

# Reinstall in editable mode
pip install -e . --quiet
echo "✓ Reinstalled package"

echo ""
echo "Done! Version is now $NEW_VERSION"
