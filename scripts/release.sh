#!/bin/bash
# Cut a release. ONE command, so "did I remember to..." stops being a question.
#
#   bash scripts/release.sh 1.49.0
#   bash scripts/release.sh 1.49.0 --no-shots   # skip the browser screenshot run
#
# It bumps the version, regenerates every derived artifact in the registry
# (scripts/artifacts.py), re-stamps them, runs the full preflight — which now
# fails on ANY stale artifact — and builds the release zip.
#
# What it deliberately does NOT do: write your release notes or your CHANGELOG
# entry. Those are the two things that have to be thought about, and preflight
# refuses to pass without them.
set -e
cd "$(dirname "$0")/.."

VERSION="$1"
SHOTS=1
[ "$2" = "--no-shots" ] && SHOTS=0

step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; exit 1; }

# RUN A GENERATOR, AND DIE IF IT DIES.
#
# Every regeneration line here used to read `cmd >/dev/null && ok "label"`, and
# that shape SWALLOWS FAILURES: `set -e` does not fire for a command on the
# left of `&&`, so a generator that crashed printed its traceback, skipped its
# tick, and the release carried on — then `artifacts.restamp()` recorded the
# current input hashes anyway, which marks a file that was never rebuilt as
# fresh, permanently. That is not a cosmetic bug in a freshness system; it is
# the freshness system certifying a stale file.
#
# Found for real: `build_wk_coach_cards.py` died with a ValueError for a whole
# release and nothing noticed.
gen() {
  local label="$1"; shift
  if ! "$@" >/dev/null; then bad "$label — generator failed, see above"; fi
  ok "$label"
}

if [ -z "$VERSION" ]; then
  CUR=$(sed -n 's/^__version__ = "\(.*\)"/\1/p' missiongen/__init__.py | head -1)
  echo "usage: bash scripts/release.sh <version> [--no-shots]   (current: $CUR)"
  exit 2
fi
echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' || bad "version must be X.Y.Z"

# ---------------------------------------------------------------- 1. version
step "Version"
sed -i.bak "s/^__version__ = \".*\"/__version__ = \"$VERSION\"/" missiongen/__init__.py
rm -f missiongen/__init__.py.bak
ok "missiongen/__init__.py -> $VERSION"

# ------------------------------------------------------- 2. the two you write
# Checked BEFORE the slow regeneration steps: there is no point spending a
# minute on screenshots to then fail on a missing changelog entry.
step "Changelog"
grep -qE "^#+ .*\[?$VERSION\]?" CHANGELOG.md \
  && ok "changelog entry written" \
  || bad "no $VERSION entry in CHANGELOG.md — write it first"

# ------------------------------------------------- 3. regenerate the derived
step "Regenerating derived artifacts"
# Producers and arguments come only from scripts/artifacts.py.
python3 scripts/manual_review.py
python3 scripts/artifacts.py before-shots

if [ "$SHOTS" = "1" ]; then
  # The screenshots come from the real UI in a real browser, so the app has to
  # be up. Started and stopped here so the release is one command.
  if python3 -c 'import playwright' 2>/dev/null; then
    # Reuse an app already listening on 8360 rather than fighting it for the
    # port. A failed bind printed an alarming ERROR and then captured against
    # whatever was already there — possibly a different build.
    APP_PID=""
    if python3 -c "import urllib.request;urllib.request.urlopen('http://localhost:8360/api/health',timeout=1)" 2>/dev/null; then
      printf '  \033[2m- reusing the app already on :8360\033[0m\n'
    else
      python3 -m uvicorn server.app:app --port 8360 --log-level error &
      APP_PID=$!
      trap 'kill $APP_PID 2>/dev/null || true' EXIT
    fi
    for _ in $(seq 1 40); do
      python3 -c "import urllib.request;urllib.request.urlopen('http://localhost:8360/api/health',timeout=1)" 2>/dev/null && break
      sleep 0.5
    done
    python3 scripts/artifacts.py screenshots >/dev/null \
      && ok "docs/img/*.png recaptured" || bad "screenshot capture failed"
    [ -n "$APP_PID" ] && kill $APP_PID 2>/dev/null || true
    trap - EXIT
  else
    bad "playwright not installed — install it, or re-run with --no-shots"
  fi
else
  printf '  \033[2m- screenshots skipped (--no-shots)\033[0m\n'
fi

python3 scripts/artifacts.py after-shots

# Record what the artifacts were built FROM, so the staleness check can tell
# later whether their inputs have moved on. Must run after every generator.
python3 -c "import sys;sys.path.insert(0,'scripts');import artifacts;artifacts.restamp()"
ok "input hashes stamped (docs/.artifacts.json)"

# ------------------------------------------------------------- 4. the gate
step "Preflight"
bash scripts/preflight.sh

# ------------------------------------------------------------- 5. package
step "Package"
bash scripts/package.sh

step "Done"
cat <<EOF
  Built and verified v$VERSION.

  Next:
    1. git add -A && git commit    (or ask Claude to)
    2. fly deploy                  from the unzipped folder
    3. check /api/health says "version": "$VERSION"

  NOT automated, because it lives outside this repository:
    - claude/build-status.md in the Claude project. It was 27 releases behind
      before anyone noticed. Update it with what shipped.
EOF
