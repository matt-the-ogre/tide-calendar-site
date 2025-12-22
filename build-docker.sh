#!/bin/bash
# Build Docker image with version information

set -e

# Get version from package.json
VERSION=$(python3 -c "import json; print(json.load(open('package.json'))['version'])")

# Get git info
COMMIT_HASH=$(git rev-parse HEAD)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "Building Docker image with version info:"
echo "  Version: $VERSION"
echo "  Commit: $COMMIT_HASH"
echo "  Branch: $BRANCH"
echo "  Build Time: $BUILD_TIMESTAMP"
echo ""

# Build Docker image with build args
docker build \
  --build-arg VERSION="$VERSION" \
  --build-arg COMMIT_HASH="$COMMIT_HASH" \
  --build-arg BRANCH="$BRANCH" \
  --build-arg BUILD_TIMESTAMP="$BUILD_TIMESTAMP" \
  -t tide-calendar-app \
  .

echo ""
echo "Build complete! Image: tide-calendar-app"
