#!/usr/bin/env bash
# Build production-ready installable zips for the ydu theme and ydu-fitment plugin.
# Excludes dev-only files (node_modules, src, tests, composer/npm manifests, vendor).
# Output: dist/ydu.zip, dist/ydu-fitment.zip
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
STAGE="$(mktemp -d)"
rm -rf "$DIST"
mkdir -p "$DIST"

echo "==> Building theme assets"
( cd "$ROOT/themes/ydu" && npm run build >/dev/null )
echo "==> Building plugin assets"
( cd "$ROOT/plugins/ydu-fitment" && npm run build >/dev/null )

# --- Theme ---
echo "==> Packaging ydu theme"
mkdir -p "$STAGE/ydu"
cp -r "$ROOT/themes/ydu/." "$STAGE/ydu/"
( cd "$STAGE/ydu" && rm -rf node_modules src .gitignore package.json package-lock.json )
( cd "$STAGE" && zip -rq "$DIST/ydu.zip" ydu \
    -x "*/node_modules/*" -x "*.map" )

# --- Plugin ---
echo "==> Packaging ydu-fitment plugin"
mkdir -p "$STAGE/ydu-fitment"
cp -r "$ROOT/plugins/ydu-fitment/." "$STAGE/ydu-fitment/"
( cd "$STAGE/ydu-fitment" && rm -rf node_modules src tests vendor \
    package.json package-lock.json composer.json composer.lock phpunit.xml.dist )
( cd "$STAGE" && zip -rq "$DIST/ydu-fitment.zip" ydu-fitment \
    -x "*/node_modules/*" -x "*.map" )

rm -rf "$STAGE"
echo "==> Done:"
ls -lh "$DIST"
