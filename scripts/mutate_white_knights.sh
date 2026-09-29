#!/usr/bin/env bash
# Prove the White Knights guards by breaking them.
#
# The content here is TRANSCRIBED from a 1980 squadron's paperwork rather than
# computed, which produces a defect class the rest of this codebase does not
# have: a wrong digit looks exactly like a right one. Several of the mutations
# below are single-digit changes to a delivery planning sheet, and they exist
# to prove that the arithmetic guards would actually notice.
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
FILES=(
  missiongen/wk.py
  missiongen/templates.py
  missiongen/builder.py
  missiongen/data/mission_templates.json
  missiongen/data/tracks.json
  missiongen/data/maps.json
  missiongen/dressing.py
  missiongen/wk_route.py
  missiongen/kneeboard.py
  missiongen/wk_guide.py
  scripts/add_white_knights.py
  missiongen/wk_coach.py
  scripts/build_wk_coach_cards.py
  missiongen/wk_brief.py
  scripts/build_wk_brief_pages.py
  missiongen/recipe.py
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

# The coached B'NAI's guards live in their own file, and it BUILDS MISSIONS —
# a full run is minutes, not seconds, so the harness aims each mutation at the
# narrowest -k that can catch it rather than running the file.
run_coach() {
  local name="$1" k="$2"
  if PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=vendor python3 -m pytest tests/test_wk_coach.py -q -x \
       -k "$k" > /tmp/mut_wk.log 2>&1; then
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

run_pp() {
  local name="$1" k="$2"
  if PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:vendor python3 -m pytest \
       tests/test_proud_phantom_lineup.py -q -x -k "$k" > /tmp/mut_pp.log 2>&1; then
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

run() {
  local name="$1" k="$2"
  if PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=vendor python3 -m pytest tests/test_wk.py -q -x \
       -k "$k" > /tmp/mut_wk.log 2>&1; then
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

# `mut` asserts the anchor exists BEFORE substituting, AND clears __pycache__
# afterwards. Both matter.
#
# THE BYTECODE TRAP, found the hard way. A mutation that changes 11400 to 11500
# leaves the file the SAME SIZE, and CPython invalidates a .pyc on (mtime,
# size). Rewrite a file within the same clock second as the cached .pyc records
# and with an identical size, and the interpreter serves the STALE bytecode —
# the mutation is on disk, the test runs against the old code, and the harness
# reports WEAK for a guard that was never actually challenged. That is the
# "mutation silently never ran" failure this project has already shipped once,
# wearing a different hat.
mut() {
  purge_pyc
  python3 - "$1" "$2" "$3" <<'PY' || { echo "  ANCHOR MISSING in $1"; exit 9; }
import io, sys
# Only two escapes are interpreted, explicitly. `unicode_escape` would be the
# obvious tool and it is the wrong one: these anchors contain em dashes, and
# unicode_escape is latin-1 based, so it would quietly mangle them into a
# string that matches nothing.
def unesc(x):
    return x.replace("\\n", "\n").replace("\\x27", "'")
p, o, n = sys.argv[1], unesc(sys.argv[2]), unesc(sys.argv[3])
s = io.open(p).read()
assert s.count(o) == 1, (p, s.count(o), o[:70])
io.open(p, "w").write(s.replace(o, n))
PY
}

echo "== the floor: two numbers, and which one governs =="

mut missiongen/wk.py '"germany": (500, "host_nation",' '"germany": (300, "host_nation",'
run "let the squadron's own floor apply in West Germany" "floor or germany_raises or briefs_the_floor or quietly_replace"

mut missiongen/wk.py 'FLOOR_DEFAULT_FT = max(v[0] for v in LOW_LEVEL_FLOOR_FT.values())' \
                     'FLOOR_DEFAULT_FT = min(v[0] for v in LOW_LEVEL_FLOOR_FT.values())'
run "let an unlisted theater fail open" "unlisted_theatre"

mut missiongen/wk.py '    return floor_ft(map_key) > FORMATION_MIN_FT' '    return False'
run "stop printing the host-nation block at all" "germany_raises or briefs_the_floor or quietly_replace"

mut missiongen/wk.py 'f"{SINGLE_SHIP_MIN_FT}\x27; FORMATIONS TO {FORMATION_MIN_FT}\x27."]' \
                     'f"{floor_ft(map_key)}\x27."]'
run "substitute the host nation's number for the squadron's" "quietly_replace"

echo "== rides that do not travel =="

mut missiongen/wk.py '"title": "Route Abort", "maps": ["germany"]}' '"title": "Route Abort"}'
run "let Route Abort be flown over a desert" "route_abort_ride or other_checkout_ride"

# Aimed at the CHECK ride's card by anchoring on its own premise text: the
# coached ride is also Sinai-only at threat 4, so a purely structural anchor
# now matches twice and the harness aborts rather than mutating the wrong one.
mut missiongen/data/mission_templates.json '"maps": [\n   "sinai"\n  ],\n  "default_map": "sinai",\n  "quick": false,\n  "library": {\n   "role": "training",\n   "threat": 4,\n   "players": "SP",\n   "new": true,\n   "featured": false,\n   "module": "F-4E",\n   "premise": "Israeli, 1973,' \
                                            '"maps": [\n   "sinai",\n   "germany"\n  ],\n  "default_map": "sinai",\n  "quick": false,\n  "library": {\n   "role": "training",\n   "threat": 4,\n   "players": "SP",\n   "new": true,\n   "featured": false,\n   "module": "F-4E",\n   "premise": "Israeli, 1973,'
run "offer the B'NAI somewhere that is not its birthplace" "pinned_to_sinai"

echo "== transcription: a wrong digit looks exactly like a right one =="

mut missiongen/wk.py '"apex_ft": 5700, "pup_ft": 11400, "climb_deg": 30,\n        "pdp_ft": 4200, "map_ft": 7626,' \
                     '"apex_ft": 5700, "pup_ft": 11500, "climb_deg": 30,\n        "pdp_ft": 4200, "map_ft": 7626,'
run "one digit wrong in a pull-up point" "pull_up_point"

mut missiongen/wk.py '"pdp_ft": 7750, "map_ft": 10590,' '"pdp_ft": 7700, "map_ft": 10590,'
run "one digit wrong in a pull-down point" "pull_down_point"

mut missiongen/wk.py '"release_ft": 3400, "drag_coeff": 1.03,' '"release_ft": 3000, "drag_coeff": 1.03,'
run "one digit wrong in a dive toss release altitude" "apex_formula or DIVE_TOSS_partners"

mut missiongen/wk.py '"apex_ft": 10000, "pup_ft": 13333, "climb_deg": 45,\n        "pdp_ft": 7750, "map_ft": 8133,' \
                     '"apex_ft": 8000, "pup_ft": 10667, "climb_deg": 45,\n        "pdp_ft": 5750, "map_ft": 8133,'
run "recompute a direct sheet from its own dive angle" "DIVE_TOSS_partners"

mut missiongen/wk.py '"turn_radius_ft": 5400, "deg_per_sec": 10, "g": 5' \
                     '"turn_radius_ft": 5400, "deg_per_sec": 14, "g": 5'
run "break the squadron's own turn arithmetic" "turn_performance"

echo "== say/do =="

mut missiongen/wk.py '    L += ["", "== WHAT THIS RIDE DOES NOT MEASURE ==",' '    L += ["", "== NOTES ==",'
run "drop the disclaimer about what triggers cannot see" "no_card_claims"

mut missiongen/wk.py '    if has_counterpart(ride_key, map_key):\n        L += [""] + WINGMAN_NOTE' \
                     '    if False:\n        L += [""] + WINGMAN_NOTE'
run "stop explaining what the AI counterpart is not" "ai_counterpart or promise_and_the_aeroplane"

mut missiongen/wk.py '"weapons functioned. Honest label — DCS triggers cannot model a frag "\n        "pattern. This is a distance-and-time approximation and nothing more.",' \
                     '"weapons functioned, measured exactly by the mission.",'
run "claim a frag model DCS does not have (ride 4)" "frag_claim"

mut missiongen/wk.py '"functioned. Honest label — DCS triggers cannot model a frag pattern. "' \
                     '"functioned, measured exactly by the mission. "'
run "claim a frag model DCS does not have (ride 7)" "frag_claim"

mut missiongen/wk.py '        return ["STAGING: the 347th was drafted into NATO contingency plans "' \
                     '        return ["The squadron deployed here in 1980. "'
run "claim a European deployment that never happened" "germany_cards_do_not_claim or says_where_it_is_actually_staged"

mut missiongen/wk.py '    L = _title(ride_key, map_key) + staging_note(map_key)' '    L = _title(ride_key, map_key)'
run "stop saying where the ride is staged" "says_where_it_is_actually_staged"

echo "== the wiring =="

mut missiongen/builder.py '        if _wk_ride:' '        if _wk_ride and not r.bb_bfm:'
run "let the generic BFM card replace the squadron's own calls" "puts_its_own_card"

mut missiongen/templates.py '    rc["map"] = map_key or rc.get("map") or (tpl.get("default_map") or "caucasus")' \
                            '    rc["map"] = rc.get("map") or map_key'
run "let a by_map block teleport the mission to another map" "teleport"

mut missiongen/templates.py '    rc.update(dict((tpl.get("by_map") or {}).get(rc["map"]) or {}))' '    pass'
run "ignore by_map overrides entirely" "ramstein"

echo "== track shape =="

mut missiongen/wk.py '"wk_10_threeship": {"n": 10,' '"wk_10_threeship": {"n": 9,'
run "two rides sharing a position in the track" "numbered_one_to_n or sizes_the_syllabus"

mut missiongen/data/tracks.json '"follows": "wk_checkout",' '"requires": "wk_checkout",'
run "gate Proud Phantom behind the checkout" "bound_as_a_series"

echo "== livery, waypoints, kneeboard =="

mut missiongen/wk.py '    L += [""] + livery_lines()' '    pass'
run "stop saying what the airplane should look like" "should_look_like"

mut missiongen/wk.py '"AND THE PART YOU WILL NOTICE: DCS SHIPS NO 70 TFS LIVERY. There is "' \
                     '"YOUR AIRCRAFT WEARS THE CORRECT MARKINGS. There is "'
run "imply the correct skin is applied" "livery_card_admits"

mut missiongen/wk_route.py '    if ride_key == "wk_3_cqt":\n        return []' \
                            '    if ride_key == "wk_3_cqt":\n        return _low_level(map_key)'
run "invent a flight plan for a ride that never leaves the chocks" "quick_turn_ride"

mut missiongen/wk_route.py '        ("ROUTE ENTRY", 18, 0, f, v),' '        ("ROUTE ENTRY", 18, 0, 2000, v),'
run "fly the low level above the floor the card prints" "flown_at_the_theatre_floor or different_route_altitudes"

mut missiongen/wk_route.py '    f = wk.floor_ft(map_key)\n    v = ias or wk.MIN_IAS_KT' \
                           '    f = wk.FORMATION_MIN_FT\n    v = ias or wk.MIN_IAS_KT'
run "use the squadron floor everywhere and ignore the host nation" "different_route_altitudes or flown_at_the_theatre_floor"

mut missiongen/wk_route.py '    pup_nm = d["pup_ft"] / 6076.12' '    pup_nm = 3.0'
run "put the IP at a generic distance instead of the sheet's" "sheets_own_pull_up_point"

mut missiongen/wk_route.py '    split_nm = a.get("support_nm") or 4.0' '    split_nm = 5.0'
run "split at a range the guide does not name" "range_the_guide_names"

mut missiongen/wk_route.py '          f"for this theater. That reference is OUR estimate, not a survey: "' \
                           '          f"for this theater, surveyed from the terrain: "'
run "present the ground reference as a survey" "ground_reference_is_labelled"

mut missiongen/builder.py '            self._wk_card = _wk_card' '            self._wk_card = None'
run "leave the card in the briefing and off the kneeboard" "on_the_kneeboard"

mut missiongen/kneeboard.py '        elif tabular:\n            chunks = [raw]' '        elif mono:\n            chunks = [raw]'
run "draw indented prose unwrapped and clip it" "off_the_right_edge"

mut scripts/add_white_knights.py '        "callsign": "REX",' '        "callsign": "OYSTER",'
python3 scripts/add_white_knights.py >/dev/null
run "fly the squadron's syllabus under somebody else's callsign" "called_REX"
python3 scripts/add_white_knights.py >/dev/null

echo "== does the syllabus cover the document? =="

mut missiongen/wk.py '    "pp_9_splithigh": {"n": 10, "track": "wk_proud_phantom", "doc": "tactics",' \
                     '    "_dropped_splithigh": {"n": 99, "track": "none", "doc": "tactics",'
run "teach four of the document's five attacks (the gap Rob found)" "attack_in_the_guide or both_halves or sizes_the_syllabus"

mut missiongen/wk.py '"deliveries": ("dt35", "dt20"),' '"deliveries": ("dt35",),'
run "drop a delivery planning sheet from the syllabus" "delivery_sheet_has_a_ride"

mut missiongen/wk.py '    "pp_9_split": {"n": 11, "track": "wk_proud_phantom", "doc": "tactics",' \
                     '    "pp_9_split": {"n": 8, "track": "wk_proud_phantom", "doc": "tactics",'
run "teach the low/low before the low/high" "both_halves or numbered_one_to_n"

echo "== the squadron's own diagrams =="

mut missiongen/wk.py 'DIAGRAMS = {k: f"wk_{k}.png" for k in ATTACKS}' \
                     'DIAGRAMS = {k: f"wk_{k}.png" for k in ATTACKS if k != "bnai"}'
run "lose a diagram for one of the five attacks" "every_attack_has_the_squadrons_diagram or guide_carries_every_diagram"

mut missiongen/wk.py '    p = DIAGRAM_DIR / name\n    return p if p.is_file() else None' \
                     '    return DIAGRAM_DIR / name'
run "hand back a path to an asset that is not there" "degrades_to_no_page"

mut missiongen/wk.py '"own page, not redrawn.",' '"own page.",'
run "print a diagram with no provenance" "says_where_it_came_from"

mut missiongen/builder.py '            _atk = _wk.RIDES[_wk_ride].get("attack")' '            _atk = None'
run "keep the diagram out of the mission" "carries_its_diagram_as_a_kneeboard or no_attack_gets_no_diagram"

mut missiongen/kneeboard.py '    scale = min(box_w / pic.width, box_h / pic.height, 1.0)' \
                            '    scale = min(box_w / pic.width, box_h / pic.height)'
run "enlarge a scan until the line art turns to fuzz" "never_enlarges_the_scan"

echo "== the counterpart, and what the jet carries =="

# (re-anchored in v1.85.0: the wingman is seat two of the player's group)
mut missiongen/builder.py '                    _n_ship = max(2 if _wk_two_ship else 1, min(4, r.slots))' \
                          '                    _n_ship = max(1, min(4, r.slots))'
run "promise a wingman and ship one airplane (the defect Rob flew into)" "wingman_the_card_promises"

# The obvious mutation here — swapping the computed answer for the hand list
# ("wk_1_stepstart", "wk_3_cqt") — is a NO-OP, because that list happens to be
# exactly right today. A hand list only bites when it DRIFTS, so this is a
# drifted one: it forgets the overhead, which does have a counterpart.
mut missiongen/wk.py '    return bool(wk_route.counterpart_legs(ride_key, map_key or "germany"))' \
                     '    return ride_key not in ("wk_1_stepstart", "wk_2_overhead", "wk_3_cqt")'
run "keep a hand-kept list of who has a wingman" "promise_and_the_aeroplane"

mut missiongen/wk_route.py '    if ride_key in ("wk_1_stepstart", "wk_3_cqt"):\n        return []' \
                           '    if ride_key in ("wk_1_stepstart", "wk_3_cqt"):\n        return _low_level(map_key)'
run "give the quick turn a wingman it cannot have" "solo_rides_have_no_wingman"

# (the line-abreast offset mutation retired in v1.85.0: the counterpart
# tables are now the two-ship PREDICATE, not flown geometry — seat two flies
# formation on the player, so a mutated offset reaches no mission.)

mut missiongen/wk_route.py '        trail_nm = -sum(wk.ATTACKS["bnai"]["trail_nm"]) / 2.0' '        trail_nm = 0.0'
run_coach "zero the trail the card still prints" "coaching_did_not_cost"

mut missiongen/wk.py '        fit[7] = MK82_LD_MER' '        pass'
run "brief six Mk-82 and carry none" "carries_something_to_drop or stores_on_the_card or high_drag_sheet"

mut missiongen/wk.py '        fit[3] = MK82_HD_TER\n        fit[11] = MK82_HD_TER' '        fit[7] = MK82_LD_MER'
run "put low drag on the high-drag sheet" "high_drag_sheet or stores_block_counts"

mut missiongen/builder.py '                        for _u in player_group.units:\n                            _u.pylons = {}' \
                          '                        pass'
run "leave the air-to-air fit hanging beside the bombs" "stores_on_the_card"

mut missiongen/wk.py 'AIM9J = "{AIM-9J}"' 'AIM9J = "{AIM-9P5}"'
run "hang a 1980s Sidewinder on a January 1980 jet" "period_correct"

mut missiongen/builder.py '                for _u in player_group.units[1:]:\n                    _u.skill = _Skill.Excellent' \
                          '                pass'
run "leave seat two at whatever skill the factory set" "wingman_the_card_promises or seat_two_of_your_own_flight"


echo "== the coached B'NAI: the cue, the order, and the second run =="

mut missiongen/wk.py '"coach": True, "brief": True, "maps": ["sinai"]},' '"brief": True, "maps": ["sinai"]},'
run_coach "quietly stop coaching the ride whose whole point is the coaching" "same_attack_and_say_so or one_trigger_per_condition_set"

mut missiongen/builder.py '            _n_cues = _wkc.attach(m, player_group, _wk_ride, r.map,' \
                          '            _n_cues = 0 * len(_wkc.attach.__name__) or _wkc_skip(m, player_group, _wk_ride, r.map,'
run_coach "wire nothing into the mission and keep the card that describes it" "one_trigger_per_condition_set"

# Aimed at the ROUTE, not at `attach`'s own guard. Removing that guard is a
# no-op: `attach` then fails its leg-table check on every other ride and
# returns 0 anyway, so the mutation proves nothing. What CAN leak is the
# coached leg table — the check ride quietly acquiring the coached ride's
# side-on approach to the IP, which is the one thing the two rides must not
# share.
mut missiongen/wk_route.py '    if r.get("coach"):' '    if r.get("attack"):'
run_coach "give the check ride the coached ride's route" "approaches_the_ip_from_the_side or only_the_coached_ride"

mut missiongen/wk_coach.py '    return int(wk.DELIVERIES["lald15"]["pup_ft"])' '    return int(4.5 * NM_FT)'
run_coach "read the drawing's 4.5 NM as the pull-up distance" "pull_up_cue_uses_the_sheet or pull_up_ring"

mut missiongen/wk_coach.py '            "pup": zone(pos["TARGET"], _pup_ft() * _FT_M, "WKC PULL-UP RING"),' \
                           '            "pup": zone(pos["PULL-UP"], 1.0 * NM_M, "WKC PULL-UP RING"),'
run_coach "make the pull-up a place instead of a range" "pull_up_ring"

mut missiongen/wk_coach.py '     "heading.", "track"),' '     "heading.", "release"),'
run_coach "wedge the whole sortie behind one missed release" "hangs_off_the_release or reached_from_the_first"

mut missiongen/wk_coach.py 'RESET_TO = "ip"' 'RESET_TO = "lowlevel"'
run_coach "send the pilot back to re-fly twenty miles of low level in silence" "reset_hands_back"

mut missiongen/wk_coach.py '                    for k2 in KEYS[:IDX[RESET_TO]]:\n                        t.actions.append(A.SetFlag(flag(k2)))' \
                           '                    pass'
run_coach "re-arm at the start and leave the second pass mute until the IP" "reattack_clears_the_pass"

mut missiongen/wk_coach.py '                t.rules.append(C.FlagIsFalse(flag(key)))' '                pass'
run_coach "let every cue re-fire once a second for the rest of the sortie" "cannot_fire_before"

mut missiongen/wk_coach.py '                if pre:\n                    t.rules.append(C.FlagIsTrue(flag(pre)))' \
                           '                if False:\n                    t.rules.append(C.FlagIsTrue(flag(pre)))'
run_coach "call PICKLE on the run-in" "cannot_fire_before"

mut missiongen/wk_coach.py '    return audio_path(key).is_file()' '    return True'
run_coach "claim a voice the build does not have" "card_does_not_claim_a_voice or missing_wav"

mut missiongen/wk_route.py '        ("TRAIL SET", 25, 8, f, wk.MIN_IAS_KT),' '        ("TRAIL SET", 25, 0, f, wk.MIN_IAS_KT),'
run_coach "run straight through the IP while the cue says turn inbound" "approaches_the_ip_from_the_side"

mut scripts/build_wk_coach_cards.py '"pup":     ((405, 515), PANEL_ATTACK),' '"pup":     ((705, 615), PANEL_ATTACK),'
run_coach "put the you-are-here ring on the paragraph beside the drawing" "ring_lands_on_the_drawing or ring_positions_climb"

mut missiongen/wk_coach.py '    return AUDIO_DIR / f"wk_bnai_{key}.wav"' '    return AUDIO_DIR / f"{key}.wav"'
run_coach "ask the recording sheet for names the mission does not look for" "recording_sheet"

echo "== the brief, and the hold =="

mut missiongen/wk.py '                        "coach": True, "brief": True, "maps": ["sinai"]},' \
                     '                        "coach": True, "maps": ["sinai"]},'
run_coach "drop the brief and keep the card that promises it" "six_brief_pages or locked_in_before_page_one or honest_about_what_the_hold"

mut missiongen/wk_brief.py '        first.actions.append(A.StartPlayerSeatLock(SEAT))' '        pass'
run_coach "let the pilot fly away in the middle of his own brief" "locked_in_before_page_one"

mut missiongen/wk_brief.py '                t.actions.append(A.StopPlayerSeatLock())' \
                           '                t.actions.append(A.StartPlayerSeatLock(SEAT))'
run_coach "never give the airplane back" "locked_in_before_page_one"

mut missiongen/wk_brief.py '                t.actions.append(A.SetFlag(arm_flag))' '                pass'
run_coach "brief him and then leave the coaching dark all sortie" "coaching_cannot_arm_until_the_brief"

mut missiongen/wk_coach.py 'F_ARM = 8899            # the whole sequence is live (cleared while resetting)' \
                           'F_ARM = 8890            # the whole sequence is live (cleared while resetting)'
run_coach "put the arm flag back on top of a phase flag (the bug that shipped)" "flag_blocks_do_not_overlap or second_run_does_not_switch or coaching_cannot_arm"

mut missiongen/wk_brief.py '            acts = [A.StopWaitUserResponse()]\n            for j in range(len(pg)):\n                acts.append(A.ClearFlag(F_CONT + j))\n                acts.append(A.ClearFlag(F_BACK + j))\n            return acts' \
                           '            return [A.StopWaitUserResponse(), A.ClearFlag(F_CONT), A.ClearFlag(F_BACK)]'
run_coach "clear one page's flags and leave the rest live (the documented footgun)" "closes_the_wait_and_clears_both"

mut missiongen/wk_brief.py '            acts.append(A.StartWaitUserResponse(F_CONT + i, F_BACK + i))' \
                           '            pass'
run_coach "show the brief as a slideshow that never waits for him" "waits_for_the_pilot_rather_than_a_timer"

mut missiongen/wk_brief.py '            for a in show(max(0, i - 1)):' '            for a in show(min(len(pg) - 1, i + 1)):'
run_coach "make BACKSPACE go forwards" "backspace_on_page_one"

mut missiongen/wk_brief.py '         f"You have the airplane."),' '         f"Good hunting."),'
run_coach "end the brief without handing the controls back in words" "hands_the_aeroplane_over_in_words"

mut missiongen/wk_brief.py 'Pull up {d[\x27pup_ft\x27]:,} feet ' 'Pull up 4.5 miles ' 
run_coach "recite the pop numbers in the brief instead of reading them" "restates_no_number_of_its_own"

mut missiongen/wk_brief.py '         "WHAT IT CANNOT DO IS PRESS ACTIVE PAUSE FOR YOU. That is a keybind "' \
                           '         "THE SIMULATION IS PAUSED WHILE YOU READ. That is a keybind "'
run_coach "tell the pilot the mission pauses the world when it cannot" "honest_about_what_the_hold"

mut missiongen/builder.py '            _n_brief = _wkb.attach(m, player_group, _wk_ride, _wkc.F_ARM,' \
                          '            _n_brief = 0 and _wkb.attach(m, player_group, _wk_ride, _wkc.F_ARM,'
run_coach "wire no brief and let the coaching arm on its old timer" "six_brief_pages or coaching_cannot_arm_until_the_brief or locked_in"

echo "== taking the brief off the screen =="

mut missiongen/wk_brief.py '                t.actions.append(A.PictureToGroup(\n                    player_group, blank, 1, True, 0,\n                    getattr(A.PictureAction.HorzAlignment, HORZ).value,\n                    getattr(A.PictureAction.VertAlignment, VERT).value,\n                    SIZE_PCT, A.PictureAction.SizeUnits.WindowSize.value))' \
                           '                pass'
run_coach "leave page six over the canopy for the whole sortie (the bug Rob flew)" "last_page_takes_the_brief"

mut missiongen/wk_brief.py '                    player_group, blank, 1, True, 0,' \
                           '                    player_group, blank, PAGE_S, True, 0,'
run_coach "hold the blank on screen as long as the page it replaced" "last_page_takes_the_brief"

mut missiongen/wk_brief.py '                    player_group.id, m.string(" "), 1, True))' \
                           '                    player_group.id, m.string(" "), 1, False))'
run_coach "clear the picture and leave the brief text sitting in the window" "last_page_takes_the_brief"

mut missiongen/wk_brief.py '        blank = m.map_resource.add_resource_file(str(clear_path()))' \
                           '        blank = res[KEYS[0]]'
run_coach "clear the brief with a copy of page one" "blank_page_ships or last_page_takes_the_brief"

mut missiongen/wk_brief.py 'PAGE_S = 600 ' 'PAGE_S = 20  '
run_coach "time the pages out from under a pilot who is still reading" "pages_before_the_last_are_replaced"

echo "== which side Egypt is on =="

# THE BUG ROB FOUND, and the line that caused it. Restoring the silent fallback
# is the whole of the defect: eleven rides taking off from Israel to bomb the
# base they were sold as living on.
mut missiongen/builder.py '        if r.home_airbase and r.home_airbase != "CARRIER":' \
                          '        home = next((a for a in own_fields if a.name == r.home_airbase), own_fields[0])\n        if False:'
run_pp "relocate a squadron to another country rather than admit the field is wrong" \
       "hard_error or takes_off_from_cairo or brief_never_puts"

mut missiongen/builder.py '            preset = {**preset, **(map_cfg.get("lineups") or {})[r.lineup]}' \
                          '            pass'
run_pp "read the lineup and then build the 1973 order of battle anyway" \
       "takes_off_from_cairo or israel_flies or threat_is_libyan"

mut missiongen/data/maps.json '        "red_country": "Libya",' \
                              '        "red_country": "Egypt",'
run_pp "make the host nation the enemy again" "threat_is_libyan or egypt_is_the_host"

mut missiongen/data/maps.json '        "blue_country": "USA",\n        "red_country": "Libya",' \
                              '        "blue_country": "Israel",\n        "red_country": "Libya",'
run_pp "fly a USAF squadron under another flag" "egypt_is_the_host or israel_flies or takes_off_from_cairo"

mut missiongen/data/maps.json '          "Cairo West",\n          "Inshas Airbase",\n          "Abu Suwayr",\n          "Beni Suef",' \
                              '          "Inshas Airbase",\n          "Abu Suwayr",\n          "Beni Suef",'
run_pp "take the base they deployed to off their own side" \
       "egypt_is_the_host or no_card_anywhere or takes_off_from_cairo"

mut missiongen/data/maps.json '        "eras": ["coldwar"],' '        "eras": ["coldwar", "modern"],'
run_pp "let a June 1980 order of battle serve a modern mission" "wrong_era"

# The 1973 reading of the map must SURVIVE. A lineup adds a scenario; it does
# not delete the one the map already had.
mut missiongen/data/maps.json '        "blue_country": "Israel",\n        "red_country": "Egypt",\n        "blue_airbases": [\n          "Hatzor",\n          "Tel Nof",\n          "Hatzerim",\n          "Ramat David",' \
                              '        "blue_country": "USA",\n        "red_country": "Egypt",\n        "blue_airbases": [\n          "Hatzor",\n          "Tel Nof",\n          "Hatzerim",\n          "Ramat David",'
run_pp "overwrite Yom Kippur instead of adding 1980 beside it" "seventy_three_order_of_battle"

mut missiongen/data/mission_templates.json '   "home_airbase": "Nellis",' \
                                           '   "home_airbase": "Nellis AFB",'
run_pp "name an airfield DCS does not have (the one the sweep found)" "no_card_anywhere"

echo "== the wingman, and the green ring =="

# ROB, across three separate-flight designs: "the other REX flight doesn't
# fly with me at all." The wingman is seat two of YOUR group now; the
# mutations that matter are the ones that quietly undo that.
mut missiongen/builder.py '        _wk_two_ship = bool(_wk_ride_pre\n                            and _wk_pre.has_counterpart(_wk_ride_pre, r.map))' \
                          '        _wk_two_ship = False'
run_coach "fly every two-ship ride alone" "seat_two_of_your_own_flight or coaching_did_not_cost"

mut missiongen/builder.py '                group_size=max(2 if _wk_two_ship else 1, min(4, r.slots)))' \
                          '                group_size=max(1, min(4, r.slots)))'
run_coach "air-start the two-ship as a single ship" "air_start_ride_is_a_two_ship"

mut missiongen/wk_coach.py '        res = {k: m.map_resource.add_resource_file(str(card_path(k, ring)))' \
                           '        res = {k: m.map_resource.add_resource_file(str(card_path(k)))'
run_coach "take a green order and ship red cards" "ships_green_cards"

mut missiongen/data/mission_templates.json '   "coach_ring": "green"' \
                                           '   "coach_ring": "red"'
run_coach "sell the green variant with a red recipe" "ships_green_cards or same_ride_with_a_different_ring"

mut missiongen/wk_coach.py 'RINGS = ("red", "green")   # every palette the card builder produces' \
                           'RINGS = ("red", "green", "amber")   # every palette the card builder produces'
run_coach "offer a palette nobody builds" "full_card_set"

echo "== the wingman takes off =="

# ROB: "the AI plane doesn't take off, it just goes slowly down the runway."
# pydcs waypoint speeds are km/h; these three sites passed m/s for four
# releases — every route commanded at 112 kt instead of 400.
mut missiongen/wk_route.py '        tas_kmh = ias_to_tas_kt(ias, alt_ft) * 1.852' \
                           '        tas_kmh = ias_to_tas_kt(ias, alt_ft) * 0.514444'
run_coach "command the route in meters per second (112 kt, the runway trundle)" \
          "commanded_at_the_speed"

# (v1.85.0: the three mutations that targeted `apply_counterpart` are gone
# WITH the function — the wingman is seat two of the player's group, so his
# waypoints, climb-out and spawn speed are the player's own, guarded above.)

echo "== a target to bomb, an axis that misses Cairo, and the squares =="

mut missiongen/wk_route.py 'AXIS_DEG = {"germany": 75.0, "sinai": 265.0, "caucasus": 250.0, "nevada": 340.0}' \
                           'AXIS_DEG = {"germany": 75.0, "sinai": 120.0, "caucasus": 250.0, "nevada": 340.0}'
run_coach "fly the 300-ft low level across Cairo (the old axis)" "out_of_cairo"

mut missiongen/builder.py '            if _wk_tpos is not None:' \
                          '            if False:'
run_coach "list two targets the route never visits and bomb sand" "stands_on_the_leg"

mut missiongen/builder.py '            if getattr(r, "coach_gates", False):' \
                          '            if False:'
run_coach "sell the navigation squares and draw none" "navigation_squares"

# (`if _n_cues:` retired as a mutation in v1.85.0: with gates on both coached
# rides it became equivalent code, not a defect. The live leak path is the
# TEMPLATE, so that is what gets mutated.)
mut missiongen/data/mission_templates.json '   "home_airbase": "Cairo West",\n   "bb_sams": true,\n   "threat_tier": "mixed",\n   "lineup": "proud_phantom"\n  },\n  "wk_ride": "pp_8_bnai",' \
                                           '   "home_airbase": "Cairo West",\n   "bb_sams": true,\n   "threat_tier": "mixed",\n   "lineup": "proud_phantom",\n   "coach_gates": true\n  },\n  "wk_ride": "pp_8_bnai",'
run_coach "put the training gates on the check ride too" "shows_the_squares"

echo "== the shared hangar, and gates on the coached ride =="

# THE HANGAR BUG cannot be expressed as a single mutation any more, and that
# was MEASURED, not assumed: with BOTH of the main path's unit_id checks
# removed and the ramp forced to 100%% fill, the flight's stands were still
# skipped — a third, physical layer (`_occ_register` feeds claimed stands
# into the keep-out) holds on its own. Three independent defenses means no
# plausible single mistake reintroduces the defect; the deterministic
# full-ramp guard (`test_no_static_shares_a_stand_with_either_aeroplane`,
# dress_fill=100) stands sentinel over all three.

mut missiongen/data/mission_templates.json '   "bb_sams": true,\n   "threat_tier": "mixed",\n   "lineup": "proud_phantom",\n   "coach_gates": true' \
                                           '   "bb_sams": true,\n   "threat_tier": "mixed",\n   "lineup": "proud_phantom"'
run_coach "take the training gates off the ride that promises them" "shows_the_squares"

echo
echo "caught $PASS, weak $WEAK"
[ "$WEAK" -eq 0 ]
