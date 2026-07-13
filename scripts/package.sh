#!/bin/bash
# Build the release zip. Single source of truth for what ships in a download.
# Usage: bash scripts/package.sh   (version is read from missiongen/__init__.py)
set -e
cd "$(dirname "$0")/.."

VERSION=$(python3 -c "import missiongen; print(missiongen.__version__)")
OUT="dcs-mission-starter-${VERSION}.zip"

# Everything a user needs to run the tool locally OR deploy it.
# NOTE: run_mac.command is the macOS launcher — it must ALWAYS be in the zip.
MANIFEST=(
  missiongen
  server
  frontend
  scripts
  docs
  samples
  vendor
  run_mac.command          # macOS double-click launcher
  README.md
  CHANGELOG.md
  LICENSE
  requirements.txt
  Dockerfile
  fly.toml
  .replit
)

rm -f "$OUT"
# -x guards against stray build artifacts sneaking in
zip -q -r "$OUT" "${MANIFEST[@]}" \
  -x '*/__pycache__/*' '*.pyc' '*/.DS_Store'

# Fail loudly if the launcher didn't make it in.
if ! unzip -l "$OUT" | grep -q 'run_mac.command'; then
  echo "ERROR: run_mac.command missing from $OUT" >&2
  exit 1
fi

echo "built $OUT ($(du -h "$OUT" | cut -f1)) — includes run_mac.command"
unzip -l "$OUT" | grep -E 'run_mac.command|README|Dockerfile|fly.toml|.replit' || true
