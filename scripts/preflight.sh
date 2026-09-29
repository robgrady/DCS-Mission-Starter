#!/bin/bash
# Pre-deploy check: run this from your deploy folder BEFORE `fly deploy`.
#
#   bash scripts/preflight.sh
#
# It exists because the AWI pack failed to reach the live site twice, for
# reasons invisible from a working local app: the packs folder wasn't beside
# the code, or the container build was configured to drop it. This checks the
# whole chain in one shot and says plainly whether you're clear to deploy.
cd "$(dirname "$0")/.."
FAIL=0
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; FAIL=1; }
note() { printf '    \033[2m%s\033[0m\n' "$1"; }

echo
echo "DCS Sortie Starter — pre-deploy check"
# Read the version by PARSING, not importing: `import missiongen` runs a
# pyproj preflight, which fails on a fresh unzip because the launcher hasn't
# built its venv yet. This check must work before anything is installed.
if [ ! -f missiongen/__init__.py ]; then
  bad "this doesn't look like the app folder"
  note "expected to find missiongen/, server/, frontend/ next to this scripts/ folder"
  note "cd into the unzipped dcs-mission-starter folder and run it again"
else
  VERSION=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' missiongen/__init__.py | head -1)
  [ -n "$VERSION" ] && ok "app version $VERSION" || bad "could not parse __version__"
fi

# 1. mission packs live on the SERVER volume now (uploaded via /admin), not
#    in this folder — nothing to check here. See /admin > Mission packs.

# 2. the changelog IS the release notes since v1.105.0 (What's new retired;
#    /api/whatsnew answers 410). One record, written once, per release.
if [ -n "$VERSION" ]; then
  if grep -qE "^#+ .*\[?$VERSION\]?" CHANGELOG.md 2>/dev/null; then
    ok "changelog entry written for $VERSION"
  else
    bad "no $VERSION entry in CHANGELOG.md"
    note "add a '## [$VERSION] — <title>' section to CHANGELOG.md"
  fi
fi

# 2b. DERIVED ARTIFACTS. Everything generated from something else — the served
#     HTML pages, the guide PDF, the UI screenshots — plus the hand-written docs
#     that carry a version stamp. Registry: scripts/artifacts.py.
#     This blocks rather than warns, by Rob's call: the roadmap page drifted 17
#     versions and then 11 more, and REPLIT.md drifted 32, all under a system
#     where nothing failed.
if [ -n "$VERSION" ]; then
  STALE=$(python3 -c "
import sys; sys.path.insert(0, 'scripts')
import artifacts
for p, why in artifacts.stale('$VERSION'):
    print(f'{p}: {why}')
" 2>/dev/null) || STALE="(staleness check failed to run)"
  if [ -z "$STALE" ]; then
    ok "every derived artifact is current"
  else
    bad "stale artifacts — do not ship"
    echo "$STALE" | while read -r l; do note "$l"; done
    note "fix them all at once with: bash scripts/release.sh $VERSION"
  fi
fi

# 3. the test suite ships in the zip, so it can be run right here, from the
#    same folder you're about to deploy. This is the check that would have
#    caught the two 500s that reached users (a latin-1 header on carrier
#    missions, a divide-by-zero on the analytics page) before they shipped.
#    Skipped rather than failed if pytest isn't installed yet: preflight has to
#    work on a fresh unzip, before the launcher has built its venv.
if [ ! -d tests ]; then
  bad "no tests/ folder — this zip is not a complete recovery point"
  note "rebuild the release with: bash scripts/package.sh"
elif ! python3 -c 'import pytest' >/dev/null 2>&1; then
  note "pytest not installed — skipping the test suite"
  note "to run it: pip install -r requirements.txt pytest && python3 -m pytest tests -q"
else
  # RUN IT IN PARALLEL WHEN WE CAN. The suite is ~3,500 tests and most of the
  # wall clock is spent building .miz files, which is CPU-bound and embarrassingly
  # parallel. Measured on the 2-core build box: 20:34 serial -> 10:17 with two
  # workers, same 3,528 passed / 43 skipped.
  #
  # `--dist loadfile` is not optional. Several test modules share a module-scoped
  # fixture that generates a whole mission (`built`, `built_green`, `built_drag`,
  # `built_full_ramp`); the default `--dist load` scatters a module's tests across
  # workers, so each worker rebuilds that mission for its share — more total work
  # than running serially. Whole files to whole workers keeps one build per fixture.
  #
  # Optional by design: this script has to work on a fresh unzip, and pytest-xdist
  # is a developer convenience, not a shipped dependency. Without it, serial.
  PAR=""
  if python3 -c 'import xdist' >/dev/null 2>&1; then
    PAR="-n auto --dist loadfile"
    note "running the suite in parallel (pytest-xdist)"
  fi
  TESTLOG=$(mktemp)
  if python3 -m pytest tests -q $PAR >"$TESTLOG" 2>&1; then
    ok "test suite passes ($(grep -oE '[0-9]+ passed' "$TESTLOG" | tail -1))"
  else
    bad "test suite FAILED — do not deploy"
    grep -E '^(FAILED|ERROR)' "$TESTLOG" | head -12 | while read -r l; do note "$l"; done
  fi
  rm -f "$TESTLOG"
fi

# 4. deploy config
[ -f fly.toml ] && ok "fly.toml present" || bad "fly.toml missing"
grep -q 'ANALYTICS_DATA_DIR' fly.toml 2>/dev/null \
  && ok "analytics volume configured" || note "analytics dir not set in fly.toml"
grep -q 'PACKS_DATA_DIR' fly.toml 2>/dev/null \
  && ok "mission-pack volume configured" || bad "PACKS_DATA_DIR missing from fly.toml"
# Contact messages are the one store a user cannot regenerate by pressing the
# button again — an unconfigured dir means the container's ephemeral disk, and
# every message silently vanishes on the next cold start. Hard fail.
grep -q 'CONTACT_DATA_DIR' fly.toml 2>/dev/null \
  && ok "contact volume configured" || bad "CONTACT_DATA_DIR missing from fly.toml"

echo
if [ "$FAIL" = "0" ]; then
  printf '  \033[32mClear to deploy.\033[0m  Run: fly deploy\n'
  printf '  Then check: https://dcs-mission-starter.fly.dev/api/health\n'
  printf '  (want "version": "%s")\n'  "$VERSION"
  printf '  Packs are uploaded at /admin > Mission packs — no deploy needed.\n\n'
else
  printf '  \033[31mNot ready — fix the ✗ items above, then run this again.\033[0m\n\n'
  exit 1
fi
