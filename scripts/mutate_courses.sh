#!/usr/bin/env bash
# Prove the Training Pipeline by breaking it.
#
# WHAT IS BEING PROTECTED. courses.py resolves a course against the shelf so
# it can never claim a ride the Library lacks; the F-4E course keeps its
# three-school order, its history-first FRS and its uncoached check ride;
# planned units are shown with a reason; the kit ships the program, the
# gradesheet and the readings and no missions; the site has the fourth door
# and opens cards with the course's jet only where offered. Each mutation is
# a way one of those could quietly stop being true while the suite stayed green.
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
FILES=(
  missiongen/courses.py
  missiongen/course_kit.py
  missiongen/data/courses.json
  missiongen/data/courses/pipeline_howto.md
  server/app.py
  frontend/index.html
)
for f in "${FILES[@]}"; do mkdir -p "$SNAP/$(dirname "$f")"; cp "$f" "$SNAP/$f"; done

baseline() {
  find missiongen tests frontend server -type f \( -name '*.py' -o -name '*.json' -o -name '*.md' -o -name '*.html' \) ! -path '*/__pycache__/*' -print0 \
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
       tests/test_courses.py -q -x -k "$k" > /tmp/mut_courses.log 2>&1; then
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

baseline_green tests/test_courses.py

echo "== the shelf check =="

mut missiongen/courses.py '    if v is None:\n        raise ValueError(f"course unit {unit.get(\x27id\x27)!r} names an unknown card {key!r}")' \
                          '    if v is None:\n        v = {}'
run "accept a card the Library does not have" "shelf_lacks"

mut missiongen/courses.py '        if unit["aircraft"] not in (choices.get(era) or []):' '        if False:'
run "prefer a jet the card cannot fly" "does_not_offer"

mut missiongen/courses.py '    if not rides:\n        raise ValueError' '    if False:\n        raise ValueError'
run "accept an empty ride range" "ride_range_must_exist"

mut missiongen/courses.py '    if reading_path(doc) is None:' '    if False:'
run "accept a reading that is not on disk" "ride_range_must_exist"

mut missiongen/courses.py '                if uid in seen:' '                if False:'
run "let two units share an id" "unique_within"

mut missiongen/courses.py 'if not doc or "/" in doc' 'if not doc or False'
run "let a reading name be a path" "bare_names or refuses_paths"

echo "== the F-4E course =="

mut missiongen/data/courses.json '"key": "pp_8_bnai",' '"key": "pp_8_bnai_coach",'
run "make the coached B\x27NAI the check ride" "ends_with_a_check_ride or tactical_checkout"

mut missiongen/data/courses.json '"requires_school": "upt",' '"requires_school": null,'
run "let the FRS need no UPT" "three_schools_in_pipeline_order"

mut missiongen/data/courses.json '"from": 4,' '"from": 1,'
run "put the contact rides in the tactical checkout too" "tactical_checkout"

mut missiongen/courses.py '            "status": "ready", "rides": 0}\n\n\ndef _planned' '            "status": "ready", "rides": 1}\n\n\ndef _planned'
run "count a reading as a ride" "counts_add_up"

mut missiongen/courses.py '    return {"kind": "planned", "id": unit["id"], "label": unit["label"],\n            "why": unit.get("why", ""), "status": "planned", "rides": 0}' \
                          '    return {"kind": "planned", "id": unit["id"], "label": unit["label"],\n            "why": "", "status": "planned", "rides": 0}'
run "drop the reason from a planned unit" "shown_with_a_reason"

mut missiongen/courses.py '            "ready": sum(1 for u in units if u["status"] == "ready"),' '            "ready": len(units),'
run "count planned units as ready" "shown_with_a_reason"

echo "== the kit =="

mut missiongen/course_kit.py '        z.writestr("Gradesheet.csv", gradesheet_csv(course))' '        pass'
run "ship a kit without the gradesheet" "carries_programme"

mut missiongen/course_kit.py '                    if u["kind"] == "reading":\n                        z.writestr' '                    if False:\n                        z.writestr'
run "ship a kit without the readings" "carries_programme"

mut missiongen/course_kit.py '                if u["kind"] != "reading":\n                    continue\n                md = _courses.reading_text(u["doc"]) or ""' \
                             '                if True:\n                    continue\n                md = ""'
run "print a program without the chapters" "programme_pdf_prints"

mut missiongen/courses.py '                                 "kind": "ride", "check": u["check"]})' '                                 "kind": "ride", "check": False})'
run "lose the check-ride flag on the gradesheet" "carries_programme"

mut server/app.py '    md = _courses_mod.reading_text(doc) if doc in docs else None' '    md = _courses_mod.reading_text(doc)'
run "serve any file on disk as a reading" "refuses_paths"

echo "== the door =="

mut frontend/index.html '  if(pref&&pref.aircraft&&acChoices(t, libState.era).includes(pref.aircraft)) libState.aircraft=pref.aircraft;' \
                        '  if(pref&&pref.aircraft) libState.aircraft=pref.aircraft;'
run "hand a card a jet it does not offer" "only_where_offered"

mut frontend/index.html '  const fixed=!tr.configurable;' '  const fixed=false;'
run "draw the empty series wizard on fixed tracks again" "no_empty_series_wizard"

mut missiongen/data/courses/pipeline_howto.md 'That record lives in your browser and nowhere else; nothing about your progress is sent anywhere.' 'That record is kept.'
run "stop telling the student where his record lives" "honest_about_what_they_are"

echo
echo "caught $PASS / $((PASS+WEAK))  (weak: $WEAK)"
[ "$WEAK" -eq 0 ]
