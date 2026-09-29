#!/usr/bin/env python3
"""Add the AAR Academy tracks to mission_templates.json.

Idempotent: re-running replaces the Academy cards and re-stamps the track
metadata on the five AAR cards that already shipped, without touching anything
else. Written as a script rather than a hand edit because the templates file is
50+ cards and a hand edit of that is how you lose one.

NUMBERING follows the Academy plan's own syllabus, 0 through 9, so a reader
working from the plan and a pilot working from the Library are looking at the
same ride numbers. Night (boom) and Off the Boat (probe) sit at 10 as extras
rather than being wedged into the sequence — they are variations on a skill the
track already taught, not new demands.

WHAT THIS DOES NOT DO: it does not change the `recipe` of any card that already
shipped. Track metadata is additive, so an existing share link still
regenerates the same bytes. The only edits to existing cards are `track`,
`aar_grade` and dropping `featured` — none of which reach the mission file.
"""
import json
from collections import OrderedDict
from pathlib import Path

P = Path(__file__).parent.parent / "missiongen" / "data" / "mission_templates.json"

BOOM = dict(aircraft="F_16C_50", tanker_type="kc135")
PROBE = dict(aircraft="FA_18C_hornet", tanker_type="kc135mprs")


def recipe(ac, **kw):
    r = {"start": "air", "bb_tanker": True, "bb_awacs": False, "bb_sams": False,
         "bb_ambient": False, "bb_targets": False, "threat_intensity": 1,
         "time_of_day": "day", "weather": "clear"}
    r.update(ac)
    r.update(kw)
    return r


# Every ride offers the eras its LANE can actually be flown in, with a
# per-era default airframe and tanker. Baked here rather than computed at
# request time because `eras` gates the engine, not just the UI — a card that
# advertises Cold War while its recipe pins an F-16C hands the builder an
# EraViolation, which is how a card looks broken. A test pins this against the
# live picker so the two cannot drift.
def lane_eras(track):
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    sys.path.insert(0, str(Path(__file__).parent.parent / "vendor"))
    from missiongen import tracks as _t
    return _t.picker(track)


# Per-era defaults: the era-correct airplane, not the lane's headline jet.
# An F-16C cannot be the Cold War default because it was not there.
ERA_DEFAULT = {
    ("aar_boom", "coldwar"): ("F_4E_45MC", "kc135"),
    ("aar_boom", "modern"): ("F_16C_50", "kc135"),
    ("aar_boom", "gwot"): ("F_16C_50", "kc135"),
    ("aar_probe", "coldwar"): ("F_14A_135_GR", "ka6d"),
    ("aar_probe", "modern"): ("FA_18C_hornet", "kc135mprs"),
    ("aar_probe", "gwot"): ("FA_18C_hornet", "kc135mprs"),
}


def era_block(track):
    """(eras, by_era, aircraft_choices) for a ride in this track."""
    tree = lane_eras(track)
    eras = [e for e in ("coldwar", "modern", "gwot") if e in tree]
    by_era, choices = OrderedDict(), OrderedDict()
    for e in eras:
        acq, tk = ERA_DEFAULT[(track, e)]
        if acq not in tree[e]:
            acq = sorted(tree[e])[0]
        if tk not in tree[e][acq]:
            tk = tree[e][acq][0]
        by_era[e] = {"aircraft": acq, "tanker_type": tk}
        choices[e] = sorted(tree[e])
    return eras, by_era, choices


def card(label, track, n, brief, premise, ac, grade=None,
         air_start="astern_tanker", tod="day", extra=None,
         default_map="caucasus", threat=1, gates=False):
    eras, by_era, choices = era_block(track)
    c = OrderedDict()
    c["label"] = label
    c["eras"] = eras
    c["quick"] = False
    if air_start:
        c["air_start"] = air_start
    c["recipe"] = recipe(ac, time_of_day=tod, **(extra or {}))
    c["by_era"] = by_era
    c["aircraft_choices"] = choices
    if grade:
        c["aar_grade"] = grade
    if gates:
        c["aar_gates"] = True
    c["track"] = {"id": track, "n": n}
    c["brief"] = brief
    c["library"] = {"role": "training", "premise": premise, "threat": threat,
                    "players": "SP"}
    c["default_map"] = default_map
    return c


# --------------------------------------------------------------------------- #
# Shared blocks. Where two lanes teach the SAME thing, they say the same words —
# a difference in wording between lanes reads as a difference in the standard.
# --------------------------------------------------------------------------- #
DRILL = [
    "THE THROTTLE DRILL, which is the actual content of this ride.",
    "From a safe in-trail position, repeat this cycle:",
    "  1. Close 20-30 feet.",
    "  2. STOP the closure without changing your vertical or lateral picture.",
    "  3. Drift aft 20-30 feet.",
    "  4. Stop the aft drift.",
    "  5. Return to the original sight picture.",
    "Three smooth cycles and you are ready for the next ride. Fewer than",
    "three and you are not — which is worth knowing now rather than at the",
    "boom.",
    "",
    "PULSE AND COUNTER-PULSE. Find the power setting that produces zero",
    "fore/aft drift; that is your BASELINE. Drifting aft: add a small pulse.",
    "Then — before the closure becomes obvious — take most of it back out.",
    "That second movement is the counter-pulse and it is the part people",
    "skip. Leaving the correction in is what carries you through zero and",
    "into the overshoot.",
    "",
    "The goal is not a motionless throttle. It is small, early corrections",
    "around a known baseline. One knot of mismatch is 1.7 feet per second,",
    "so a difference you cannot see becomes an aircraft length in ten.",
]

FADE_NOTE = [
    "GRADED. Silence means you are inside tolerance — the mission speaks only",
    "when something needs saying, and the closure call fires three times and",
    "then stops. Everything else is on the F10 menu when YOU want it.",
]


# --------------------------------------------------------------------------- #
# RIDE TITLES. Written to be descriptive rather than evocative: a pilot
# scanning a Library, a zip listing or a printed contents page should be able
# to tell what a ride TEACHES without opening it. "Fit Check" reads as an
# in-joke to anyone who has not read the syllabus; "Orientation and Control
# Check" does not need the syllabus to make sense.
#
# Spelling is British throughout ("refuelling"), matching every AAR card and
# kneeboard already shipped. Changing that is a product-wide decision, not one
# to make inside a title table.
#
# Format: "Air-to-Air Refuelling <n> (<Lane>) — <what it teaches>"
#   * The number keeps the flying order visible everywhere.
#   * The lane disambiguates two tracks that share ride numbers.
#   * The part after the em dash is what the Library rows, the printed
#     syllabus and the zip filenames all show, so it carries the meaning.
RIDE_NAMES = {
    ("boom", 0): "Orientation and Control Check",
    ("boom", 1): "Formation on the Tanker",
    ("boom", 2): "Closure Control to Pre-Contact",
    ("boom", 3): "First Contact on the Boom",
    ("boom", 4): "Sustained Contact and Fuel Transfer",
    ("boom", 5): "Disconnect Recovery and Reset",
    ("boom", 6): "Refuelling Through the Turn",
    ("boom", 7): "Rendezvous, Radio Flow and Join",
    ("boom", 8): "Qualification Check Ride",
    ("boom", 9): "Operational Transfer on a Live Sortie",
    ("boom", 10): "Night Refuelling (extra)",
    ("probe", 0): "Orientation and Control Check",
    ("probe", 1): "Formation on the Tanker",
    ("probe", 2): "Closure Control to the Basket",
    ("probe", 3): "First Contact with the Basket",
    ("probe", 4): "Sustained Contact and Hose Management",
    ("probe", 5): "Missed Approach Recovery and Reset",
    ("probe", 6): "Refuelling Through the Turn",
    ("probe", 7): "Rendezvous, Radio Flow and Join",
    ("probe", 8): "Qualification Check Ride",
    ("probe", 9): "Operational Transfer on a Live Sortie",
    ("probe", 10): "Carrier Organic Tanking (extra)",
}

LANE_WORD = {"boom": "Boom", "probe": "Probe"}


def title(track, n):
    lane = track[4:]
    return (f"Air-to-Air Refuelling {n} ({LANE_WORD[lane]}) "
            f"— {RIDE_NAMES[(lane, n)]}")


def fit_check(track, ac, lane_note):
    return card(
        title(track, 0), track, 0, [
            "== 0 · FIT CHECK ==",
            "NEW DEMAND: none. This is the diagnostic. Can you sit next to a",
            "large airplane and stay there, and do your controls do what you",
            "think they do.",
            "",
            "There is no plug in this ride and no reason to attempt one.",
            "",
            "FIRST, ON THE GROUND OR IN THE CRUISE: check your bindings. The",
            "refuelling door or probe, PTT, speedbrake, trim, and the",
            "disconnect control. Reaching for a control you have not bound",
            "while twenty feet from a tanker is how people hit tankers.",
            "",
            "TWENTY SECONDS TO SETTLE. Scoring does not begin the moment you",
            "spawn. If you are in VR, use that window: recentre sitting",
            "naturally with square shoulders, and set seat height so the",
            "tanker reference is visible without a crouch you cannot hold for",
            "ten minutes.",
            "",
        ] + DRILL + [
            "",
        ] + lane_note + [
            "",
            "THIS RIDE IS GRADED. You will be told when you have held position",
            "for fifteen seconds, and again at sixty. If you never hear the",
            "first call, this is exactly the ride you needed — fly it again",
            "rather than moving on. That is not a setback. It is the diagnostic",
            "doing its job.",
        ],
        "The diagnostic. Can you sit beside a tanker for a minute, and does your throttle do what you think? Three clean close-stop-aft-stop cycles and you may move on.",
        ac, grade="station")


def closure(track, ac, tail):
    return card(
        title(track, 2), track, 2, [
            "== 2 · THE CLOSURE ==",
            "NEW DEMAND: arriving slowly enough that stopping is a decision",
            "rather than a hope.",
            "",
            "You start pre-contact. Move forward to the contact position and",
            "STOP THERE without making contact. Back out. Do it again. Ten",
            "arrivals, zero plugs.",
            "",
            "TWO NUMBERS, because there are two phases and the card used to",
            "print only the first:",
            " - APPROACH, from pre-contact: 1 to 3 knots of overtake. Not 10.",
            " - THE LAST FEW FEET: about ONE FOOT PER SECOND. That is roughly",
            "   half a knot — THREE TIMES SLOWER than the approach. This is the",
            "   number people miss. The closure that gets you to the position",
            "   is not the closure that makes the connection.",
            "",
            "STABILISE AT PRE-CONTACT FIRST. Fifteen seconds, zero closure,",
            "before you move forward. That is the gate, and skipping it is the",
            "single most common way this ride goes wrong.",
            "",
            "CHANGE ONE TREND AT A TIME. If you are high or low, fix that",
            "before you add forward closure. Two problems solved at once is",
            "two problems solved badly.",
            "",
        ] + tail + [""] + FADE_NOTE,
        "Ten arrivals at the contact position, zero plugs. Two closure numbers — one for the approach, and one three times slower for the last few feet.",
        ac, grade="closure")


def flow(track, ac, tail):
    return card(
        title(track, 4), track, 4, [
            "== 4 · THE FLOW ==",
            "NEW DEMAND: staying there. Contact is a moment; this ride is about",
            "the minute after it.",
            "",
            "TARGET: 45 continuous seconds connected, then longer. Not a",
            "handful of one-second stabs — a connection you could have taken",
            "fuel through.",
            "",
            "WHAT CHANGES WHILE YOU ARE THERE. You are getting HEAVIER. The",
            "power setting that held you steady at the start will let you drift",
            "aft by the end, and the trim you set will slowly stop being right.",
            "A memorised throttle position is not a technique; the baseline",
            "moves and you have to move with it.",
            "",
        ] + tail + [
            "",
            "IF THE OSCILLATION IS GROWING, BACK OUT. Not as a failure — as the",
            "procedure. Fatigue and growing oscillation are the standard reason",
            "to disconnect, stabilize and rest, and doing that produces better",
            "refuelling in less time than pressing does. Pressing a bad",
            "connection has never once fixed it.",
            "",
        ] + FADE_NOTE,
        "Contact is a moment; this is the minute after it. Forty-five continuous seconds — and you are getting heavier the whole time, so the power that held you at the start will not hold you at the end.",
        ac, grade="contact")


def reset(track, ac, tail):
    return card(
        title(track, 5), track, 5, [
            "== 5 · RESET ==",
            "NEW DEMAND: getting it wrong ON PURPOSE, and recovering.",
            "",
            "Everything so far trained the good approach. This ride trains the",
            "bad one, because the bad one is what you will actually have.",
            "",
            "THE DRILL, ten times. Arrive deliberately fast. Arrive",
            "deliberately high. Let yourself get out of position — then FIX IT:",
            "back out to pre-contact, stabilize, come again.",
            "",
            "A RESET IS NOT A FAILED RUN. It is good airmanship and it is the",
            "skill that makes refuelling reliable rather than lucky. A pilot",
            "who has only practised the good approach has no trained response",
            "to a bad one, so their first bad approach becomes a bad sortie:",
            "they press, it gets worse, and they conclude they cannot refuel.",
            "",
            "There is no score for plugs today. You cannot practice a back-out",
            "without a mess to back out of.",
            "",
        ] + tail + [
            "",
            "GRADED on position — so expect to break the grade repeatedly.",
            "Today that IS the exercise, not a failure.",
        ],
        "Get it wrong on purpose, ten times, and recover each time. A reset is not a failed run — it is the skill that makes refuelling reliable rather than lucky.",
        ac, grade="contact")


def turn(track, ac, tail):
    return card(
        title(track, 6), track, 6, [
            "== 6 · THE TURN ==",
            "NEW DEMAND: staying in position while the tanker banks.",
            "",
            "The tanker flies a racetrack, so it turns at each end. That is not",
            "staged for you — it is simply what a tanker on a track does, and",
            "it is where a lot of otherwise-solid refuelling falls apart.",
            "",
            "WHAT CHANGES. Inside the turn you need less power and will slide",
            "forward. Outside you need more, and will fall back and get high.",
            "The sight picture rotates. Your chosen reference on the tanker",
            "does not — keep using it.",
            "",
            "WHAT DOES NOT CHANGE: everything else. Same tolerances, same two",
            "closure numbers, same one-input-then-wait.",
            "",
        ] + tail + [
            "",
            "THE DRILL. Get into position on a straight leg. Stay there through",
            "the turn. When you lose it — and you will, the first few times —",
            "back out, rejoin on the straight, wait for the next end.",
            "",
            "HONESTLY: we did not time the tanker's turn to meet you, and no",
            "countdown is called. You will wait for it. Waiting is part of",
            "tanking.",
            "",
        ] + FADE_NOTE,
        "Hold position through the tanker's turn. Inside you slide forward, outside you fall back and get high, and the sight picture rotates while your reference does not.",
        ac, grade="contact")


def rendezvous(track, ac, tail):
    return card(
        title(track, 7), track, 7, [
            "== 7 · THE RENDEZVOUS ==",
            "NEW DEMAND: everything that happens BEFORE the part you have been",
            "practising. Navigation, the radio flow, the join, observation,",
            "and only then pre-contact.",
            "",
            "READ THIS FIRST. Every ride until now deliberately deleted the",
            "commute — you started 1 nm astern, on speed, because thirty",
            "seconds of skill wrapped in half an hour of transit is not",
            "practice. This ride puts the commute back ON PURPOSE, once,",
            "because finding him and arriving already matched is its own skill",
            "and you cannot drill it by starting there.",
            "",
            "THE SEQUENCE, in order, and do not compress it:",
            "  TACAN and radio -> join -> OBSERVATION, line abreast and stepped",
            "  down -> stabilize -> pre-contact -> hold 15 s -> forward.",
            "",
            "MATCH HIS SPEED BEFORE YOU ARE CLOSE, not after. The join is where",
            "people acquire an overtake they then spend the whole sortie",
            "fighting. Closure you have not noticed is closure you cannot stop.",
            "",
        ] + tail + [
            "",
        ] + FADE_NOTE,
        "Everything before the part you have been practising: navigation, the radio flow, the join, observation. The commute is back, once, on purpose — arriving already matched is its own skill.",
        ac, grade="station", air_start="tanker",
        extra={"bb_awacs": True, "bb_navpoints": True},
        gates=True)


def qualification(track, ac, item4):
    return card(
        title(track, 8), track, 8, [
            "== 8 · QUALIFICATION ==",
            "NEW DEMAND: doing all of it with nobody talking to you.",
            "",
            "The check ride. Nothing new is taught and nothing is coached —",
            "the grader is on and the instructor is not talking.",
            "",
            "THE STANDARD, which you have already met piece by piece:",
            " 1. Arrive at pre-contact stabilised, zero closure, and hold it",
            "    15 seconds before moving forward. That is the gate.",
            " 2. Hold the close-in envelope on speed for 60 unbroken seconds.",
            "    That is the standard, and it is OURS rather than anyone's",
            "    manual — no document we hold states a duration.",
            " 3. No overtake above 25 knots inside a quarter mile. Not once.",
            f" 4. {item4}",
            " 5. A stable disconnect and a safe separation. Stay steady until",
            "    you are confirmed clear, THEN move aft smoothly.",
            "",
            "WHAT THE MISSION CAN AND CANNOT SEE — read this, because it is the",
            "difference between a grade and a decoration. Items 1 to 3 are",
            "measured by the mission and you will get a message when you pass",
            "them. Items 4 and 5 are NOT measured. DCS mission triggers cannot",
            "see a refuelling event, cannot read your fuel, and cannot tell a",
            "clean separation from a scramble. Those two are on your honor and",
            "your fuel gauge.",
            "",
            "We would rather tell you that than hand you a certificate we did",
            "not earn. If you hear the sixty-second call and you came away with",
            "full tanks and a tidy separation, you are qualified.",
            "",
            "Go and fly ride 9. That is the one this was all for.",
        ],
        "The check ride. Grader on, coaching off. Three of the five criteria are measured by the mission and two are on your honor — and the card says exactly which is which.",
        ac, grade="quiet")


def transfer(track, ac, tail):
    return card(
        title(track, 9), track, 9, [
            "== 9 · OPERATIONAL TRANSFER ==",
            "NEW DEMAND: mission workload and a fuel decision — refuelling as",
            "something you fit around a job, rather than the job.",
            "",
            "The point of all of it. A real sortie with real tasking and a",
            "tanker on station, where refuelling is a thing you do on the way",
            "rather than the reason you took off.",
            "",
            "NO TUTORIAL PROMPTS AND NO GRADE. There is no station-keeping",
            "message on this ride. The measure is whether you came home with",
            "the tasking done, and that is not a thing a trigger should be",
            "scoring.",
            "",
            "TANK BEFORE YOU NEED TO. The commonest operational refuelling",
            "error is not technique — it is arriving at the tanker at minimum",
            "fuel with no margin for three bad approaches. Decide early, go",
            "early, and leave yourself the retries.",
            "",
        ] + tail + [
            "",
            "This is the transfer test. Not another coached repetition of the",
            "same setup — a different problem that happens to contain the one",
            "you trained.",
        ],
        "A real sortie with real tasking and a tanker on station. No prompts, no grade — the measure is whether you came home with the job done.",
        ac, air_start=None, threat=2,
        extra={"bb_awacs": True, "bb_sams": True, "bb_targets": True,
               "bb_ambient": True, "bb_navpoints": True, "threat_intensity": 2})


# --------------------------------------------------------------------------- #
# Lane-specific tails
# --------------------------------------------------------------------------- #
BOOM_FIT = [
    "BOOM LANE NOTE. When you get there, an operator will fly the boom into",
    "your receptacle. That is half the problem solved for you — and it is",
    "exactly why your half has to be still. Your job in contact is to stop",
    "moving, and this ride is where you find out whether you can.",
    "",
    "F-16 SPECIFIC: opening the air-refuelling door changes the flight-control",
    "gains. Open it several minutes early if external tanks need to",
    "depressurise, and expect the jet to feel different afterwards. That is",
    "the airplane agreeing that this task wants lower gain.",
]
PROBE_FIT = [
    "PROBE LANE NOTE, and it matters MORE here. With a boom there is an",
    "operator flying half the problem for you. With a basket there is nobody:",
    "no operator, no director lights, no calls. Every bit of formation slop",
    "you bring with you stays in the system, and the basket will find out",
    "before you do.",
]

BOOM_CLOSURE = [
    "BOOM SPECIFIC: the director lights are TREND guidance, not a command to",
    "make a discrete input. Cross-check them against your sight picture on",
    "the tanker. A pilot flying the lights instead of the airplane has",
    "simply swapped one thing to chase for another.",
]
PROBE_CLOSURE = [
    "PROBE SPECIFIC, and this is the ride where it bites: a basket you drove",
    "into is a basket that is now swinging, and a swinging basket costs you",
    "the next three attempts. Arriving slowly is not politeness. It is the",
    "difference between one attempt and four.",
]

BOOM_FLOW = [
    "BOOM SPECIFIC: once you are in, stop looking at the boom. Go back to",
    "your reference on the tanker and hold it. The operator has the nozzle;",
    "you have the airplane. Chasing the boom nozzle is chasing something",
    "somebody else is already flying.",
]
PROBE_FLOW = [
    "PROBE SPECIFIC: after the probe goes in, keep coming forward enough to",
    "put a healthy bend in the hose, then hold formation. Do NOT stop dead at",
    "the instant of contact and drift straight back out — that is the",
    "commonest way a good plug becomes a disconnect three seconds later.",
    "Then stop looking at the basket. Back to the tanker reference.",
]

BOOM_RESET = [
    "BOOM SPECIFIC: after a disconnect, check whether your jet wants its",
    "refuelling system reset before the next attempt, get back to a stable",
    "pre-contact, and wait for the next clearance. Do not creep forward while",
    "you are sorting the switches out.",
]
PROBE_RESET = [
    "PROBE SPECIFIC: GIVE THE BASKET TIME. After a miss it is moving. Three",
    "or four seconds sitting at pre-contact is cheaper than three more",
    "attempts at something that will not hold still.",
    "",
    "A MISS IS NORMAL AND COSTS YOU NOTHING. That sentence is the whole",
    "lesson. Every pilot who cannot refuel has quietly decided a miss is a",
    "failure, so they press — and pressing is what actually costs them.",
]

BOOM_TURN = [
    "BOOM SPECIFIC: the director lights will be working harder in the turn.",
    "Resist the urge to fly them harder in response. Same trend guidance,",
    "same small inputs.",
]
PROBE_TURN = [
    "PROBE SPECIFIC: in a turn the hose trails differently and the basket",
    "sits somewhere new relative to the wing. If you have been flying the",
    "basket rather than the tanker, this is the ride that finds out. Fly the",
    "tanker.",
]

BOOM_RV = [
    "BOOM SPECIFIC: get the refuelling door open and settled BEFORE you are",
    "close. It changes how the jet handles, and the moment to discover that",
    "is not at pre-contact.",
]
PROBE_RV = [
    "PROBE SPECIFIC: probe out early and confirm it. There is no operator to",
    "tell you it is still stowed.",
]

BOOM_XFER = [
    "BOOM SPECIFIC: door open early, gains settled, then fly the tanker.",
    "Under a task load the temptation is to rush the configuration — that is",
    "how a routine top-up becomes the hardest part of the sortie.",
]
PROBE_XFER = [
    "PROBE SPECIFIC: with nobody helping and a basket that may need several",
    "tries, your fuel margin is not optional. Plan the tanker into the sortie",
    "rather than treating it as the thing you do when the light comes on.",
]

BOOM_Q4 = ("Plug and take fuel to a full transfer, and hold each connection "
           "long enough to be worth having.")
PROBE_Q4 = ("Plug and take fuel to a full transfer. Count your attempts — a "
            "qualification with eleven stabs in it is not one.")


NEW = OrderedDict()
for tid, ac, fit, cl, fl, rs, tn, rv, xf, q4 in [
    ("aar_boom", BOOM, BOOM_FIT, BOOM_CLOSURE, BOOM_FLOW, BOOM_RESET,
     BOOM_TURN, BOOM_RV, BOOM_XFER, BOOM_Q4),
    ("aar_probe", PROBE, PROBE_FIT, PROBE_CLOSURE, PROBE_FLOW, PROBE_RESET,
     PROBE_TURN, PROBE_RV, PROBE_XFER, PROBE_Q4),
]:
    p = tid[4:]
    NEW[f"aar_{p}_0_fit"] = fit_check(tid, ac, fit)
    NEW[f"aar_{p}_2_closure"] = closure(tid, ac, cl)
    NEW[f"aar_{p}_4_flow"] = flow(tid, ac, fl)
    NEW[f"aar_{p}_5_reset"] = reset(tid, ac, rs)
    NEW[f"aar_{p}_6_turn"] = turn(tid, ac, tn)
    NEW[f"aar_{p}_7_rv"] = rendezvous(tid, ac, rv)
    NEW[f"aar_{p}_8_qual"] = qualification(tid, ac, q4)
    NEW[f"aar_{p}_9_transfer"] = transfer(tid, ac, xf)

# The probe lane has no shipped Anchor card — the boom lane's aar_1_join fills
# that slot. Write the probe one.
NEW["aar_probe_1_anchor"] = card(
    title("aar_probe", 1), "aar_probe", 1, [
        "== 1 · THE ANCHOR ==",
        "NEW DEMAND: a stable formation sight picture, held, with no contact",
        "objective at all.",
        "",
        "You are airborne in trail. The only job is to arrive at OBSERVATION —",
        "line abreast the wing, stepped down — and sit there. DO NOT GO FOR",
        "THE BASKET on this ride. Seriously.",
        "",
        "PICK A FIXED REFERENCE ON THE TANKER and keep it nearly motionless:",
        "a wing root, a nacelle, the pod, a fuselage feature. That reference",
        "is the instrument you are flying. The basket, your probe and your",
        "airspeed are supporting cues, in that order of decreasing importance.",
        "",
        "MATCH HIS MOTION, not a memorised airspeed. The number is a",
        "cross-check; relative drift is the control problem.",
        "",
        "PASS: thirty seconds line abreast, hands steady, without a power",
        "change you did not intend. If the tanker keeps sliding around your",
        "canopy, contact practice is premature and ride 2 will be miserable.",
        "",
    ] + FADE_NOTE,
    "Join from trail and park line abreast — no basket this ride. Pick one reference on the tanker and keep it motionless; that reference is the instrument you are flying.",
    PROBE, grade="station", air_start="tanker")


# --------------------------------------------------------------------------- #
# Cards that already shipped: stamped into the tracks, NOT rebuilt.
# --------------------------------------------------------------------------- #
# The five shipped cards were written as a set of FOUR and say so in their
# briefs ("First of four", "== AAR 1 ·", "fly AAR 2 again"). Inside an eleven-
# ride track those sentences are now wrong, and a brief that miscounts its own
# course is the same defect class as a brief promising what the mission does
# not contain. Rewritten in place, by exact string, so a future edit to the
# card text fails loudly here rather than silently skipping.
RENUMBER = {
    "aar_1_join": [
        ("== AAR 1 · THE JOIN-UP ==", "== 1 · THE ANCHOR =="),
        ("First of four. You are airborne a few miles in trail — the ONLY job today",
         "Ride 1 of the boom track. You are airborne a few miles in trail — the"),
    ],
    "aar_2_contact": [
        ("== AAR 2 · PRE-CONTACT AND CONTACT ==", "== 3 · FIRST PLUG =="),
        ("Second of four, and you start where the last one ended: pre-contact,",
         "Ride 3, and you start where ride 2 ended: pre-contact,"),
    ],
    "aar_3_probe": [
        ("== AAR 3 · PROBE AND DROGUE ==", "== 3 · FIRST BASKET =="),
        ("Third of four, and a genuinely different task from the boom — which is",
         "Ride 3 of the probe track, and a genuinely different task from the boom —"),
    ],
    "aar_4_night": [
        ("== AAR 4 · NIGHT TANKING ==", "== 10 · NIGHT TANKING (extra) =="),
        ("Fourth of four. Nothing about the procedure changes. Everything about",
         "An extra, not a ride: nothing about the procedure changes. Everything about"),
        ("If you are not solid in daylight, fly AAR 2 again first. Night does not",
         "If you are not solid in daylight, fly ride 3 again first. Night does not"),
    ],
    "aar_boat": [
        ("== AAR · OFF THE BOAT ==", "== 10 · OFF THE BOAT (extra) =="),
    ],
}

EXISTING = {
    "aar_1_join": ("aar_boom", 1, "station", title("aar_boom", 1),
                   "NEW DEMAND: a stable formation sight picture, held, with "
                   "no contact objective at all."),
    "aar_2_contact": ("aar_boom", 3, "contact", title("aar_boom", 3),
                      "NEW DEMAND: contact mechanics. One plug, then another "
                      "— the connection itself, not yet the minute after it."),
    "aar_4_night": ("aar_boom", 10, "quiet", title("aar_boom", 10),
                    "NEW DEMAND: none. Same procedure with the visual cues "
                    "removed, which is why it is an extra and not a ride."),
    "aar_3_probe": ("aar_probe", 3, "contact", title("aar_probe", 3),
                    "NEW DEMAND: contact mechanics with nobody helping. The "
                    "basket does nothing for you and chasing it is the whole "
                    "failure mode."),
    "aar_boat": ("aar_probe", 10, "contact", title("aar_probe", 10),
                 "NEW DEMAND: none. The same skill from the air wing's own "
                 "tanker, lower and slower, which is why it is an extra."),
}


def main():
    d = json.loads(P.read_text(), object_pairs_hook=OrderedDict)

    for k, (track, n, grade, label, demand) in EXISTING.items():
        c = d[k]
        eras, by_era, choices = era_block(track)
        # WIDEN ONLY. An era the card already advertised keeps whatever it
        # already resolved to — its own by_era entry, or (absent one) its
        # recipe pin, which is why those eras get NO entry written here.
        #
        # The first version of this merge wrote the lane default into every
        # era, which quietly replaced `aar_boat`'s S-3B Viking with a KC-130
        # in the modern era: the card is the CARRIER-ORGANIC one, and the
        # air wing's own tanker is the entire point of it.
        had = set(c.get("eras") or [])
        c["eras"] = sorted(set(eras) | had,
                           key=["wwii", "coldwar", "modern", "gwot"].index)
        merged = OrderedDict((c.get("by_era") or {}))
        for e in c["eras"]:
            if e in had or e in merged:
                continue
            merged[e] = dict(by_era.get(e) or {})
        c["by_era"] = OrderedDict(
            (e, merged[e]) for e in c["eras"] if e in merged)
        c["aircraft_choices"] = choices
        c["track"] = {"id": track, "n": n}
        c["aar_grade"] = grade
        c["label"] = label
        # Every ride in a printed syllabus states its one new demand, or the
        # reader cannot tell an ordered course from a pile of missions. The
        # five cards that shipped before the track existed did not, so the
        # line goes in after the card's own == HEADER ==, idempotently.
        br = [x for x in (c.get("brief") or []) if not x.startswith("NEW DEMAND")]
        for old, new in RENUMBER.get(k, []):
            if old in br:
                br[br.index(old)] = new
            elif new not in br:
                raise SystemExit(
                    f"{k}: cannot renumber — neither the old line nor its "
                    f"replacement is present. The card text changed; update "
                    f"RENUMBER before re-running.\n  looked for: {old!r}")
        if br:
            br = [br[0], "", demand] + br[1:]
        c["brief"] = br
        # The track card is the featured entry point now; ten loose cards in
        # the featured row is not a syllabus, it is clutter. NEW goes too — a
        # badge on a card the grid never renders is not a signal, it is
        # dilution of the badge everywhere it IS rendered.
        (c.get("library") or {}).pop("featured", None)
        (c.get("library") or {}).pop("new", None)

    for k, v in NEW.items():
        d[k] = v

    P.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(NEW)} new cards, {len(EXISTING)} restamped, {len(d) - 1} total")


if __name__ == "__main__":
    main()
