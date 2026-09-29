#!/usr/bin/env bash
# Prove the check-ride engine by breaking it.
#
# WHAT IS BEING PROTECTED. checkride.py grades a fingertip check the way an
# instructor does: time-in-band per item read off LEAD's state, a ratio made
# of paired counters (no division in the Editor), a timed rejoin, three
# critical items, U/F/G/E per item and Q/Q-/U overall, silence on the check
# and coach-on for the pre-check. timing_coach's check mode does the same
# for the timing phase. Each mutation is a way one of those could quietly
# stop being true while the suite stayed green.
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
FILES=(
  missiongen/checkride.py
  missiongen/formation.py
  missiongen/timing_coach.py
  missiongen/courses.py
  missiongen/data/courses.json
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
       tests/test_checkride.py -q -x -k "$k" > /tmp/mut_checkride.log 2>&1; then
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

baseline_green tests/test_checkride.py

echo "== the arithmetic =="

mut missiongen/checkride.py 'LADDER = (("E", 10, 9), ("G", 4, 3), ("F", 2, 1))' 'LADDER = (("E", 10, 8), ("G", 4, 3), ("F", 2, 1))'
run "loosen the E ratio in the ladder" "ladder_is_ninety"

mut missiongen/checkride.py '                tot = [A.IncreaseFlag(f["e_tot"], 9), A.IncreaseFlag(f["g_tot"], 3),' '                tot = [A.IncreaseFlag(f["e_tot"], 8), A.IncreaseFlag(f["g_tot"], 3),'
run "grow the total counter by 8 instead of 9 (E at 80 %)" "counters_grow"

mut missiongen/checkride.py '            e = C.FlagIsLessThanFlag(f["e_tot"], f["e_in"])' '            e = C.FlagIsLessThanFlag(f["e_in"], f["e_tot"])'
run "compare the E counters the wrong way round" "counters_grow"

mut missiongen/checkride.py 'F_ARM = 8700            # joined; grading is live' 'F_ARM = 8879            # joined; grading is live'
run "put the arm flag on the timing coach block" "check_block_and_no_other"

echo "== the framework =="

mut missiongen/checkride.py '        lead_level = [C.UnitBankWithin(lead.id, -LEVEL_BANK, LEVEL_BANK),' '        lead_level = [C.UnitBankWithin(me.id, -LEVEL_BANK, LEVEL_BANK),'
run "read the level item off the student instead of lead" "read_off_lead"

mut missiongen/checkride.py '        lead_turn_l = [C.UnitBankWithin(lead.id, -89, -TURN_BANK)]' '        lead_turn_l = [C.UnitBankWithin(lead.id, TURN_BANK, 89)]'
run "count only right turns" "both_ways"

mut missiongen/checkride.py '        inside = lambda r: C.UnitInMovingZone(me.id, r, lead.id)          # noqa: E731' '        inside = lambda r: C.UnitInMovingZone(me.id, r * 2, lead.id)      # noqa: E731'
run "double every band" "read_off_lead or critical_items"

mut missiongen/checkride.py '             [A.SetFlag(F_CRIT), A.SetFlagValue(F_CRIT_WHY, 1),' '             [A.SetFlagValue(F_CRIT_WHY, 1),'
run "let the collision band not be critical" "critical_items"

mut missiongen/checkride.py '        rule("Check card: overall U", [after(6), C.FlagIsTrue(F_CRIT)], [msg(f"OVERALL: U — re-fly the check.", 60)])' '        rule("Check card: overall U", [after(6), C.FlagIsTrue(F_ANY_U)], [msg(f"OVERALL: U — re-fly the check.", 60)])'
run "let a critical item not fail the check" "critical_items"

mut missiongen/checkride.py '                 [msg(f"F  {lab} — 50 % or better; out of position and corrected.", 40), A.SetFlag(F_ANY_F)])' '                 [msg(f"F  {lab} — 50 % or better; out of position and corrected.", 40)])'
run "let an F item not make the check a Q-" "instructors_letters"

mut missiongen/checkride.py '        rule("Check: rejoined", [C.FlagIsTrue(F_WENT_OUT), C.FlagIsFalse(F_REJOINED), inside(POSITION_M)],' '        rule("Check: rejoined", [C.FlagIsTrue(F_PITCH), C.FlagIsFalse(F_REJOINED), inside(POSITION_M)],'
run "credit a rejoin without a departure" "rejoin_is_graded"

mut missiongen/formation.py '    if check != "check":\n        _coach(m, prof, lead_g, player_g, warnings)' '    if True:\n        _coach(m, prof, lead_g, player_g, warnings)'
run "leave the coach on during the check" "check_is_silent"

mut missiongen/formation.py '                             warnings, practice=(check == "practice"),' '                             warnings, practice=False,'
run "label the pre-check as the check" "check_is_silent"

echo "== the profile =="

mut missiongen/formation.py '        "check": "check",\n        "legs": [(0, 3, 0, 0), (-45, 2, 0, 0), (0, 1, 0, 0), (45, 2, 0, 0),' '        "check": "check",\n        "legs": [(0, 3, 0, 0), (45, 2, 0, 0), (0, 1, 0, 0), (45, 2, 0, 0),'
run "make the check profile differ from the pre-check" "same_legs"

mut missiongen/formation.py '    return int(sum(minutes for _dh, minutes, _dft, _dkt in prof["legs"]) * 60)' '    return int(sum(minutes for _dh, minutes, _dft, _dkt in prof["legs"]) * 60) + 60'
run "call the pitchout a minute after the legs end" "same_legs"

echo "== the timing check =="

mut missiongen/timing_coach.py '                     + ([] if check else [msg(text)]))' '                     + [msg(text)])'
run "let the timing check talk" "timing_check_is_silent"

mut missiongen/timing_coach.py '            if anchor_late:\n                rule("Timing check: critical",' '            if False:\n                rule("Timing check: critical",'
run "drop the late-anchor critical item" "timing_check_is_silent"

mut missiongen/timing_coach.py 'TIGHT_S = 10            # +/-10 s: the E window on a check ride' 'TIGHT_S = 30            # +/-10 s: the E window on a check ride'
run "make the E window as wide as the G window" "timing_check_is_silent"

echo "== the course =="

mut missiongen/data/courses.json '"key": "timing_5_check",\n        "check": true' '"key": "timing_5_check",\n        "check": false'
run "take the check flag off the timing check" "ends_in_a_check or gradesheet_flags"

mut missiongen/courses.py '        "check": bool(unit.get("check")),\n    }\n\n\ndef _reading' '        "check": False,\n    }\n\n\ndef _reading'
run "never flag a track unit as a check" "ends_in_a_check or gradesheet_flags"

echo
echo "caught $PASS / $((PASS+WEAK))  (weak: $WEAK)"
[ "$WEAK" -eq 0 ]
