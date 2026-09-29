#!/usr/bin/env bash
# Prove the Academy guards by breaking them.
#
# A test that has never failed on wrong data is a decoration. Each mutation
# below introduces a defect the suite is supposed to catch; a mutation that
# does NOT turn the suite red is a weak guard and gets reported as such.
#
# Restores from a snapshot in /tmp rather than `git checkout <file>` — that
# command has destroyed uncommitted work in this repo three times.
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
# EVERY file any mutation below touches. This list going stale is not a
# theoretical risk: two tracks.py mutations were written before tracks.py was
# added here, so `restore` silently skipped them and the mutated engine was
# committed. The guard below fails the run if a mutation dirties a file the
# snapshot does not cover.
FILES=(
  missiongen/aar.py
  missiongen/aar_grade.py
  missiongen/aar_guide.py
  missiongen/tracks.py
  missiongen/builder.py
  missiongen/data/tracks.json
  missiongen/data/mission_templates.json
  missiongen/support_air.py
  docs/aar-academy-boom.md
  docs/aar-academy-probe.md
  docs/aar-academy-boom.pdf
  docs/aar-academy-probe.pdf
)
for f in "${FILES[@]}"; do mkdir -p "$SNAP/$(dirname "$f")"; cp "$f" "$SNAP/$f"; done

# A CONTENT BASELINE of the whole working tree, taken as-is — including any
# uncommitted work in progress. `git status` is the wrong instrument here: it
# cannot tell a mutation from the change you were already making, which is how
# a stale FILES list went unnoticed. This compares the tree to itself.
baseline() {
  find missiongen server frontend tests docs scripts -type f \
       \( -name '*.py' -o -name '*.json' -o -name '*.html' -o -name '*.md' \
          -o -name '*.pdf' \) \
       ! -path '*/__pycache__/*' -print0 | sort -z | xargs -0 md5sum
}
baseline > "$SNAP/baseline.txt"

purge_pyc() { find missiongen tests -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true; }
restore() { purge_pyc; for f in "${FILES[@]}"; do cp "$SNAP/$f" "$f"; done; }
trap restore EXIT

PASS=0; WEAK=0

run() {   # run <name> <expected-failing-test-substring> [file]
  local name="$1" k="$2" f="${3:-tests/test_aar_academy.py}"
  if PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=vendor python3 -m pytest "$f" -q -x \
       -k "$k" > /tmp/mut.log 2>&1; then
    echo "  WEAK      $name — suite still green"
    WEAK=$((WEAK+1))
  else
    echo "  caught    $name"
    PASS=$((PASS+1))
  fi
  restore
  # Anything that differs from the baseline after a restore is a file this
  # mutation touched and FILES does not cover. Two tracks.py mutations were
  # written before tracks.py was in FILES, so `restore` skipped them and the
  # mutated engine got committed. Stop rather than let that happen twice.
  local drift
  drift=$(baseline | diff - "$SNAP/baseline.txt" | grep '^<' || true)
  if [ -n "$drift" ]; then
    echo "  ABORT     restore missed a file — add it to FILES:"
    echo "$drift" | sed 's/^< [0-9a-f]*  /            /'
    exit 2
  fi
}

# The printed guides are BUILT from the module, so a mutation to aar_guide.py
# does not reach the tests until the guides are regenerated. Without this the
# guide mutations pass against stale documents and report "caught" for the
# wrong reason.
rebuild_guides() { PYTHONPATH=vendor python3 scripts/build_aar_guides.py >/dev/null 2>&1; }

run_guide() {   # like run(), but regenerates the guides either side
  rebuild_guides
  run "$@"
  rebuild_guides
}

echo "== mutating the reconciled numbers =="
python3 - <<'EOF'
import re,pathlib
p=pathlib.Path('missiongen/aar.py'); s=p.read_text()
s=s.replace('" - CLOSURE, LAST FEW FEET: bleed it to about ONE FOOT PER SECOND —",','')
p.write_text(s)
EOF
run "drop the final-closure number" "closure_phases"

python3 - <<'EOF'
import pathlib
p=pathlib.Path('missiongen/aar.py'); s=p.read_text()
s=s.replace("it is OUR proficiency mark, set","it is the doctrinal standard, set")
s=s.replace('"   it is not quoted from anyone —','"   it is quoted from ATP-56 —')
p.write_text(s)
EOF
run "let the 60 s standard borrow doctrine's authority" "60_second_standard_admits"

echo "== mutating the grader's honesty =="
python3 - <<'EOF'
import pathlib
p=pathlib.Path('missiongen/aar_grade.py'); s=p.read_text()
i=s.index('"NOT MEASURED, and no card in this product will pretend otherwise:"')
j=s.index('"The tolerances are deliberately WIDE.')
p.write_text(s[:i]+s[j:])
EOF
run "delete the not-measured disclaimer" "contact_is_not_measured or admits_what_is_not_measured"

python3 - <<'EOF'
import pathlib
p=pathlib.Path('missiongen/aar_grade.py'); s=p.read_text()
p.write_text(s.replace("CLOSE_M = 150.0","CLOSE_M = 1500.0"))
EOF
run "widen the working envelope past the 1 nm air start" "close_envelope"

python3 - <<'EOF'
import pathlib
p=pathlib.Path('missiongen/aar_grade.py'); s=p.read_text()
p.write_text(s.replace("STABLE_BAND_KT = 10.0","STABLE_BAND_KT = 2.0"))
EOF
run "tighten the speed band to where a correction costs credit" "speed_band"

python3 - <<'EOF'
import pathlib
p=pathlib.Path('missiongen/aar_grade.py'); s=p.read_text()
p.write_text(s.replace("CALIBRATE_S = 20","CALIBRATE_S = 0"))
EOF
run "score before the VR calibration window" "calibration_window"

echo "== mutating the wiring =="
python3 - <<'EOF'
import pathlib
p=pathlib.Path('missiongen/builder.py'); s=p.read_text()
p.write_text(s.replace("if grade and aar_key and player_group is not None:",
                       "if False and grade and aar_key and player_group is not None:"))
EOF
run "stop attaching the grader while cards still claim it" "writes_grading_triggers"

python3 - <<'EOF'
import pathlib
p=pathlib.Path('missiongen/aar_grade.py'); s=p.read_text()
p.write_text(s.replace('        _menu(m, C, A, Tr, player_group, prof, ias, alt)\n',''))
EOF
run "remove the F10 self-requested hints" "writes_grading_triggers"

echo "== mutating the syllabus =="
python3 - <<'EOF'
import json,pathlib
p=pathlib.Path('missiongen/data/mission_templates.json')
d=json.loads(p.read_text())
d["aar_boom_6_turn"].pop("track")          # a ride quietly leaves its track
p.write_text(json.dumps(d,indent=1,ensure_ascii=False))
EOF
run "drop a ride out of the track" "contiguous or eleven_rides or hidden_from_the_loose_grid"

python3 - <<'EOF'
import json,pathlib
p=pathlib.Path('missiongen/data/mission_templates.json')
d=json.loads(p.read_text())
d["aar_boom_9_transfer"]["aar_grade"]="quiet"   # grade the capstone
p.write_text(json.dumps(d,indent=1,ensure_ascii=False))
EOF
run "grade the ungraded capstone" "ungraded_capstone"

python3 - <<'EOF'
import json,pathlib
p=pathlib.Path('missiongen/data/mission_templates.json')
d=json.loads(p.read_text())
d["aar_boom_5_reset"].setdefault("library",{})["featured"]=True
p.write_text(json.dumps(d,indent=1,ensure_ascii=False))
EOF
run "let a ride compete with its own track for the featured row" "still_featured"

python3 - <<'EOF'
import json,pathlib
p=pathlib.Path('missiongen/data/mission_templates.json')
d=json.loads(p.read_text())
d["aar_probe_4_flow"]["brief"]=[l for l in d["aar_probe_4_flow"]["brief"]
                                if not l.startswith("NEW DEMAND")]
p.write_text(json.dumps(d,indent=1,ensure_ascii=False))
EOF
run "let a ride stop stating its one new demand" "one_new_demand"

python3 - <<'EOF'
import json,pathlib
p=pathlib.Path('missiongen/data/tracks.json')
d=json.loads(p.read_text())
d["aar_boom"]["premise"]=d["aar_boom"]["premise"].replace("Eleven","Eight")
p.write_text(json.dumps(d,indent=1,ensure_ascii=False))
EOF
run "let the track card miscount its own rides" "real_ride_count"

python3 - <<'EOF'
import json,pathlib
p=pathlib.Path('missiongen/data/tracks.json')
d=json.loads(p.read_text())
d["aar_probe"]["tanker"]="kc135"     # hand a Hornet a boom tanker
p.write_text(json.dumps(d,indent=1,ensure_ascii=False))
EOF
run "give the probe lane a boom tanker" "share_an_airframe"

echo "== mutating the printed guides =="
cp docs/aar-academy-boom.md docs/aar-academy-probe.md
run "ship the boom guide as the Navy guide" "not_the_same_document"

python3 - <<'EOF'
import pathlib
p=pathlib.Path('docs/aar-academy-probe.md'); s=p.read_text()
p.write_text(s.replace("cannot see a refuelling event","sees everything you do"))
EOF
run "let the printed guide drop the honest-numbers note" "honest_numbers_note"

python3 - <<'EOF'
import json,pathlib
p=pathlib.Path('missiongen/data/mission_templates.json')
d=json.loads(p.read_text())
d["aar_boom_4_flow"]["label"]="AAR Boom 4 — The Flow"   # back to a codename
p.write_text(json.dumps(d,indent=1,ensure_ascii=False))
EOF
run "let a ride title go back to an evocative codename" "titles_say_what"

python3 - <<'EOF'
import json,pathlib
p=pathlib.Path('missiongen/data/mission_templates.json')
d=json.loads(p.read_text())
d["aar_probe_6_turn"]["label"]="Air-to-Air Refuelling 6 — Refuelling Through the Turn"
p.write_text(json.dumps(d,indent=1,ensure_ascii=False))
EOF
run "drop the lane from a title so two files collide" "name_their_own_lane or share_a_title"

echo "== mutating the wizard =="
python3 - <<'EOF'
import pathlib
p=pathlib.Path('missiongen/aar.py'); s=p.read_text()
# back to a deny-list that fails OPEN
s=s.replace("    return receiver_id in AAR_RECEIVERS",
            "    return receiver_id not in ('P-51D',)")
p.write_text(s)
EOF
run "make the receiver list fail open again" "cannot_refuel_are_refused or fails_closed" tests/test_aar_wizard.py

python3 - <<'EOF'
import pathlib
p=pathlib.Path('missiongen/aar.py'); s=p.read_text()
p.write_text(s.replace('"F-14BU": PROBE,', '"F-14B(U)": PROBE,'))
EOF
run "key the F-14B(U) on its display label instead of its type id" "pending_module_is_keyed or right_lane" tests/test_aar_wizard.py

python3 - <<'EOF'
import pathlib
p=pathlib.Path('missiongen/tracks.py'); s=p.read_text()
p.write_text(s.replace('out[key] = cfg.get("provisional_id") or cfg["label"]',
                       'out[key] = cfg["label"]'))
EOF
run "map pending modules to the label the wizard shows" "f14bu_is_reachable or pending_module_is_keyed" tests/test_aar_wizard.py

python3 - <<'EOF'
import pathlib
p=pathlib.Path('missiongen/tracks.py'); s=p.read_text()
p.write_text(s.replace('        if era.startswith("_") or era == "wwii" or era not in playable:',
                       '        if era.startswith("_") or era == "wwii":'))
EOF
run "offer an era the free map cannot build" "only_offers_eras" tests/test_aar_wizard.py

python3 - <<'EOF'
import pathlib
p=pathlib.Path('missiongen/tracks.py'); s=p.read_text()
# stop filtering the offered aircraft by service window
p.write_text(s.replace("        for key in aar.receivers_for(lane, era, service, era_cfg, keyed):",
                       "        for key in aar.receivers_for(lane, era, service, {}, keyed):"))
EOF
run "offer an aircraft that did not exist in that era" "was_in_service or did_not_exist_yet" tests/test_aar_wizard.py

python3 - <<'EOF'
import json,pathlib
p=pathlib.Path('missiongen/data/mission_templates.json')
d=json.loads(p.read_text())
d["aar_boat"]["by_era"]["modern"]={"aircraft":"FA_18C_hornet","tanker_type":"kc130"}
p.write_text(json.dumps(d,indent=1,ensure_ascii=False))
EOF
run "replace the carrier-organic tanker with the lane default" "carrier_organic_card" tests/test_aar_wizard.py

python3 - <<'EOF'
import json,pathlib
p=pathlib.Path('missiongen/data/mission_templates.json')
d=json.loads(p.read_text())
d["aar_boom_2_closure"]["eras"]=["modern"]     # card narrower than the wizard
p.write_text(json.dumps(d,indent=1,ensure_ascii=False))
EOF
run "let a ride advertise fewer eras than the wizard offers" "advertises_exactly_the_eras" tests/test_aar_wizard.py

echo "== era availability, and the guide that has to describe it =="
python3 - <<'EOF'
import re, pathlib
p = pathlib.Path('missiongen/aar.py'); s = p.read_text()
old = '"eras": ["coldwar", "modern"],\n        "naval": True,\n        "organic": True,\n        "basis": "tuned for DCS; the Cold War'
assert old in s, "anchor gone"
p.write_text(s.replace(old, old.replace('["coldwar", "modern"]', '["coldwar"]'), 1))
EOF
run "hide the KA-6D from the modern era again" "a6e_buddy_tanker or retired_carrier_tankers" tests/test_aar.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar.py'); s = p.read_text()
old = '"service": [1970, 1997],'
assert old in s, "anchor gone"
p.write_text(s.replace(old, "", 1))
EOF
run "drop a tanker's service window" "every_tanker_has_a_service_window" tests/test_aar.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar_guide.py'); s = p.read_text()
old = '    A(_hud_sheet())'
assert old in s, "anchor gone"
p.write_text(s.replace(old, "", 1))
EOF
run_guide "drop the indicator artwork from the printed guide" "prints_the_indicator_artwork" tests/test_aar_academy.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar_guide.py'); s = p.read_text()
old = '"## Kneeboard — the position indicator", "", "```",'
assert old in s, "anchor gone"
p.write_text(s.replace(old, '"", "", "```",', 1))
EOF
run_guide "drop the indicator card from the printed guide" "carries_every_kneeboard_card" tests/test_aar_academy.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar_guide.py'); s = p.read_text()
# a reportlab call in the markdown twin — the exact defect that 500'd the
# track download minutes before a release
old = '        L += [f"**Period note.** {pn}", ""]'
assert old in s, "anchor gone"
p.write_text(s.replace(old, '        A(Paragraph(f"{pn}", S_SMALL))', 1))
EOF
run "put a PDF call inside the markdown builder" "renders_both_guides" tests/test_aar_academy.py

echo "== reported from the cockpit: store, speed, air start, docs =="
python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/support_air.py'); s = p.read_text()
old = "        _fit_refuelling_store(tk, ttype, aar_key)"
assert old in s, "anchor gone"
p.write_text(s.replace(old, "        pass", 1))
EOF
run "ship the buddy tanker with empty pylons again" "STORE" tests/test_aar_academy.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar.py'); s = p.read_text()
old = '"ias_kt": 290,\n        "max_ias_kt": 310,'
assert old in s, "anchor gone"
p.write_text(s.replace(old, '"ias_kt": 250,\n        "max_ias_kt": 310,', 1))
EOF
run "slow the buddy tanker back down below a Tomcat" "fast_enough_for_a_tomcat" tests/test_aar.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/builder.py'); s = p.read_text()
old = "            u.psi = -math.radians(hdg % 360.0)"
assert old in s, "anchor gone"
p.write_text(s.replace(old, "            pass", 1))
EOF
run "leave psi unset so the jet spawns facing north" "behind_the_tanker" tests/test_aar_academy.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/builder.py'); s = p.read_text()
old = "            hdg = self._tanker_track_heading(tanker)"
assert old in s, "anchor gone"
p.write_text(s.replace(
    old, '            hdg = math.degrees(getattr(tk_unit, "heading", 0.0) or 0.0)', 1))
EOF
run "read the tanker heading before pydcs assigns it" "behind_the_tanker" tests/test_aar_academy.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar.py'); s = p.read_text()
old = "    ias = track_ias_kt(key, receiver_id)"
assert old in s, "anchor gone"
p.write_text(s.replace(old, '    ias = t["ias_kt"]', 1))
EOF
run "print the tanker default instead of the flown speed" "flown_speed or actually_flies" tests/test_aar_academy.py

echo "== reported from the cockpit: the track was below the terrain =="

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar.py'); s = p.read_text()
old = "TERRAIN_CLEARANCE_FT = 3000"
assert old in s, "anchor gone"
p.write_text(s.replace(old, "TERRAIN_CLEARANCE_FT = 0", 1))
EOF
run "put the track back on top of the peaks" "terrain or track_clears or RECEIVER or caucasus" tests/test_aar.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar.py'); s = p.read_text()
old = "TERRAIN_CLEARANCE_FT = 3000"
assert old in s, "anchor gone"
p.write_text(s.replace(old, "TERRAIN_CLEARANCE_FT = 800", 1))
EOF
run "clear the tanker but not the receiver 1,000 ft below it" "terrain or track_clears or RECEIVER or caucasus" tests/test_aar.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar.py'); s = p.read_text()
old = "TERRAIN_MAX_DEFAULT_FT = max(v[0] for v in TERRAIN_MAX_FT.values())"
assert old in s, "anchor gone"
p.write_text(s.replace(old, "TERRAIN_MAX_DEFAULT_FT = min(v[0] for v in TERRAIN_MAX_FT.values())", 1))
EOF
run "let an unlisted map fail open" "unknown_map or terrain" tests/test_aar.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar.py'); s = p.read_text()
old = '    return TANKERS[key].get("max_alt_ft", TANKERS[key]["alt_ft"]) >= \\\n        terrain_floor_ft(map_key)'
assert old in s, "anchor gone"
p.write_text(s.replace(old, "    return True", 1))
EOF
run "offer a Hercules a track above its ceiling" "cannot_climb or terrain or offered" tests/test_aar.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar.py'); s = p.read_text()
old = '    return int(min(max(alt, terrain_floor_ft(map_key)),\n                   t.get("max_alt_ft", alt)))'
assert old in s, "anchor gone"
p.write_text(s.replace(old, "    return int(alt)", 1))
EOF
run "raise the card but not the mission" "terrain or puts_the_tanker or caucasus or printed_guide" tests/test_aar.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar.py'); s = p.read_text()
old = "return int(-(-raw // 1000) * 1000)"
assert old in s, "anchor gone"
p.write_text(s.replace(old, "return int(raw // 1000 * 1000)", 1))
EOF
run "round the briefing altitude DOWN" "caucasus or terrain" tests/test_aar.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar.py'); s = p.read_text()
old = '"caucasus": (18510, "cited")'
assert old in s, "anchor gone"
p.write_text(s.replace(old, '"caucasus": (8510, "cited")', 1))
EOF
run "understate Elbrus on the free map" "caucasus or terrain" tests/test_aar.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar.py'); s = p.read_text()
old = "            if map_key and not clears_terrain(k, map_key):"
assert old in s, "anchor gone"
p.write_text(s.replace(old, "            if False:", 1))
EOF
run "let terrain remove a tanker silently (the KA-6D lesson)" "terrain_removed or excluded" tests/test_aar.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar_guide.py'); s = p.read_text()
old = '         f"Track: **{aar.track_ias_kt(tanker, _type_id(ac))} KIAS at "\n         f"{aar.track_alt_ft(tanker, mp):,} ft**.", "",'
assert old in s, "anchor gone"
new = '         f"Track: **{T[chr(39)+chr(105)+chr(97)+chr(115)+chr(95)+chr(107)+chr(116)+chr(39)]} KIAS", "",'
p.write_text(s.replace(old, new, 1))
EOF
run "revert the markdown guide to the tanker's book altitude" "printed_guide" tests/test_aar.py

python3 - <<'EOF'
import pathlib
p = pathlib.Path('missiongen/aar_guide.py'); s = p.read_text()
old = '        f"<b>{aar.track_ias_kt(tanker, _type_id(ac))} KIAS, "\n        f"{aar.track_alt_ft(tanker, mp):,} ft</b>, on free Caucasus in the "'
assert old in s, "anchor gone"
new = '        f"<b>{aar.TANKERS[tanker][chr(105)+chr(97)+chr(115)+chr(95)+chr(107)+chr(116)]} KIAS, "\n        f"{aar.TANKERS[tanker][chr(97)+chr(108)+chr(116)+chr(95)+chr(102)+chr(116)]:,} ft</b>, on free Caucasus in the "'
p.write_text(s.replace(old, new, 1))
EOF
run "revert the PDF guide to the tanker's book altitude" "printed_guide" tests/test_aar.py


echo
echo "caught $PASS, weak $WEAK"
[ "$WEAK" -eq 0 ]
