#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [ ! -f "$FRONTEND_DIR/package.json" ]; then
  echo "frontend/package.json not found. Skipping frontend checks."
  exit 0
fi

cd "$FRONTEND_DIR"

echo "Installing frontend dependencies..."

if [ -f "package-lock.json" ]; then
  npm ci
else
  echo "package-lock.json not found. Running npm install instead."
  npm install
fi

has_script() {
  node -e "const s=require('./package.json').scripts || {}; process.exit(s['$1'] ? 0 : 1)"
}

if has_script lint; then
  echo "Running frontend lint..."
  npm run lint
else
  echo "No lint script found. Skipping lint."
fi

if has_script test; then
  echo "Running frontend tests..."
  npm run test
else
  echo "No test script found. Skipping tests."
fi

if has_script build; then
  echo "Running frontend build..."
  npm run build
else
  echo "No build script found. Skipping build."
fi