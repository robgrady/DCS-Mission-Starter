#!/usr/bin/env python3
"""Insert the Timing track (F-4E) into mission_templates.json and tracks.json.

IDEMPOTENT, same contract as add_white_knights.py: rewrites the entries it
owns and touches nothing else. Re-run after editing the rides below.

WHY THESE FOUR RIDES
--------------------
Rob: "We need to add times to the waypoints. As a military mission planner
explore what functionality we need to add" — then "make a set of missions to
help teach it. I fly the F-4E." Timing is taught the way planners learn it:

  1. FLY THE CARD      takeoff anchor. The card has a clock for the first
                       time; fly the legs on the stopwatch and see how far
                       off you are at each point.
  2. HIT THE TOT       TOT anchor. The time on target is fixed and the
                       mission clock was solved backwards from it. Thirty
                       seconds either side, and it counts double.
  3. THE PACKAGE       push anchor, with an AI flight of Phantoms two minutes
                       ahead on LOCKED ETAs. Their timeline is real; yours
                       has to fit behind it.
  4. ABSORB THE EARLY  TOT anchor with a three-minute HOLD at WP1 — the
                       Reflected technique. You will arrive early on purpose,
                       and the lesson is pushing at the ETA, not on arrival.

All four fly from Fassberg on the Cold War Germany map, because from there a
gun-belt target is 17-19 minutes out: long enough to be late, short enough
to fly twice in an evening.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

DATA = ROOT / "missiongen" / "data"
TRACK = "timing_f4e"
HOME = "Fassberg"

BASE_RECIPE = {
    "aircraft": "F_4E_45MC",
    "callsign": "Chevy",
    "start": "warm",
    "home_airbase": HOME,
    "bb_targets": True,
    "bb_sams": True,
    "threat_tier": "guns",
    "threat_intensity": 1,
    "bb_tanker": False,
    "bb_awacs": False,
    "bb_ambient": False,
    "weather": "clear",
    "timing_coach": True,
}

RIDES = [
    {
        "key": "timing_1_flythecard", "n": 1,
        "label": "Timing 1 — Fly the Card (F-4E)",
        "premise": "The flight plan has a clock on it for the first time. "
                   "Wheels up three minutes after the mission starts, then "
                   "WP1, IP and TARGET each at a printed time. Graded at all four.",
        "recipe": {"time_of_day": "day", "timing_anchor": "takeoff"},
        "brief": [
            "== TIMING 1: FLY THE CARD ==",
            "Every leg on your kneeboard now carries groundspeed, leg time,",
            "cumulative time and an ETA. The anchor is TAKEOFF: wheels up three",
            "minutes after the mission clock starts, and everything counts from",
            "there. Nothing else is asked of you on this ride.",
            " - Hack your clock at wheels-up. Fly the briefed speed on each leg.",
            " - The first leg is timed on a climb schedule, not at cruise: if you",
            "   level off early or late you will see it at WP1.",
            " - The coach calls EARLY / ON TIME / LATE at WP1, IP and TARGET,",
            "   and opens a scorecard a minute after the target.",
            "Base 50. On time +10 a point; late -10; early -5. Fly it twice.",
        ],
    },
    {
        "key": "timing_2_hitthetot", "n": 2,
        "label": "Timing 2 — Hit the TOT (F-4E)",
        "premise": "Time on target is fixed at 05:45:00 and the mission clock "
                   "was solved backwards from it. Thirty seconds either side, "
                   "and the TOT counts double.",
        "recipe": {"time_of_day": "dawn", "timing_anchor": "tot",
                   "timing_at": "05:45", "threat_intensity": 2},
        "brief": [
            "== TIMING 2: HIT THE TOT ==",
            "The anchor is the TOT: 05:45:00 at TARGET, plus or minus thirty",
            "seconds. Read the timing block: the mission clock starts when it",
            "does BECAUSE that time has to be met — wheels up, WP1 and IP are",
            "all derived from the target time, not the other way round.",
            " - Late at WP1 is recoverable: the IP leg has speed in hand.",
            " - Late at the IP is not. The run-in is 76 seconds long.",
            " - Early is the easier problem: a 30-second S-turn before the IP",
            "   costs nothing; a 30-second dash after it costs the TOT.",
            "TARGET on time is +20 on this ride; late or early there costs double.",
        ],
    },
    {
        "key": "timing_3_thepackage", "n": 3,
        "label": "Timing 3 — The Package (F-4E)",
        "premise": "Two Phantoms fly your card two minutes ahead of you on "
                   "LOCKED ETAs. Their timeline is real; yours has to fit "
                   "behind it. Push WP1 at 12:35:00.",
        "recipe": {"time_of_day": "day", "timing_anchor": "push",
                   "timing_at": "12:35", "timing_package": True,
                   "threat_intensity": 2},
        "brief": [
            "== TIMING 3: THE PACKAGE ==",
            "A two-ship of Phantoms flies the same card two minutes ahead of",
            "you, and their ETAs are LOCKED — DCS will fly them to the second.",
            "The anchor is the PUSH: WP1 at 12:35:00, plus or minus a minute.",
            " - The package calls when it crosses the IP. If you are on time,",
            "   you are two minutes behind it — outside its frag, inside its",
            "   suppression. That spacing IS the mission.",
            " - Do not catch them up. Faster than the card at the IP puts you",
            "   over the target while their bombs are still in the air.",
            " - Do not fall back. Two minutes late and the gunners have reloaded.",
            "Wheels-up, WP1 (double), IP and TARGET are all graded.",
        ],
    },
    {
        "key": "timing_4_absorbtheearly", "n": 4,
        "label": "Timing 4 — Absorb the Early (F-4E)",
        "premise": "A three-minute hold at WP1, on purpose: you will get "
                   "there early, and the lesson is pushing at the ETA rather "
                   "than on arrival. TOT 05:50:00.",
        "recipe": {"time_of_day": "dawn", "timing_anchor": "tot",
                   "timing_at": "05:50", "timing_hold_min": 3,
                   "threat_intensity": 2},
        "brief": [
            "== TIMING 4: ABSORB THE EARLY ==",
            "Same anchor as ride 2 — TOT 05:50:00, plus or minus thirty seconds",
            "— but the card carries a three-minute HOLD at WP1. You will reach",
            "WP1 about three minutes before its printed ETA. That is planned.",
            " - Arrive at WP1, turn onto a racetrack (one-minute legs), and",
            "   push out of the hold on the WP1 ETA — not when you get there.",
            " - The WP1 grade is taken when you enter the zone, so expect an",
            "   EARLY call there. It is the IP and the TARGET that count.",
            " - This is how every professional package absorbs an early takeoff,",
            "   a short vector or a tailwind: the hold is the shock absorber.",
            "IP and TARGET on time, after a hold you flew by the clock: that is the pass.",
        ],
    },
]

RIDES.append({
    "key": "timing_5_check", "n": 5,
    "label": "Timing 5 — Check Ride (F-4E)",
    "premise": "TOT 06:00:00, and nobody talks. Wheels-up, WP1, IP and TARGET "
               "graded U / F / G / E on the clock; late at the target is a "
               "critical item. Q, Q- or U at the end.",
    "recipe": {"time_of_day": "dawn", "timing_anchor": "tot",
               "timing_at": "06:00", "threat_intensity": 2, "check_ride": True},
    "brief": [
        "== TIMING 5: CHECK RIDE ==",
        "The anchor is the TOT: 06:00:00 at TARGET. The coach is silent —",
        "one hack at the start, then the card a minute after the target.",
        " - E inside ten seconds of a point's time; G inside its window;",
        "   F early; U late or not reached.",
        " - Late at TARGET is a critical item: the check is a U.",
        " - Q needs G or better at every point; an F anywhere is a Q-.",
        "Nobody is surprised on a check ride. If you are, fly rides 2 and 4 again.",
    ],
})

TRACK_ENTRY = {
    "label": "Timing — The Clock on the Card (F-4E, 1980)",
    "short": "Timing · F-4E",
    "role": "training",
    "service": "USAF",
    "aircraft": "F_4E_45MC",
    "eras": ["coldwar"],
    "default_map": "germany",
    "featured": True,
    "series": "The Clock on the Card",
    "premise": "Four short Phantom rides from Fassberg that teach waypoint "
               "timing the way planners learn it — fly the card on a "
               "stopwatch, hit a fixed TOT, fit in behind a package on locked "
               "ETAs, absorb an early arrival with a hold — then a silent "
               "check ride. Every ride is graded in-mission.",
    "blurb": [
        "Timing is anchored, not accumulated. One time is fixed — the",
        "takeoff, the push, or the time on target — and every other number",
        "on the card is solved from it. These four rides fix a different",
        "one each, and the mission clock moves to make it true.",
    ],
}


def main():
    tpl_path = DATA / "mission_templates.json"
    tracks_path = DATA / "tracks.json"
    tpls = json.loads(tpl_path.read_text())
    tracks = json.loads(tracks_path.read_text())

    for ride in RIDES:
        recipe = dict(BASE_RECIPE)
        recipe.update(ride["recipe"])
        tpls[ride["key"]] = {
            "label": ride["label"],
            "eras": ["coldwar"],
            "maps": ["germany"],
            "default_map": "germany",
            "quick": False,
            "route": "strike",
            "library": {
                "role": "training", "threat": recipe["threat_intensity"],
                "players": "SP", "new": True, "featured": ride["n"] == 1,
                "module": "F-4E", "premise": ride["premise"],
            },
            "recipe": recipe,
            "track": {"id": TRACK, "n": ride["n"]},
            "brief": ride["brief"],
        }
    tracks[TRACK] = TRACK_ENTRY

    tpl_path.write_text(json.dumps(tpls, indent=1, ensure_ascii=False) + "\n")
    tracks_path.write_text(json.dumps(tracks, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {len(RIDES)} rides and track {TRACK!r}")


if __name__ == "__main__":
    main()
