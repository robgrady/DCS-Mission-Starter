#!/usr/bin/env bash
# Prove the Case III guards by breaking them.
#
# A TRAINING PACK IS THE HIGHEST-RISK THING THIS PRODUCT SHIPS. Every other
# mission can be wrong and merely disappointing; a training pack that is wrong
# teaches somebody the wrong procedure and he believes it. So the mutations
# below are not typos — each one is a DEFENSIBLE-LOOKING implementation that a
# reasonable person would write, and every one of them is wrong:
#
#   * derive the marshal radial from the BRC (nine degrees, invisible)
#   * make platform a range gate (every community guide quotes a DME beside it)
#   * use static trigger zones (the obvious thing; the ship is under way)
#   * let the cues run in sequence (ride 4 then fires three gates it is already
#     inside, in its first second)
#   * grade the push time without allowing for the transit (marks everybody
#     late, including the pilot who flew it perfectly)
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
FILES=(
  missiongen/cq.py
  missiongen/cq_route.py
  missiongen/cq_coach.py
  missiongen/builder.py
  missiongen/data/mission_templates.json
  missiongen/data/tracks.json
  missiongen/tracks.py
  frontend/index.html
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
       tests/test_case3.py -q -x -k "$k" > /tmp/mut_case3.log 2>&1; then
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

baseline_green tests/test_case3.py

echo "== the marshal rule =="

# NINE DEGREES. The fix is still on a radial and still at the right range, and
# the student starts the approach three and a half miles off the arc.
mut missiongen/cq.py '    return (final_bearing(brc) + MARSHAL_RADIAL_OFFSET) % 360.0' \
                     '    return (brc + MARSHAL_RADIAL_OFFSET) % 360.0'
run "hang the marshal radial off the BRC instead of the final bearing" \
    "marshal_radial_is_not_simply"

mut missiongen/cq.py '    return (brc - ANGLED_DECK_DEG) % 360.0' \
                     '    return (brc + ANGLED_DECK_DEG) % 360.0'
run "put the angled deck to starboard" "marshal_radial_is_not_simply"

mut missiongen/cq.py '    return int(angels) + MARSHAL_DME_PLUS' \
                     '    return int(angels) + 10'
run "hold ten miles closer than angels + 15" \
    "angels_plus_fifteen or marshal_fix_in_the_mission"

mut missiongen/cq.py 'MARSHAL_BASE_FT = 6000' 'MARSHAL_BASE_FT = 20000'
run "raise the base of the stack above every ride in the syllabus" \
    "natops_floor"

# The outbound leg of a holding pattern goes AWAY from the fix.
mut missiongen/cq_route.py '        ("OUTBOUND END", point_at_dme(carrier_pos, brc, out_dme, across), alt,' \
                           '        ("OUTBOUND END", point_at_dme(carrier_pos, brc, dme - leg_nm, across), alt,'
run "fly the outbound leg toward the ship" "left_hand_racetrack"

echo "== platform is an altitude =="

mut missiongen/cq_coach.py '            "platform": [[lo(cq.PLATFORM_FT), hi(PLATFORM_FLOOR_FT),\n                          outside(cq.ARC_DME)]],' \
                           '            "platform": [band(19.0, 17.5)],'
run "make platform a range gate, the way the community guides quote it" \
    "platform_is_graded_as_an_altitude"

mut missiongen/cq.py 'PLATFORM_FT = 5000' 'PLATFORM_FT = 3000'
run "shallow the descent three thousand feet late" \
    "platform_is_graded_as_an_altitude"

mut missiongen/cq.py 'PLATFORM_FPM_MAX = 2000' 'PLATFORM_FPM_MAX = 4000'
run "let the descent stay at 4,000 fpm all the way down" \
    "descent_rate_grade or platform_is_graded"

mut missiongen/cq_coach.py '                      C.UnitVerticalSpeedWithin(me.id, -DIVE_FLOOR_MS,\n                                                -DIVE_LIMIT_MS)]],' \
                           '                      C.UnitVerticalSpeedWithin(me.id, -DIVE_LIMIT_MS,\n                                                DIVE_LIMIT_MS)]],'
run "grade the descent rate with a window that is not a descent" \
    "descent_rate_grade"

echo "== the ship is under way =="

mut missiongen/cq_coach.py '            return C.UnitInMovingZone(me.id, nm * NM_M, boat.id)' \
                           '            return C.UnitInZone(me.id, int(nm))'
run "use static trigger zones for the range gates" \
    "moving_zone or gates_are_centred or fires_at_the_range"

mut missiongen/cq_coach.py '            return C.UnitOutsideMovingZone(me.id, nm * NM_M, boat.id)' \
                           '            return C.UnitOutsideZone(me.id, int(nm))'
run "use a static zone for the outer half of every gate" \
    "moving_zone or gates_are_centred"

mut missiongen/cq_coach.py '            return C.UnitInMovingZone(me.id, nm * NM_M, boat.id)' \
                           '            return C.UnitInMovingZone(me.id, nm * NM_M, me.id)'
run "hang the gates off the player instead of the carrier" \
    "gates_are_centred"

mut missiongen/cq.py 'LEVEL_DME = 10' 'LEVEL_DME = 14'
run "move the level-off gate four miles out" "fires_at_the_range"

echo "== which cues a ride gets =="

mut missiongen/cq_coach.py '    "cq_4_ball": ["ball", "bolter"],' \
                           '    "cq_4_ball": ["ten", "dirty", "six", "ball", "bolter"],'
run "let the ball ride fire the gates it starts inside" \
    "starts_inside or declares_its_cues"

mut missiongen/cq_coach.py '    "cq_5_nightcq": [],          # the check ride is silent\n}\n\n# ------' \
                           '    "cq_5_nightcq": ["ten", "dirty", "six", "ball"],\n}\n\n# ------'
run "coach the check ride" "check_ride_is_silent or coached_rides_are_coached"

mut missiongen/cq_coach.py '    "cq_1_stack": ["push_early", "push_late", "push_ontime"],' \
                           '    "cq_1_stack": [],'
run "stop grading the one thing ride 1 exists to teach" \
    "timing_verdicts or coached_rides_are_coached"

echo "== the timing grade =="

# WITHOUT THE TRANSIT ALLOWANCE EVERY PILOT IS LATE, including the one who
# crossed the fix on the second.
mut missiongen/cq_coach.py '        window = (push_s or 0) + transit' \
                           '        window = (push_s or 0)'
run "grade the push time with no allowance for the flight to the band" \
    "allows_for_the_flight_time"

mut missiongen/cq_coach.py '    return cq.marshal_dme(angels) - 2.0' \
                           '    return cq.marshal_dme(angels) + 3.0'
run "put the commence band inside the holding pattern" \
    "commence_band_is_clear"

mut missiongen/cq.py 'EAT_TOLERANCE_S = 10             # the fleet-taught number; NATOPS gives none' \
                     'EAT_TOLERANCE_S = 600             # the fleet-taught number; NATOPS gives none'
run "widen the timing window to ten minutes" \
    "timing_verdicts or allows_for_the_flight_time"

echo "== flags =="

mut missiongen/cq_coach.py 'F_PHASE = 8940           # 8940 + i: cue i has fired' \
                           'F_PHASE = 8890           # 8940 + i: cue i has fired'
run "overlap the cue flags with the White Knights coaching" "flag_block_collides"

mut missiongen/cq_coach.py 'F_ARM = 8979             # the whole thing is live' \
                           'F_ARM = 8945             # the whole thing is live'
run "make the arm flag one of the cue flags" "flag_block_collides"

echo "== what the pilot is told =="

mut missiongen/builder.py '                    f">> YOUR FLIGHT: {ac}, airborne, recovering aboard "' \
                          '                    f">> YOUR FLIGHT: {ac} parked and ready aboard "'
run "tell the pilot his airborne jet is parked and ready" \
    "does_not_say_the_jet_is_parked"

mut missiongen/builder.py '        if r.cq_ride:\n            # THE STARTER PARAGRAPH IS FALSE ON A TRAINING RIDE.' \
                          '        if False:\n            # THE STARTER PARAGRAPH IS FALSE ON A TRAINING RIDE.'
run "print the sandbox paragraph over a syllabus ride" "promise_a_sandbox"

mut missiongen/cq.py 'REQUIRES_MODULE = "DCS: Supercarrier"' 'REQUIRES_MODULE = ""'
run "stop saying the pack needs the Supercarrier module" "supercarrier_is_declared"

mut missiongen/cq.py '        L += [f"== YOUR COCKPIT — {ck[\x27label\x27]} =="]\n' \
                     '        L += ["== YOUR COCKPIT =="]\n        ck = COCKPIT["hornet"]\n'
run "print the Hornet cockpit card in the Tomcat" "tomcat_card_teaches_the_tomcat"

echo "== the pack is complete =="

mut missiongen/data/mission_templates.json '"cq_ride": "cq_4_ball"\n  },\n  "track": {\n   "id": "cq_case3_hornet",' \
                                           '"cq_ride": "cq_1_stack"\n  },\n  "track": {\n   "id": "cq_case3_hornet",'
run "point two Hornet cards at the same ride" "ships_for_both_jets or points_at_a_real_ride"

mut missiongen/data/mission_templates.json '"callsign": "CHECKMATE",\n   "start": "air",\n   "bb_tanker": false,\n   "bb_awacs": false,\n   "bb_targets": false,\n   "bb_ambient": false,\n   "bb_carrier": true,\n   "carrier_hull": "cvn_73",\n   "carrier_layout": "recovery",\n   "home_airbase": "CARRIER",\n   "threat_intensity": 1,\n   "threat_tier": "light",\n   "time_of_day": "night",\n   "weather": "overcast",' \
                                           '"callsign": "CHECKMATE",\n   "start": "air",\n   "bb_tanker": false,\n   "bb_awacs": false,\n   "bb_targets": false,\n   "bb_ambient": false,\n   "bb_carrier": true,\n   "carrier_hull": "cvn_73",\n   "carrier_layout": "recovery",\n   "home_airbase": "CARRIER",\n   "threat_intensity": 1,\n   "threat_tier": "light",\n   "time_of_day": "day",\n   "weather": "overcast",'
run "fly a Case III check ride in daylight" "run_at_night"

# The published gates, changed in the module. Caught only because the tests
# carry the numbers themselves — see the comment above the parametrisation.
mut missiongen/cq.py 'ONSPEED_KT = 150' 'ONSPEED_KT = 250'
run "cross the six-mile fix at 250 knots" "published_gates"

mut missiongen/cq.py 'GLIDESLOPE_DEG = 3.5' 'GLIDESLOPE_DEG = 3.0'
run "fly a three-degree glideslope to a boat that grades three and a half" \
    "published_gates or card_and_the_flight_plan_agree"

echo "== the paid module, on the surfaces a pilot actually opens =="

# A ride that belongs to a track is NEVER a grid card, so the chip on the grid
# card is not the surface that matters. These two are.
mut frontend/index.html '      // panel and the track panel. Both say it.\n      (t.requires?\x27<span class="lchip needsmod"><svg class="icon"><use href="#i-lock"/></svg> Requires \x27+t.requires+\x27</span>\x27:\x27\x27)+\x27</div>\x27+' \
                        '      // panel and the track panel. Both say it.\n      \x27</div>\x27+'
run "drop the module requirement from the ride panel" "library_card_says_it_needs"

mut missiongen/tracks.py '        "requires": t.get("requires"),' '        "requires": None,'
run "stop publishing the track\x27s module requirement to the browser" \
    "library_card_says_it_needs"

mut missiongen/data/tracks.json '"requires": "DCS: Supercarrier",\n  "featured": true,' \
                                '"featured": true,'
run "leave the Tomcat track without a declared module" \
    "supercarrier_is_declared or library_card_says_it_needs"

echo "== no card may brief a recovery it has not built =="

# THE GAP THIS FOUND, restored exactly: a featured card telling the pilot to
# fly a night marshal stack in a daylight mission on the deck.
mut missiongen/data/mission_templates.json '"The boat is steaming into the wind with the pattern open. This is a CASE I",' \
                                           '"CASE III (night/IMC): Marshal stack, push on time, CATCC approach.",'
run "brief a Case III on the daylight carrier sandbox" \
    "case_three_it_has_not_built"

mut missiongen/data/mission_templates.json '"syllabus with cues and grades, and it needs DCS: Supercarrier."' \
                                           '"syllabus with cues and grades."'
run "point at the Case III track without naming the module it needs" \
    "points_at_the_syllabus"

# The quieter version of the same gap: night and weather right, but you are on
# the deck and the brief walks you through a stack the mission has not built.
mut missiongen/data/mission_templates.json '"or grades it. If you do not already know the procedure, learn it in the",\n   "Case III track in the Library, which teaches the marshal stack, the push on",' \
                                           '"or grades it. Hold the marshal stack and push on time.",\n   "There is nowhere else to learn this.",'
run "instruct a Case III on the night sandbox and point nowhere" \
    "case_three_it_has_not_built"

echo "== the regression found while building this =="

mut missiongen/builder.py '                if not label and not _pyl:' '                if not _wkr_ride:'
run "warn that an armed jet starts clean" "told_it_starts_clean"

echo
echo "caught $PASS, weak $WEAK"
[ "$WEAK" -eq 0 ]
