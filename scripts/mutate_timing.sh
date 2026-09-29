#!/usr/bin/env bash
# Prove waypoint timing by breaking it.
#
# WHAT IS BEING PROTECTED. timing.py anchors the clock (takeoff / push / TOT),
# times the card, and moves the mission start so the anchor is met; the
# builder writes the ETAs on the player's waypoints unlocked and on the
# package LOCKED two minutes ahead; saydo.check_timing recomputes card vs file
# vs clock after the build; timing_coach grades four points in flag block
# 8860-8879 and scores the anchor double; the four F-4E rides quote only
# clocks the plan produces. Each mutation is a way one of those could quietly
# stop being true while the suite stayed green.
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
FILES=(
  missiongen/timing.py
  missiongen/timing_coach.py
  missiongen/saydo.py
  missiongen/builder.py
  missiongen/brief.py
  missiongen/recipe.py
  missiongen/data/mission_templates.json
)
for f in "${FILES[@]}"; do mkdir -p "$SNAP/$(dirname "$f")"; cp "$f" "$SNAP/$f"; done

baseline() {
  find missiongen tests -type f \( -name '*.py' -o -name '*.json' \) ! -path '*/__pycache__/*' -print0 \
    | sort -z | xargs -0 md5sum
}
baseline > "$SNAP/baseline.txt"
purge_pyc() { find missiongen tests -name __pycache__ -type d -prune \
              -exec rm -rf {} + 2>/dev/null || true; }
restore() { purge_pyc; for f in "${FILES[@]}"; do cp "$SNAP/$f" "$f"; done; }
trap restore EXIT

PASS=0; WEAK=0

baseline_green() {
  if ! PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:vendor python3 -m pytest \
       "$@" -q > /tmp/mut_baseline.log 2>&1; then
    echo "  ABORT     the suite is RED before any mutation was applied."
    tail -15 /tmp/mut_baseline.log | sed 's/^/            /'
    exit 3
  fi
  echo "  baseline  green"
}

run() {
  local name="$1" k="$2"
  if PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:vendor python3 -m pytest \
       tests/test_timing.py -q -x -k "$k" > /tmp/mut_timing.log 2>&1; then
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

baseline_green tests/test_timing.py

echo "== the arithmetic =="

mut missiongen/timing.py 'GROUND_S = {"cold": 8 * 60, "warm": 3 * 60, "runway": 60, "air": 0}' \
                         'GROUND_S = {"cold": 8 * 60, "warm": 8 * 60, "runway": 60, "air": 0}'
run "give a warm start the cold ground block" "ground_block_by_start_type"

mut missiongen/timing.py '    if not first_leg or nm <= 0:' '    if True:'
run "time the first leg at cruise, not on the climb" "climb_schedule"

mut missiongen/timing.py '        new_start = want - anchor_after_takeoff - ground' \
                         '        new_start = want - anchor_after_takeoff'
run "solve the start without the ground block" "tot_anchor_moves"

mut missiongen/timing.py '    if want is not None and start_secs is not None:' '    if False:'
run "ignore the anchor time entirely" "tot_anchor_moves or push_anchor_fixes"

mut missiongen/timing.py '        held = int(hold_s) if (hold_s and r["to"] == ANCHOR_WP["push"]) else 0' \
                         '        held = 0'
run "drop the hold from the card" "hold_adds"

mut missiongen/timing.py '        held = int(hold_s) if (hold_s and r["to"] == ANCHOR_WP["push"]) else 0' \
                         '        held = int(hold_s) if hold_s else 0'
run "hold at every point instead of the push point" "hold_adds"

mut missiongen/timing.py '    return float(speed) / _MS_PER_KT * math.cos(math.radians(to_deg - track_deg))' \
                         '    return abs(float(speed) / _MS_PER_KT * math.cos(math.radians(to_deg - track_deg)))'
run "turn every headwind into a tailwind" "wind_is_symmetric"

mut missiongen/timing.py '    tol = TOL_S if anchor == "tot" else PUSH_TOL_S if anchor == "push" else TOL_S' \
                         '    tol = PUSH_TOL_S'
run "give the TOT the push tolerance" "tot_window_is_thirty or tot_anchor_moves"

mut missiongen/timing.py '        if t["to"] == tl["anchor_wp"]:\n            tol = tl["tolerance_s"]' \
                         '        if False:\n            tol = tl["tolerance_s"]'
run "grade the anchor point with the loose window" "tot_window_is_thirty"

mut missiongen/timing.py '    if not (0 <= h < 24 and 0 <= mi < 60 and 0 <= s < 60):' '    if False:'
run "accept 25:00 as a clock time" "parser_refuses"

echo "== the file =="

mut missiongen/timing.py '            p.ETA_locked = bool(locked)' '            p.ETA_locked = True'
run "lock the player\x27s ETAs" "unlocked or say_do_check_passes"

mut missiongen/timing.py '            p.ETA = int(t["eta_s"] + offset_s)' '            p.ETA = int(t["eta_s"])'
run "put the package on the player\x27s own timeline" "two_minutes_ahead"

mut missiongen/timing.py '            if locked:\n                p.speed_locked = False' '            pass'
run "lock the package\x27s speed as well as its time (ME refuses to save)" "two_minutes_ahead"

mut missiongen/builder.py '            _tm.apply_to_group(g, tl, locked=True, offset_s=-lead_s)' \
                          '            _tm.apply_to_group(g, tl, locked=False, offset_s=-lead_s)'
run "leave the package unlocked so it does not fly the card" "two_minutes_ahead"

mut missiongen/builder.py '            m.start_time = tl["mission_start"]' '            pass'
run "print the moved clock but never move the mission" "mission_clock_is_the_moved_one or say_do_check_passes"

mut missiongen/builder.py '        _tm.apply_to_group(player_group, tl, locked=False)' '        pass'
run "print ETAs on the card and write none in the file" "carry_the_cards_etas or say_do_check_passes"

mut missiongen/builder.py '            g.late_activation = True' '            g.late_activation = False'
run "spawn the package at mission start" "two_minutes_ahead"

echo "== the paperwork =="

mut missiongen/builder.py '            lines += [""] + _tm1.brief_lines(self._timing, where)' '            pass'
run "leave the timeline out of the in-game brief" "in_game_brief_prints or say_do_check_passes"

mut missiongen/brief.py '    if stats.get("timing"):\n        # THE CLOCK ON THE CARD' '    if False:\n        # THE CLOCK ON THE CARD'
run "leave the timeline out of the PDF/markdown brief" "documents_print_the_same_clock"

mut missiongen/brief.py '    moved = (ctx.get("stats") or {}).get("start_clock")' '    moved = None'
run "print the dawn preset in the DTG after the clock moved" "dtg_follows"

mut missiongen/builder.py '            stats["start_clock"] = tl["start_clock"][:5]' '            pass'
run "forget to tell the paperwork the clock moved" "dtg_follows or say_do_check_passes"

echo "== the say/do check =="

mut missiongen/saydo.py '        if int(getattr(p, "ETA", 0) or 0) != int(t["eta_s"]):' '        if False:'
run "accept a waypoint whose ETA drifted" "eta_drifted"

mut missiongen/saydo.py '        if getattr(p, "ETA_locked", False):' '        if False:'
run "accept a locked player point" "locked_player_point"

mut missiongen/saydo.py '            if clock != t["eta"]:' '            if False:'
run "accept a clock that moved after the plan" "moved_after_the_plan"

mut missiongen/saydo.py '    for name in rows:\n        if name not in seen:' '    for name in ():\n        if name not in seen:'
run "accept a renamed waypoint" "renamed_waypoint"

mut missiongen/saydo.py '            and anchor_clock not in brief_text:' '            and False:'
run "let the brief omit the anchor" "anchor_missing_from_the_brief"

mut missiongen/saydo.py '                     (check_timing, (m, player_group, timing, text))):' \
                        '                     ):'
run "never run the timing check at all" "planted_drift_reaches"

echo "== the coach =="

mut missiongen/timing_coach.py 'ANCHOR_MULT = 2' 'ANCHOR_MULT = 1'
run "score the anchor like any other point" "anchor_double"

mut missiongen/timing_coach.py 'F_ARM = 8879' 'F_ARM = 8899'
run "put the arm flag on the White Knights block" "inside_its_flag_block"

mut missiongen/timing_coach.py '            if name != "TAKEOFF":\n                rule(f"Timing grade: {name} missed",' \
                               '            if False:\n                rule(f"Timing grade: {name} missed",'
run "never grade a point flown past outside the zone" "inside_its_flag_block"

mut missiongen/builder.py '        if r.timing_coach:\n            from . import timing_coach as _tc' \
                          '        if True:\n            from . import timing_coach as _tc'
run "attach the coach when nobody asked" "no_coach_and_no_package"

mut missiongen/builder.py '        if r.timing_package:\n            pkg = self._launch_timing_package' \
                          '        if True:\n            pkg = self._launch_timing_package'
run "launch the package when nobody asked" "no_coach_and_no_package or ride_three"

echo "== the recipe =="

mut missiongen/recipe.py '            if self.timing_anchor == "takeoff":\n                raise RecipeError(' \
                         '            if False:\n                raise RecipeError('
run "accept a time with a takeoff anchor" "needs_an_anchor"

echo "== the rides =="

mut missiongen/data/mission_templates.json '"timing_at": "05:45"' '"timing_at": "05:44"'
run "move ride 2\x27s TOT off the time its brief quotes" "hand_written_briefs or fixes_the_anchor"

mut missiongen/data/mission_templates.json '"timing_hold_min": 3' '"timing_hold_min": 0'
run "take the hold out of ride 4" "fixes_the_anchor"

mut missiongen/data/mission_templates.json '"timing_package": true' '"timing_package": false'
run "take the package out of ride 3" "ride_three or fixes_the_anchor"

echo
echo "caught $PASS / $((PASS+WEAK))  (weak: $WEAK)"
[ "$WEAK" -eq 0 ]
