"""Case III night carrier recovery — the doctrine, as data.

WHY THIS EXISTS
---------------
Casmo, after flying a carrier mission we generated: *"i have zero idea how to
do a case 3 recovery so i was flying around blind."*

He was not missing a skill. He was missing a procedure. Case III is a fixed
sequence of gates with published numbers at each one, and a pilot who does not
know the numbers cannot fly it however well he can fly. So this module is the
numbers — one place, sourced, with the reasoning attached — and `cq_route`,
`cq_coach` and the kneeboard all read from here rather than each keeping a
copy. The same shape as `wk.py` holds the 70 TFS Standards for the White
Knights rides.

WHERE EVERY NUMBER COMES FROM
-----------------------------
CV NATOPS Manual, NAVAIR 00-80T-105 (31 July 2009), section 6.4 and the
glossary, read directly rather than through a community summary — the summaries
disagree with each other and with the manual, and two of the disagreements are
in numbers that matter (see PLATFORM_FT and MARSHAL_RADIAL_FROM below).

Radio sequence and the LSO's own deviation thresholds: Eagle Dynamics, *DCS
Supercarrier Operations Guide*.

Cockpit procedure: the Heatblur F-14 manual and ED's F/A-18C documentation.

WHAT DCS DOES NOT DO, WHICH IS WHY THE RIDES CARRY TRIGGERS
-----------------------------------------------------------
Supercarrier gives us Marshal, an expected approach time, radar contact, the
approach handoff, the platform acknowledgement, ACLS lock, the three-quarter
mile ball call and Paddles all the way down. It does NOT enforce the approach
time — you can push half an hour early and nothing happens — and AI aircraft
cannot fly a Case III at all (they revert to Case I in the pattern), so no
stack is populated with AI and pretended otherwise.

Everything DCS ignores, these rides grade themselves: departure against the
push time, rate of descent below platform, altitude at ten miles, speed at six.
Paddles grades the last mile, because Paddles is good at it.

REQUIRES THE SUPERCARRIER MODULE, AND SAYS SO
---------------------------------------------
Marshal, the approach controller, ACLS and the LSO are module features. A Case
III trainer on the free boat would teach a procedure the mission cannot run.
`REQUIRES_MODULE` is carried into the library card and the brief rather than
discovered at mission start.
"""
from __future__ import annotations

NM_M = 1852.0
NM_FT = 6076.12
FT_M = 0.3048
KT_MS = 0.514444          # trigger-zone speed CONDITIONS are m/s
KT_KMH = 1.852            # waypoint speeds are km/h — see wk_route for the scar
FPM_MS = 0.00508          # feet per minute -> metres per second

REQUIRES_MODULE = "DCS: Supercarrier"

# --------------------------------------------------------------------------- #
# When Case III applies
# --------------------------------------------------------------------------- #
# NATOPS glossary, weather criteria: "Case III weather is any ceiling below
# 1,000 feet or a visibility less than 5 nm."
CASE3_CEILING_FT = 1000
CASE3_VIS_NM = 5

# AND THE CLOCK OVERRIDES THE WEATHER. §6.4: Case III "shall be utilized ...
# during all flight operations conducted between one-half hour after sunset and
# one-half hour before sunrise". A clear, calm night is a Case III night. This
# is the single most useful thing to tell a student first, because it explains
# why he is being taught an instrument approach for a cloudless evening.
NIGHT_MARGIN_MIN = 30

# §6.4: "Night/IMC Case III recoveries shall be made with single aircraft."
SINGLE_AIRCRAFT = True

# --------------------------------------------------------------------------- #
# The marshal stack
# --------------------------------------------------------------------------- #
# §6.4.1.1, verbatim: "The primary TACAN marshal fix is the 180 degree radial
# relative to the expected final bearing at a distance of 1 mile for every
# 1,000 feet of altitude plus 15 miles (angels +15). The holding pattern is a
# left-hand, 6-minute racetrack pattern. The inbound leg shall pass over the
# holding fix. In no case will the base altitude be lower than 6,000 feet."
MARSHAL_RADIAL_OFFSET = 180.0
MARSHAL_DME_PLUS = 15
MARSHAL_BASE_FT = 6000
MARSHAL_PATTERN_MIN = 6
MARSHAL_TURN_MIN = 2      # 2-minute turns, 1-minute legs. NATOPS states only
MARSHAL_LEG_MIN = 1       # the 6-minute total; the split is the fleet
                          # convention and ED's guide, and it is what a 180 at
                          # 250 KIAS and 30 degrees of bank actually takes.
                          # Community sources give the inverse; NATOPS does not
                          # adjudicate, and this file says so rather than
                          # asserting a number it cannot source.
MARSHAL_HOLD_KT = 250
MARSHAL_SEPARATION_MIN = 1       # §6.4.5, between aircraft departing marshal
EAT_TOLERANCE_S = 10             # the fleet-taught number; NATOPS gives none

# THE RADIAL HANGS OFF THE FINAL BEARING, NOT THE BRC — and this is the error
# that puts a student off the arc before he has started. Final bearing is the
# extension of the LANDING AREA centerline, which on an angled deck sits about
# nine degrees to port of the ship's base recovery course. NATOPS glossary:
# "The magnetic bearing assigned by CATCC for final approach. It is an
# extension of the landing area centerline."
MARSHAL_RADIAL_FROM = "final bearing"
ANGLED_DECK_DEG = 9.0     # port of BRC. Nominal for the US carriers DCS models
                          # (they are all 8-10 degrees); we do not have a
                          # per-hull survey and do not pretend to.


def final_bearing(brc: float) -> float:
    """The magnetic bearing of the landing area centerline, from the BRC."""
    return (brc - ANGLED_DECK_DEG) % 360.0


def marshal_radial(brc: float) -> float:
    """The radial the stack sits on: final bearing reciprocal."""
    return (final_bearing(brc) + MARSHAL_RADIAL_OFFSET) % 360.0


def marshal_dme(angels: int) -> int:
    """Angels + 15. The rule that makes one descent profile fit every stack."""
    return int(angels) + MARSHAL_DME_PLUS


def stack_is_legal(angels: int) -> bool:
    return angels * 1000 >= MARSHAL_BASE_FT


# --------------------------------------------------------------------------- #
# The descent
# --------------------------------------------------------------------------- #
# §6.4.7.2, verbatim: "Jet/turboprop aircraft shall descend at 250 KIAS and
# 4,000 feet per minute until platform is reached, at which point the descent
# shall be shallowed to 2,000 feet per minute. Unless otherwise directed,
# aircraft shall commence transition to a landing configuration at the 8-nm
# fix."
DESCENT_KT = 250
DESCENT_FPM = 4000

# PLATFORM IS AN ALTITUDE. NOT A RANGE. NATOPS glossary, verbatim: "platform.
# A point of 5,000 feet altitude in the approach pattern at which all jet and
# turboprop aircraft will decrease their rate of descent to not more than 2,000
# feet per minute, continuing letdown to the 10-nm DME fix."
#
# Community guides routinely quote it as "5,000 ft and about 19 DME" — the DME
# is incidental, a consequence of where the profile happens to put you, and a
# student hunting for a range gate flies straight through the rate change. It
# is graded here as an altitude for that reason.
PLATFORM_FT = 5000
PLATFORM_FPM_MAX = 2000

# The correction to the final bearing (§6.4.7.3) and the arc. DCS models
# neither — its controller simply says "fly bullseye" at intercept — so these
# are taught on the card and not graded.
CORRECT_AT_DME = 20
ARC_DME = 12

# The gates, in the order you meet them. (dme, altitude_ft, kias, what)
GATES = [
    (10, 1200, 250, "level, letdown complete — call ten miles"),
    (8, 1200, 250, "transition to landing configuration — gear, flaps, hook"),
    (6, 1200, 150, "configured, slowing to on-speed AOA"),
]
LEVEL_DME = 10
LEVEL_FT = 1200
DIRTY_DME = 8
ONSPEED_DME = 6
ONSPEED_KT = 150          # §6.4.7.8/9: through the 6-mile fix at 150 KIAS

GLIDESLOPE_DEG = 3.5      # ED's Supercarrier guide, and what its LSO grades
BALL_CALL_NM = 0.75


def glideslope_intercept_nm(alt_ft: float = LEVEL_FT) -> float:
    """Where 1,200 feet meets the glideslope. About 3.2 nm.

    ED's own guide says "expect to reach 600 feet at 3 miles", which is not on
    the 3.5 degree glidepath it specifies two pages earlier — 600 feet is 1.6
    nm. We teach the NATOPS rule instead: hold 1,200 until the glideslope
    arrives, which is roughly 3 miles, and let the needles say when.
    """
    import math
    return alt_ft / (NM_FT * math.tan(math.radians(GLIDESLOPE_DEG)))


# --------------------------------------------------------------------------- #
# Bolter and waveoff (§6.4.8)
# --------------------------------------------------------------------------- #
# "Jet and turboprop aircraft shall climb straight ahead on the extended final
# bearing to 1,200 feet altitude ... All waveoff/bolter pattern turns shall be
# level ... Fixed-wing aircraft commence turn to final at the 4 nm DME or 2
# minutes past abeam position."
BOLTER_ALT_FT = 1200
BOLTER_TURNS_LEVEL = True
BOLTER_FINAL_DME = 4
BOLTER_TIMEOUT_MIN = 2

# --------------------------------------------------------------------------- #
# What the LSO grades, so the cards can say it in the same words
# --------------------------------------------------------------------------- #
# ED's Supercarrier guide publishes these. Printing them is not cheating: a
# student who knows the machine's tolerance flies to the middle of it instead
# of guessing where the edge is.
LSO_LINEUP_DEG = 1.7
LSO_LOW_DEG = 1.5
LSO_HIGH_DEG = 2.5
LSO_FAR_LOW_DEG = 2.7
LSO_FAR_HIGH_DEG = 4.9

LSO_CALLS = [
    ("You're high / You're low, POWER", "glidepath"),
    ("You're lined up left / right", "lineup"),
    ("You're fast / You're slow", "AOA — fast means the nose is too low"),
    ("Easy with the nose / wings / it", "you are moving a control too quickly"),
    ("Power. Power. POWER", "it is getting urgent in that order"),
    ("Wave off, wave off, wave off", "go around, now"),
    ("Bolter, bolter, bolter", "you missed the wires — fly the pattern"),
]

# --------------------------------------------------------------------------- #
# The radio sequence (ED's guide, in the order the menu offers it)
# --------------------------------------------------------------------------- #
CALLS = [
    ("INBOUND", "you",
     "Marshal, [side number], marking mother's [bearing] for [range], "
     "angels [alt], low state [fuel]."),
    ("MARSHAL", "the boat",
     "Case III recovery, CV-1 approach, expected BRC [heading], altimeter "
     "[setting]. Marshal mother's [radial] radial, [DME] DME, angels [alt]. "
     "Expected approach time is [time]."),
    ("ESTABLISHED", "you",
     "[side number], established angels [alt]. State [fuel]."),
    ("COMMENCING", "you",
     "[side number] commencing, [altimeter], state [fuel]."),
    ("CHECK IN", "you",
     "[side number], checking in, [distance] miles, [fuel]."),
    ("PLATFORM", "you", "[side number], platform."),
    ("NEEDLES", "the boat",
     "[side number], ACLS lock on [distance] miles, say needles."),
    ("BALL CALL", "the boat",
     "[side number], [glidepath], [lineup], three-quarter mile, call the ball."),
    ("THE BALL", "you", "[side number], [type], ball, [fuel state]."),
]

# §6.4.13.2, verbatim: fuel state in thousands of pounds ("3.5"), altitude in
# angels ("1.2"), and heading changes on final are "normally soft headings"
# ("301, right five").
PHRASEOLOGY = [
    ("Fuel state", "thousands of pounds — \"three point five\""),
    ("Altitude", "angels — \"one point two\""),
    ("Heading on final", "soft — \"three zero one, right five\""),
    ("Clara", "you cannot see the ball"),
    ("Bullseye", "the ICLS, not the map reference"),
    ("Mother / father", "the ship / her TACAN"),
    ("Charlie", "cleared to land"),
    ("Delta", "hold and conserve"),
]

# --------------------------------------------------------------------------- #
# The cockpit half — the part that differs between the two jets
# --------------------------------------------------------------------------- #
# Heatblur's manual is explicit that the Tomcat carries the AN/ARA-63, which
# IS the airborne half of ICLS (NATOPS glossary: the ILM components are the
# AN/SPN-41 shipboard and "the AN/ARA-63 or AN/ARN-138 (airborne)"). I went
# into this build believing the F-14 had no ICLS. It does.
AIRFRAMES = {
    "F_14A_135_GR": "f14",
    "F_14A_135_GR_Early": "f14",
    "F_14A_95_GR": "f14",
    "F_14B": "f14",
    "FA_18C_hornet": "hornet",
}

COCKPIT = {
    "f14": {
        "label": "F-14A / F-14B",
        "onspeed": "15 units AOA — the amber donut on the indexer",
        "onspeed_units": 15.0,
        "setup": [
            ("TACAN", "T/R. Not A/A — that is for tankers. BCN is not "
                      "functional in DCS."),
            ("ICLS", "AN/ARA-63 panel: channel set, POWER ON. Twenty channels. "
                     "The Tomcat does have ICLS; the ARA-63 is its receiver."),
            ("ACLS", "APN-154 MODE to ACLS, or the SPN-42 never locks. Data "
                     "Link Control Panel on, MODE TAC."),
            ("STEERING", "AWL/PCD submode. HUD and VDI AWL switches to ILS for "
                         "crossed pointers — full scale 2 degrees on the HUD, "
                         "1.5 on the VDI."),
            ("COUPLE", "With ACL READY and A/P CPLR lit, press nosewheel "
                       "steering. Disengage on PLM. Add APC for hands-off."),
        ],
        "watch": [
            ("VOICE", "ACL is unavailable — go voice."),
            ("TILT", "no datalink for two seconds; the AFCS will disengage."),
            ("CMD CTRL", "you are under datalink control for the landing."),
        ],
        # Heatblur, verbatim in substance: the ARA-63 glideslope should not be
        # used until within 20 degrees of the final bearing, because the planar
        # SPN-41 elevation antenna gives erroneous indications outside it.
        "note": ("The ARA-63 glideslope is unreliable until you are within 20 "
                 "degrees of the final bearing. Turning the wrong way on "
                 "intercept makes it climb away from you and track inverted."),
    },
    "hornet": {
        "label": "F/A-18C",
        "onspeed": "8.1 units AOA — the middle tick of the bracket",
        "onspeed_units": 8.1,
        "setup": [
            ("TACAN", "T/R."),
            ("ICLS", "ILS on the UFC, channel on the scratchpad. Bars appear "
                     "beside the velocity vector."),
            ("ACLS", "Mode I coupled approach — one press of the coupled "
                     "autopilot. Expect CPLD P/R."),
            ("THE CATCH", "Mode I flies pitch and roll ONLY. Add ATC in "
                          "approach mode for the throttle, which holds AOA — "
                          "not airspeed."),
        ],
        "watch": [
            ("CPLD P/R", "coupled in pitch and roll; you still own the throttle "
                         "unless ATC is on."),
        ],
        "note": ("ACLS requires the Supercarrier module. It is not available "
                 "off the free boat."),
    },
}


def cockpit_for(aircraft_key: str) -> dict | None:
    """The setup card for this airframe, or None if it is not a Case III jet."""
    k = AIRFRAMES.get(aircraft_key)
    return COCKPIT.get(k) if k else None


# --------------------------------------------------------------------------- #
# The rides
# --------------------------------------------------------------------------- #
# One ride per gate, each starting where the last one ended. A pilot busts a
# night recovery in one of four distinct places with four different causes, and
# a single long mission teaches none of them: bust the marshal departure and
# you never reach the ball, so twenty minutes of flying buys one attempt at the
# part you actually got wrong.
#
# `angels` is the assigned stack. Rides 1-4 sit at the base of the stack (6,000
# ft / 21 DME) because NATOPS puts a single night aircraft there. Ride 5 is
# assigned angels 8, deliberately, so the check ride makes the pilot APPLY the
# angels + 15 rule instead of reciting one memorised pair of numbers.
RIDES = {
    "cq_1_stack": {
        "n": 1,
        "name": "The Stack",
        "coach": True,
        "angels": 6,
        "start": "marshal",
        "push_min": 8,          # mission minutes from start to the push time
        "premise": (
            "Holding, and only holding. Left-hand, six-minute racetrack, "
            "inbound leg over the fix — and the thing that actually takes "
            "practice: stretching and shortening the legs so you depart at the "
            "assigned second."),
        "graded": [
            "departure within 10 seconds of the push time",
            "assigned altitude held in the stack",
            "the pattern flown on the correct side of the fix",
        ],
    },
    "cq_2_push": {
        "n": 2,
        "name": "The Push",
        "coach": True,
        "angels": 6,
        "start": "marshal",
        "push_min": 1,
        "premise": (
            "The descent. 250 knots, 4,000 feet per minute, and the rate "
            "change at platform that half of all students miss because they "
            "are hunting for a DME instead of watching an altimeter."),
        "graded": [
            "rate of descent below platform, 2,000 fpm maximum",
            "level at 1,200 ft by 10 DME",
        ],
    },
    "cq_3_approach": {
        "n": 3,
        "name": "The Approach",
        "coach": True,
        "angels": 6,
        "start": "twelve",
        "premise": (
            "Correcting to the final bearing, dirtying up at 8, on speed by 6, "
            "and holding 1,200 feet until the glideslope comes to you rather "
            "than diving to meet it."),
        "graded": [
            "1,200 ft held to glideslope intercept",
            "150 KIAS at 6 DME",
        ],
    },
    "cq_4_ball": {
        "n": 4,
        "name": "The Ball",
        "coach": True,
        "angels": 6,
        "start": "final",
        "premise": (
            "The last mile, over and over. Ball call in the right format, then "
            "flying the ball instead of spotting the deck — and the bolter "
            "pattern taught rather than discovered."),
        "graded": [
            "the ball call, in format",
            "glidepath and lineup, by Paddles",
            "a bolter pattern flown level",
        ],
    },
    "cq_5_nightcq": {
        "n": 5,
        "name": "Night CQ",
        "coach": False,
        "angels": 8,
        "start": "inbound",
        "push_min": 12,
        "premise": (
            "Everything, once, for real. Night, weather, no gates drawn, no "
            "cue cards. Check in with Marshal and take yourself to the deck."),
        "graded": ["all of it, in one pass"],
    },
}

RIDE_ORDER = [k for k, _ in sorted(RIDES.items(), key=lambda kv: kv[1]["n"])]

SQUADRON = {
    "f14": {
        "unit": "VF-101",
        "nickname": "Grim Reapers",
        "role": "Fleet Replacement Squadron, F-14",
        "station": "NAS Oceana, Virginia",
    },
    "hornet": {
        "unit": "VFA-106",
        "nickname": "Gladiators",
        "role": "Fleet Replacement Squadron, F/A-18",
        "station": "NAS Oceana, Virginia",
    },
}


def ride(key: str) -> dict | None:
    return RIDES.get(key)


def is_cq_ride(key: str | None) -> bool:
    return bool(key) and key in RIDES


# --------------------------------------------------------------------------- #
# The card
# --------------------------------------------------------------------------- #
def brief_lines(ride_key: str, aircraft_key: str, brc: float | None = None,
                hull_label: str | None = None) -> list:
    """The Case III card: what this ride is, what it grades, and how to set the
    jet up for it.

    GENERATED, NOT STORED, for the same reason the White Knights card is: the
    same ride tells a different truth in a different cockpit. The Tomcat sets
    ICLS on the ARA-63 panel and the Hornet on the UFC; the on-speed number is
    15 units in one and 8.1 in the other. A stored card would have to pick one
    and be wrong in the other jet, which is the say/do gap in a flight suit.
    """
    r = ride(ride_key)
    if not r:
        return []
    ck = cockpit_for(aircraft_key) or {}
    sq = SQUADRON.get(AIRFRAMES.get(aircraft_key, ""), {})
    n, total = r["n"], len(RIDES)

    L = [f"== {sq.get('unit', 'CQ')} {sq.get('nickname', '')} — "
         f"CASE III {n} of {total}: {r['name'].upper()} ==",
         ""]
    if sq:
        L.append(f"{sq['role']}, {sq['station']}.")
        L.append("")
    L.append(r["premise"])
    L += ["",
          f"REQUIRES {REQUIRES_MODULE}. Marshal, the approach controller, ACLS "
          f"and the LSO are module features. Without them there is no Case III "
          f"sequence to fly, so this ride would be teaching a procedure the "
          f"mission cannot run.",
          ""]

    L += ["== WHY IT IS CASE III ==",
          f"Below a {CASE3_CEILING_FT:,} ft ceiling or {CASE3_VIS_NM} nm "
          f"visibility — and, whatever the weather, for all flight operations "
          f"from {NIGHT_MARGIN_MIN} minutes after sunset to {NIGHT_MARGIN_MIN} "
          f"minutes before sunrise. A clear, calm night is a Case III night. "
          f"Single aircraft.",
          ""]

    L += ["== THE GATES =="]
    L.append(f"MARSHAL   angels {r['angels']} at "
             f"{marshal_dme(r['angels'])} DME on the "
             f"{MARSHAL_RADIAL_FROM} + {int(MARSHAL_RADIAL_OFFSET)} radial. "
             f"Left-hand {MARSHAL_PATTERN_MIN}-minute racetrack, "
             f"{MARSHAL_TURN_MIN}-minute turns and {MARSHAL_LEG_MIN}-minute "
             f"legs, inbound leg over the fix.")
    L.append(f"PUSH      {DESCENT_KT} KIAS, {DESCENT_FPM:,} fpm.")
    L.append(f"PLATFORM  {PLATFORM_FT:,} ft — AN ALTITUDE, NOT A RANGE. "
             f"Shallow to {PLATFORM_FPM_MAX:,} fpm.")
    for dme, alt, kias, what in GATES:
        L.append(f"{dme:>2} DME    {alt:,} ft, {kias} KIAS — {what}.")
    L.append(f"BALL      glideslope {GLIDESLOPE_DEG} degrees, intercept about "
             f"{glideslope_intercept_nm():.1f} DME. Ball call at "
             f"{BALL_CALL_NM} nm.")
    L.append("")

    L += ["== GRADED ON =="]
    for g in r["graded"]:
        L.append(f"  - {g}")
    L += ["",
          "The grades appear on screen the moment they happen, not in a "
          "debrief you have to go and find. Everything here is something DCS "
          "does not check for itself: it will let you push half an hour early, "
          "descend at six thousand feet a minute and arrive at six miles a "
          "hundred knots fast without a word. Paddles grades the last mile, "
          "and does it better than a trigger can.",
          ""]

    if ck:
        L += [f"== YOUR COCKPIT — {ck['label']} =="]
        for k, v in ck["setup"]:
            L.append(f"{k:<10}{v}")
        L.append(f"{'ON SPEED':<10}{ck['onspeed']}")
        if ck.get("watch"):
            L.append("")
            L.append("WATCH FOR")
            for k, v in ck["watch"]:
                L.append(f"  {k:<10}{v}")
        if ck.get("note"):
            L += ["", ck["note"]]
        L.append("")

    L += ["== ON THE RADIO =="]
    for label, who, text in CALLS:
        L.append(f"{label:<12}({who}) {text}")
    L += ["", "PHRASEOLOGY"]
    for k, v in PHRASEOLOGY:
        L.append(f"  {k:<18}{v}")
    L += ["",
          "== WHAT PADDLES IS MEASURING ==",
          f"Lineup error over {LSO_LINEUP_DEG} degrees, or glidepath more than "
          f"{LSO_LOW_DEG} low or {LSO_HIGH_DEG} high, and he starts talking. "
          f"Two deviations at once for two seconds, or one bad one for four, "
          f"and he waves you off."]
    for call, means in LSO_CALLS:
        L.append(f"  {call:<38}{means}")

    L += ["",
          "== BOLTER ==",
          f"Straight ahead on the extended final bearing, climb to "
          f"{BOLTER_ALT_FT:,} ft. ALL waveoff and bolter pattern turns are "
          f"LEVEL. Report abeam with your state; turn to final at "
          f"{BOLTER_FINAL_DME} DME or {BOLTER_TIMEOUT_MIN} minutes past abeam."]

    if hull_label:
        L += ["", f"MOTHER is {hull_label}."]
    return L
