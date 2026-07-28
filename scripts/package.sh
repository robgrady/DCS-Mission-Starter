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
  run_windows.bat          # Windows double-click launcher
  REPLIT.md                # implementation brief for Replit / hosting agents
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

# Fail loudly if either launcher didn't make it in.
for launcher in run_mac.command run_windows.bat; do
  if ! unzip -l "$OUT" | grep -q "$launcher"; then
    echo "ERROR: $launcher missing from $OUT" >&2
    exit 1
  fi
done

echo "built $OUT ($(du -h "$OUT" | cut -f1)) — includes both launchers"
unzip -l "$OUT" | grep -E 'run_mac.command|run_windows.bat|README|Dockerfile|fly.toml|.replit' || true
