#!/usr/bin/env bash
# Prove the position-indicator guards by breaking them.
#
# Split from mutate_aar_academy.sh rather than appended: that script's
# mutations are inline heredocs, and a snippet containing triple-quoted Python
# cannot be nested inside one without the quoting collapsing. It did collapse,
# silently, and the block simply never ran — a mutation suite that reports
# "all caught" while skipping a third of its cases is worse than none.
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
FILES=(
  missiongen/aar_hud.py
  missiongen/aar_grade.py
  missiongen/data/mission_templates.json
)
for f in "${FILES[@]}"; do mkdir -p "$SNAP/$(dirname "$f")"; cp "$f" "$SNAP/$f"; done

baseline() {
  find missiongen tests -type f \( -name '*.py' -o -name '*.json' \) \
       ! -path '*/__pycache__/*' -print0 | sort -z | xargs -0 md5sum
}
baseline > "$SNAP/baseline.txt"
purge_pyc() { find missiongen tests -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true; }
restore() { purge_pyc; for f in "${FILES[@]}"; do cp "$SNAP/$f" "$f"; done; }
trap restore EXIT

PASS=0; WEAK=0
run() {
  local name="$1" k="$2"
  if PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=vendor python3 -m pytest tests/test_aar_hud.py -q -x \
       -k "$k" > /tmp/mut_hud.log 2>&1; then
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

# Each mutation is a one-line sed-style replacement, deliberately: no nested
# quoting, nothing that can silently fail to apply. `mut` verifies the
# substitution actually happened before the test runs.
mut() {   # mut <file> <old> <new>
  python3 - "$@" <<'EOF'
import sys, pathlib
f, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
p = pathlib.Path(f); s = p.read_text()
if old not in s:
    sys.exit(f"MUTATION DID NOT APPLY — {old!r} not in {f}")
p.write_text(s.replace(old, new, 1))
EOF
}

H=missiongen/aar_hud.py
G=missiongen/aar_grade.py

echo "== the axis it must never draw =="
mut $H '"IT DOES NOT SHOW LEFT/RIGHT, and that is deliberate rather than",' \
       '"IT SHOWS LEFT/RIGHT TOO, read off the tanker zone.",' || exit 2
run "claim a lateral cue the sphere cannot measure" "no_lateral_cue"

mut $H '"Color is never the only cue: every state is also a shape, a position",' \
       '"Watch the color.",' || exit 2
run "let color become the only cue" "colour_is_never_the_only_cue"

echo "== fading =="
mut $H '    return {"station", "closure", "contact"}' \
       '    return {"station", "closure", "contact", "quiet"}' || exit 2
run "put the indicator on the silent qualification ride" \
    "quiet_profile_gets_no_indicator or qualification_ride_carries_no"

echo "== thresholds =="
mut $H 'FORE_BAND_KT = 5.0' 'FORE_BAND_KT = 14.0' || exit 2
run "let the indicator say on-speed while the grade is breaking" \
    "bands_are_tighter"

mut $H 'UNSAFE_OVERTAKE_KT = 25.0' 'UNSAFE_OVERTAKE_KT = 40.0' || exit 2
run "let the picture and the spoken warning disagree on unsafe" \
    "safety_threshold_matches"

mut $H 'F_HUD_OFF = 8855' 'F_HUD_OFF = 8816' || exit 2
run "collide the indicator flags with the grader's" "flag_blocks_do_not_overlap"

echo "== saying it twice, and not saying it at all =="
mut $G '        if prof["closure_calls"] and not hud:' \
       '        if prof["closure_calls"]:' || exit 2
run "nag in the corner alongside the picture" "does_not_also_nag"

mut $G '        once("AAR grade: 15 s gate",' \
       '        if hud:
            return True
        once("AAR grade: 15 s gate",' || exit 2
run "fade away the two announcements worth reading" "discrete_calls_survive"

echo "== placement, size and flicker, all reported from the cockpit =="
mut $H 'HORZ = "Left"' 'HORZ = "Center"' || exit 2
run "put it back under the nose" "sits_left_at_eye_level"

mut $H 'SIZE_PCT = 10' 'SIZE_PCT = 22' || exit 2
run "put the size back to double" "about_half_the_size"

mut $H 'MIN_REDRAW_S = 4' 'MIN_REDRAW_S = 0' || exit 2
run "let it redraw the instant anything changes" "redraw_is_rate_limited or carries_the_redraw_lockout"

mut $H 'acts += [A.ClearFlag(F_DRAWN), A.SetFlag(F_DRAWN)]' \
       'acts += [A.SetFlag(F_DRAWN)]' || exit 2
run "set the lockout clock without restarting it" "restarts_the_lockout_clock"

echo "== the mission must OPEN, not merely build =="
mut $H 'getattr(A.PictureAction.HorzAlignment, HORZ).value' \
       'getattr(A.PictureAction.HorzAlignment, HORZ)' || exit 2
run "serialize an enum member instead of its value" "READ_BACK"

echo "== helper gates =="
python3 - <<'EOF'
import json, pathlib
p = pathlib.Path('missiongen/data/mission_templates.json')
d = json.loads(p.read_text())
d["aar_boom_0_fit"]["aar_gates"] = True
p.write_text(json.dumps(d, indent=1, ensure_ascii=False))
EOF
run "put helper gates on a close-in formation ride" \
    "gates_are_on_the_rendezvous or close_in_ride_places_no_gates"

echo
echo "caught $PASS, weak $WEAK"
[ "$WEAK" -eq 0 ]
