#!/usr/bin/env bash
# Prove the boat-card guards by breaking them.
#
# EVERY DEFECT HERE WAS INVISIBLE TO A GREEN SUITE AND OBVIOUS FROM THE
# COCKPIT. Casmo flew a Case III recovery and reported that the card said
# "carrier on channel 2" while channel 2 gave him nothing; the preset test we
# had was real, but it only ever built a LAND Hornet mission, so the carrier
# row's channel had never once been read back out of a cockpit. Separately,
# the ICLS channel and the BRC lived only as gray text on a kneeboard image
# inside the .miz, so the brief he planned from could not have told him what
# to dial. Neither is arithmetic drift. Both are a promise nobody checked.
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
FILES=(
  missiongen/presets.py
  missiongen/naval.py
  missiongen/brief.py
  missiongen/pydcs_patches.py
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
       tests/test_boat_card.py tests/test_comms_truth.py \
       -q -x -k "$k" > /tmp/mut_boat.log 2>&1; then
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

baseline_green tests/test_boat_card.py tests/test_comms_truth.py

echo "== the cockpit Casmo was sitting in =="

# THE BUG, RESTORED EXACTLY: one radio programmed, the Tomcat's second UHF set
# left holding pydcs's factory channel 2 of 258.000.
mut missiongen/presets.py '    if pure:\n        return pure\n' \
                          '    if pure:\n        return pure[:1]\n'
run "load only the first UHF radio and leave the RIO's on factory" \
    "second_uhf_set or whole_card or channel_two"

# The older shape of the same defect: rank the radios and take the best one.
mut missiongen/presets.py '    pure = [rid for rid, f in fracs.items() if f == 1.0]\n    if pure:\n        return pure\n' \
                          '    pure = []\n    if pure:\n        return pure\n'
run "fall back to the single best radio for every airframe" \
    "second_uhf_set or channel_two"

# The overcorrection: program everything, including sets that cannot tune UHF.
mut missiongen/presets.py '    pure = [rid for rid, f in fracs.items() if f == 1.0]' \
                          '    pure = [rid for rid, f in fracs.items() if f >= 0.0]'
run "write the UHF ladder into the A-10C's VHF radios" "vhf_radio_is_never_given"

# Mother is CH2 in the guide, on the kneeboard and in the pilot's mouth.
mut missiongen/presets.py '("Flight", 1), ("Carrier", 2), ("AWACS", 3), ("Tanker", 4),' \
                          '("Flight", 1), ("Carrier", 6), ("AWACS", 3), ("Tanker", 4),'
run "move Mother off channel 2" "channel_two or whole_card"

mut missiongen/presets.py '            channels[last] = guard_mhz' \
                          '            pass  # guard'
run "stop reserving Guard on the last channel" "guard_rides"

echo "== the beacons =="

# The single most common cause of "my carrier TACAN doesn't work": the beacon
# is created air-to-air, so the channel on the card is right and a pilot in
# T/R hears nothing at all.
mut missiongen/naval.py '                                              unit_id=ship_id, aa=False))' \
                        '                                              unit_id=ship_id, aa=True))'
run "make the carrier TACAN an air-to-air beacon" "surface_beacon"

mut missiongen/naval.py '        wp.tasks.append(ActivateBeaconCommand(channel=tac_ch,\n                                              modechannel="X",' \
                        '        wp.tasks.append(ActivateBeaconCommand(channel=tac_ch,\n                                              modechannel="X", bearing=False,'
run "publish DME with no radial" "surface_beacon"

mut missiongen/naval.py 'wp.tasks.append(ActivateICLSCommand(channel=cv["icls"], unit_id=ship_id))' \
                        'wp.tasks.append(ActivateICLSCommand(channel=cv["icls"] + 1, unit_id=ship_id))'
run "activate an ICLS channel one off the one on the card" "icls_channel"

mut missiongen/naval.py '        notes.append(f"ICLS {cv[\x27icls\x27]}")\n' ''
run "activate ICLS and never tell the pilot the channel" "icls_channel"

mut missiongen/naval.py '    if "acls" in systems:\n        wp.tasks.append(ActivateACLSCommand(unit_id=ship_id))\n        notes.append("ACLS on")' \
                        '    if "acls" in systems:\n        wp.tasks.append(ActivateACLSCommand(unit_id=ship_id))\n    notes.append("ACLS on")'
run "advertise ACLS on every hull, including the ones without it" "acls_is_claimed"

mut missiongen/naval.py 'wp.tasks.append(ActivateLink4Command(unit_id=ship_id, frequency=int(cv["link4"])))' \
                        'wp.tasks.append(ActivateLink4Command(unit_id=ship_id, frequency=int(cv["link4"]) * 2))'
run "put Link 4 on a frequency the card does not print" "link4_frequency"

# Blanket activation: the 1944 Essex with ICLS and ACLS.
mut missiongen/naval.py '    systems = hull.get("systems", ["tacan", "icls", "link4", "acls"])' \
                        '    systems = ["tacan", "icls", "link4", "acls"]'
run "give the 1944 Essex a landing system" "no_boat_systems or acls_is_claimed"

echo "== the radio the ship is actually on =="

mut missiongen/naval.py '    grp.set_frequency(int(round(cv["freq"] * 1e6)))' \
                        '    grp.set_frequency(int(round(cv["freq"])))'
run "set the battle group's frequency in megahertz" \
    "frequency_the_card_prints or carrier_frequency_is_in_hertz"

mut missiongen/pydcs_patches.py '    d["modulation"] = getattr(self, "modulation", Modulation.AM.value)' \
                                '    d["modulation"] = Modulation.FM.value'
run "put the carrier on FM, where an ARC-159 cannot hear it" "transmits_am"

mut missiongen/pydcs_patches.py '    d["modulation"] = getattr(self, "modulation", Modulation.AM.value)\n' ''
run "go back to writing no modulation at all" "transmits_am"

echo "== what the pilot can read before he starts =="

# THE REGRESSION ITSELF: the row loop stops emitting the note, so ICLS, Link 4
# and the BRC go back to living only on a kneeboard image inside the .miz.
mut missiongen/brief.py '                 f"| {tacan} | {note} |")' \
                        '                 f"| {tacan} |")'
run "drop the notes cell from every comms row again" \
    "brief_carries_the_boat_card or header_matches_its_rows"

# WAS WEAK, AND WORTH KEEPING FOR THE REASON: mutating only the HEADER left the
# rows six cells wide, so every guard that reads a row still passed while the
# rendered table dropped the notes column on the floor. Header and rows have to
# be checked as a pair, which is what test_the_comms_table_header_matches_its_rows
# now does.
mut missiongen/brief.py '"| Agency | C/S | Freq MHz | CHAN | TACAN | Notes |",\n          "|---|---|---|---|---|---|"]' \
                        '"| Agency | C/S | Freq MHz | CHAN | TACAN |",\n          "|---|---|---|---|---|"]'
run "narrow the header and leave the rows wide" "header_matches_its_rows"

mut missiongen/brief.py '        note = (note or "").replace("|", "\\|")' \
                        '        note = ""'
run "print an empty notes cell on every row" "brief_carries_the_boat_card"

echo
echo "caught $PASS, weak $WEAK"
[ "$WEAK" -eq 0 ]
