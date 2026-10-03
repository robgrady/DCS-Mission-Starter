#!/bin/bash
# Build the release zip. Single source of truth for what ships in a download.
# Usage: bash scripts/package.sh   (version is read from missiongen/__init__.py)
set -e
cd "$(dirname "$0")/.."

# Parse, don't import. `import missiongen` pulls in vendored pydcs (and pyproj),
# so packaging failed on any checkout where the vendor path isn't already on
# sys.path — the same trap preflight.sh was fixed for.
VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' missiongen/__init__.py | head -1)
if [ -z "$VERSION" ]; then echo "ERROR: could not parse __version__" >&2; exit 1; fi
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
  tests                    # MUST ship: the zip is the recovery point. A build
                           # environment can be reclaimed at any time, and a
                           # release that carries the code but not its tests
                           # restores a product nobody can verify. This has
                           # already cost one 188-test suite.
  run_mac.command          # macOS double-click launcher
  run_windows.bat          # Windows double-click launcher
  REPLIT.md                # implementation brief for Replit / hosting agents
  README.md
  CHANGELOG.md
  AGENTS.md                # Owner versioning rules must survive a release restore.
  LICENSE
  requirements.txt
  Dockerfile
  .dockerignore            # MUST ship: its !packs/** exception keeps the
                           # curated .miz files in the docker build context
  .gitignore               # MUST ship: tests/test_pack_delivery.py reads it,
                           # and a tree restored from a zip has no git history
  fly.toml
  .replit
)

rm -f "$OUT"
# -x guards against stray build artifacts sneaking in
zip -q -r "$OUT" "${MANIFEST[@]}" \
  -x '*/__pycache__/*' '*.pyc' '*/.DS_Store'

# Fail loudly if anything the zip is REQUIRED to contain didn't make it in.
for must in run_mac.command run_windows.bat tests/conftest.py; do
  if ! unzip -l "$OUT" | grep -q "$must"; then
    echo "ERROR: $must missing from $OUT" >&2
    exit 1
  fi
done

NTESTS=$(unzip -l "$OUT" | grep -c 'tests/test_.*\.py')
echo "built $OUT ($(du -h "$OUT" | cut -f1)) — both launchers, $NTESTS test files"
unzip -l "$OUT" | grep -E 'run_mac.command|run_windows.bat|README|Dockerfile|fly.toml|.replit' || true
