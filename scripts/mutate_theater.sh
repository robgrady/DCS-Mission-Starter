#!/usr/bin/env bash
# Prove the theater-chart and red-air-placement guards by breaking them.
#
# BOTH DEFECTS HERE WERE INVISIBLE TO THE SUITE AND OBVIOUS FROM THE COCKPIT,
# which is the shape worth remembering. The Persian Gulf chart rendered 68% of
# its base as sea — Iran flooded, the Strait of Hormuz paved — and nothing
# failed, because nothing had ever asserted that a coastline matches a coast.
# The enemy CAP stationed on the player's side of the line 42% of the time,
# and nothing failed, because nothing had ever asserted which half of the map
# the enemy starts in. Neither is arithmetic drift; both are a claim nobody
# had written down.
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
FILES=(
  missiongen/data/coastlines.json
  missiongen/threats.py
  missiongen/brief.py
  missiongen/builder.py
)
for f in "${FILES[@]}"; do mkdir -p "$SNAP/$(dirname "$f")"; cp "$f" "$SNAP/$f"; done

baseline() {
  find missiongen tests -type f \( -name '*.py' -o -name '*.json' \) \
       ! -path '*/__pycache__/*' -print0 | sort -z | xargs -0 md5sum
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
       tests/test_theater_chart.py tests/test_red_air_placement.py \
       -q -x -k "$k" > /tmp/mut_theater.log 2>&1; then
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

baseline_green tests/test_theater_chart.py tests/test_red_air_placement.py

echo "== the coastline =="

# THE BUG ROB SAW, restored exactly: the ring closed with box corners instead
# of a shoreline, so latitude 30 from lon 64 to lon 48 swept Iran into the sea.
mut missiongen/data/coastlines.json '[[24.60, 50.85], [25.50, 50.75], [26.15, 51.20], [25.60, 51.60], [24.90, 51.55],' \
                                    '[[23.00, 50.00], [22.00, 64.00], [30.00, 64.00], [30.00, 48.00], [24.90, 51.55],'
run "close the Gulf with box corners and flood Iran" \
    "airfield_we_use or geography or rendered_chart"

# Seven island airfields had no island at all before this release.
mut missiongen/data/coastlines.json '      [[26.58, 53.90], [26.56, 54.06], [26.48, 54.06], [26.47, 53.92]],\n' ''
run "leave Kish in open water" "airfield_we_use or islands_sit_in_water"

# The other half of the same class: a shoreline drawn inland of a coastal field.
mut missiongen/data/coastlines.json '[26.45, 54.85]' '[26.60, 54.90]'
run "cut the shoreline inland of Bandar Lengeh" "airfield_we_use"

mut missiongen/data/coastlines.json '[25.55, 57.88]' '[25.75, 57.88]'
run "cut the shoreline inland of Bandar-e-Jask" "airfield_we_use"

# An island polygon that is not IN the water proves nothing — it is a tan blob
# on a tan plate, and it would hide a real coastline error underneath it.
mut missiongen/data/coastlines.json '[[26.86, 53.22], [26.85, 53.44], [26.77, 53.45], [26.77, 53.24]]' \
                                    '[[29.86, 53.22], [29.85, 53.44], [29.77, 53.45], [29.77, 53.24]]'
run "beach an island in the middle of Iran" "islands_sit_in_water or airfield_we_use"

# The rendered page, not the data: swap the two base colors.
mut missiongen/brief.py 'WATER = (174, 191, 199)          # style-guide plate sea' \
                        'WATER = (216, 209, 187)          # style-guide plate sea'
run "paint the sea the color of the land" "rendered_chart"

echo "== where the enemy starts =="

# THE BAND ROB FLEW INTO: 0.40 of the way from the friendly center is the
# friendly half, and 42% of rolls landed there.
mut missiongen/threats.py '        frac = rng.uniform(0.55, 0.80)' \
                          '        frac = rng.uniform(0.40, 0.65)'
run "station the enemy CAP over the player's own airfields" \
    "friendly_side or station_band"

mut missiongen/threats.py '        frac = rng.uniform(0.55, 0.80)' \
                          '        frac = rng.uniform(0.50, 0.80)'
run "put the CAP station exactly on the midline" "station_band"

mut missiongen/threats.py '        frac = rng.uniform(0.55, 0.80)' \
                          '        frac = rng.uniform(0.95, 0.99)'
run "park the CAP on top of the enemy airfield SAMs" "station_band"

# The cheapest way to pass every placement guard is to make no enemy air.
mut missiongen/threats.py '    types = cap_types_for(era, enemy_side, tier)\n    if not types or n <= 0:' \
                          '    types = cap_types_for(era, enemy_side, tier)\n    if True:'
run "delete the enemy air force to satisfy the placement guards" \
    "cap_is_still_actually_placed"

# Ambient enemy transports must start on enemy ground, not the player's ramp.
mut missiongen/builder.py '                    m, enemy_country, enemy_fields, era_cfg[enemy_side], r.density,' \
                          '                    m, enemy_country, own_fields, era_cfg[enemy_side], r.density,'
run "start enemy transports on the player's own airfields" "parked_on_a_friendly"

echo
echo "caught $PASS, weak $WEAK"
[ "$WEAK" -eq 0 ]
