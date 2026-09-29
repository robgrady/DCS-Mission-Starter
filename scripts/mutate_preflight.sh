#!/usr/bin/env bash
# Prove the parallel-preflight guards by breaking them.
#
# THIS ONE IS UNUSUAL AND WORTH SAYING OUT LOUD: every mutation below leaves a
# GREEN test suite behind. Break the distribution and 3,528 tests still pass,
# just slower and with four missions built twice. Make xdist mandatory and the
# suite still passes here, on the box that has xdist — it fails on Rob's fresh
# unzip, which no test on this box will ever run. That is exactly why the
# guards are text assertions on the script rather than a measurement: there is
# no artifact to read back, because the defect produces a correct result.
#
# Text guards rot. The counterweight is
# test_the_module_scoped_mission_fixtures_this_protects_still_exist, which
# fails if the premise (module-scoped fixtures that build whole missions) ever
# goes away — at which point --dist loadfile is worth re-deciding rather than
# re-asserting.
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
FILES=(
  scripts/preflight.sh
  requirements.txt
)
for f in "${FILES[@]}"; do mkdir -p "$SNAP/$(dirname "$f")"; cp "$f" "$SNAP/$f"; done

baseline() {
  find missiongen tests scripts -type f \( -name '*.py' -o -name '*.json' -o -name '*.sh' \) \
       ! -path '*/__pycache__/*' -print0 | sort -z | xargs -0 md5sum
  md5sum requirements.txt
}
baseline > "$SNAP/baseline.txt"
purge_pyc() { find missiongen tests -name __pycache__ -type d -prune \
              -exec rm -rf {} + 2>/dev/null || true; }
restore() { purge_pyc; for f in "${FILES[@]}"; do cp "$SNAP/$f" "$f"; done; }
trap restore EXIT

PASS=0; WEAK=0

# THE BASELINE MUST BE GREEN BEFORE ANY OF THIS MEANS ANYTHING.
#
# This check exists because it bit: a brief was edited so that it failed one of
# the very guards this harness exercises, the harness was run without running
# the plain suite first, and EVERY mutation on that guard reported "caught" —
# because the tests were already failing. Thirty-six caught, zero weak, and the
# whole run was noise. A mutation harness measures the DELTA between green and
# broken; with no green there is no delta.
baseline_green() {
  if ! PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:vendor python3 -m pytest \
       "$@" -q > /tmp/mut_baseline.log 2>&1; then
    echo "  ABORT     the suite is RED before any mutation was applied."
    echo "            Every mutation below would report 'caught' and mean nothing."
    tail -15 /tmp/mut_baseline.log | sed 's/^/            /'
    exit 3
  fi
  echo "  baseline  green"
}

run() {
  local name="$1" k="$2"
  if PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:vendor python3 -m pytest \
       tests/test_preflight_parallel.py \
       -q -x -k "$k" > /tmp/mut_preflight.log 2>&1; then
    echo "  WEAK      $name — suite still green"; WEAK=$((WEAK+1))
  else
    echo "  caught    $name"; PASS=$((PASS+1))
  fi
  restore
  local drift
  drift=$(baseline | diff - "$SNAP/baseline.txt" | grep '^<' || true)
  if [ -n "$drift" ]; then
    echo "  ABORT     restore missed a file — add it to FILES:"
    echo "$drift" | sed 's/^< [0-9a-f]*  /            /'
    exit 2
  fi
}

mut() {
  purge_pyc
  python3 - "$1" "$2" "$3" <<'PY' || { echo "  ANCHOR MISSING in $1"; exit 9; }
import io, sys
def unesc(x):
    return x.replace("\\n", "\n").replace("\\x27", "'")
p, o, n = sys.argv[1], unesc(sys.argv[2]), unesc(sys.argv[3])
s = io.open(p).read()
assert s.count(o) == 1, (p, s.count(o), o[:70])
io.open(p, "w").write(s.replace(o, n))
PY
}

baseline_green tests/test_preflight_parallel.py

echo "== the distribution =="

# THE EXPENSIVE MISTAKE: parallelise, but let xdist scatter each module across
# workers. Every module-scoped mission fixture then builds once per worker.
mut scripts/preflight.sh 'PAR="-n auto --dist loadfile"' \
                         'PAR="-n auto --dist load"'
run "scatter each module across workers (--dist load)" "distribution_is_by_file"

mut scripts/preflight.sh 'PAR="-n auto --dist loadfile"' 'PAR="-n auto"'
run "parallelise with no distribution chosen at all" "distribution_is_by_file"

echo "== staying optional =="

# preflight has to survive a fresh unzip on a machine with no pytest-xdist.
mut scripts/preflight.sh 'python3 -m pytest tests -q $PAR' \
                         'python3 -m pytest tests -q -n auto --dist loadfile'
run "hardcode -n on the pytest line" "flag_is_built_from_a_variable"

mut scripts/preflight.sh 'python3 -m pytest tests -q $PAR' \
                         'python3 -m pytest tests -q'
run "drop the parallel flags entirely" "flag_is_built_from_a_variable"

# Assignment hoisted out of the probe: the flags apply whether xdist is there
# or not, which is the hardcoded case wearing an if-block as a disguise.
mut scripts/preflight.sh '  PAR=""\n  if python3 -c \x27import xdist\x27 >/dev/null 2>&1; then\n    PAR="-n auto --dist loadfile"\n' \
                         '  PAR="-n auto --dist loadfile"\n  if python3 -c \x27import xdist\x27 >/dev/null 2>&1; then\n'
run "hoist PAR out of the probe so it always applies" "only_switched_on_if_xdist"

mut scripts/preflight.sh 'if python3 -c \x27import xdist\x27 >/dev/null 2>&1; then' \
                         'if true; then'
run "delete the xdist probe" "only_switched_on_if_xdist"

echo "== the pytest step still exists =="

# The cheapest way to make a test-running script pass a test-running guard.
mut scripts/preflight.sh '  if python3 -m pytest tests -q $PAR >"$TESTLOG" 2>&1; then' \
                         '  if true >"$TESTLOG" 2>&1; then'
run "stop running the suite in preflight" "runs_the_suite_at_all"

echo "== what the zip tells the reader =="

mut requirements.txt '# TEST-ONLY, optional: `pytest-xdist`.' '# TEST-ONLY, optional: nothing.'
run "remove xdist from requirements.txt" "requirements_documents_xdist"

mut requirements.txt 'python3 -m pytest tests -q -n auto --dist loadfile' \
                     'python3 -m pytest tests -q -n auto'
run "document the install without the distribution" "requirements_documents_xdist"

# WAS WEAK, AND THE REASON IS WORTH KEEPING: the first version of the guard
# searched the whole comment block for the string "--dist loadfile", so cutting
# the flag from the COMMAND still passed on the strength of the sentence
# explaining why the flag matters. Re-aimed at the command line itself.
mut requirements.txt '# does:  python3 -m pytest tests -q -n auto --dist loadfile' \
                     '# does:  python3 -m pytest tests -q'
run "document a command that never parallelises" "requirements_documents_xdist"

# The flag without the reason: the next person to tune this has nothing to weigh.
mut requirements.txt '# `--dist loadfile` matters: several modules share a module-scoped fixture that' \
                     '# Use `--dist loadfile`.  Trust me. It is fine.  It is definitely fine.'
run "give the flag with no reason for it" "requirements_documents_xdist"

mut requirements.txt 'pyproj==3.7.2' 'pyproj==3.7.2\npytest-xdist==3.8.0'
run "pin xdist as a deployed runtime dependency" "requirements_documents_xdist"

echo
echo "caught $PASS, weak $WEAK"
[ "$WEAK" -eq 0 ]
