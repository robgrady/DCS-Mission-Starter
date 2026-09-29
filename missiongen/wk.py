"""The 70th Tactical Fighter Squadron "White Knights", F-4E, 1980.

WHAT THIS MODULE IS
-------------------
Four documents issued to a new arrival at the 70 TFS, Moody AFB, Georgia, in
January and February 1980, turned into data the mission builder can read:

    Low Level Training .................. 7 Jan 1980
    Conventional Tactics ................ 27 Jan 1980
    Standards ........................... 6 Feb 1980
    Weapons Information Sheet No. 1 ..... BFM Maneuvers on Command (undated)

All four signed BARRY M. MEUSE, Lt Colonel, USAF, Commander 70TFS.

THE PROVENANCE RULE, WHICH IS DIFFERENT HERE THAN ANYWHERE ELSE IN THE ENGINE
----------------------------------------------------------------------------
Almost every other number in this product is either ours (`aar.TERRAIN_MAX_FT`
rows tagged "ours") or cited to a published source. The numbers below are
neither: they are a squadron's own working document. That is a STRONGER
provenance than anything else we ship, and the rule that follows is simple —

    A value tagged `doc` is transcribed from the squadron's paper.
    It is not rounded, not modernised, and not corrected.

Where the squadron's number cannot be flown as written in a given theatre, the
brief prints BOTH and says which governs. It does not silently substitute. That
is the say/do rule applied to history: a card that quietly replaced the 70th's
300 ft with somebody else's 500 ft would be putting words in a dead man's
mouth.

WHAT IS DELIBERATELY NOT HERE
-----------------------------
* Moody AFB. It is not in DCS. The rides are staged, the cards say so.
* The range they used in January 1980. Grand Bay was established in 1985 and
  Townsend was closed from 1972 to 1981; which range they actually used is not
  in any source reached. Rather than invent one, the delivery syllabus lives on
  the Proud Phantom track, where the base IS documented.
* Any European deployment in the F-4E era. There wasn't one. The wing was
  drafted into NATO contingency plans and committed to the RDJTF, and flew to
  Nellis, Cold Lake and Cairo West. The Germany track is the war it was
  assigned, briefed as the plan — never as a deployment that happened.
"""
from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# 0. The squadron
# --------------------------------------------------------------------------- #
SQUADRON = "70th Tactical Fighter Squadron"
NICKNAME = "White Knights"
WING = "347th Tactical Fighter Wing"
STATION = "Moody AFB, Georgia"
TAILCODE = "MY"
CALLSIGN = "REX"          # Standards II, used throughout as the flight callsign
# ...and the name the SIM will say. DCS's radio speaks eight fighter names;
# REX is not one of them, so the flight flies under its stable mapping and
# the cards say both (v1.92.0, "always map"). See callsign.py.
from .callsign import dcs_name as _dcs_name
RADIO_CALLSIGN = _dcs_name(CALLSIGN)
COMMANDER = "Lt Col Barry M. Meuse"
WING_COMMANDER = "Col Bradley C. Hosmer"   # cited externally, Aug 79 - Aug 81

DOCS = {
    "lowlevel": ("70 TFS Low Level Training", "7 Jan 1980"),
    "tactics": ("70 TFS Conventional Tactics", "27 Jan 1980"),
    "standards": ("70 TFS Standards", "6 Feb 1980"),
    "wis1": ("70 TFS WIS No. 1 — BFM Maneuvers on Command", "undated"),
}

# --------------------------------------------------------------------------- #
# 1. Standards I-II — the comm card
# --------------------------------------------------------------------------- #
# Transcribed from Standards Section I. The code names are the squadron's own
# and are what the brief prints, because "DIRT" is what a 70th crew would have
# said on the radio and "Ground Control" is not.
COMMS = [
    # (preset, agency, manual freq MHz, code name)
    ("CH 1", "347th Command Post (RAYMOND 17/RAMROD)", 381.3, "RAYMOND"),
    ("CH 2", "Ground Control", 275.8, "DIRT"),
    ("CH 3", "Moody Tower", 289.6, "DONNA"),
    ("CH 4", "VAD Dept Control", 306.3, "GOOD BYE"),
    ("CH 7", "Casino Ops", 379.5, "BOBBY"),
]
CHANNELISATION = "7, (1), 2, 7, 2, 3 and 4"
AUX_ATIS = 6          # "Aux 6 will be checked for ATIS"
AUX_GUARD = 16        # "Aux 16 and guard frequencies will always be monitored"
AUX_GROUND = 11       # Standards VII: monitored when leaving ground frequency

STEP_MIN = 60         # "All flights will normally step one hour prior to T/O"
START_MIN_SMALL = 25  # flights of three or less
START_MIN_FOUR = 30   # four-ship
SYSTEMS_CHECK_FT = 7000   # Standards III.6 — not below this, mid-air lookout

# --------------------------------------------------------------------------- #
# 2. Standards III — departures
# --------------------------------------------------------------------------- #
TACTICAL_SPLIT = {
    "alt_ft": 1000, "ias_kt": 300, "split_deg": 30,
    "hold_s": (4, 6),
    "doc": "Standards III.1.a",
}
TEN_SECOND = {"turn_deg": 90, "burner_out_kt": 350, "in_place_nm": 2.0,
              "rejoin_kt": 350, "rejoin_bank_deg": 30,
              "doc": "Standards III.2"}

# --------------------------------------------------------------------------- #
# 3. Standards VI-VII — recovery and landing
# --------------------------------------------------------------------------- #
OVERHEAD = {
    "two_ship": "line abreast, #1 on the east side, lead pitches first",
    "three_ship": "point spread, #2 on the east side, pitch in order 1, 2, 3",
    "four_ship": "battle box, #1 and #3 on the east side, pitch 1, 2, 3, 4",
    # The bit of local knowledge that makes this the 70th's overhead and not a
    # generic one. It is in the document as a NOTE and it changes the spacing.
    "tower_rule_ft": 2000,
    "tower_note": ("#2 cannot fly west of the control tower, so spacing on "
                   "initial will be much closer than normal line abreast — "
                   "about 2,000 ft. Collapse the formation prior to initial."),
    "doc": "Standards VI.1",
}
DRAG_NM = {4: 15, 3: 12, 2: 9, 1: 6}      # Standards VI.2.b straight-in drags
LANDING = {
    "max_fuel_lb": 6000,
    "hook_kt": 110, "hook_marker_ft": 4000, "hook_rollout_ft": 1000,
    "doc": "Standards VII",
}

# --------------------------------------------------------------------------- #
# 4. Standards VIII — combat quick turn
# --------------------------------------------------------------------------- #
CQT = {
    "minutes": 45,
    "area": "between T-3 and T-4 at the north end of the field",
    "clock_starts": "the roll-over tire inspection in the CQT area",
    "clock_stops": "the 781A entry accepting the aircraft",
    "loads": "20mm, bombs and gas",
    "doc": "Standards VIII",
}

# --------------------------------------------------------------------------- #
# 5. Standards IV — tanker rendezvous
# --------------------------------------------------------------------------- #
TANKER_RV = {
    "tacan_offset": 63,          # "compatible TACAN channels (63 digits apart)"
    "tacan_range_nm": 200,
    "tacan_unusable": ((1, 11), (58, 74), (121, 126)),
    "holddown_s": 10,            # for ADF confirmation
    "order": (1, 3, 2, 4),
    "call_precedence": ("BEACON", "APX-80 (Flash)", "A/A TACAN", "CONTACT (radar)"),
    "contact_by_nm": 30,
    "block_levels": 4, "block_ft": 3000, "fallback_levels": 3, "fallback_ft": 2000,
    "doc": "Standards IV",
}

# --------------------------------------------------------------------------- #
# 6. Standards V — basic intercepts
# --------------------------------------------------------------------------- #
INTERCEPT = {
    "bank_deg": 45,          # "All turns are 45 degrees of bank"
    "setup_kt": 350,
    "target_kt": 350,
    "fighter_kt": 400,
    "outbound_min": 2,
    "alt_split_ft": 2000,
    "three_ship_trail_nm": (3, 4),
    "three_ship_delay_s": 20,
    "doc": "Standards V",
}
INTERCEPT_SETUPS = {
    "180": "From route formation, turn away 90°. Outbound two minutes. One "
           "aircraft turns 180° right, the other 180° left.",
    "135": "From route formation, lead turns 45° away, #2 turns 90° away. "
           "Outbound two minutes. One turns left 180°, the other right 180°.",
    "90": "From route formation, both aircraft turn away 45°. Outbound two "
          "minutes. One turns right 90°, the other left 90°.",
}

# --------------------------------------------------------------------------- #
# 7. Low Level Training — definitions, contract, turns, terrain, threats
# --------------------------------------------------------------------------- #
LOW_LEVEL_DEF_FT = 500        # "Low Level - flight at 500' and below"
NAV_BLOCK_FT = 300            # navigate at or above 300' AGL
SINGLE_SHIP_MIN_FT = 100      # single ship down to 100' AGL
FORMATION_MIN_FT = 300        # formations use these procedures down to 300'
MIN_IAS_KT = 400              # Contract 7
LINE_ABREAST_NM = (5, 7)
THREE_SHIP_STACK_NM = (6, 9)
WITHIN_DEG = 90               # Contract 12
KIO_CLIMB_FT = 500            # Contract 16

# Comm-out turn: "an optimum turn using mil power and 12-14 units."
COMM_OUT_TURN = [
    (540, 12, 7.00),
    (480, 12, 5.75),
    (420, 12, 4.00),
]
HARD_TURN = "5 to 6 G above corner velocity; 18 to 20 units AOA below corner"
BREAK_TURN = ("limit G, drag power and speed brakes above corner (max power, "
              "brakes retracted approaching corner); max power and max "
              "obtainable AOA — 25 units or less — within G limits below "
              "corner. Minimum radius and maximum rate, with no consideration "
              "for energy conservation.")

# The twenty numbered rules of Section VIII. Abridged to the ones a mission can
# actually enforce or grade; the numbering is the document's, so a card can
# cite "Contract 12" and a reader can find it on the page.
CONTRACT = {
    1: "Aircraft Commanders will maintain positive control of the aircraft and "
       "ensure terrain clearance at all times.",
    2: "Aircraft Commanders will maintain lookout from 10 o'clock to 2 o'clock.",
    3: "Weapon System Officers will maintain tactical formation and direct "
       "turns through concise and timely directive commentary.",
    5: "Weapon System Officers will maintain lookout through the formation to "
       "deep 6 o'clock.",
    6: "Elements will fly in the same training altitude blocks.",
    7: "Elements will maintain 400 KIAS minimum during low level training.",
    8: "Wingman will not fly lower (AGL) than their leader.",
    10: "Use of the UHF will be minimized except to ensure mutual support, "
        "elimination of confusion or safety of flight.",
    11: "The wingman will always strive for line abreast.",
    12: "The wingman will always remain within 90 degrees of lead's heading.",
    13: "The aircraft in front is responsible for getting back to line abreast.",
    16: "The term KNOCK-IT-OFF will be used to terminate low altitude "
        "operations and may be called by any flight member. All aircraft will "
        "acknowledge with call sign, roll wings level and initiate a climb "
        "above 500' or the next higher altitude block.",
    18: "KNOCK-IT-OFF will be called when an aircraft is observed descending "
        "during a turn and bank is not decreasing. Response will be a wings "
        "level roll for recovery.",
    20: "Formation training below 500' AGL is limited to two-ship tasks.",
}

# WSO -> AC, the vocabulary that actually flies the airplane at 300 feet.
WSO_CALLS = [
    ("5 Right/Left", "Check turn to get the formation line abreast."),
    ("30 Right/Left", "Optimum turn of approximately 30°. The formation is in "
                      "a comm-out 90° turn and the other aircraft is turning "
                      "into us."),
    ("90 Right/Left", "Turn 90°. Mil power plus G and AOA."),
    ("Hard Right/Left", HARD_TURN + "."),
    ("Break Right/Left", "Last ditch. " + BREAK_TURN),
    ("Weave Right/Left", "Optimum turn, approximately 60° HCA. Wings level, "
                         "cross in front of the other aircraft, then back to "
                         "course on the WSO's call."),
    ("Push it up 10/20", "Increase power to catch up with lead."),
    ("Pull it back 10/20", "Decrease power to fall back with lead."),
    ("Up 100 / Down 100", "Climb or descend 100 feet — comfort level exceeded, "
                          "or the formation is not level."),
    ("Six is clear", "Advises the AC that six o'clock is being checked."),
    ("Roll Out", "Set wings level."),
    ("Knock it off", "Discontinue maneuvering, climb above 500' AGL, "
                     "investigate."),
]

# AC -> WSO. Short, and the first one is the whole job.
AC_CALLS = [
    ("Rocks right/left", "Expect to see terrain going by."),
    ("Bunt", "Expect a pushover."),
    ("Birds", "Usually said after the fact. Expect an abrupt maneuver."),
    ("Rolling right/left", "Self explanatory."),
    ("Visual", "Lead/wingman in sight."),
    ("Tally", "Bogey/bandit in sight."),
]

COMM_OUT_TURNS = {
    "away90": (
        "90° TURN AWAY FROM THE WINGMAN. Lead turns 30° away and rolls out. "
        "#2's WSO sees the turn and directs his AC '90 right/left'. #2 picks a "
        "90° point on the horizon; as the turn progresses he picks up VISUAL "
        "as lead crosses his 10-to-2 o'clock, and his WSO calls the roll-out "
        "at the 90° point. #1's WSO holds visual on the wingman, and when #2 "
        "crosses six o'clock — for 5-7 nm line abreast — directs his AC to "
        "complete the turn. Both roll out line abreast, 90° from the original "
        "heading."),
    "into90": (
        "90° TURN INTO THE WINGMAN. Lead starts a 90° turn into the wingman. "
        "#2's WSO directs '30 left/right'. Lead passes BEHIND you. When lead "
        "is directly at six o'clock, #2's WSO directs '60 left/right'. When "
        "both aircraft are back line abreast, '#2 ROLL OUT'."),
    "away_lt90": (
        "LESS THAN 90° AWAY. As the 90° away, until #2's WSO sees lead roll "
        "into him — then 'ROLL OUT', then 'WEAVE LEFT/RIGHT'. At about 60° HCA "
        "#1's WSO calls his own roll-out. When #2 is at six o'clock, #1 turns "
        "the required number of degrees back to course and line abreast."),
    "into_lt90": (
        "LESS THAN 90° INTO. Lead turns hard into the wingman to the desired "
        "heading and rolls out. '#2, 30 left/right'; when lead has rolled out, "
        "'WEAVE RIGHT/LEFT'; at about 60° HCA, 'ROLL OUT'."),
    "180": "180° turns will NOT be standard, but prebriefed each time they are used.",
}

TURN_ERROR = ("The most common mistake in low altitude turning is the initial "
              "tendency to CLIMB, usually caused by starting the turn lower "
              "than the comfort factor. The roll-in is critical: if a level "
              "nose track is not established rapidly there is no reference on "
              "which to base correction. If a climbing trend is evident from "
              "the roll-in, do NOT attempt to overbank down to the original "
              "altitude — stop the climb and complete the turn at an altitude "
              "where you can be comfortable.")

RIDGE = {
    "approach": "Begin a climb before the ridgeline so you crest the top with "
                "a LEVEL flight path. Done correctly the ridgeline masks you "
                "from an AI missile threat.",
    "bunt": ("Negative-G pushover. Keeps sight of lead/wingman and does not "
             "flash your white belly. Takes longer and is uncomfortable."),
    "rollover": ("Roll inverted and apply positive G. Quicker, but you lose "
                 "visual on lead and can disorient easily. The slice variant "
                 "blends rudder and rollover in about a 135° slice."),
    "rule": "Small ridgelines require only a bunt; large ridgelines are "
            "generally best crossed with a rollover or slice.",
    "caution": "In either option, be aware of the possibility of committing "
               "your nose too low transitioning from the top of the ridgeline "
               "back down into a low altitude posture.",
}

THREATS = {
    "avoid_ag": ["Don't fly near the threat.", "Avoid LOCs.",
                 "Fly in rough terrain.",
                 "Avoid terrain that will hi-light you (dry lakes, light areas)."],
    "radar": ["Stay fast.", "Get lower.", "Chaff — with a maneuver.",
              "Put terrain between you and the threat."],
    "missile": ["Put it on the beam.", "Drop chaff.", "SAM evasive maneuver."],
    "air": ["Push it up.", "Spread the formation.", "Get lower."],
    "remember": ["Threat ordnance is limited.",
                 "At low level your vulnerable cone is reduced."],
}

ROUTE_ABORT = {
    "primary": ["Avoid the ground.", "Avoid a mid-air."],
    "vfr_kt": 350,
    "mea_rule": "1,000' above the highest obstacle on the route, rounded up to "
                "the nearest thousand, plus 500' MSL.",
    "mea_example": (731, 1731, 2500),   # the document's own worked example
    "lost_wingman_ft": 1000,
    "doc": "Low Level IX",
}

# --------------------------------------------------------------------------- #
# 8. The low-level FLOOR, by theatre — the one place history and host nation
#    disagree, and the reason `by_map` exists.
# --------------------------------------------------------------------------- #
# (floor_ft, basis, note). `basis` is one of:
#   "squadron"    — the 70th's own contract, from the 7 Jan 1980 document
#   "host_nation" — a national rule that overrides the squadron's number
#
# UNLISTED MAPS FAIL CLOSED to the most restrictive floor we know about. For a
# minimum altitude, failing closed means the HIGHER number: an unlisted map
# gets a conservative floor rather than permission the theatre never gave.
LOW_LEVEL_FLOOR_FT = {
    "germany": (500, "host_nation",
                "West Germany's general Cold War minimum for jet low flying "
                "was 500 ft AGL, with seven designated 250 ft low-flying areas "
                "and nowhere else. Your squadron's contract does not apply "
                "here."),
    "sinai": (FORMATION_MIN_FT, "squadron",
              "No host-nation restriction applies. The squadron's own "
              "formation floor governs."),
    "nevada": (FORMATION_MIN_FT, "squadron",
               "Range airspace. The squadron's own formation floor governs."),
    "caucasus": (FORMATION_MIN_FT, "squadron",
                 "The squadron's own formation floor governs."),
}
FLOOR_DEFAULT_FT = max(v[0] for v in LOW_LEVEL_FLOOR_FT.values())


def floor_ft(map_key: str) -> int:
    """The lowest altitude a FORMATION may work at in this theatre."""
    row = LOW_LEVEL_FLOOR_FT.get(map_key)
    return int(row[0]) if row else int(FLOOR_DEFAULT_FT)


def floor_basis(map_key: str) -> str:
    row = LOW_LEVEL_FLOOR_FT.get(map_key)
    return row[1] if row else "host_nation"


def floor_note(map_key: str) -> str:
    row = LOW_LEVEL_FLOOR_FT.get(map_key)
    return row[2] if row else (
        "This theatre is not in our table, so the most restrictive floor we "
        "know about is applied. A floor we cannot source is not permission.")


def floor_conflicts(map_key: str) -> bool:
    """True when the theatre floor is ABOVE what the squadron trained to.

    This is the whole reason the ride is interesting, and it must be computed
    rather than written into a card — a card that hard-codes 'your contract is
    illegal here' would be wrong the moment somebody flew it in Egypt.
    """
    return floor_ft(map_key) > FORMATION_MIN_FT


# --------------------------------------------------------------------------- #
# 9. WIS No. 1 — BFM maneuvers on command
# --------------------------------------------------------------------------- #
# The intra-cockpit directive calls, with the document's own parameters. These
# are what the mission speaks to the pilot, so the wording stays the squadron's.
BFM_CALLS = [
    ("HARD LEFT/RIGHT",
     "Defensive turn to prevent an attacker entering the vulnerable cone. "
     "Start with 5-6 Gs above corner, or 18-20 units below corner. Max power. "
     "Expect 'harder' or 'ease off' immediately."),
    ("HARDER LEFT/RIGHT",
     "The turn intensity you responded with was insufficient. Increase G or "
     "AOA, or slow down to turn tighter."),
    ("EASE OFF", "The turn you are sustaining is excessive. Decrease G and "
                 "AOA. Maintain max power."),
    ("BREAK LEFT/RIGHT/UP",
     "Last ditch — a missile launch has occurred or is imminent. Energy "
     "conservation is NOT a factor. Minimum radius and maximum rate, best "
     "achieved at corner velocity. Above corner: limit G, drag power, speed "
     "brakes as required. Below corner: max power and max obtainable AOA. "
     "A single plane maneuver into the attack, and it had better work."),
    ("ROLL LEFT/RIGHT",
     "A bandit overshoot has occurred and the defender is not committing to "
     "the fight. Relax AOA immediately to roll quickly with aileron, far "
     "enough to check the bandit's position and reaction."),
    ("REVERSE LEFT/RIGHT",
     "Overshoot, and the defender chooses to stay and fight. Decrease the "
     "attacker's nose/tail separation: loaded roll (G, not AOA) with moderate "
     "buffet, 18-20 AOA, nose high, aileron and rudder. 'Extend' is a poor "
     "follow-up here and usually leads to 'Break'."),
    ("SET YOUR WINGS",
     "The second move in taking away the bandit's nose/tail separation. "
     "Minimise or stop horizontal motion — set the wings level with the "
     "horizon. Expect a 'pull' call."),
    ("PULL",
     "Wings set, a healthy pull toward the pure vertical. Slows or stops "
     "horizontal movement and generates nose/tail separation with nose "
     "position advantage. Pull at G or AOA limit until the desired nose "
     "position is established."),
    ("GUNS BREAK",
     "Last ditch against a gun attack. A successful gun defense must occur "
     "OUT OF PLANE, so this is a ROLLING break. Roll performance is poor at "
     "very high AOA — above corner, aileron and rudder THEN back stick; below "
     "corner, aileron, rudder and back stick simultaneously to the G limit. "
     "Minimum 180° of roll, and NOT a smooth, predictable, continuous rate "
     "roll."),
    ("JINKOUT",
     "Guns defense while gaining energy and possible separation. Random "
     "applications of roll, pitch and acceleration that move the AIRCRAFT — "
     "not just the controls. Each time, hold them just long enough to "
     "establish a new flight path. A multiplane maneuver, NOT a porpoise. "
     "Maximum power, and extreme caution for G overshoots as you accelerate "
     "past corner."),
    ("EXTEND",
     "Gain energy and separation when not immediately threatened. Ideally a "
     "straight line unloaded acceleration. Max power and zero G at the call."),
    ("KICK OUT LEFT/RIGHT",
     "Maintain tally on the bandit during an extension. Hard turn parameters. "
     "Expect a series of kickouts and extensions if the bandit pursues."),
    ("KICK ACROSS THE TAIL",
     "Reposition the attacker on the opposite side during an extension. "
     "Performed the same as the kickout."),
    ("PITCHBACK LEFT/RIGHT",
     "Nose high course reversal from high calibrated airspeed — trading "
     "EXCESS airspeed for altitude. Max power, pull the nose high at about "
     "6½ G. May resemble a chandelle, Immelmann or half Cuban 8. 400 KCAS is "
     "generally a good tactical minimum."),
    ("SLICEBACK LEFT/RIGHT",
     "Nose low course reversal from low or medium airspeed — trading altitude "
     "for turn performance. Roll the lift vector below the horizon and pull, "
     "generally max power and AOA to maintain 400 knots or greater."),
    ("PITCH LEFT/RIGHT TO SLICE",
     "Efficient course reversal from high calibrated airspeed, sacrificing "
     "some energy for a quicker turn. Pitch up at about 6½ G and retard the "
     "power; play the transition so the nose passes down through the horizon "
     "nearing corner. Up to 25 units AOA as speed reaches corner."),
]

# Inter-flight. Seven calls, and the last one is the best line in the packet.
FLIGHT_CALLS = [
    ("VISUAL", "One fighter sees the other. No enemy in sight."),
    ("TALLY", "Sight of an enemy fighter. Wingman not in sight."),
    ("TALLY/VISUAL", "Sight of the enemy aircraft AND your wingman."),
    ("PRESS", "From the free fighter to the engaged fighter: continue your "
              "attack. The free fighter will be able to support you during an "
              "overshoot or come-off. But don't bet your ass on it — never "
              "trust your wingman to bail you out."),
    ("LAG", "The opposite of PRESS. The free fighter will NOT be in a position "
            "to support you during an overshoot or come-off."),
    ("COME-OFF", "From the leader: come off the attack, the leader is in "
                 "position to deliver ordnance. From the wingman: if he "
                 "doesn't come off right now, he is committed to continue "
                 "engaging until the wingman can reposition."),
    ("NO TALLY, NO VISUAL, I'M ENGAGED",
     "Hack your clock. In ten to thirty seconds you'll be dead."),
]

# --------------------------------------------------------------------------- #
# 10. Conventional Tactics I — assumptions
# --------------------------------------------------------------------------- #
INGRESS = {"tas_kt": 540, "turn_radius_ft": 5400, "deg_per_sec": 10, "g": 5}
DELIVERY_TURN = {"tas_kt": 500, "turn_radius_ft": 6500, "radial_g": (3.5, 4.0)}
EGRESS = dict(INGRESS)
TRACKING_S = 3            # tracking time on final, all deliveries
TRACKING_S_DIRECT = 5     # 30° and 15° direct delivery

DT_DRILL = (
    "At PUP, pull to the climb angle calculated for the DT delivery you "
    "planned to use. Continue the attack as planned. IF YOUR DT WORKS, PRESS "
    "ON. If you have to revert to your back-up direct delivery, at the AOD "
    "check IPP and continue to the direct delivery release altitude.")

# --------------------------------------------------------------------------- #
# 11. Conventional Tactics VI — the delivery planning sheets
# --------------------------------------------------------------------------- #
# Transcribed. Every field is the squadron's; nothing is derived.
DELIVERIES = {
    "lald15": {
        "label": "Low Angle Low Drag, 15°",
        "ordnance": "6 × MK-82LD", "angle": 15, "release_kt": 500,
        "release_ft": 2000, "mils": 121, "mils_aoa": 0.8,
        "corr": "0.7 mil/kt head/tail, 10 ft/kt crosswind",
        "slant_ft": 5551, "interval_s": 0.1, "pattern_ft": 201,
        "last_bomb_ft": 1886, "aod_ft": 2300, "ipp_mils": 45,
        "apex_ft": 5700, "pup_ft": 11400, "climb_deg": 30,
        "pdp_ft": 4200, "map_ft": 7626,
    },
    "dive30": {
        "label": "Dive Bomb, 30°",
        "ordnance": "6 × MK-82LD", "angle": 30, "release_kt": 500,
        "release_ft": 4000, "mils": 119, "mils_aoa": 0.6,
        "corr": "1.07 mil/kt head/tail, 12 ft/kt crosswind",
        "slant_ft": 6755, "interval_s": 0.1, "pattern_ft": 136,
        "last_bomb_ft": 3781, "aod_ft": 1500, "ipp_mils": 35,
        "apex_ft": 10000, "pup_ft": 13333, "climb_deg": 45,
        "pdp_ft": 7750, "map_ft": 8133,
    },
    "hidrag10": {
        "label": "High Drag, 10°",
        "ordnance": "4 × MK-82HD", "angle": 10, "release_kt": 500,
        "release_ft": 1000, "mils": 171, "mils_aoa": 0.8,
        "corr": "1.2 mil/kt head/tail, 11 ft/kt crosswind",
        "slant_ft": 3070, "interval_s": 0.1, "pattern_ft": 202,
        "last_bomb_ft": 954, "aod_ft": 2700, "ipp_mils": 70,
        "apex_ft": 2500, "pup_ft": 9999, "climb_deg": 15,
        "pdp_ft": 1750, "map_ft": 5405,
    },
    "dt35": {
        "label": "Dive Toss, 35°",
        "ordnance": "6 × MK-82LD", "angle": 35, "release_kt": 500,
        "release_ft": 6000, "drag_coeff": 1.04,
        "slant_ft": 10400, "min_release_ft": 4000,
        "interval_s": 0.1, "pattern_ft": 870, "release_advance": 250,
        "apex_ft": 10000, "pup_ft": 13333, "climb_deg": 45,
        "pdp_ft": 7750, "map_ft": 10590,
        "backup": "dive30",
    },
    "dt20": {
        "label": "Dive Toss, 20°",
        "ordnance": "6 × MK-82LD", "angle": 20, "release_kt": 500,
        "release_ft": 3400, "drag_coeff": 1.03,
        "slant_ft": 10000, "min_release_ft": 2000,
        "interval_s": 0.1, "pattern_ft": 1080, "release_advance": 250,
        "apex_ft": 5700, "pup_ft": 11400, "climb_deg": 30,
        "pdp_ft": 4200, "map_ft": 11800,
        "backup": "lald15",
    },
}
DT_PULLOUT = "Dive Toss 4G pullout in 2 seconds."

# --------------------------------------------------------------------------- #
# 12. Conventional Tactics II-V — the four attacks
# --------------------------------------------------------------------------- #
ATTACKS = {
    "echelon": {
        "label": "Echelon Attack (Low/High)",
        "section": "IV",
        "definition": "Attacks where all aircraft in the formation attack from "
                      "the same hemisphere.",
        "geometry": [
            "Mutual support is maintained all the way to the pop point.",
            "Lead employs a low angle off, low altitude delivery.",
            "The wingman uses a 90° angle off medium altitude delivery.",
            "Number two DELAYS HIS POP FIVE SECONDS and climbs to a higher and "
            "wider base — spacing on lead, precluding distraction while "
            "tracking and conflict during recovery.",
            "The second aircraft must recover ABOVE the highest anticipated frag.",
            "Lead jinks and turns to the egress heading so number two can "
            "maneuver rapidly to line abreast.",
        ],
        "pro": ["Good visual cross-coverage and mutual support throughout most "
                "of the attack.",
                "Flight integrity in poor weather or limited visibility.",
                "Minimum time in the target area.",
                "Best utilised when the attack axis is limited.",
                "An excellent low visibility alternate to the split for "
                "separate targets in the target area."],
        "con": ["Minimum attack axis divergence.",
                "If the wingman doesn't delay pop up long enough, he will end "
                "up in-trail with lead.",
                "Requires one attacker to go high to obtain frag separation."],
        "delay_s": 5,
    },
    "double90": {
        "label": "Double 90 Attack",
        "section": "V",
        "definition": "Primarily employed when high drag weapons are being "
                      "carried and time is used for frag clearance.",
        "geometry": [
            "Two-ship mutual support is maintained until approximately 4 NM "
            "short of the target.",
            "Lead turns 30° AWAY from the wingman and pops immediately for a "
            "low angle off delivery.",
            "The wingman turns 90° INTO lead, DELAYS EIGHT SECONDS, then turns "
            "90° back towards the target and begins his pop.",
            "Recommended: the wingman hacks the clock on lead's bomb "
            "detonation — it gives an added indication of his separation.",
            "Lead jinks off opposite the roll-in heading.",
        ],
        "why": ["It puts lead in a position to visually clear the wingman's "
                "six as #2 completes his delivery.",
                "It provides time for number two to complete his attack and "
                "have the two-ship egress together with mutual support."],
        "pro": ["Flight integrity in poor weather or limited visibility.",
                "Maximises each aircraft's six o'clock coverage during his "
                "pop-up attack.",
                "Best utilised when time is used for frag clearance.",
                "Ideal for low ceiling/visibility."],
        "con": ["Minimum attack divergence.",
                "If the wingman doesn't delay long enough, frag clearance will "
                "not be met.",
                "Low altitude deliveries increase target acquisition problems."],
        "delay_s": 8,
        "support_nm": 4.0,
    },
    "bnai": {
        "label": "B'NAI Attack (Low/High)",
        "section": "III",
        "definition": "Designed by the Israelis in the 1973 Mid East war to "
                      "improve visual cross-coverage during a pop up attack in "
                      "an SA-6 environment. Because of this greater SAM "
                      "threat, the SA-6 was considered a primary threat and "
                      "MIGs were secondary.",
        "geometry": [
            "A 2-3 NM in-trail attack formation.",
            "While lead is attacking, number two is at low altitude visually "
            "covering lead's six o'clock.",
            "Lead executes a turning recovery to minimum altitude and egress "
            "heading; in the meantime he is in position to visually cover the "
            "wingman during his attack.",
            "Number two comes off the target in the OPPOSITE direction from "
            "lead. Both aircraft continue to turn until established on egress "
            "heading or line abreast, whichever is considered most important "
            "at the time.",
            "To set in-trail spacing, approach the IP at nearly 90° angle off "
            "with lead on the side of the formation nearest the target. At the "
            "IP lead turns inbound and number two turns away momentarily, then "
            "back inbound.",
        ],
        "pro": ["Maximizes each aircraft's six o'clock coverage during his pop "
                "up attack.",
                "Good offensive maneuverability.",
                "No flight path conflicts."],
        "con": ["No visual cross coverage from the IP to the pop.",
                "Same ingress ground track.",
                "Extended time in the immediate target area.",
                "Defenses alerted for the number two aircraft."],
        "trail_nm": (2, 3),
        # --- read off the DIAGRAM, not the prose -------------------------- #
        # The B'NAI page carries annotations the body text does not: the pop
        # is labelled in four stages, and the two aircraft climb at different
        # angles. Transcribed here because the coached ride cues on them and a
        # cue that fires on a number nobody can point at is decoration.
        #
        # The stage ORDER is the drawing's, bottom of the curve upward:
        # PUP, ROLL-IN, APEX, TRACK POINT. Roll-in below apex is not a
        # transcription slip — you begin the pull-down at roll-in and the jet
        # coasts up to apex as the nose comes through, which is why the
        # delivery sheets put PDP 1,500 ft under APEX for a 30 degree climb.
        "pop_stages": ("PUP", "ROLL-IN", "APEX", "TRACK POINT"),
        "climb_deg_lead": 30,        # "PUP (CL ∡ - 30°)", right-hand track
        "climb_deg_two": 45,         # "(CL ∡ - 45°) PUP", left-hand track
        "tas_kt": 540,               # matches INGRESS["tas_kt"]; not a
                                     # second, softer source for the same fact
        "diagram_note": "Both aircraft may attack from the same direction or "
                        "from a different direction, as depicted.",
    },
    "split_lowhigh": {
        "label": "Split Attack, Low/High",
        "section": "II",
        "definition": "Attacks where the target is attacked from approximately "
                      "opposite directions.",
        "geometry": [
            "The most effective geometry is just a little short of 180° from "
            "one another, and different release parameters.",
            "Two-ship mutual support is maintained until approximately 4.5 NM "
            "short of the target.",
            "Lead turns 30° and pops immediately for a low angle off delivery.",
            "The wingman turns 45° and pops for an almost 90° angle off "
            "delivery.",
            "The resultant attack axes converge at approximately 120-150°.",
            "Target separation is accomplished through timing and both "
            "horizontal and vertical separation. With close-in release ranges "
            "the wingman establishes time separation over the target by "
            "DELAYING HIS ROLL-IN — which also gives more angle off and higher "
            "release parameters than lead.",
        ],
        "pro": ["Enemy defenses split.",
                "May cause confusion, further reducing enemy defense.",
                "Ideal for simultaneous attacks on separate targets in the "
                "same area (minimum separation).",
                "Both attacks can be low angle.",
                "Minimum time in the target area."],
        "con": ["Loss of some mutual support.",
                "Potential flight path conflict over the target and on "
                "recovery.",
                "Possible frag clearance problem for the subsequent aircraft."],
        "support_nm": 4.5,
        "converge_deg": (120, 150),
    },
    "split_lowlow": {
        "label": "Split Attack, Low/Low (Separate Aimpoints)",
        "section": "II",
        "definition": "The same geometry as the low/high profile with the "
                      "exception of different aimpoints.",
        "geometry": [
            "At the split point lead turns 45° and pops immediately for a low "
            "angle off delivery.",
            "The wingman turns 45°, DELAYS FIVE SECONDS, and also pops to a "
            "low angle off delivery.",
            "The resultant attack axes converge at approximately 160-180°.",
            "EXERCISE CAUTION WHEN SELECTING THE AIMPOINTS FOR EACH AIRCRAFT. "
            "Separation for MK-82s should be approximately 6,000 ft.",
            "Because both aircraft are performing low angle off deliveries "
            "simultaneously, each must ensure frag clearance not only from "
            "their own delivery, but from the subsequent aircraft's frag also.",
            "For the 180° egress, greater target separation is required — in "
            "this attack, 10,000 ft.",
        ],
        "pro": ["As the low/high split."],
        "con": ["Loss of some mutual support.",
                "Potential flight path conflict over the target and on "
                "recovery.",
                "Possible frag clearance problem for the subsequent aircraft."],
        "delay_s": 5,
        "aimpoint_sep_ft": 6000,
        "target_sep_ft": 10000,
        "converge_deg": (160, 180),
    },
}

# Teaching order. NOT the document's order, and the reason is in the document's
# own disadvantage lists: you do not start a new wingman on the attack whose
# drawbacks open with "loss of some mutual support" and end with a flight path
# conflict over the target.
ATTACK_ORDER = ["echelon", "double90", "bnai", "split_lowhigh", "split_lowlow"]

# THE SQUADRON'S OWN DIAGRAMS, lifted from the pages of Conventional Tactics by
# scripts/build_wk_diagrams.py. Redrawing them would have meant re-deriving
# every angle by eye from a scan and inventing a second source of truth for
# geometry nobody can check — so the picture on the kneeboard is the picture on
# the page. A pilot in the pop needs a picture, not a paragraph.
DIAGRAM_DIR = Path(__file__).parent / "data" / "wk"
DIAGRAMS = {k: f"wk_{k}.png" for k in ATTACKS}


def diagram_path(attack_key: str):
    """The diagram file for an attack, or None if the asset is absent.

    Returns None rather than raising: a missing asset must degrade to a card
    with no picture, never to a mission that will not build."""
    name = DIAGRAMS.get(attack_key)
    if not name:
        return None
    p = DIAGRAM_DIR / name
    return p if p.is_file() else None


def diagram_note(attack_key: str) -> list:
    """The line that goes with the picture. It says where it came from, because
    a diagram with no provenance is just a drawing."""
    a = ATTACKS.get(attack_key) or {}
    name, date = DOCS["tactics"]
    return [f"DIAGRAM: {a.get('label', attack_key)} — {name}, Section "
            f"{a.get('section', '?')}, {date}. Reproduced from the squadron's "
            f"own page, not redrawn.",
            "Read the pop-up geometry off the drawing: PUP, roll-in, apex, "
            "track point, and the minimum attack parameter circle around the "
            "target. The egress options are below it."]


def attack_brief(key: str) -> list:
    """The attack card, straight out of the guide."""
    a = ATTACKS[key]
    L = [f"== {a['label'].upper()} ==",
         f"70 TFS Conventional Tactics, Section {a['section']}.", "",
         a["definition"], "", "HOW IT IS FLOWN:"]
    L += [f" - {g}" for g in a["geometry"]]
    if a.get("why"):
        L += ["", "WHY IT IS BUILT THIS WAY:"] + [f" - {w}" for w in a["why"]]
    L += ["", "ADVANTAGES (the squadron's own list):"]
    L += [f" + {p}" for p in a["pro"]]
    L += ["", "DISADVANTAGES (also the squadron's own — read these twice):"]
    L += [f" - {c}" for c in a["con"]]
    return L


# --------------------------------------------------------------------------- #
# 13. Shared brief blocks
# --------------------------------------------------------------------------- #
def header_lines(doc_key: str) -> list:
    name, date = DOCS[doc_key]
    return [f"70 TFS \"WHITE KNIGHTS\" — {WING}, {STATION}",
            f"Source: {name}, {date}. {COMMANDER}, Commander.",
            ""]


def staging_note(map_key: str) -> list:
    """Said once on every card, because it is the honest part.

    Moody AFB is not in DCS. A card that quietly flew this syllabus somewhere
    else without saying so would be exactly the say/do gap this product exists
    to remove — the pilot would reasonably assume the ground under him was the
    ground the document was written about.
    """
    if map_key == "sinai":
        return ["STAGING: Cairo West and the Egyptian ranges. The squadron was "
                "actually here — twelve F-4Es, June to 3 October 1980, "
                "exercise PROUD PHANTOM.", ""]
    if map_key == "germany":
        return ["STAGING: the 347th was drafted into NATO contingency plans "
                "and never deployed to Europe in the Phantom. This is the war "
                "it was ASSIGNED, flown as the plan — not a deployment that "
                "happened. Moody AFB is not in DCS.", ""]
    return ["STAGING: Moody AFB is not in DCS. The terrain under you is a "
            "stand-in; the procedures are the squadron's own.", ""]


def comm_card_lines() -> list:
    L = ["== COMM CARD (Standards, Section I) ==",
         f"Flight callsign {CALLSIGN} in the Standards. On the radio you fly "
         f"as {RADIO_CALLSIGN.upper()} 1 — DCS speaks only its eight fighter "
         f"names, and that is the one ATC and your wingman will use. "
         f"Channelisation sequence {CHANNELISATION}.", ""]
    for preset, agency, freq, code in COMMS:
        L.append(f" {preset}  {freq:7.3f}  {code:<9} {agency}")
    L += ["",
          f" Aux {AUX_ATIS} for ATIS. Aux {AUX_GUARD} and guard always "
          f"monitored.",
          f" Aux {AUX_GROUND} monitored when leaving ground frequency.",
          "",
          "The code names are the squadron's. On the radio you say DIRT, not "
          "'ground control'."]
    return L


def contract_lines(map_key: str) -> list:
    """The low-level contract, with the theatre floor resolved against it."""
    f = floor_ft(map_key)
    L = ["== THE CONTRACT (Low Level Training, Section VIII) ==",
         "Twenty numbered rules. These are the ones this ride enforces.", ""]
    for n in (1, 2, 3, 7, 8, 11, 12, 13, 16, 20):
        L.append(f" {n:>2}. {CONTRACT[n]}")
    L += ["", "== ALTITUDE: TWO NUMBERS, AND WHICH ONE GOVERNS =="]
    L += [f"YOUR SQUADRON: low level is {LOW_LEVEL_DEF_FT}' and below. Navigate "
          f"at or above {NAV_BLOCK_FT}', descending into the "
          f"{SINGLE_SHIP_MIN_FT}'-{NAV_BLOCK_FT}' block only as required to "
          f"defeat surface and air threats. Single ship to "
          f"{SINGLE_SHIP_MIN_FT}'; FORMATIONS TO {FORMATION_MIN_FT}'."]
    if floor_conflicts(map_key):
        L += ["",
              f"THIS THEATRE: {f}' AGL. {floor_note(map_key)}",
              "",
              f"*** {f} FEET GOVERNS. ***",
              "Your contract is the squadron's and it does not travel. This is "
              "not a correction to the 7 January document — it is what happens "
              "to a squadron's own rules the day it crosses somebody else's "
              "border, and it is the reason flight leads read host-nation "
              "supplements before they read tactics."]
    else:
        L += ["",
              f"THIS THEATRE: no host-nation restriction. {f}' governs — your "
              f"own number."]
    L += ["",
          f"AND {MIN_IAS_KT} KIAS MINIMUM (Contract 7). Slower than that at "
          f"this height is not a low level, it is a target."]
    return L


def wso_call_lines() -> list:
    L = ["== INTER-COCKPIT: WSO TO AC ==",
         "The pit flies the formation. You fly the airplane and avoid the "
         "rocks.", ""]
    for call, meaning in WSO_CALLS:
        L.append(f" \"{call}\" — {meaning}")
    L += ["", "== AC TO WSO =="]
    for call, meaning in AC_CALLS:
        L.append(f" \"{call}\" — {meaning}")
    return L


def bfm_call_lines() -> list:
    L = ["== BFM MANEUVERS ON COMMAND (WIS No. 1) ==",
         "Mission success will be determined by the quickness and accuracy of "
         "execution and general aircraft control and situation awareness in "
         "response to these calls.", ""]
    for call, meaning in BFM_CALLS:
        L.append(f" \"{call}\"")
        L.append(f"    {meaning}")
    L += ["", "== INTER-FLIGHT =="]
    for call, meaning in FLIGHT_CALLS:
        L.append(f" \"{call}\" — {meaning}")
    return L


def delivery_lines(key: str) -> list:
    """A delivery planning sheet, printed as the sheet."""
    d = DELIVERIES[key]
    L = [f"== DELIVERY PLANNING SHEET — {d['label'].upper()} ==",
         "70 TFS Conventional Tactics, Section VI. Transcribed, not rounded.",
         "",
         f" ORDNANCE                 {d['ordnance']}",
         f" DELIVERY                 {d['angle']}°",
         f" RELEASE AIRSPEED         {d['release_kt']} KIAS",
         f" RELEASE ALTITUDE         {d['release_ft']:,}'"]
    if "mils" in d:
        L.append(f" MILS                     {d['mils']} (+{d['mils_aoa']})")
        L.append(f" CORRECTION FACTORS       {d['corr']}")
    if "drag_coeff" in d:
        L.append(f" DRAG COEFFICIENT         {d['drag_coeff']}")
    L.append(f" PICKLE SLANT RANGE       {d['slant_ft']:,}'")
    if "min_release_ft" in d:
        L.append(f" MIN RELEASE / DIRECT B/U {d['min_release_ft']:,}'")
    if "last_bomb_ft" in d:
        L.append(f" LAST BOMB OFF            {d['last_bomb_ft']:,}' AGL")
    if "aod_ft" in d:
        L.append(f" AIM OFF DISTANCE         {d['aod_ft']:,}'")
    if "ipp_mils" in d:
        L.append(f" IPP                      {d['ipp_mils']} mils")
    L.append(f" INTERVALOMETER           {d['interval_s']}")
    L.append(f" PATTERN LENGTH           {d['pattern_ft']:,}'")
    if "release_advance" in d:
        L.append(f" RELEASE ADVANCE          {d['release_advance']}")
    L += ["",
          " POP UP DATA (ALTITUDES ARE AGL)",
          f"   APEX                   {d['apex_ft']:,}'",
          f"   PULL UP POINT          {d['pup_ft']:,}'",
          f"   CLIMB ANGLE            {d['climb_deg']}°",
          f"   PULL DOWN POINT        {d['pdp_ft']:,}'",
          f"   MAP                    {d['map_ft']:,}'"]
    if "drag_coeff" in d:
        L += ["", DT_PULLOUT]
    L += ["",
          "IN THE JET: the DCS F-4E's bombing calculator asks the WSO for "
          "run-in speed, run-in altitude, IP-to-target distance, target "
          "altitude, dive angle and release interval, and returns the drag "
          "coefficient, release range, release advance and manual sight "
          "depression. Those are the rows above. Fill the squadron's sheet, "
          "then dial the same numbers in."]
    return L


def ingress_lines() -> list:
    return ["== ASSUMPTIONS (Conventional Tactics, Section I) ==",
            f" INGRESS   {INGRESS['tas_kt']} TAS · turn radius "
            f"{INGRESS['turn_radius_ft']:,}' · {INGRESS['deg_per_sec']}°/sec · "
            f"{INGRESS['g']} G",
            f" DELIVERY  {DELIVERY_TURN['tas_kt']} TAS · turn radius "
            f"{DELIVERY_TURN['turn_radius_ft']:,}' · radial G "
            f"{DELIVERY_TURN['radial_g'][0]}-{DELIVERY_TURN['radial_g'][1]}",
            f" EGRESS    {EGRESS['tas_kt']} TAS · turn radius "
            f"{EGRESS['turn_radius_ft']:,}' · {EGRESS['deg_per_sec']}°/sec · "
            f"{EGRESS['g']} G",
            "",
            f"Tracking time on final is {TRACKING_S} seconds for all "
            f"deliveries; {TRACKING_S_DIRECT} seconds for 30° and 15° direct.",
            "",
            "TAS AND KIAS ARE NOT THE SAME NUMBER. The sheet ingresses at "
            f"{INGRESS['tas_kt']} TRUE and releases at 500 INDICATED. At a "
            "thousand feet those are about 532 KIAS and 500 KIAS — you "
            "decelerate slightly into the release, which is what the sheet "
            "describes."]


# --------------------------------------------------------------------------- #
# 13b. The paint — which we cannot apply, and therefore say
# --------------------------------------------------------------------------- #
# SEA camouflage, Federal Standard numbers. Cited: the scheme was in use on
# USAF F-4s into the 1980s; Europe One reached the F-4 with the 1985 revision
# of T.O. 1-1-4 and Hill Gray was approved for the type in November 1985, so
# both are years too late for this squadron in January 1980.
LIVERY = {
    "scheme": "Southeast Asia (SEA) camouflage",
    "colors": [("FS 34079", "Dark Green"), ("FS 34102", "Medium Green"),
                ("FS 30219", "Sierra Tan"),
                ("FS 36622", "Camouflage Gray, undersides")],
    "band": "Blue and white checkered tail stripe. The 68th TFS wore red; the "
            "wing's third squadron in 1980 was the 339th, whose color is not "
            "in any source reached.",
    "code": "MY, shared by every fighter squadron at Moody.",
    "serial": "Small 'AF' plus the fiscal-year digits, large last three. The "
              "'0-' prefix for airframes over ten years old was dropped in "
              "1972.",
    "stencils": "White over the green areas, black over the tan; black on the "
                "undersides. Full density — the stencil reduction came with "
                "the 1983 T.O. update.",
    "airframes": ["68-0429 (photographed at Moody, 1980)",
                  "68-0369 (photographed 1980; crashed 10 Dec 1982)"],
    "unverified": ["Whether the undersides were gray or wraparound camouflage.",
                   "The checkerboard geometry — square count, band height, "
                   "whether it was outlined.",
                   "Whether any wing, TAC or squadron badge was carried on the "
                   "airframe."],
}


def livery_lines() -> list:
    """What your aircraft SHOULD look like, and the admission that it will not.

    There is no 70th TFS or 347th TFW livery for the DCS F-4E — not in the User
    Files catalog, not on the forums, not on GitHub. The engine will not write
    a livery id it has not seen on a real install (that guess produced blank
    aircraft once already), so this mission ships in whatever DCS picks.

    Saying so is the only honest option. A card that described the checkered
    tail while the jet wore somebody else's paint would be the say/do gap in
    the one place the pilot can actually SEE it.
    """
    L = ["== YOUR AIRCRAFT ==",
         f"F-4E Phantom II, tail code {TAILCODE}, {SQUADRON} — "
         f"{LIVERY['scheme']}."]
    for fs, name in LIVERY["colors"]:
        L.append(f"   {fs}   {name}")
    L += ["",
          f"TAIL BAND: {LIVERY['band']}",
          f"SERIAL: {LIVERY['serial']}",
          f"STENCILS: {LIVERY['stencils']}",
          "",
          "AIRFRAMES PHOTOGRAPHED IN 1980: " + "; ".join(LIVERY["airframes"]) + ".",
          "",
          "NOT ESTABLISHED, AND NOT INVENTED HERE:"]
    L += [f" - {x}" for x in LIVERY["unverified"]]
    L += ["",
          "AND THE PART YOU WILL NOTICE: DCS SHIPS NO 70 TFS LIVERY. There is "
          "no 347th TFW skin for the F-4E in the User Files catalog, on the "
          "forums, or on GitHub. This mission does not write one, because "
          "naming a livery folder that may not exist on your disk produces a "
          "blank airplane. You will fly this syllabus in whatever paint DCS "
          "picks. The description above is what it SHOULD look like, and the "
          "gap between the two is ours, not yours."]
    return L


# --------------------------------------------------------------------------- #
# 13c. What the jet actually carries
# --------------------------------------------------------------------------- #
# THE SHEET SAYS "6 x MK-82LD" AND THE JET CARRIED FOUR SPARROWS. `mission_kind`
# was never set on these cards, so every ride resolved to the air-to-air fit and
# the whole delivery syllabus flew with nothing to drop. Rob found it by flying
# it, which is the wrong way round.
#
# The fix is not "set mission_kind to strike" — that hands you a derived strike
# fit that may be anything. It is to hang EXACTLY WHAT THE PLANNING SHEET NAMES,
# station by station, so the card and the pylons cannot disagree.
#
# The F-4E's stores map onto the sheets almost exactly:
#   6 x MK-82LD  -> one MER on the centerline (station 7)
#   4 x MK-82HD  -> two TERs of two, inboard wing (stations 3 and 11)
MK82_LD_MER = "{HB_F4E_MK-82_6x}"            # 6x Mk-82 LD on a MER
MK82_HD_TER = "{HB_F4E_MK-82_Snakeye_2x}"    # 2x Mk-82 Snakeye on a TER
AIM7E2 = "{HB_F4E_AIM-7E-2}"                 # period Sparrow
AIM9J = "{AIM-9J}"                           # period Sidewinder

# Self-defense, carried on every ride. An unarmed Phantom over a defended
# target is not a training simplification, it is a different airplane.
AA_FIT = {5: AIM7E2, 6: AIM7E2, 8: AIM7E2, 9: AIM7E2, 2: AIM9J, 10: AIM9J}


def loadout_for(ride_key: str) -> dict:
    """{station: clsid} for a ride, or {} to leave the engine's own fit alone.

    Only the rides that DROP something get a hand-composed fit. The low-level
    and air-to-air rides keep whatever the engine composes, because their cards
    do not promise ordnance.
    """
    r = RIDES.get(ride_key) or {}
    keys = list(r.get("deliveries") or ())
    if r.get("delivery") and r["delivery"] not in keys:
        keys.insert(0, r["delivery"])
    if r.get("attack") and not keys:
        # An attack ride flies a delivery even though its card is about
        # geometry. The Double 90 exists FOR high drag; everything else on the
        # syllabus drops low drag.
        keys = ["hidrag10"] if ride_key.endswith("double90") else ["lald15"]
    if not keys:
        return {}
    fit = dict(AA_FIT)
    if any(DELIVERIES[k]["ordnance"].endswith("MK-82HD") for k in keys):
        fit[3] = MK82_HD_TER
        fit[11] = MK82_HD_TER
    else:
        fit[7] = MK82_LD_MER
    return fit


def loadout_lines(ride_key: str) -> list:
    """The stores block for the card, derived from the same dict the mission
    loads. One source, so the kneeboard cannot describe a fit the jet is not
    wearing."""
    fit = loadout_for(ride_key)
    if not fit:
        return []
    names = {MK82_LD_MER: "6x Mk-82 LD (MER)",
             MK82_HD_TER: "2x Mk-82 Snakeye HD (TER)",
             AIM7E2: "AIM-7E-2 Sparrow", AIM9J: "AIM-9J Sidewinder"}
    L = ["== STORES ==",
         "Composed from the delivery planning sheet, not from a generic strike "
         "fit. What is printed here is what is on the pylons."]
    for st in sorted(fit):
        L.append(f"   STATION {st:<3} {names.get(fit[st], fit[st])}")
    tot = sum(6 if fit[st] == MK82_LD_MER else 2 if fit[st] == MK82_HD_TER
              else 0 for st in fit)
    if tot:
        L.append("")
        L.append(f"   {tot} x Mk-82 total — the number on the sheet.")
    return L


# --------------------------------------------------------------------------- #
# 14. The rides
# --------------------------------------------------------------------------- #
# `n` is the position in the track. `doc` is the document the ride comes out of.
# `maps` is a whitelist where the ride cannot honestly be flown everywhere.
RIDES = {
    # ---- Track 1: Squadron Checkout -------------------------------------- #
    "wk_1_stepstart": {"n": 1, "track": "wk_checkout", "doc": "standards",
                       "title": "Step, Start, Taxi, Go"},
    "wk_2_overhead": {"n": 2, "track": "wk_checkout", "doc": "standards",
                      "title": "The Overhead and the Landing"},
    "wk_3_cqt": {"n": 3, "track": "wk_checkout", "doc": "standards",
                 "title": "Combat Quick Turn"},
    "wk_4_lineabreast": {"n": 4, "track": "wk_checkout", "doc": "lowlevel",
                         "title": "Line Abreast"},
    "wk_5_commout": {"n": 5, "track": "wk_checkout", "doc": "lowlevel",
                     "title": "Comm-Out Turns"},
    "wk_6_ridge": {"n": 6, "track": "wk_checkout", "doc": "lowlevel",
                   "title": "Ridge Crossing"},
    "wk_7_threats": {"n": 7, "track": "wk_checkout", "doc": "lowlevel",
                     "title": "Threats on the Route"},
    # The one ride that does not travel. Inadvertent IMC is the lesson, and
    # the weather that teaches it does not occur over the Western Desert.
    "wk_8_abort": {"n": 8, "track": "wk_checkout", "doc": "lowlevel",
                   "title": "Route Abort", "maps": ["germany"]},
    "wk_9_intercepts": {"n": 9, "track": "wk_checkout", "doc": "standards",
                        "title": "Basic Intercepts"},
    "wk_10_threeship": {"n": 10, "track": "wk_checkout", "doc": "standards",
                        "title": "Three-Ship Intercepts"},
    "wk_11_bfm": {"n": 11, "track": "wk_checkout", "doc": "wis1",
                  "title": "BFM Maneuvers on Command"},
    # ---- Track 2: Proud Phantom ------------------------------------------ #
    "pp_1_drag": {"n": 1, "track": "wk_proud_phantom", "doc": "standards",
                  "title": "The Tanker Drag", "maps": ["sinai"]},
    "pp_2_lald": {"n": 2, "track": "wk_proud_phantom", "doc": "tactics",
                  "title": "Low Angle Low Drag, 15 Degrees",
                  "delivery": "lald15", "maps": ["sinai"]},
    "pp_3_dive30": {"n": 3, "track": "wk_proud_phantom", "doc": "tactics",
                    "title": "Dive Bomb, 30 Degrees",
                    "delivery": "dive30", "maps": ["sinai"]},
    "pp_4_hidrag": {"n": 4, "track": "wk_proud_phantom", "doc": "tactics",
                    "title": "High Drag, 10 Degrees — and the Frag",
                    "delivery": "hidrag10", "maps": ["sinai"]},
    "pp_5_divetoss": {"n": 5, "track": "wk_proud_phantom", "doc": "tactics",
                      "title": "Dive Toss, and the Back-Up",
                      "delivery": "dt35", "deliveries": ("dt35", "dt20"),
                      "maps": ["sinai"]},
    "pp_6_echelon": {"n": 6, "track": "wk_proud_phantom", "doc": "tactics",
                     "title": "Echelon Attack", "attack": "echelon",
                     "maps": ["sinai"]},
    "pp_7_double90": {"n": 7, "track": "wk_proud_phantom", "doc": "tactics",
                      "title": "Double 90 Attack", "attack": "double90",
                      "delivery": "hidrag10", "maps": ["sinai"]},
    # THE COACHED RIDE COMES FIRST, AND THE CHECK RIDE KEEPS ITS NAME.
    # A syllabus teaches a thing and then tests it; shipping only the test was
    # the gap. The two rides fly the SAME attack — same document, same
    # geometry, same airplanes — and differ in exactly one respect: whether
    # anything talks to you while you fly it. Ride 9 is ride 8 with the
    # coaching switched off, which is the only honest way to find out whether
    # the coaching taught you anything.
    "pp_8_bnai_coach": {"n": 8, "track": "wk_proud_phantom", "doc": "tactics",
                        "title": "B'NAI Attack — Coached", "attack": "bnai",
                        "coach": True, "brief": True, "maps": ["sinai"]},
    "pp_8_bnai": {"n": 9, "track": "wk_proud_phantom", "doc": "tactics",
                  "title": "B'NAI Attack", "attack": "bnai", "maps": ["sinai"]},
    "pp_9_splithigh": {"n": 10, "track": "wk_proud_phantom", "doc": "tactics",
                       "title": "Split Attack, Low/High",
                       "attack": "split_lowhigh", "maps": ["sinai"]},
    # KEY SAYS 9, POSITION SAYS 10, AND THAT IS DELIBERATE. This card shipped
    # in v1.76.0 as `pp_9_split`, so the key is now in share links and in
    # somebody's Library. Renaming it to match its new position would be
    # tidier and would break every one of those. Key stability wins; the
    # number a pilot sees comes from `n`, not from the key.
    "pp_9_split": {"n": 11, "track": "wk_proud_phantom", "doc": "tactics",
                   "title": "Split Attack, Low/Low", "attack": "split_lowlow",
                   "maps": ["sinai"]},
}

TRACK_OF = {k: v["track"] for k, v in RIDES.items()}


def rides_in(track_id: str) -> list:
    """[(n, key, ride)] in flying order. Raises on a duplicate position."""
    out = sorted(((v["n"], k, v) for k, v in RIDES.items()
                  if v["track"] == track_id), key=lambda t: t[0])
    ns = [n for n, _k, _v in out]
    if len(set(ns)) != len(ns):
        raise ValueError(f"{track_id}: two rides share a position: {ns}")
    return out


def maps_for(ride_key: str) -> list | None:
    """The map whitelist for a ride, or None when it travels anywhere."""
    return RIDES.get(ride_key, {}).get("maps")


# --------------------------------------------------------------------------- #
# 15. THE WINGMAN NOTE — said on every ride that has one, for one reason
# --------------------------------------------------------------------------- #
def has_counterpart(ride_key: str, map_key: str = "") -> bool:
    """Is there actually a second airplane in this mission?

    THE PROMISE AND THE AIRPLANE NOW COME FROM ONE FUNCTION. Twenty-one
    missions shipped with the note below on the card and a single aircraft in
    the file, because the note was written from a hand-kept list of ride keys
    and the flight was never built at all. A card may only promise him where
    `wk_route` will actually place him.
    """
    from . import wk_route
    return bool(wk_route.counterpart_legs(ride_key, map_key or "germany"))


WINGMAN_NOTE = [
    "== ABOUT YOUR WINGMAN ==",
    f"Your number two is IN YOUR FLIGHT, on your wing — {RADIO_CALLSIGN} 1-2 "
    f"({CALLSIGN} 1-2 in the Standards), under "
    "your radio menu, not a separate scripted airplane.",
    "",
    "This replaced three attempts at an independent second flight, each of "
    "which flew its own schedule and none of which could hold position on a "
    "human. DCS has exactly one mechanism that flies WITH you, and this is "
    "it: he taxis when you taxi, forms up after takeoff, and rejoins when "
    "you call it.",
    "",
    "WHAT THAT COSTS, said plainly: he will not fly the two-ship geometry by "
    "himself. The delayed pop, the ninety into you, the trail he holds — the "
    "printed numbers are YOURS to fly, and his attack comes when you send "
    "him (radio menu: Flight — Engage). What you get in exchange is an "
    "airplane that is actually there, every time you look left.",
]


def _title(ride_key: str, map_key: str) -> list:
    r = RIDES[ride_key]
    trk = "SQUADRON CHECKOUT" if r["track"] == "wk_checkout" else "PROUD PHANTOM"
    return header_lines(r["doc"]) + [
        f"== {trk} · RIDE {r['n']} — {r['title'].upper()} ==", ""]


# --------------------------------------------------------------------------- #
# 16. brief_lines — one card per ride, per map
# --------------------------------------------------------------------------- #
def brief_lines(ride_key: str, map_key: str = "", aircraft_id: str = "") -> list:
    """The kneeboard card for one ride.

    Generated rather than stored, because the same ride tells a different truth
    in a different theatre — the low-level floor above all. A stored card would
    have to pick one theatre and be wrong in the other.
    """
    if ride_key not in RIDES:
        return []
    L = _title(ride_key, map_key) + staging_note(map_key)
    L += _BODY[ride_key](map_key)
    if has_counterpart(ride_key, map_key):
        L += [""] + WINGMAN_NOTE
    _st = loadout_lines(ride_key)
    if _st:
        L += [""] + _st
    L += [""] + livery_lines()
    L += ["", "== WHAT THIS RIDE DOES NOT MEASURE ==",
          "Mission Editor triggers can see altitude, speed, position, time and "
          "whether something died. They cannot see your dive angle at release, "
          "your mil setting, whether you used dive toss or reverted to direct, "
          "or how far from the aimpoint the bombs actually fell. Nothing here "
          "claims otherwise."]
    return L


def _b_stepstart(map_key: str) -> list:
    ts = TACTICAL_SPLIT
    return comm_card_lines() + [
        "",
        "== THE SORTIE ==",
        f"Step {STEP_MIN} minutes prior to takeoff. Engines "
        f"{START_MIN_SMALL} minutes prior for a flight of three or fewer, "
        f"{START_MIN_FOUR} for a four-ship.",
        "",
        f" 1. Check in on CH 7 (BOBBY) at start engines time.",
        " 2. Lead sends the flight to ground (DIRT) and taxis to the arming "
        "area.",
        " 3. Before taxiing out of the arming area, lead gives the visual "
        "signal — a HEAD NOD — to lower canopies. At night they come down "
        "when the flight is sent to CH 3.",
        " 4. Tower (DONNA) for takeoff clearance.",
        " 5. After runway lineup and T/O clearance, lead sends the flight to "
        "CH 4 (GOOD BYE) and initiates a check-in.",
        "",
        "== THE TACTICAL SPLIT (Standards III.1.a) ==",
        f"Two-ship: at {ts['alt_ft']:,} feet MSL and {ts['ias_kt']} KIAS, BOTH "
        f"aircraft split {ts['split_deg']}° away from runway heading, roll out "
        f"and terminate afterburner. After {ts['hold_s'][0]} to "
        f"{ts['hold_s'][1]} seconds, both return to runway heading. Initiate "
        f"comm-out turns as required.",
        "",
        f"NO SYSTEMS CHECK BELOW {SYSTEMS_CHECK_FT:,} FEET AGL, and the "
        "document says why: to maximise mid-air collision avoidance lookout. "
        "Systems checks are initiated by lead.",
        "",
        "CHANGE OF LEAD: a wingman NEVER automatically assumes the lead of a "
        "flight. Lead always initiates a change with a prebriefed signal or "
        "over the radio, and the aircraft assuming the lead always "
        "acknowledges that he has it.",
        "",
        "== GRADED ==",
        " - The check-in on the right channel, in the right order.",
        f" - The split: {ts['alt_ft']:,}' MSL, {ts['ias_kt']} KIAS, "
        f"{ts['split_deg']}° off runway heading, burner out.",
        f" - Nothing checked below {SYSTEMS_CHECK_FT:,}' AGL.",
    ]


def _b_overhead(map_key: str) -> list:
    o = OVERHEAD
    return [
        "== RECOVERY (Standards, Section VI) ==",
        "The primary means of recovery is vectors to initial for tactical "
        "overheads.",
        "",
        f" Two ship   — {o['two_ship']}",
        f" Three ship — {o['three_ship']}",
        f" Four ship  — {o['four_ship']}",
        "",
        "NOTE, and this one is local knowledge rather than doctrine:",
        f"  {o['tower_note']}",
        "",
        "ALTERNATE — VFR straight-in drags. Go idle, speed brakes, configure "
        "and slow to approach speed, following lead's flight path:",
        "  #4 at 15 NM · #3 at 12 NM · #2 at 9 NM · #1 at 6 NM.",
        "",
        "== LANDING (Standards, Section VII) ==",
        f" Max fuel for landing will normally be {LANDING['max_fuel_lb']:,} lbs.",
        f" IF AIRSPEED ON ROLLOUT IS {LANDING['hook_kt']} KNOTS OR MORE AT THE "
        f"{LANDING['hook_marker_ft']:,}' MARKER and normal deceleration is not "
        f"felt — LOWER THE HOOK, then continue solving the problem. At "
        f"{LANDING['hook_kt']} knots it takes approximately "
        f"{LANDING['hook_rollout_ft']:,} feet to get the hook down.",
        "",
        f" Aux {AUX_GROUND} is monitored when leaving ground frequency.",
        " Report aircraft status (Code 1, 2 or 3), sortie time and mission "
        "effectiveness to the Command Post (RAYMOND 17) on CH 1.",
        "",
        "== GRADED ==",
        " - Pitch order and side of the field.",
        f" - Spacing on initial (about {o['tower_rule_ft']:,}', collapsed "
        f"before initial).",
        f" - Fuel at landing at or below {LANDING['max_fuel_lb']:,} lbs.",
    ]


def _b_cqt(map_key: str) -> list:
    return [
        "== COMBAT QUICK TURN (Standards, Section VIII) ==",
        f"The CQT is a procedure used to load your aircraft with "
        f"{CQT['loads']} within a specified time period — normally "
        f"{CQT['minutes']} MINUTES. As an aircrew you play a vital role in "
        f"insuring the success of this procedure by accomplishing your portion "
        f"of the CQT correctly.",
        "",
        "THIS RIDE IS A STOPWATCH, NOT A SORTIE.",
        "",
        " 1. Land. Complete normal aircraft de-arm.",
        " 2. While taxiing back, accomplish the quick turn checklist. The "
        "right engine is not shut down, so a right spoiler check cannot be "
        "accomplished.",
        f" 3. Proceed to the CQT area, {CQT['area']}.",
        " 4. Follow the marshalling of the turnaround supervisor. Expect a "
        "cursory aircraft inspection before entering the CQT area.",
        f" 5. THE CLOCK STARTS at {CQT['clock_starts']}.",
        " 6. Follow the turnaround supervisor's voice instructions while the "
        "gun is being reloaded.",
        " 7. After engine shutdown, REMAIN IN THE COCKPIT. You are the brake "
        "rider while the aircraft is backed into the simulated revetment.",
        " 8. WSO: after a TER is completely loaded with bombs, begin the "
        "weapons preflight per the -34 checklist.",
        " 9. PILOT: begin the preflight inspection as soon as refuelling is "
        "complete.",
        f"10. When both are satisfied, the pilot makes the 781A entry "
        f"accepting the aircraft. THE CLOCK STOPS.",
        "",
        "FROM THE CHOCKS instead of from a flight: contact RAYMOND 17 prior to "
        "engine start — \"Aircraft 423, cranking one for Combat Quick Turn\" — "
        "then ground for permission to start and taxi to the CQT area.",
        "",
        "== SURGE ROE (Standards, Section IX), which is why this exists ==",
        " - Maximize realistic training. Don't get into a rut.",
        " - Brief 2½ hours prior to takeoff time. Step early.",
        " - Brief a max of 2 ranges plus 1 alternate mission. Be prepared.",
        " - Minimize turn times. Don't wait for a STEP call.",
        " - MAKE YOUR LANDING TIMES — the range you save may be your own.",
        " - De-arm even if no bombs were carried, to bring the pins back.",
        " - Stay flexible.",
        "",
        "== GRADED ==",
        f" - The {CQT['minutes']}-minute clock, start to stop.",
        " - Status call to CASINO OPS approximately 50 NM out.",
    ]


def _b_lineabreast(map_key: str) -> list:
    f = floor_ft(map_key)
    return contract_lines(map_key) + [
        "",
        "== CREW RESPONSIBILITIES (Low Level, Section II) ==",
        "AIRCRAFT COMMANDER:",
        " - AVOID THE ROCKS. That is the primary task and everything else is "
        "subordinate to it.",
        " - Visual lookout for hazards from 10 o'clock to 2 o'clock. Hazards "
        "are rocks, trees, towers, birds, light airplanes, guns, SAMs and MIGs "
        "— note the number of peacetime hazards.",
        " - Navigation. Extensive route and target study is required.",
        " - Advise the WSO whenever you come into the cockpit, and whenever "
        "visual is gained or lost in a turn.",
        " - Don't exceed the comfort level of anyone in the flight.",
        "",
        "WEAPON SYSTEM OFFICER:",
        f" - Visual lookout to the inside of the formation, from 3 o'clock to "
        f"as far back as you can see. At {LINE_ABREAST_NM[0]}-"
        f"{LINE_ABREAST_NM[1]} nm line abreast, the pit should be able to "
        f"check back 14 nm.",
        " - Talk. Use the UHF for all directive commentary concerning threats, "
        "even if you are only talking to your AC. Keep cockpit comm to a "
        "minimum — don't comm jam yourself.",
        " - Back up the navigation. Monitor RHAW audio. ECM pod and ALE-40 set "
        "up for optimum use.",
        " - #2's WSO KEEPS THE AIRCRAFT IN FORMATION. You are the only one in "
        "your airplane who should be looking at lead.",
        " - Do not let your AC become distracted from his primary task of "
        "avoiding the rocks.",
        "",
        "== THE RIDE ==",
        f"Line abreast, {LINE_ABREAST_NM[0]}-{LINE_ABREAST_NM[1]} nm, at or "
        f"above {f}' AGL, at or above {MIN_IAS_KT} KIAS. Straight legs and "
        f"gentle heading changes. You are learning to hold a position with the "
        f"radio quiet, and nothing else.",
        "",
        "== GRADED ==",
        f" - Never below {f}' AGL (Contract 9 and the theatre floor).",
        " - Never lower than lead (Contract 8).",
        f" - Never more than {WITHIN_DEG}° off lead's heading (Contract 12).",
        f" - At or above {MIN_IAS_KT} KIAS (Contract 7).",
        f" - KNOCK-IT-OFF is armed. Any flight member may call it; everyone "
        f"acknowledges with callsign, rolls wings level and climbs above "
        f"{KIO_CLIMB_FT}'.",
    ]


def _b_commout(map_key: str) -> list:
    L = ["== COMM-OUT TURNS (Low Level, Section III) ==",
         "The point of this ride is that the radio stays quiet. Lead turns; "
         "you read it off his wing; your pit calls it. Nobody transmits.",
         "",
         "THREE DISTINCT STAGES:",
         " ROLL IN — when the turn is signalled or called, check for a visual "
         "reference 90° to the flight path. This precludes the distraction of "
         "checking the HSI, and the reference can be used for any delayed or "
         "in-place turn. A rapid, UNLOADED roll to a bank angle which allows "
         "the nose to track a straight line along the horizon.",
         " ESTABLISHING — focus your eyes on the ground at the 10 or 2 o'clock "
         "position depending on the direction of turn, so peripheral vision "
         "includes the nose at one extreme and the terrain being turned into "
         "at the other. Corrections by BANK ANGLE. Rudder is not recommended "
         "once the turn is established — your inputs will disturb your "
         "interpretation of nose position.",
         " ROLL OUT — a final check of nose position. Still good or slightly "
         "rising, roll unloaded to wings level. Slightly below the level "
         "reference, roll out with a slight back stick pressure to break the "
         "descent. Eyes shift directly over the nose.",
         "",
         "COMMON ERROR:",
         f" {TURN_ERROR}",
         ""]
    for key in ("away90", "into90", "away_lt90", "into_lt90"):
        L += [COMM_OUT_TURNS[key], ""]
    L += [COMM_OUT_TURNS["180"], "",
          f"COMM-OUT TURN PARAMETERS — mil power and 12-14 units:"]
    for kcas, units, g in COMM_OUT_TURN:
        L.append(f"   {kcas} KCAS / {units} units / {g:.2f} G")
    L += ["", "== GRADED ==",
          " - Line abreast restored within the briefed spacing after each turn.",
          " - No climb through the roll-in (the common error, above).",
          f" - Floor and speed as ride 4: {floor_ft(map_key)}' AGL, "
          f"{MIN_IAS_KT} KIAS."]
    return L + [""] + wso_call_lines()


def _b_ridge(map_key: str) -> list:
    return [
        "== TERRAIN FLYING: RIDGE CROSSING (Low Level, Section V) ==",
        "",
        f"APPROACH — {RIDGE['approach']} This is the most important phase.",
        "",
        "Once you top the crest you have two options to get back into the low "
        "altitude regime on the other side:",
        "",
        f" BUNT — {RIDGE['bunt']}",
        f" ROLLOVER — {RIDGE['rollover']}",
        "",
        f"RULE OF THUMB: {RIDGE['rule']}",
        "",
        f"CAUTION: {RIDGE['caution']}",
        "",
        "== WHY IT IS FLOWN THIS WAY ==",
        "Cresting level is what masks you. Cresting nose-high paints your "
        "planform against the sky on the far side, and cresting nose-low puts "
        "you into the back slope with the nose already going down — which is "
        "the accident the caution above is describing.",
        "",
        "== GRADED ==",
        " - Crest altitude: level flight path over the top, not a climb "
        "through it.",
        f" - Recovery to the block on the far side without descending below "
        f"{floor_ft(map_key)}' AGL.",
        " - Formation integrity through the crossing.",
    ]


def _b_threats(map_key: str) -> list:
    t = THREATS
    L = ["== THREAT CONSIDERATIONS (Low Level, Section VI) ==",
         "",
         "AIR TO GROUND — HOW TO AVOID:"]
    L += [f" - {x}" for x in t["avoid_ag"]]
    L += ["", "IF ENGAGED (THREAT RADAR):"] + [f" - {x}" for x in t["radar"]]
    L += ["", "IF ENGAGED (MISSILE):"] + [f" - {x}" for x in t["missile"]]
    L += ["", "AIR TO AIR — IF ENGAGED:"] + [f" - {x}" for x in t["air"]]
    L += ["",
          "If the threat is stagnated or starts to fall back, continue low "
          "level to the target but monitor his position as necessary.",
          "If the threat is within weapon's parameters — essentially the gun, "
          "he must be in close:",
          "  ENGAGED FIGHTER — deny a gun or missile shot. \"S\" turn, remain "
          "as low as possible, BREAK TURN.",
          "  FREE FIGHTER — roll slide attack on the bandit.",
          "",
          "REMEMBER:"] + [f" - {x}" for x in t["remember"]]
    L += ["",
          "== HOW YOU TALK ABOUT IT (Low Level, Section IV) ==",
          "Radio calls should be DIRECTIVE, followed immediately by "
          "DESCRIPTIVE commentary. The directive part buys the maneuver; the "
          "descriptive part buys the next decision.",
          "",
          "  \"REX 2 BREAK RIGHT / SA-7 RIGHT 5 O'CLOCK\"",
          "",
          " \"Push it up\"       Select AB, spread the formation, check six.",
          " \"Spread\"           Check a few degrees away to commit a bandit "
          "or gain turning room.",
          " \"Knock it off\"     Discontinue maneuvering, climb above 500' "
          "AGL and investigate.",
          " \"Cease Maneuvering\" Simulated attack over. The flight returns to "
          "the planned low level route.",
          "",
          "== GRADED ==",
          " - Reaction to a launch: beam, chaff, maneuver.",
          " - Formation still together at the far end of the route.",
          f" - Floor and speed hold through all of it: "
          f"{floor_ft(map_key)}' AGL, {MIN_IAS_KT} KIAS."]
    return L


def _b_abort(map_key: str) -> list:
    lo, mid, hi = ROUTE_ABORT["mea_example"]
    return [
        "== ROUTE ABORT (Low Level, Section IX) ==",
        "",
        "THIS RIDE IS DESIGNED TO GO WRONG. The weather closes in front of "
        "you and the sortie ends. Getting that right is a skill, and it is the "
        "one the squadron put a whole section into.",
        "",
        "PRIMARY CONSIDERATIONS, IN THIS ORDER:",
        f" 1. {ROUTE_ABORT['primary'][0]}",
        f" 2. {ROUTE_ABORT['primary'][1]}",
        "",
        "VFR LOW LEVEL ROUTE ABORT — for emergencies, contingencies, or unable "
        f"to maintain VMC: slow to {ROUTE_ABORT['vfr_kt']} KIAS, maintain VMC "
        "and climb to a safe altitude. Contact the appropriate ATC facility if "
        "an IFR clearance is required.",
        "",
        "INADVERTENT ENTRY INTO IMC: climb to the briefed IMC route abort "
        f"altitude, slow to {ROUTE_ABORT['vfr_kt']} KIAS, contact ATC as soon "
        "as possible and obtain an IFR clearance.",
        "",
        f"COMPUTE THE ABORT ALTITUDE BEFORE YOU GO: {ROUTE_ABORT['mea_rule']}",
        f"  The squadron's own worked example: highest obstacle {lo}' MSL; "
        f"{lo}' + 1,000' = {mid}'; round up to {hi:,}' MSL.",
        "",
        "LOST WINGMAN from tactical formation: ensure altitude separation and "
        f"ground clearance. The flight leader complies with the above; the "
        f"wingman climbs to {ROUTE_ABORT['lost_wingman_ft']:,}' ABOVE the "
        "briefed route abort altitude and obtains a separate IFR clearance.",
        "",
        "== WHY THIS RIDE IS GERMANY ONLY ==",
        "Because the weather that teaches it happens here. Central European "
        "IMC is the reason this procedure exists, and building the same card "
        "over a desert would be a brief promising a problem the mission does "
        "not contain.",
        "",
        "== GRADED ==",
        f" - Slowed to {ROUTE_ABORT['vfr_kt']} KIAS.",
        " - Reached the briefed abort altitude — which you computed, and which "
        "is on this card because you put it there.",
        " - Lateral separation from lead maintained through the climb.",
    ]


def _b_intercepts(map_key: str) -> list:
    i = INTERCEPT
    L = ["== BASIC INTERCEPTS (Standards, Section V) ==",
         "The following are possible setups and are not all inclusive.",
         "",
         f"ALL TURNS ARE {i['bank_deg']}° OF BANK.",
         f"During setups, maintain {i['setup_kt']} KIAS.",
         f"During the attack, the TARGET maintains {i['target_kt']} KIAS and "
         f"the FIGHTER maintains {i['fighter_kt']} KIAS.",
         ""]
    for name in ("180", "135", "90"):
        L += [f" {name}° SETUP", f"   {INTERCEPT_SETUPS[name]}",
              f"   Outbound for {i['outbound_min']} minutes. Maintain "
              f"{i['alt_split_ft']:,}' altitude separation until visual. "
              f"Accomplish a straight through or ID pass.", ""]
    L += ["THE ALTITUDE SPLIT IS THE SAFETY CASE. Two aircraft converging "
          f"head-on at a combined {i['target_kt'] + i['fighter_kt']} knots have "
          f"very little time to solve a problem, and {i['alt_split_ft']:,} feet "
          "is what buys it. It comes off when — and only when — you are "
          "visual.",
          "",
          "== GRADED ==",
          f" - Outbound timing: {i['outbound_min']} minutes.",
          f" - Altitude separation held at {i['alt_split_ft']:,}' until visual.",
          f" - Speed discipline: {i['setup_kt']} on the setup, "
          f"{i['fighter_kt']} in the attack.",
          f" - Bank angle {i['bank_deg']}° on the turns."]
    return L


def _b_threeship(map_key: str) -> list:
    i = INTERCEPT
    lo, hi = i["three_ship_trail_nm"]
    return [
        "== THREE-SHIP INTERCEPTS (Standards, Section V) ==",
        "Three-ship intercepts will be accomplished with two aircraft "
        "attacking and one aircraft as a target.",
        "",
        "From fingertip or route formation at a known point (a radial and "
        "DME), #1 and #2 turn 90° left or right; #3 turns 90° in the opposite "
        f"direction. Proceed outbound for {i['outbound_min']} minutes — or "
        "until flight lead directs — then complete a 180° turn leading back to "
        f"the starting point, with #2 going in trail by {lo}-{hi} miles. #2 "
        f"delays his turn approximately {i['three_ship_delay_s']} seconds.",
        "",
        f"EACH AIRCRAFT MAINTAINS A PREBRIEFED HARD ALTITUDE — "
        f"{i['alt_split_ft']:,}' MINIMUM SPACING — THROUGHOUT THE MISSION, "
        f"REGARDLESS OF THE ROLE BEING PLAYED. That sentence is the whole "
        "safety case for putting three airplanes in the same piece of sky, "
        "and it is why the block does not move when the roles rotate.",
        "",
        "#1 accomplishes a straight-through while #2 completes a stern "
        "conversion. Then switch roles: #1 becomes the target, #2 and #3 are "
        "the attackers. Continue switching so each aircraft gets an "
        "opportunity to be the target, accomplish a straight-through, and do a "
        "stern conversion.",
        "",
        "All aircraft should be co-speed; the target is non-maneuvering. The "
        "last set-up can be run with both attackers doing a stern, thereby "
        "preparing for the rejoin.",
        "",
        "FOUR SHIP: split into two-ships and obtain two separate areas.",
        "",
        "== GRADED ==",
        f" - Your hard altitude block, held in every role.",
        f" - Trail spacing {lo}-{hi} nm at the turn.",
        f" - The {i['three_ship_delay_s']}-second delay.",
    ]


def _b_bfm(map_key: str) -> list:
    return bfm_call_lines() + [
        "",
        "== HOW THIS RIDE WORKS ==",
        "The calls above are made TO YOU as the fight develops. Your job is "
        "the document's own standard: quickness and accuracy of execution, and "
        "general aircraft control and situation awareness in response to the "
        "call.",
        "",
        "This is a crew-coordination document before it is a BFM document. In "
        "a Phantom the man who can see the bandit is often not the man flying "
        "the airplane, and the whole vocabulary exists so that the seeing and "
        "the flying can be done by two different people at six G.",
        "",
        "== GRADED ==",
        " - Response time to a directive call.",
        " - Correct direction.",
        " - The floor. This is over water with a hard deck, and the deck is "
        "not negotiable.",
        "",
        "AND ONE LINE FROM THE SHEET THAT IS WORTH THE WHOLE RIDE:",
        "  \"No tally, no visual, I'm engaged — hack your clock; in ten to "
        "thirty seconds you'll be dead.\"",
    ]


def _b_drag(map_key: str) -> list:
    t = TANKER_RV
    lo1, hi1 = t["tacan_unusable"][0]
    lo2, hi2 = t["tacan_unusable"][1]
    lo3, hi3 = t["tacan_unusable"][2]
    return [
        "== TANKER RENDEZVOUS PROCEDURES (Standards, Section IV) ==",
        "",
        "All aircrew members must be thoroughly prepared for any AAR mission "
        "PRIOR to the briefing.",
        "",
        "THE RENDEZVOUS IS THE LEAD GIB'S JOB. It is also the responsibility "
        "of the wingmen to monitor the rendezvous and be prepared to run it in "
        "the event that lead is Bent Gadget, aborts, and so on. The tanker "
        "must be advised that the fighters will run the rendezvous and that he "
        "should not initiate his turn until directed by the fighters.",
        "",
        "AIR-TO-AIR TACAN:",
        f" - Establish compatible channels with the tanker — "
        f"{t['tacan_offset']} DIGITS APART. Use an AA X or Y channel between 1 "
        f"and 126. Max A/A range is {t['tacan_range_nm']} NM.",
        f" - CHANNELS {lo1}-{hi1}, {lo2}-{hi2} AND {lo3}-{hi3} ARE NOT USABLE.",
        f" - After lock-on the tanker will require a {t['holddown_s']}-SECOND "
        f"HOLD-DOWN for ADF confirmation.",
        "",
        "CALL PRECEDENCE — any member of the flight may call information on "
        "the tanker's position, in this order (a TACAN call implies Flash or "
        "Beacon is no longer needed). Other flight members DO NOT REPEAT a "
        "call already made:",
        f"   {' -> '.join(t['call_precedence'])}",
        "   \"2's BEACON on the nose for 40 miles.\"",
        "   \"3's got a Flash 20° left for 30 miles.\"",
        "   \"4's TACAN — 38 miles.\"",
        "   \"Lead's got a contact 20° left for 26 miles.\"",
        "",
        f"If lead fails to obtain a contact prior to {t['contact_by_nm']} NM "
        "range, he will normally designate the aircraft with the most reliable "
        "information to direct the rendezvous.",
        "",
        "ALTITUDE BLOCK: flight leads should anticipate being cleared for "
        f"{t['block_levels']} consecutive flight levels — a {t['block_ft']:,}' "
        "block, e.g. 190, 200, 210, 220. IF THE CLEARANCE DOES NOT INCLUDE THE "
        f"FOURTH LEVEL, ASK FOR IT. The mission may be continued using "
        f"{t['fallback_levels']} flight levels — a {t['fallback_ft']:,}' block.",
        "",
        "REFUELLING:",
        " - Wingmen are cleared to the observation position when lead opens "
        "his IFR door or when cleared verbally.",
        " - OBSERVATION POSITION is no further aft than a line through the "
        "tanker's wingtips, stacked level with the top of the tanker's "
        "vertical stabilizer. Move forward to a position line abreast with the "
        "tanker's in-board engine when an aircraft is moving off the boom to "
        "your side.",
        f" - REFUELLING ORDER IS {', '.join(str(x) for x in t['order'])}, "
        "unless otherwise briefed.",
        " - Min comm procedures may be requested. The only thing you have to "
        "know is your offload.",
        " - On completion the flight backs off and down for the rejoin.",
        "",
        "Lead acknowledges the boomer's radio check with call sign and \"loud "
        "and clear\". Each succeeding flight member acknowledges with call "
        "sign only: \"REX 1, loud and clear\"... 2, 3, 4.",
        "",
        "== WHY THIS IS RIDE ONE ==",
        "Because the squadron got to Egypt somehow, and this is how. Twelve "
        "F-4Es went to Cairo West in the summer of 1980 and none of them got "
        "there without a tanker.",
        "",
        "== GRADED ==",
        " - Position discipline at the observation position.",
        " - Closure to the pre-contact position.",
        " - Nothing about the plug itself: DCS triggers cannot see a "
        "refuelling event or read your fuel state. This card does not pretend "
        "otherwise.",
    ]


def _b_delivery_ride(delivery_key: str, extra: list = ()) -> list:
    return delivery_lines(delivery_key) + list(extra)


def _b_lald(map_key: str) -> list:
    return _b_delivery_ride("lald15", [
        "",
        "== WHY THIS ONE FIRST ==",
        "Shallowest delivery, lowest workload — and it is the squadron's own "
        "direct back-up for the 20° dive toss, so you need it again in ride 5.",
        "",
        "== GRADED ==",
        " - Release altitude 2,000'.",
        " - Release airspeed 500 KIAS.",
        " - LAST BOMB OFF at 1,886' AGL. Go below it and the ride is failed, "
        "because that number is the frag envelope and it is not advisory.",
    ])


def _b_dive30(map_key: str) -> list:
    return _b_delivery_ride("dive30", [
        "",
        "== WHAT IS NEW ==",
        "A real pop. Twice the apex of ride 2 and a 45° climb angle, and the "
        "wind correction factors appear for the first time — 1.07 mil per knot "
        "of head or tail, 12 feet per knot of crosswind.",
        "",
        "== GRADED ==",
        " - Apex within band, release altitude 4,000' AGL, 500 KIAS.",
        " - Last bomb off at or above 3,781' AGL.",
    ])


def _b_hidrag(map_key: str) -> list:
    return _b_delivery_ride("hidrag10", [
        "",
        "== THE POINT OF THIS RIDE IS FRAG ==",
        "You are pickling at a THOUSAND FEET and your own weapons are now the "
        "threat. Last bomb off is 954' AGL. Everything in the four attacks you "
        "fly next — the delays, the angles off, the 10,000' of target "
        "separation — exists because of the number on this card.",
        "",
        "Flown under a low ceiling, because that is the condition the Double "
        "90 was designed for, and the Double 90 is ride 7.",
        "",
        "== GRADED ==",
        " - Release altitude 1,000' AGL, 500 KIAS.",
        " - A FRAG PROXY: were you still inside the frag radius when your own "
        "weapons functioned. Honest label — DCS triggers cannot model a frag "
        "pattern. This is a distance-and-time approximation and nothing more.",
    ])


def _b_divetoss(map_key: str) -> list:
    # Read the sheet list off the ride rather than naming it twice. A pair
    # hard-coded here and declared there is two sources of truth for the same
    # fact, and one of them drifts.
    keys = RIDES["pp_5_divetoss"]["deliveries"]
    L = []
    for i, k in enumerate(keys):
        L += (["", ""] if i else []) + delivery_lines(k)
    return L + [
        "",
        "== THE DRILL (Conventional Tactics, Section I) ==",
        DT_DRILL,
        "",
        "The sequence, said plainly: the 35° dive toss backs up to the 30° "
        "direct, and the 20° dive toss backs up to the 15° low angle low drag. "
        "You planned one; you may fly the other; the decision point is the aim "
        "off distance and you do not get to think about it there.",
        "",
        "IN THE JET: 1.04 and 1.03 are the DRAG COEFFICIENTS your WSO puts "
        "into the WRCS. They are not trivia on a sheet — they are a value "
        "somebody dials in.",
        "",
        "== THE RIDE ==",
        "Two good dive toss passes and one deliberately failed one, so that "
        "the first time the computer lets you down is not over a defended "
        "target.",
        "",
        "== GRADED ==",
        " - DT release altitude.",
        " - The revert branch: were you at the direct delivery release "
        "altitude by the aim off distance.",
        " - What is NOT graded: whether you actually used dive toss. Triggers "
        "cannot see the mode. The altitude and the timing are what prove it.",
    ]


def _b_attack_ride(attack_key: str, extra: list = ()) -> list:
    return attack_brief(attack_key) + list(extra)


def _b_echelon(map_key: str) -> list:
    a = ATTACKS["echelon"]
    return _b_attack_ride("echelon", [
        "",
        "== WHY THIS ATTACK IS FIRST ==",
        "Not because the guide lists it first — it doesn't, the split is the "
        "primary. It is first because of the squadron's own advantage list: "
        "good visual cross-coverage and mutual support THROUGHOUT MOST OF THE "
        "ATTACK. You do not start a new wingman on the one whose disadvantages "
        "open with losing mutual support.",
        "",
        "== YOU ARE NUMBER TWO ==",
        "Which is the harder seat, and the one with the delay in it.",
        "",
        "== GRADED ==",
        f" - Your pop delayed at least {a['delay_s']} seconds after lead's.",
        " - Your recovery ABOVE lead's frag.",
        " - Rejoin to line abreast after lead jinks to the egress heading.",
        " - AND THE FAILURE THE DOCUMENT NAMES: if you do not delay long "
        "enough you will end up IN-TRAIL with lead. If that happens the card "
        "says so in those words.",
    ])


def _b_double90(map_key: str) -> list:
    a = ATTACKS["double90"]
    return _b_attack_ride("double90", [
        "",
        "== WEAPONS ==",
        "High drag — ride 4's numbers. 4 × MK-82HD, 10°, 1,000' AGL, 500 KIAS.",
        "",
        "== THE CLOCK ==",
        f"Hack it on LEAD'S BOMB DETONATION. That is the recommended procedure "
        f"in the document and it is your separation cue: {a['delay_s']} "
        f"seconds between his pop and yours.",
        "",
        "== GRADED ==",
        f" - The {a['delay_s']} seconds.",
        " - A FRAG PROXY: were you outside the envelope when lead's weapons "
        "functioned. Honest label — DCS triggers cannot model a frag pattern. "
        "This is a distance-and-time approximation and nothing more. The card "
        "says it here rather than pointing at ride 4, because a brief that "
        "cross-references its caveats is relying on you having read the other "
        "card.",
        f" - Mutual support held to {a['support_nm']} NM.",
    ])


def _b_bnai(map_key: str) -> list:
    a = ATTACKS["bnai"]
    lo, hi = a["trail_nm"]
    return _b_attack_ride("bnai", [
        "",
        "== WHERE YOU ARE FLYING THIS ==",
        "Read the definition again, then look at the map. The B'NAI was "
        "invented over this ground, in 1973, by the air force that had to "
        "solve the SA-6. Your squadron wrote it down in January 1980 and "
        "deployed here five months later.",
        "",
        "There is an SA-6 in this mission. That is not decoration — it is the "
        "reason the attack exists.",
        "",
        "== AND THE PART YOU SHOULD NOT SKIP ==",
        "From the squadron's own disadvantage list: the ingress ground track "
        "is the SAME for both of you, you spend extended time in the immediate "
        "target area, and THE DEFENSES ARE ALERTED FOR THE NUMBER TWO "
        "AIRCRAFT.",
        "",
        "You are number two.",
        "",
        "== GRADED ==",
        f" - In-trail spacing {lo}-{hi} NM at the IP.",
        " - Your altitude while covering lead's six — low, and staying low.",
        " - Coming off the target in the OPPOSITE direction from lead.",
    ])


def _b_bnai_coach(map_key: str) -> list:
    """The coached B'NAI. Same attack, same document, somebody in the pit.

    The card deliberately does NOT restate the geometry paragraph the check
    ride prints — that is the same text from the same section and printing it
    twice makes two places to fix it. It states what is different: the cues,
    the honest limit of what a Mission Editor condition can see, and the fact
    that you are expected to fly it more than once before you move on.
    """
    from . import wk_coach
    a = ATTACKS["bnai"]
    lo, hi = a["trail_nm"]
    d = DELIVERIES["lald15"]
    from . import wk_brief
    return _b_attack_ride("bnai", [
        "",
        "== THIS IS THE TEACHING RIDE ==",
        "Ride 9 is this same attack with nothing talking to you. Fly this one "
        "until the calls are telling you what you were already doing, then go "
        "and fly ride 9 and find out whether that was true.",
        "",
        "== THE POP, IN THE ORDER THE DRAWING GIVES IT ==",
        " - " + " -> ".join(a["pop_stages"]),
        f"Pull-up at {d['pup_ft']:,} ft from the target, climb "
        f"{a['climb_deg_lead']}° as lead, {a['climb_deg_two']}° as number "
        f"two. Roll-in {d['pdp_ft']:,} ft, apex {d['apex_ft']:,} ft, release "
        f"{d['release_ft']:,} ft at {d['angle']}° and {d['release_kt']} KIAS.",
        "",
        "ROLL-IN IS BELOW APEX AND THAT IS NOT A MISPRINT. You begin the "
        "pull-down at roll-in and the airplane coasts up to apex as the nose "
        "comes through — which is why the sheet puts them exactly "
        f"{a['climb_deg_lead']} x 50 = {a['climb_deg_lead'] * 50:,} ft apart.",
        "",
        "== ON THE DIAGRAM'S 4.5 NM ==",
        "The drawing carries a 4.5 NM annotation. It is NOT the pull-up "
        "distance — the guide's split-attack section uses the same figure for "
        "where mutual support ends — so the cue fires on the delivery sheet's "
        f"{d['pup_ft']:,} ft instead, which is the number tied to the release "
        "parameters printed above. Both numbers are the squadron's; only one "
        "of them is about the pop.",
        "",
        f"== IN-TRAIL {lo}-{hi} NM ==",
        "Approach the IP at nearly 90° angle off with lead on the side "
        "nearest the target. The flight plan flies that approach for you on "
        "this ride — TRAIL SET sits 8 NM off the run-in axis — so the cue and "
        "the route agree about where the turn happens.",
    ] + [""] + wk_brief.brief_lines() + wk_coach.brief_lines())


def _b_splithigh(map_key: str) -> list:
    a = ATTACKS["split_lowhigh"]
    lo, hi = a["converge_deg"]
    return _b_attack_ride("split_lowhigh", [
        "",
        "== THE PRIMARY ATTACK, AND THE LAST ONE YOU LEARN ==",
        "The guide lists the split FIRST, because it is the squadron's primary "
        "attack. This syllabus teaches it LAST, and the reason is in the "
        "guide's own disadvantage list: loss of some mutual support, and a "
        "potential flight path conflict over the target and on recovery. You "
        "do not hand those to a new wingman on his first two-ship attack.",
        "",
        "== YOU ARE NUMBER TWO ==",
        f"Mutual support to {a['support_nm']} NM. Lead turns 30° and pops "
        f"immediately for a low angle off delivery. YOU turn 45° and pop for an "
        f"ALMOST 90° ANGLE OFF delivery — a different axis, a different sight "
        f"picture, and higher release parameters than his.",
        "",
        f"The attack axes converge at {lo}-{hi}°. That is the 'low/high' part: "
        "you are not mirroring lead, you are attacking the same aimpoint from a "
        "steeper angle and from above his frag.",
        "",
        "== HOW YOU BUY THE SEPARATION ==",
        "Timing, plus horizontal AND vertical geometry. With close-in release "
        "ranges you establish time separation over the target by DELAYING YOUR "
        "ROLL-IN — which is also what gives you the extra angle off and the "
        "higher release parameters. One decision does three jobs.",
        "",
        "== GRADED ==",
        " - Your angle off at release: near 90°, not lead's 30°.",
        f" - Axis convergence inside the {lo}-{hi}° band.",
        " - Frag clearance from lead's weapons AND your own.",
        " - Mutual support held to the split point.",
    ])


def _b_split(map_key: str) -> list:
    a = ATTACKS["split_lowlow"]
    return _b_attack_ride("split_lowlow", [
        "",
        "== SAME SPLIT, DIFFERENT AIMPOINTS ==",
        "Ride 9 was the low/high: one aimpoint, two axes, you high and steep. "
        "This is the low/low — the SAME geometry with the exception of "
        "different aimpoints, and both of you low.",
        "",
        "== THE HARDEST RIDE IN THE COURSE, AND THE GUIDE IS BLUNT ABOUT WHY ==",
        f"Two separate aimpoints {a['aimpoint_sep_ft']:,}' apart. For the 180° "
        f"egress depicted in the guide, {a['target_sep_ft']:,}' of TARGET "
        "separation is required for frag clearance.",
        "",
        "You are converging nearly head-on with a friendly at 540 TAS while "
        "both of you are pulling off a target, and each of you has to clear "
        "not only your own frag but the other man's.",
        "",
        "== GRADED ==",
        f" - Your {a['delay_s']}-second delay at the split point.",
        " - DID YOU HIT YOUR AIMPOINT — not lead's.",
        " - Frag clearance from both deliveries.",
        " - Minimum separation from lead during the egress. This is the one "
        "the squadron listed as a disadvantage: potential flight path conflict "
        "over the target and on recovery.",
    ])


_BODY = {
    "wk_1_stepstart": _b_stepstart,
    "wk_2_overhead": _b_overhead,
    "wk_3_cqt": _b_cqt,
    "wk_4_lineabreast": _b_lineabreast,
    "wk_5_commout": _b_commout,
    "wk_6_ridge": _b_ridge,
    "wk_7_threats": _b_threats,
    "wk_8_abort": _b_abort,
    "wk_9_intercepts": _b_intercepts,
    "wk_10_threeship": _b_threeship,
    "wk_11_bfm": _b_bfm,
    "pp_1_drag": _b_drag,
    "pp_2_lald": _b_lald,
    "pp_3_dive30": _b_dive30,
    "pp_4_hidrag": _b_hidrag,
    "pp_5_divetoss": _b_divetoss,
    "pp_6_echelon": _b_echelon,
    "pp_7_double90": _b_double90,
    "pp_8_bnai_coach": _b_bnai_coach,
    "pp_8_bnai": _b_bnai,
    "pp_9_splithigh": _b_splithigh,
    "pp_9_split": _b_split,
}
