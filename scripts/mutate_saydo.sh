#!/usr/bin/env bash
# Prove the say/do self-check, the readback gate and the scorecard by breaking
# them.
#
# WHAT IS BEING PROTECTED. Every gap in the expert-mission ledger was a number
# copied by hand from the world into the paperwork. saydo.py recomputes the
# paperwork from the world after each build; gates.py installs Fulda's
# set / not-set / advance triplet ONLY on airframes whose cockpit parameter we
# have verified; cq_coach prints Rampagers' scorecard. Each mutation below is a
# way one of those could quietly stop being true while the suite stayed green.
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
FILES=(
  missiongen/callsign.py
  missiongen/saydo.py
  missiongen/gates.py
  missiongen/cockpit.py
  missiongen/cq_coach.py
  missiongen/builder.py
  missiongen/brief.py
)
for f in "${FILES[@]}"; do mkdir -p "$SNAP/$(dirname "$f")"; cp "$f" "$SNAP/$f"; done

baseline() {
  find missiongen tests -type f -name '*.py' ! -path '*/__pycache__/*' -print0 \
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
       tests/test_saydo.py -q -x -k "$k" > /tmp/mut_saydo.log 2>&1; then
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

baseline_green tests/test_saydo.py

echo "== the check itself =="

mut missiongen/saydo.py '        if not any(abs(f - k) < 0.003 for k in known):' \
                        '        if False:'
run "never report a card frequency nothing holds" "nothing_holds_is_a_finding"

mut missiongen/saydo.py '        if NOT_TUNABLE in (note or ""):\n            continue                      # disclosed on the card itself' \
                        '        if True:\n            continue'
run "skip every entry as if it were disclosed" "nothing_holds_is_a_finding"

mut missiongen/saydo.py '    if said_hhmm != actual:' '    if False:'
run "accept a brief clock that is not the mission clock" "off_the_mission_clock"

mut missiongen/saydo.py '    if brief_text and actual not in brief_text:' '    if False:'
run "let the brief omit the clock" "prints_the_clock_it_really_starts_on"

mut missiongen/saydo.py '    if stock_root.lower() not in (brief_text or "").lower():' \
                        '    if False:'
run "let the brief hide the stock callsign" "must_be_admitted"

mut missiongen/builder.py '            self.warnings += _saydo.run(m, comms, player_group,' \
                          '            _unused = _saydo.run(m, comms, player_group,'
run "run the check and throw its findings away" "findings_reach_the_build_warnings"

echo "== what the brief admits =="

mut missiongen/saydo.py '    if stock_root and voiced and stock_root.lower() != voiced.lower():' \
                        '    if False:'
run "drop the stock-callsign line from Known Issues" "returns_if_the_file_and_paper_ever_disagree"

echo "== the callsign DCS can say =="

mut missiongen/callsign.py '            u.callsign_dict = {1: idx, 2: 1, 3: i, "name": f"{used}1{i}"}' \
                           '            u.callsign_dict = {1: 1, 2: 1, 3: i, "name": f"{used}1{i}"}'
run "write the name but leave the index DCS reads at Enfield (pydcs\x27s bug)" "carries_the_index_dcs_reads"

mut missiongen/callsign.py '    return names[zlib.crc32(w.lower().encode("utf-8")) % len(names)]' \
                           '    return w'
run "fly the authentic name the sim cannot say" "carries_the_index_dcs_reads or others_map_stably"

mut missiongen/callsign.py '    return names[zlib.crc32(w.lower().encode("utf-8")) % len(names)]' \
                           '    import random; return random.choice(names)'
run "map the same squadron to a different name every build" "others_map_stably"

mut missiongen/builder.py '            _csn.apply(player_group, self._callsign_used)' '            pass'
run "print the mapped name but never put it in the file" "carries_the_index_dcs_reads or numeric_nation"

mut missiongen/builder.py '            if _numeric:\n                # A named callsign on a nation whose radio speaks numbers:' \
                          '            if False:\n                # A named callsign on a nation whose radio speaks numbers:'
run "give a numeric nation a western name it cannot say" "named_callsign_on_a_numeric_nation"

mut missiongen/builder.py '        if stats.get("known_issues"):\n            lines += ["", "WHAT DCS WILL GET WRONG:"]' \
                          '        if False:\n            lines += ["", "WHAT DCS WILL GET WRONG:"]'
run "leave Known Issues out of the in-game brief" "known_issues_name_the_ai_limits"

mut missiongen/brief.py '    if stats.get("known_issues"):\n        # Every expert campaign carries this page.' \
                        '    if False:\n        # Every expert campaign carries this page.'
run "leave Known Issues out of the PDF/markdown brief" "markdown_brief_carries"

mut missiongen/brief.py 'HOUR = {"dawn": "05", "day": "12", "dusk": "18", "night": "22"}' \
                        'HOUR = {"dawn": "05", "day": "13", "dusk": "18", "night": "22"}'
run "let the PDF DTG hour drift from the mission hour (the twin)" "dtg_hour_is_the_mission_hour"

echo "== the VHF-only jet =="

mut missiongen/saydo.py '    if any(lo <= flight_mhz <= hi for lo, hi in bands):\n        return flight_mhz, tactical_mhz, False' \
                        '    if True:\n        return flight_mhz, tactical_mhz, False'
run "give a VHF-only Mustang a UHF flight frequency again" "vhf_only_jet or cannot_tune"

mut missiongen/saydo.py '            note = (note + " · " if note else "") + NOT_TUNABLE' \
                        '            note = note'
run "find the untunable entry but say nothing on the card" "cannot_tune_is_disclosed"

echo "== the readback gate =="

mut missiongen/cockpit.py '    "F-4E-45MC": {\n        "comm1": "COMM_FREQ", "comm2": "AUX_FREQ",' \
                          '    "F-14B": {"comm1": "GUESS", "source": ""},\n    "F-4E-45MC": {\n        "comm1": "COMM_FREQ", "comm2": "AUX_FREQ",'
run "install a gate on an unverified airframe with a guessed name" "refuses_an_unverified or facts_came_from"

mut missiongen/gates.py 'WINDOW_MHZ = 0.006' 'WINDOW_MHZ = 0.030'
run "widen the window onto the neighbouring 25 kHz channel" "installs_the_triplet"

mut missiongen/gates.py 'REMIND_S = 30       # Fulda\x27s cadence' 'REMIND_S = 300      # Fulda\x27s cadence'
run "remind after five minutes instead of thirty seconds" "installs_the_triplet"

mut missiongen/cq_coach.py '                if key == "checkin" and mother_mhz:\n                    acts.append(A.SetFlag(_gates.F_START))' \
                           '                if False:\n                    acts.append(A.SetFlag(_gates.F_START))'
run "never open the gate at check-in" "checkin_cue_opens_the_gate"

mut missiongen/gates.py '    if cockpit.supports_readback(aircraft):\n        return (f"Radio check: the coach confirms' \
                        '    if True:\n        return (f"Radio check: the coach confirms'
run "claim a working gate in the brief line for every airframe" "refuses_an_unverified"

echo "== the scorecard =="

mut missiongen/cq_coach.py 'DEBRIEF_AFTER_S = 60' 'DEBRIEF_AFTER_S = 600'
run "print the card ten minutes after the last cue" "prints_its_card_a_minute"

mut missiongen/cq_coach.py 'BASE_SCORE = 50' 'BASE_SCORE = 100'
run "change the published base score" "every_grade_has_a_score_line or reach_the_dictionary"

mut missiongen/cq_coach.py '    "level_ten": (10, "Level 1,200 at ten miles"),\n}' '}'
run "drop a grade from the scorecard" "every_grade_has_a_score_line"

mut missiongen/cq_coach.py '            busts = [k for k in gkeys if k in BUSTS]\n            if busts:' \
                           '            busts = [k for k in gkeys if k in BUSTS]\n            if False:'
run "never print the clean line" "prints_its_card_a_minute or reach_the_dictionary"

mut missiongen/cq_coach.py '        if gkeys and keys:\n            last = fired("cue", keys[-1])' \
                           '        if keys:\n            last = fired("cue", keys[-1])'
run "print a card on the ungraded rides too" "ungraded_ride_prints_no_card"

echo
echo "caught $PASS · weak $WEAK"
[ "$WEAK" -eq 0 ]
