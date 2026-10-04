#!/usr/bin/env bash
# Prove the shelf-and-upload guards by breaking them.
#
# THE DEFECT CLASS HERE IS NOT ARITHMETIC, IT IS DESCRIPTION DRIFT.
#
# All three bugs these guards exist for were one shape: a place in the product
# still describing a product that had moved on. `packs.install` learned
# `.sspack` and the file picker did not. Bundled packs were deleted and the
# review page kept calling `_bundled()`. Packs became the published artifact
# and the Library kept minting a card per track beside them.
#
# None of it was reachable by reading one file, and none of it failed loudly.
# Two of the three were only ever visible from a browser, and the third only
# after FOLLOWING the redirect a successful upload returns — which is why the
# guards below include a real page in a real Chromium, and why the mutations
# have to be run against those and not only against source text.
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
FILES=(
  frontend/index.html
  server/admin.py
  README.md
  server/app.py
  missiongen/packs.py
  missiongen/pattern.py
  missiongen/recipe.py
)
for f in "${FILES[@]}"; do mkdir -p "$SNAP/$(dirname "$f")"; cp "$f" "$SNAP/$f"; done

baseline() {
  find frontend server missiongen tests README.md -type f \
       \( -name '*.py' -o -name '*.json' -o -name '*.html' -o -name '*.md' \) \
       ! -path '*/__pycache__/*' -print0 | sort -z | xargs -0 md5sum
}
baseline > "$SNAP/baseline.txt"
purge_pyc() { find server missiongen tests -name __pycache__ -type d -prune \
              -exec rm -rf {} + 2>/dev/null || true; }
restore() { purge_pyc; for f in "${FILES[@]}"; do cp "$SNAP/$f" "$f"; done; }
trap restore EXIT

PASS=0; WEAK=0

# Two of these guards launch a browser, so the harness aims each mutation at
# the narrowest -k that can catch it rather than running the file.
run() {
  local name="$1" k="$2"
  if PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:vendor python3 -m pytest \
       tests/test_library_shelf.py tests/test_pattern.py -q -x -k "$k" > /tmp/mut_shelf.log 2>&1; then
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

echo "== the shelf =="

# THE BUG ROB SAW. Restoring `trackItems()` is the exact code that was there.
mut frontend/index.html 'function libItems(){ return (Object.entries(OPT.templates)' \
  'function libItems(){ return Object.entries(OPT.tracks||{}).map(([k,t])=>({k:\x27track_\x27+k,track:t,label:t.label,eras:t.eras,default_map:t.default_map,recipe:{},kind:\x27full\x27,tasked:true,role:\x27training\x27,premise:t.premise,threat:1,players:\x27SP\x27,module:null,featured:!!t.featured,new:true})).concat(Object.entries(OPT.templates)'
run "shelve a syllabus that has no pack, and duplicate every one that has" \
    "shelf_is_not_built or real_shelf"

# The half that must NOT change: hiding the card cannot delete the panel.
mut frontend/index.html '  if(k.startsWith(\x27track_\x27)) return openTrack(k.slice(6));' \
                        '  if(false) return null;'
run "hide the card and take every old track link down with it" \
    "track_panel_is_still_reachable or real_shelf"

# The older half of the same rule, from v1.76.0.
mut frontend/index.html '.filter(([k,v])=>v&&!k.startsWith(\x27_\x27)&&!v.quick&&!trackOf(k))' \
                        '.filter(([k,v])=>v&&!k.startsWith(\x27_\x27)&&!v.quick)'
run "scatter 44 numbered rides through an alphabetical grid" \
    "ride_that_belongs_to_a_track or real_shelf"

echo "== the upload =="

# THE PICKER BUG, verbatim: what the attribute said for two releases.
mut server/admin.py "accept='.sspack,.zip,.miz'" "accept='.zip,.miz'"
run "gray out the one extension this product builds" "picker_offers_every_extension"

mut server/admin.py "accept='.sspack,.zip,.miz'" "accept='.miz,.zip'"
run "drop .sspack while still looking like a considered list" \
    "picker_offers_every_extension"

# ...and the note, which is what an author reads when the picker confuses him.
mut server/admin.py '"<p class=note>A <b>.sspack</b> built by <code>scripts/build_pack.py</code> "' \
                    '"<p class=note>A <b>.zip</b> of missions. Also a "'
run "teach the author to rename the product's own output" \
    "upload_note_leads_with_the_format"

# THE INTERNAL ERROR, put back where it was.
mut server/admin.py '    def esc(v):\n        return html.escape(str(v if v is not None else ""))' \
                    '    flash += str(_packs._bundled().get(pid) or "")\n\n    def esc(v):\n        return html.escape(str(v if v is not None else ""))'
run "call a function deleted two releases ago on the page after every upload" \
    "admin_calls_nothing or uploading_a_pack_lands"

# The same shape from the other side: a page that never gets loaded cannot
# fail, so the end-to-end guard must FOLLOW the redirect rather than stop at
# the 303 the way the old delivery test did.
mut server/admin.py '        return _packs_page("That pack is not installed on this server.")' \
                    '        raise RuntimeError("boom")'
run "make the review page raise for a pack that is not there" \
    "review_page_survives or uploading_a_pack_lands"

echo "== the payload behind it =="

mut server/app.py '    for man in _packs.list_packs():' \
                  '    for man in []:'
run "install a pack and render no card for it" \
    "payload_offers_the_pack or real_shelf"

mut server/app.py '        t["published"] = installed_pack(tid) is not None' \
                  '        t["published"] = True'
run "claim every syllabus is published" "payload_offers_the_pack or real_shelf"

mut server/app.py '        t["published"] = installed_pack(tid) is not None' \
                  '        t["published"] = False'
run "hide the download for a syllabus that IS published" "real_shelf"

echo "== the waypoint story, and the credit =="

mut README.md 'a curated training ride whose printed syllabus IS the route' \
              'a special ride whose printed brief IS the route'
run "tell two-thirds of the waypoint story again" "waypoint_story"

mut frontend/index.html 'Flight testing &amp; feedback: <b>Tricker</b> · ' ''
run "drop the flight tester from the footer" "flight_tester"

echo "== the pattern conveyor =="

# THE LIMIT ROB HIT: "Pattern Traffic is too limited."
mut missiongen/pattern.py 'MAX_COUNT = 8' 'MAX_COUNT = 4'
run "cap the pattern at four again" "eight_aircraft or ui_offers"

mut frontend/index.html '          <option value="5">5 aircraft</option>\n          <option value="6">6 aircraft</option>\n          <option value="7">7 aircraft</option>\n          <option value="8">8 aircraft</option>\n' ''
run "raise the engine cap and leave the picker at four" "ui_offers"

mut missiongen/pattern.py '    dist = FIRST_FINAL + slot * TRAIL_SPACING' \
                          '    dist = FIRST_FINAL'
run "spawn eight aircraft on the same spot of sky" "spaced_in_trail"

mut missiongen/pattern.py '    return ["landing" if i % 2 == 0 else "takeoff" for i in range(count)]' \
                          '    return ["landing"] * count'
run "make both-sides traffic all-landing" "both_mode"

mut missiongen/recipe.py '        "pattern_count": (1, MAX_COUNT)' \
                         '        "pattern_count": (1, 4)'
run "keep a private copy of the ceiling that can drift" "recipe_enforces"

echo
echo "caught $PASS, weak $WEAK"
[ "$WEAK" -eq 0 ]
