"""The BFM ladder — three perches, and the instruction that makes them count.

A merge on its own is not training. It is one setup, flown until you have
memorised that setup. Every real syllabus teaches basic fighter maneuvers as
three RIDES, because the three positions ask three different questions:

    OFFENSIVE PERCH   you start at his six — can you convert without
                      overshooting?
    DEFENSIVE PERCH   he starts at yours — can you deny the shot and force
                      an overshoot?
    HIGH ASPECT       both hot, nose to nose — can you choose the right fight
                      and win the first 90 degrees?

The difficulty knob here is deliberately GEOMETRY, not AI skill. DCS AI at
Excellent flies numbers a human airframe cannot match, so a pilot who loses to
it learns "I lose", not "I flew that badly". Change where the fight starts and
the same bandit at the same skill teaches three different lessons.

On the numbers in the standards cards: the ones WE control — ranges, altitude
blocks, times, hard decks — are exact, because we set them when we build the
mission. Aircraft performance numbers are given as a band with a method for
finding your own, because corner velocity is per-type, per-weight, per-fuel,
and a confidently wrong number in a training document is worse than an honest
range. (If you know your jet's number, use it; the card tells you how to find
it.)
"""

# Geometry per rung, in the pilot's own terms. `range_m` is slant range at
# t=0; `bearing_off_nose` is where the bandit sits relative to YOUR nose
# (0 = dead ahead, 180 = dead astern); `bandit_heading_off` is the bandit's
# heading relative to yours (0 = co-heading, 180 = head-on).
SETUPS = {
    "neutral": {
        "label": "Neutral — line abreast",
        "stage": None,
        "range_m": 3700,          # 2 nm
        "bearing_off_nose": 90,
        "bandit_heading_off": 0,
        "alt_offset_m": 0,
    },
    "offensive": {
        "label": "BFM 1 — Offensive perch",
        "stage": "1 of 3",
        "range_m": 2200,          # 1.2 nm
        "bearing_off_nose": 0,    # he is ahead of you: you own his six
        "bandit_heading_off": 30, # 30 deg angle off, the classic perch
        "alt_offset_m": 0,
    },
    "defensive": {
        "label": "BFM 2 — Defensive perch",
        "stage": "2 of 3",
        "range_m": 2200,
        "bearing_off_nose": 180,  # he is astern: he owns YOUR six
        "bandit_heading_off": 0,  # co-heading, tracking you
        "alt_offset_m": 300,      # slightly high, the way an attacker sets up
    },
    "high_aspect": {
        "label": "BFM 3 — High-aspect merge",
        "stage": "3 of 3",
        "range_m": 9260,          # 5 nm — about 30 s at merge closure
        "bearing_off_nose": 0,
        "bandit_heading_off": 180,  # nose to nose, both hot
        "alt_offset_m": 0,
    },

    # ---------------------------------------------------------------------
    # THE REAL PERCHES.
    #
    # The four rungs above are ours: a reasonable ladder, invented. These six
    # are not invented. AETC Syllabus F16C0B00PL (56 FW, Luke AFB, April 2014)
    # flies offensive BFM on BFM-1/2/3 and defensive BFM on BFM-4/5/6, and each
    # of those sorties runs the SAME three setups:
    #
    #     *6. Offensive BFM — a. 9,000 ft; b. 6,000 ft; c. 3,000 ft
    #     *6. Defensive BFM — a. 9,000 ft; b. 6,000 ft; c. 3,000 ft
    #
    # That is the whole ladder, and it is a range ladder inside each position
    # rather than one range per position. Nine thousand feet gives you a turn
    # circle to think about; three thousand gives you a snapshot and a
    # decision. Same jet, same bandit, same skill — three different problems.
    #
    # The originals are kept, unchanged, because share links are byte-stable
    # and a recipe minted against `offensive` must keep building the same
    # mission forever. These are additive.
    "off_9k": {
        "label": "BFM-1 — Offensive perch, 9,000 ft",
        "stage": "1 of 3 (offensive)",
        "range_m": 2743,          # 9,000 ft
        "bearing_off_nose": 0,
        "bandit_heading_off": 30,
        "alt_offset_m": 0,
        "syllabus": "BFM-1 / BFM-2 / BFM-3, task 6a",
    },
    "off_6k": {
        "label": "BFM-1 — Offensive perch, 6,000 ft",
        "stage": "2 of 3 (offensive)",
        "range_m": 1829,          # 6,000 ft
        "bearing_off_nose": 0,
        "bandit_heading_off": 30,
        "alt_offset_m": 0,
        "syllabus": "BFM-1 / BFM-2 / BFM-3, task 6b",
    },
    "off_3k": {
        "label": "BFM-1 — Offensive perch, 3,000 ft",
        "stage": "3 of 3 (offensive)",
        "range_m": 914,           # 3,000 ft
        "bearing_off_nose": 0,
        "bandit_heading_off": 30,
        "alt_offset_m": 0,
        "syllabus": "BFM-1 / BFM-2 / BFM-3, task 6c",
    },
    "def_9k": {
        "label": "BFM-4 — Defensive perch, 9,000 ft",
        "stage": "1 of 3 (defensive)",
        "range_m": 2743,
        "bearing_off_nose": 180,
        "bandit_heading_off": 0,
        "alt_offset_m": 300,
        "syllabus": "BFM-4 / BFM-5 / BFM-6, task 6a",
    },
    "def_6k": {
        "label": "BFM-4 — Defensive perch, 6,000 ft",
        "stage": "2 of 3 (defensive)",
        "range_m": 1829,
        "bearing_off_nose": 180,
        "bandit_heading_off": 0,
        "alt_offset_m": 300,
        "syllabus": "BFM-4 / BFM-5 / BFM-6, task 6b",
    },
    "def_3k": {
        "label": "BFM-4 — Defensive perch, 3,000 ft",
        "stage": "3 of 3 (defensive)",
        "range_m": 914,
        "bearing_off_nose": 180,
        "bandit_heading_off": 0,
        "alt_offset_m": 300,
        "syllabus": "BFM-4 / BFM-5 / BFM-6, task 6c",
    },
}

DEFAULT_SETUP = "neutral"

# The training floor. This started as our own reasonable-sounding number, and
# was labelled as ours because the AETC B-Course grades "floor awareness"
# without ever stating the floor. Two independent USAF documents state it, for
# exactly this activity, and they agree:
#
#   48 OG / 493 FS F-15C Flying Training Syllabus, Feb 2009 (Col J. T. Quintas,
#   48 OG/CC) — SPINS for MQT-2/3/4 and 2 FL-1/2/3: "Floor: 5,000 ft AWL/AGL."
#
#   AFMAN 11-2F-22A Vol 3, F-22A Operations Procedures, 20 Sep 2018, Table 3.2
#   Minimum Altitude Summary — "Aerobatics / Air Combat Training / Advanced
#   Handling: 5,000."
#
# So it is no longer ours. Same figure, two commands, two airframes, nine years
# apart. See docs/source-library-proposals.md.
HARD_DECK_FT = 5000


def geometry_summary(setup: str) -> str:
    """Describe the same starting geometry the mission generator uses."""
    cfg = SETUPS.get(setup, SETUPS[DEFAULT_SETUP])
    bearing = {0: "ahead", 90: "abeam", 180: "astern"}.get(
        cfg["bearing_off_nose"], f"at {cfg['bearing_off_nose']} degrees")
    altitude = ("co-altitude" if not cfg["alt_offset_m"] else
                f"{cfg['alt_offset_m'] / 0.3048:,.0f} ft above you")
    heading = ("head-on" if cfg["bandit_heading_off"] == 180 else
               "co-heading" if not cfg["bandit_heading_off"] else
               f"{cfg['bandit_heading_off']} degrees angle off")
    return (f"{cfg['label']}: bandit {cfg['range_m'] / 1852:.1f} nm {bearing}, "
            f"{altitude}, {heading}.")


def _hdr(title):
    return ["=" * 66, title, "=" * 66]


def brief_lines(setup: str, aircraft_id: str = "", guns_only: bool = False):
    """The standards card for one rung.

    Structure is deliberate and the same every time, because a pilot should be
    able to find the part they want without reading the whole sheet:
    OBJECTIVE (what you are learning) · SETUP (what you should see at t=0, so
    you can verify the sim gave you the briefed picture) · STANDARDS (what good
    looks like, measurable) · COMMON ERRORS (each with the cue that reveals it,
    because an error you cannot notice is not one you can fix) · DEBRIEF
    (three questions) · MOVE ON WHEN (the gate to the next rung).
    """
    s = SETUPS.get(setup) or SETUPS[DEFAULT_SETUP]
    fn = {
        "offensive": _offensive,
        "defensive": _defensive,
        "high_aspect": _high_aspect,
    }.get(setup, _neutral)
    out = _hdr(f"BFM — {s['label']}" + (f"   (stage {s['stage']})" if s["stage"] else ""))
    out += fn(guns_only)
    out += _common_tail(guns_only)
    return out


def _corner_note():
    return [
        "  Corner velocity — the speed that buys the most turn rate — is",
        "  per-type, per-weight and per-fuel, so this card will not invent a",
        "  number for your jet. Find it once: at 15,000 ft, pull maximum G at",
        "  450 kt and hold the pull as you decelerate. The speed where turn",
        "  rate peaks before G falls away is yours. For most fast jets it is",
        "  somewhere between 330 and 400 KIAS. Write it down; every card below",
        "  says 'corner' and means that number.",
    ]


def _offensive(guns_only):
    return [
        "",
        "OBJECTIVE",
        "  Convert a six-o'clock position into a valid firing solution without",
        "  flying out in front of him.",
        "",
        "SETUP — what you should see at t=0",
        "  Bandit 1.2 nm off your nose, co-altitude, 30 degrees angle off,",
        "  straight and level. You are behind him and he has not reacted yet.",
        "  If that is not the picture you see, re-roll — the setup is the",
        "  lesson, and a wrong setup teaches a different lesson.",
        "",
        "STANDARDS — what good looks like",
        "  - Control closure with LAG pursuit before you need to. Pure pursuit",
        "    is for the shot, not for the approach.",
        "  - Do not go inside 0.8 nm with high closure. Range is the resource",
        "    you are spending; spend it deliberately.",
        "  - Guns: a tracking solution held 1.5 s or more inside 1,500 ft.",
        "    Missile: a launch from inside a valid envelope, not a hope shot.",
        "  - No overshoot: you never cross his flight path out in front.",
        f"  - Hard deck {HARD_DECK_FT:,} ft AGL. Knock it off rather than take",
        "    a fight below it. The ground has ended more BFM sorties than any",
        "    bandit.",
        "",
        "COMMON ERRORS — and the cue that tells you it is happening",
        "  1. Pure pursuit from the perch. Closure builds, you arrive too fast",
        "     and overshoot.",
        "     CUE: he is growing quickly in the canopy and drifting toward the",
        "     bow rather than staying put.",
        "  2. Pulling lead too early. High AOA, energy gone, he reverses into",
        "     you and the fight is neutral or worse.",
        "     CUE: you are below 250 KIAS in the first 30 seconds.",
        "  3. Losing sight while looking inside at the HUD or the radar.",
        "     CUE: the words 'where did he go'. That is the sortie over — knock",
        "     it off and re-roll rather than fly a fight you cannot see.",
    ]


def _defensive(guns_only):
    return [
        "",
        "OBJECTIVE",
        "  Deny an attacker at your six a tracking solution, and force an",
        "  overshoot you can convert.",
        "",
        "SETUP — what you should see at t=0",
        "  Bandit 1.2 nm astern, slightly high, co-speed and closing. You are",
        "  straight and level. The fight starts with YOUR first move — check",
        "  six early, because nothing on your instruments will tell you.",
        "",
        "STANDARDS — what good looks like",
        "  - First defensive input within 3 seconds of the tally. Hesitation",
        "    is the single biggest killer at this rung.",
        "  - Break turn INTO him, at corner, maximum performance — not a lazy",
        "    turn, and not a max-rate pull that puts you on the deck.",
        "  - Change the plane of motion. A flat circle is a gift: it lets him",
        "    pull lead and track.",
        "  - Force the overshoot BEFORE you reverse. Reversing early hands him",
        "    the shot you were trying to deny.",
        "  - Survive 90 seconds and you have passed this ride, even if you",
        "    never got offensive.",
        "",
        "COMMON ERRORS — and the cue that tells you it is happening",
        "  1. Running in a straight line, hoping for separation.",
        "     CUE: your speed is high, his nose is still on you, and nothing",
        "     is changing. You are dying tired.",
        "  2. Defending in one plane.",
        "     CUE: he stays glued between your 5 and 7 o'clock through the",
        "     whole turn. He is not being forced to solve anything.",
        "  3. Reversing on hope rather than on his overshoot.",
        "     CUE: he is still more than 1,500 ft out and his nose is still on",
        "     you when you reverse.",
    ]


def _high_aspect(guns_only):
    return [
        "",
        "OBJECTIVE",
        "  Make the merge decision deliberately — one-circle or two — and win",
        "  the first 90 degrees after the pass.",
        "",
        "SETUP — what you should see at t=0",
        "  Bandit 5 nm on the nose, co-altitude, hot. Closure is roughly a",
        "  thousand knots, so you have about thirty seconds to arrive at the",
        "  merge on your terms.",
        "",
        "STANDARDS — what good looks like",
        "  - DECIDE BEFORE THE MERGE and say it out loud: nose-to-tail",
        "    (one-circle, a radius fight) or nose-to-nose (two-circle, a rate",
        "    fight). A default is not a decision.",
        "  - Arrive at the pass AT corner, not above it. Fast feels good and",
        "    buys a turn radius that puts him inside you.",
        "  - In the first 90 degrees after the pass you must gain angles OR",
        "    gain energy. Neither means you lost the merge.",
        "  - Keep sight through the pass. Lose sight, knock it off.",
        "",
        "COMMON ERRORS — and the cue that tells you it is happening",
        "  1. No decision, so you end up in a two-circle rate fight by",
        "     accident, possibly against a jet that out-rates you.",
        "     CUE: you are nose-low, behind the power curve, and he is",
        "     gaining angles every pass.",
        "  2. Merging too fast.",
        "     CUE: 500+ KIAS at the pass, and your first turn takes you a mile",
        "     wide of where you wanted to be.",
        "  3. Fighting through the HUD instead of over your shoulder.",
        "     CUE: you are flying the symbology, not the airplane.",
    ]


def _neutral(guns_only):
    return [
        "",
        "OBJECTIVE",
        "  A fight from a neutral start — the everyday rep, and the one to fly",
        "  when you want a fight rather than a lesson.",
        "",
        "SETUP — what you should see at t=0",
        "  Bandit 2 nm abeam, co-altitude, looking at you.",
        "",
        "STANDARDS — what good looks like",
        "  - Energy before angles. Do not spend what you cannot get back.",
        "  - Keep sight. Lose sight, knock it off.",
        f"  - Hard deck {HARD_DECK_FT:,} ft AGL.",
        "",
        "  For structured practice fly the three-perch ladder instead:",
        "  offensive perch, defensive perch, then the high-aspect merge.",
    ]


def _common_tail(guns_only):
    tail = ["", "DEBRIEF — three questions, every sortie"]
    tail += [
        "  1. What was the picture at the first turn, and what did I do about",
        "     it?",
        "  2. Where was my energy when I needed it — and what did I spend it",
        "     on?",
        "  3. Did I ever lose sight? If so, at what moment, and why?",
        "",
        "MOVE ON WHEN",
        "  You can fly the ride to standard three sorties running. Re-roll",
        "  between sorties: same setup, different bandit type and different",
        "  ground. The setup is the lesson; the variation is what stops you",
        "  memorising one fight.",
        "",
        "ABOUT YOUR ADVERSARY",
        "  The bandit is flown one skill notch below the mission's engagement",
        "  skill, on purpose. DCS AI at Excellent pulls numbers no airframe",
        "  really has, and losing to that teaches you nothing except that you",
        "  lost. This bandit is beatable by flying well.",
    ]
    if guns_only:
        tail += [
            "",
            "GUNS ONLY",
            "  No missiles on either airplane. This is a pure angles fight:",
            "  everything is decided by the turn, and there is no escape from a",
            "  bad merge except flying your way out of it.",
        ]
    tail += _hdr("")[:1] + _corner_note()
    return tail
