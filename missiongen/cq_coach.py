"""Case III coaching and grading — the parts DCS does not do for us.

WHAT THIS ADDS, AND WHY IT IS NOT REDUNDANT WITH SUPERCARRIER
--------------------------------------------------------------
Supercarrier already talks: it assigns a marshal, gives an approach time, calls
radar contact, acknowledges platform, locks ACLS and hands you to Paddles at
three-quarters of a mile. None of that is reimplemented here and none of it
should be.

What Supercarrier does NOT do is check whether you flew the procedure. You can
push half an hour before your approach time and nothing happens. You can
descend at six thousand feet a minute below platform and nothing happens. You
can arrive at six miles a hundred knots fast and the first thing that notices
is the LSO, by which point the lesson is over.

So this module grades exactly those things and nothing else, and it tells the
pilot the moment it sees them rather than in a debrief he has to go and find.

EVERY GATE IS A MOVING ZONE
---------------------------
The ship is under way at about 25 knots, so a static trigger zone at 10 DME
drifts four miles out of position over a ten-minute recovery. `UnitInMovingZone`
takes a radius and a unit, so every range gate here is an annulus centered on the
carrier herself and is correct at any point in the ride. The marshal fix is not
a zone at all for the same reason — "established" is an altitude inside a DME
band, which is what the words actually mean.

WHICH CUES A RIDE GETS IS DECLARED, NOT INFERRED
------------------------------------------------
Ride 4 starts at three miles, already inside every range gate on the profile.
If the phases were merely sequential, it would fire "ten miles", "dirty up" and
"on speed" in the first second, all of them wrong. So each ride names the cues
it uses. That is four extra lines of data and it removes a whole class of
defect.

Flag block 8940-8979. wk_coach owns 8880-8899, wk_brief 8900-8939, aar_hud
8840-8859, aar_grade 8810-8839, formation 8801, crewops 200/300.
"""
from __future__ import annotations

from . import cq, cq_route

# --- flags ------------------------------------------------------------------
F_PHASE = 8940           # 8940 + i: cue i has fired
F_PHASE_MAX = 16         # 8940-8955
F_GRADE = 8960           # 8960 + i: grade i has fired
F_GRADE_MAX = 16         # 8960-8975
F_DEBRIEF = 8975         # the ride is over; print the card (grade slot 15 is
                         # reserved for it — 15 grades is more than any ride has)
F_ARM = 8979             # the whole thing is live
# 8976–8978 belong to gates.py (readback start / done / reminded).
# 8956-8959 and 8976-8978 are deliberate gaps. F_ARM sits at the top of the
# block with room underneath because wk_coach shipped a bug where the arm flag
# WAS one of the phase flags, and the sequence silently disarmed itself.

TEXT_S = 12              # cues are numbers to act on, not atmosphere — they
                         # need to outlive a glance at the instruments
GRADE_S = 15             # a grade is the teaching moment; give it longer

MS_PER_KT = cq.KT_MS
FT_M = cq.FT_M
NM_M = cq.NM_M

# THE ONE NUMBER HERE I COULD NOT SOURCE. pydcs's `UnitVerticalSpeedWithin`
# defaults to (-300, 300) with no unit named. A default meant to be permissive
# — "any vertical speed" — is 300 m/s (about 59,000 fpm), not 300 fpm, so the
# field is metres per second. That is an inference from the default, not a
# citation, and it is written down here rather than buried in a conversion.
FPM_TO_MS = 0.00508
DIVE_LIMIT_MS = cq.PLATFORM_FPM_MAX * FPM_TO_MS      # 2,000 fpm -> 10.16 m/s
DIVE_FLOOR_MS = 1000.0                               # "and anything worse"

# Tolerances the grades use. Deliberately wider than the procedure, because a
# grade that fires on a hundred feet is noise and a pilot stops reading them.
LEVEL_TOL_FT = 200
SPEED_TOL_KT = 15
PLATFORM_FLOOR_FT = 1500     # below this you are on the level segment, not
                             # descending through platform


# --------------------------------------------------------------------------- #
# The cues
# --------------------------------------------------------------------------- #
# (key, directive, the number that goes with it)
CUES = [
    ("checkin", "MARSHAL",
     "Check in. Mother's radial and DME are on your kneeboard — but fly what "
     "Marshal assigns you on the radio."),
    ("established", "ESTABLISHED",
     "On altitude at the fix. Report established with your state. Left-hand "
     "six-minute racetrack, inbound leg over the fix."),
    ("push", "COMMENCE",
     "Push time. Call commencing with your altimeter and state. 250 knots, "
     "4,000 feet per minute."),
    ("platform", "PLATFORM",
     "5,000 feet. Call platform, and shallow to 2,000 feet per minute — not "
     "one foot more."),
    ("ten", "TEN MILES",
     "Level 1,200 feet. Letdown complete. Call ten miles."),
    ("dirty", "DIRTY UP",
     "Eight miles. Gear, flaps, hook. Stay at 1,200."),
    ("six", "ON SPEED",
     "Six miles. 150 knots, then on-speed AOA. Hold 1,200 until the "
     "glideslope comes to you."),
    ("ball", "CALL THE BALL",
     "Side number, type, ball, fuel state. Fly the ball — do not go looking "
     "for the deck behind it."),
    ("bolter", "BOLTER",
     "Straight ahead, climb to 1,200. All turns LEVEL. Report abeam with your "
     "state, turn to final at 4 DME."),
]
CUE_KEYS = [c[0] for c in CUES]
CUE_IDX = {k: i for i, k in enumerate(CUE_KEYS)}

# Which cues each ride actually uses. See the module docstring: ride 4 begins
# inside every range gate on the profile, so inferring this from sequence would
# fire three wrong cues in its first second.
RIDE_CUES = {
    "cq_1_stack": ["checkin", "established", "push"],
    "cq_2_push": ["push", "platform", "ten"],
    "cq_3_approach": ["ten", "dirty", "six", "ball"],
    "cq_4_ball": ["ball", "bolter"],
    "cq_5_nightcq": [],          # the check ride is silent
}

# --------------------------------------------------------------------------- #
# The grades
# --------------------------------------------------------------------------- #
# (key, verdict text). Each fires at most once and says what it saw.
GRADES = [
    ("push_early", "EARLY. You left marshal before your approach time. In a "
                   "real stack that is a separation problem for everybody "
                   "below you — adjust the legs, do not just orbit."),
    ("push_late", "LATE. You left marshal after your approach time. Stretching "
                  "the legs is how you fix being early; being late means you "
                  "have to shorten them next time."),
    ("push_ontime", "ON TIME. That is the hard part of holding and you did it."),
    ("dive", "TOO FAST. Below platform the limit is 2,000 feet per minute. "
             "Faster than that and you arrive low and fast at ten miles with "
             "nothing left to fix it with."),
    ("ten_high", "HIGH AT TEN. You should be level at 1,200. High here means "
                 "you dive to catch the glideslope later, which is how the "
                 "approach falls apart."),
    ("ten_low", "LOW AT TEN. Level 1,200 by ten miles — below that you are "
                "dragging in, burning fuel and low on options."),
    ("fast_six", "FAST AT SIX. 150 knots at the six-mile fix, in the landing "
                 "configuration. Arriving fast means you are still slowing "
                 "when you should be flying the ball."),
    ("level_ten", "LEVEL AT TEN, 1,200 feet. Exactly right."),
]
GRADE_KEYS = [g[0] for g in GRADES]
GRADE_IDX = {k: i for i, k in enumerate(GRADE_KEYS)}

# THE SCORECARD. Rampagers prints one at engine shutdown — base score,
# every rule itemised with its points, one line that overrides the lot. Ours
# prints when the ride's last cue is a minute old: base 50, each grade that
# fired with its points, and a "clean" line when no bust fired. Triggers
# cannot add numbers into a message, so the card is itemised, not summed;
# the pilot can add, and the itemisation is the teaching anyway.
BASE_SCORE = 50
SCORE = {
    "push_early": (-5, "Left marshal early"),
    "push_late": (-5, "Left marshal late"),
    "push_ontime": (10, "Commenced on time"),
    "dive": (-10, "Exceeded 2,000 fpm below platform"),
    "ten_high": (-5, "High at ten miles"),
    "ten_low": (-5, "Low at ten miles"),
    "fast_six": (-5, "Fast at six miles"),
    "level_ten": (10, "Level 1,200 at ten miles"),
}
BUSTS = [k for k, (pts, _t) in SCORE.items() if pts < 0]
DEBRIEF_AFTER_S = 60

RIDE_GRADES = {
    "cq_1_stack": ["push_early", "push_late", "push_ontime"],
    "cq_2_push": ["dive", "ten_high", "ten_low", "level_ten"],
    "cq_3_approach": ["fast_six"],
    "cq_4_ball": [],             # Paddles grades the last mile, and does it
                                 # better than a trigger can
    "cq_5_nightcq": [],          # the check ride is silent
}


def cues_for(ride_key: str) -> list:
    return list(RIDE_CUES.get(ride_key, []))


def grades_for(ride_key: str) -> list:
    return list(RIDE_GRADES.get(ride_key, []))


def cue(key: str) -> tuple:
    return CUES[CUE_IDX[key]]


def grade_text(key: str) -> str:
    return GRADES[GRADE_IDX[key]][1]


def push_time_s(ride_key: str) -> int | None:
    """Mission seconds at which the approach time falls, or None.

    We assign it rather than reading it, because DCS generates the expected
    approach time while the mission runs and no mission file can see that
    number. The kneeboard says so in as many words — the ride grades you
    against the time it gave you on paper.
    """
    r = cq.ride(ride_key) or {}
    m = r.get("push_min")
    return int(m * 60) if m else None


def commence_dme(angels: int) -> float:
    """Where "he has commenced" becomes unambiguous.

    Two miles inside the fix. The holding pattern lives between the fix and
    about four miles outside it, so the aircraft never touches this band while
    holding — crossing it inbound means one thing only.
    """
    return cq.marshal_dme(angels) - 2.0


def commence_transit_s(angels: int) -> int:
    """How long the two miles from the fix to the commence band actually take.

    Without this the timing grade is wrong for everyone: a pilot who crosses
    the fix at exactly the approach time reaches the band about half a minute
    later, and would be graded LATE for flying it perfectly.
    """
    tas = cq_route.ias_to_tas_kt(cq.MARSHAL_HOLD_KT, angels * 1000)
    return int(round(2.0 / tas * 3600.0))


def score_line(key: str) -> str:
    pts, text = SCORE[key]
    return f"{'+' if pts > 0 else ''}{pts}  {text}"


def attach(m, player_group, carrier_group, ride_key: str, warnings=None,
           aircraft: str | None = None, mother_mhz: float | None = None):
    """Wire the cues and the grades. Returns True if anything was attached.

    NEVER RAISES — same contract as `wk_coach.attach` and `aar_grade.attach`.
    A mission that loses its coaching is worse than one that has it; a mission
    that fails to build is worse than both.
    """
    warnings = warnings if warnings is not None else []
    r = cq.ride(ride_key)
    if not r or m is None or player_group is None or carrier_group is None:
        return False
    keys, gkeys = cues_for(ride_key), grades_for(ride_key)
    if not keys and not gkeys:
        return False
    try:
        from dcs import action as A
        from dcs import condition as C
        from dcs import triggers as Tr

        me = player_group.units[0]
        boat = carrier_group.units[0]
        angels = r["angels"]
        push_s = push_time_s(ride_key)

        def msg(text, secs):
            return A.MessageToGroup(player_group.id, m.string(text), secs)

        def inside(nm):
            return C.UnitInMovingZone(me.id, nm * NM_M, boat.id)

        def outside(nm):
            return C.UnitOutsideMovingZone(me.id, nm * NM_M, boat.id)

        def band(outer_nm, inner_nm):
            """Inside `outer`, still outside `inner` — one DME gate."""
            return [inside(outer_nm), outside(inner_nm)]

        def hi(ft):
            return C.UnitAltitudeHigher(me.id, ft * FT_M)

        def lo(ft):
            return C.UnitAltitudeLower(me.id, ft * FT_M)

        def faster(kt):
            return C.UnitSpeedHigher(me.id, kt * MS_PER_KT)

        def armed():
            return C.FlagIsTrue(F_ARM)

        def fired(kind, key):
            base = F_PHASE if kind == "cue" else F_GRADE
            idx = CUE_IDX[key] if kind == "cue" else GRADE_IDX[key]
            return base + idx

        def rule(comment, conds, actions):
            # `.rules` and `.actions`, appended to directly — pydcs's trigger
            # objects have no add_* helpers, and an AttributeError here would
            # be swallowed by this function's never-raise contract and surface
            # as a mission that silently has no coaching in it.
            t = Tr.TriggerContinious(comment=comment)
            for c in conds:
                t.rules.append(c)
            for a in actions:
                t.actions.append(a)
            m.triggerrules.triggers.append(t)
            return t

        # --- the cue conditions -------------------------------------------- #
        mdme = cq.marshal_dme(angels)
        CUE_RULES = {
            # Just after start, once the pilot has his eyes outside.
            "checkin": [[C.TimeAfter(20)]],
            # "Established" means at altitude, in the band the fix sits in.
            "established": [band(mdme + 6, mdme - 6)
                            + [hi(angels * 1000 - 300),
                               lo(angels * 1000 + 300)]],
            "push": ([[C.TimeAfter(push_s)]] if push_s else
                     [[inside(mdme + 6)]]),
            # PLATFORM is an altitude. The floor keeps it from firing on the
            # level segment of a ride that starts below 5,000 already.
            "platform": [[lo(cq.PLATFORM_FT), hi(PLATFORM_FLOOR_FT),
                          outside(cq.ARC_DME)]],
            "ten": [band(cq.LEVEL_DME, cq.LEVEL_DME - 1.5)],
            "dirty": [band(cq.DIRTY_DME, cq.DIRTY_DME - 1.5)],
            "six": [band(cq.ONSPEED_DME, cq.ONSPEED_DME - 1.5)],
            "ball": [[inside(1.5)]],
            # A bolter is: you were at the ball, and a minute later you are
            # outside two miles again. There is no "you missed the wires"
            # condition in the Mission Editor, so this is the honest proxy —
            # and it is also true of a waveoff, which needs the same pattern.
            "bolter": [[C.FlagIsTrue(fired("cue", "ball")), outside(2.0),
                        C.TimeSinceFlag(fired("cue", "ball"), 45)]],
        }

        from . import gates as _gates
        for key in keys:
            _k, directive, detail = cue(key)
            f = fired("cue", key)
            for i, conds in enumerate(CUE_RULES[key]):
                acts = [msg(f"{directive} — {detail}", TEXT_S), A.SetFlag(f)]
                # The check-in cue opens the readback gate: from here the
                # mission watches COMM1 for Mother's frequency.
                if key == "checkin" and mother_mhz:
                    acts.append(A.SetFlag(_gates.F_START))
                rule(f"CQ cue: {key}" + (f" ({i})" if i else ""),
                     [armed(), C.FlagIsFalse(f)] + list(conds), acts)

        # The gate itself (Fulda's set / not-set / advance triplet) is
        # installed by the builder AFTER the radios are programmed, so its
        # reminder can name the channel that really holds Mother. Here we
        # only open it — see `gates.readback`.

        # --- the grade conditions ------------------------------------------ #
        cdme = commence_dme(angels)
        transit = commence_transit_s(angels)
        tol = cq.EAT_TOLERANCE_S
        window = (push_s or 0) + transit
        GRADE_RULES = {
            "push_early": [[inside(cdme), C.TimeBefore(window - tol)]],
            "push_late": [[inside(cdme), C.TimeAfter(window + tol)]],
            "push_ontime": [[inside(cdme), C.TimeAfter(window - tol),
                             C.TimeBefore(window + tol)]],
            # Descending FASTER than the limit is the bust, so the "within"
            # window is written as the bust itself: between 2,000 fpm down and
            # anything worse.
            "dive": [[lo(cq.PLATFORM_FT), hi(PLATFORM_FLOOR_FT),
                      C.UnitVerticalSpeedWithin(me.id, -DIVE_FLOOR_MS,
                                                -DIVE_LIMIT_MS)]],
            "ten_high": [band(cq.LEVEL_DME, cq.LEVEL_DME - 1.5)
                         + [hi(cq.LEVEL_FT + LEVEL_TOL_FT)]],
            "ten_low": [band(cq.LEVEL_DME, cq.LEVEL_DME - 1.5)
                        + [lo(cq.LEVEL_FT - LEVEL_TOL_FT)]],
            "level_ten": [band(cq.LEVEL_DME, cq.LEVEL_DME - 1.5)
                          + [lo(cq.LEVEL_FT + LEVEL_TOL_FT),
                             hi(cq.LEVEL_FT - LEVEL_TOL_FT)]],
            "fast_six": [band(cq.ONSPEED_DME, cq.ONSPEED_DME - 1.5)
                         + [faster(cq.ONSPEED_KT + SPEED_TOL_KT)]],
        }

        for key in gkeys:
            f = fired("grade", key)
            for i, conds in enumerate(GRADE_RULES[key]):
                rule(f"CQ grade: {key}" + (f" ({i})" if i else ""),
                     [armed(), C.FlagIsFalse(f)] + list(conds),
                     [msg(grade_text(key), GRADE_S), A.SetFlag(f)])

        # --- the scorecard -------------------------------------------------- #
        # Opens a minute after the ride's last cue. Every grade that fired
        # prints its line; if no bust fired, say so — silence after a good
        # ride reads as a broken mission.
        if gkeys and keys:
            last = fired("cue", keys[-1])
            r_name = r.get("name", ride_key)
            card = Tr.TriggerOnce(comment="CQ debrief: open the card")
            for c in [armed(), C.TimeSinceFlag(last, DEBRIEF_AFTER_S)]:
                card.rules.append(c)
            card.actions.append(A.SetFlag(F_DEBRIEF))
            card.actions.append(msg(f"RIDE DEBRIEF — {r_name}. Base score "
                                    f"{BASE_SCORE}.", 30))
            m.triggerrules.triggers.append(card)
            for key in gkeys:
                if key not in SCORE:
                    continue
                t = Tr.TriggerOnce(comment=f"CQ debrief: {key}")
                for c in [C.TimeSinceFlag(F_DEBRIEF, 2),
                          C.FlagIsTrue(fired("grade", key))]:
                    t.rules.append(c)
                t.actions.append(msg(score_line(key), 30))
                m.triggerrules.triggers.append(t)
            busts = [k for k in gkeys if k in BUSTS]
            if busts:
                clean = Tr.TriggerOnce(comment="CQ debrief: clean")
                clean.rules.append(C.TimeSinceFlag(F_DEBRIEF, 2))
                for k in busts:
                    clean.rules.append(C.FlagIsFalse(fired("grade", k)))
                clean.actions.append(msg("No busts recorded on this ride.", 30))
                m.triggerrules.triggers.append(clean)

        # --- ride 4 flies the last mile again ------------------------------ #
        # The whole value of a ball ride is repetition, and a cue that fires
        # once gives you one repetition. Ninety seconds after the bolter cue,
        # the ball and bolter flags clear and the next pass is coached too.
        if "bolter" in keys:
            rule("CQ: re-arm the ball for another pass",
                 [armed(), C.FlagIsTrue(fired("cue", "bolter")),
                  C.TimeSinceFlag(fired("cue", "bolter"), 90)],
                 [A.ClearFlag(fired("cue", "ball")),
                  A.ClearFlag(fired("cue", "bolter"))])

        # --- who turns it on ----------------------------------------------- #
        # Armed at mission start. Unlike the White Knights coached ride there is
        # no six-page brief holding the controls first — a Case III ride begins
        # airborne, already in the procedure, and a pilot in the stack at night
        # has somewhere to be.
        opening = Tr.TriggerOnce(comment="CQ: arm the coaching")
        opening.rules.append(C.TimeAfter(1))
        opening.actions.append(A.SetFlag(F_ARM))
        m.triggerrules.triggers.append(opening)
        return True
    except Exception as exc:                              # pragma: no cover
        warnings.append(f"Case III coaching not attached: {exc}")
        return False
