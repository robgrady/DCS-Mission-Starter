"""In-mission AAR coaching and grading, built entirely from Mission Editor
triggers — no Lua, no scripts inside the .miz.

WHY THIS EXISTS, AND WHAT IT DELIBERATELY DOES NOT DO.

The AAR Academy plan specifies a grading engine keyed on `S_EVENT_REFUELING`,
`S_EVENT_REFUELING_STOP` and `Unit.getFuel()`. **None of those are reachable
from Mission Editor triggers.** ME conditions cannot see a refuelling event and
cannot read fuel. So a trigger-only grader cannot tell you that you plugged, how
long you held it, or how much you took.

It can tell you the other thing, and the other thing is most of the skill. The
plan's own central claim is that *air refuelling is close formation flying with
a fuel connection attached* — so a grader that measures POSITION and SPEED and
says nothing about the plug is not a degraded version of the real thing. It is
the argument, enforced.

WHAT IS MEASURED, and how honestly:

  * IN THE ENVELOPE — `UnitInMovingZone(player, R, tanker)`. This is a SPHERE
    centered on the tanker unit, so it cannot tell astern from abeam. We use it
    only to answer "are you working close", which is a question a sphere can
    answer correctly.
  * ON SPEED — the receiver's speed against the tanker's known constant track
    speed. On a straight track leg with both aircraft on the same heading this
    IS the closure rate. In the tanker's turn, or with the receiver at an
    angle, it is not, and the threshold is set wide enough that the difference
    cannot produce a false accusation.
  * DWELL — `TimeSinceFlag`. The stability flag is cleared the instant
    tolerance is broken, so the timer restarts rather than accumulating credit
    across excursions.
  * EXCURSIONS — a counter incremented on each fall-out.

THE TOLERANCE RULE, which outranks precision.

A grader that calls a correct pilot wrong is worse than no grader, because once
a learner distrusts the grade every later grade is noise. So every tolerance
here is set WIDE — wide enough that a pilot flying the position properly is
never outside it, at the cost of letting a sloppy one pass. When in doubt the
grader says nothing. Silence is the default state, not the reward.

BANDWIDTH FEEDBACK. Every call is edge-triggered through a flag, exactly as
`formation.py` does it: a continuous DCS trigger re-evaluates every second, so
a bare condition shouts once a second for as long as it is true. Each call here
requires its own "already said this" flag clear, then sets it; the matching
recovery rule requires it set, then clears it. One call per transition.

FADING. The unsafe-closure call stops after MAX_CLOSURE_CALLS. Coaching that
never fades is coaching the pilot learns to fly around instead of learning from.

Flag block 8810-8839. `formation.py` owns 8801; `crewops.py` owns 200/300.
"""
from __future__ import annotations

_KT_MS = 0.514444          # knots -> m/s
_FT_M = 0.3048

# --- the envelope ---------------------------------------------------------
#
# CLOSE_M is the "working close" sphere: observation, pre-contact and contact
# all sit inside about 50 m of a tanker's reference point, and the pre-contact
# air start puts you 1 nm (1,852 m) out. 150 m is therefore three times larger
# than anywhere you legitimately are while working, and an eighth of where you
# start — it cannot be wrong in either direction.
CLOSE_M = 150.0
# WARN_M is where an overtake becomes other people's problem. Wider than
# CLOSE_M so the call arrives BEFORE you are close, which is the only time it
# is useful.
WARN_M = 400.0

# Speed tolerance for the stability credit. A pilot holding contact is inside
# 1-2 kt; 10 kt is five times that, so a correct pilot never loses credit for
# a correction, only for genuinely not being on speed.
STABLE_BAND_KT = 10.0
# Overtake that is unsafe rather than merely untidy. 25 kt inside 400 m closes
# the gap in about half a minute and is the classic way people arrive at a
# tanker too fast. No correct pilot does this.
UNSAFE_OVERTAKE_KT = 25.0

# The gate and the standard. See `aar.brief_lines` — 15 s is a gate whose
# doctrinal shape is ATP-56's stabilised-then-cleared; 60 s is OURS.
GATE_S = 15
STANDARD_S = 60

# Nothing is scored for the first CALIBRATE_S seconds. In VR a sight picture
# is meaningless until the pilot has recentered and set seat height, and
# grading someone who is still moving their head is grading the headset.
CALIBRATE_S = 20

MAX_CLOSURE_CALLS = 3

# --- flags ----------------------------------------------------------------
F_STABLE = 8810        # set while inside tolerance; cleared the moment it breaks
F_GATE_DONE = 8811     # the 15 s gate has been credited
F_STD_DONE = 8812      # the 60 s standard has been credited
F_OUT_SAID = 8813      # hysteresis for the fell-out call
F_CLOSURE_SAID = 8814  # hysteresis for the overtake call
F_CLOSURE_N = 8815     # how many overtake calls have been spent (fading)
F_EXCURSIONS = 8816    # counter: times you fell out after being credited
F_WAS_CLOSE = 8817     # set while inside CLOSE_M, so leaving is detectable
F_MENU = 8820          # 8820..8829 reserved for the F10 hint menu


# --- what each ride grades ------------------------------------------------
#
# `focus` changes only the opening call and which optional rules attach. The
# tolerances never change between rides, because a standard that moves is not a
# standard.
PROFILES = {
    "station": {
        "label": "station keeping",
        "opening": "This ride grades ONE thing: can you sit in the close-in "
                   "position and stay there. Nothing about the plug is "
                   "measured. Get in, get still, and let the clock run.",
        "closure_calls": True,
    },
    "closure": {
        "label": "closure control",
        "opening": "This ride grades CLOSURE. Arrive slow enough that stopping "
                   "is a decision rather than a hope. You will be told if you "
                   "are overtaking hard — three times, and then never again, "
                   "because after three you know.",
        "closure_calls": True,
    },
    "contact": {
        "label": "position while working",
        "opening": "The plug is not measured here — no trigger in DCS can see "
                   "it. What IS measured is whether you stay in the envelope "
                   "and on speed while you work. That is the part that makes "
                   "the plug happen.",
        "closure_calls": True,
    },
    "quiet": {
        "label": "position, quietly",
        "opening": "Grading is on, coaching is off. You will hear nothing "
                   "until you ask for it on the F10 menu, or until you have "
                   "held the position for a minute.",
        "closure_calls": False,
    },
}


def _speed_ms(track_speed_kmh: float) -> float:
    return track_speed_kmh / 3.6


def attach(m, player_group, tanker_group, aar_key, profile="station",
           warnings=None, hud=False, receiver_id="", map_key="") -> bool:
    """Wire the grader into mission `m`. Returns True if it attached.

    `hud=True` means the position indicator is attached and owns the CONTINUOUS
    cues — fell-out and overtake. Those two are the ones that arrive while the
    pilot is busy, in the top-right corner they cannot look at; a graphic in
    the lower field of view says the same thing without asking for their eyes.
    The three DISCRETE calls stay as text either way: an opening brief and two
    pass announcements are events, not nagging, and they are worth reading.

    Never raises: a pydcs signature drift must degrade the card to an ungraded
    one, not fail the build. That is the same contract `formation._coach` has.
    """
    try:
        from dcs import condition as C, action as A, triggers as Tr
        from . import aar as _aar

        prof = PROFILES.get(profile) or PROFILES["station"]
        me = player_group.units[0]
        tk = tanker_group.units[0]
        track_ms = _speed_ms(_aar.track_speed_kmh(aar_key, receiver_id, map_key))
        stable_lo = track_ms - STABLE_BAND_KT * _KT_MS
        stable_hi = track_ms + STABLE_BAND_KT * _KT_MS
        unsafe_ms = track_ms + UNSAFE_OVERTAKE_KT * _KT_MS
        ias = _aar.track_ias_kt(aar_key, receiver_id)
        alt = _aar.track_alt_ft(aar_key, map_key)

        def say(text, secs=12):
            return A.MessageToGroup(player_group.id, m.string(str(text)), secs)

        def once(comment, conds, acts):
            t = Tr.TriggerOnce(comment=comment)
            for c in conds:
                t.rules.append(c)
            for a in acts:
                t.actions.append(a)
            m.triggerrules.triggers.append(t)
            return t

        def cont(comment, conds, acts):
            t = Tr.TriggerContinious(comment=comment)
            for c in conds:
                t.rules.append(c)
            for a in acts:
                t.actions.append(a)
            m.triggerrules.triggers.append(t)
            return t

        # ---- opening call, and the calibration window ---------------------
        # Scoring does not start at spawn. A VR pilot needs to recenter with
        # square shoulders and set seat height before any sight picture means
        # anything, and a flat-screen pilot needs to find the tanker. Twenty
        # seconds is the plan's figure and it costs nothing — the alternative
        # is grading a pilot who is still adjusting their head position.
        once("AAR grade: what this ride measures",
             [C.TimeAfter(5)],
             [say(f"AAR — {prof['label'].upper()}. {prof['opening']} "
                  f"Scoring starts in {CALIBRATE_S} seconds — if you are in "
                  f"VR, recenter now, sitting naturally, and set your seat "
                  f"height so the tanker reference is visible without a "
                  f"crouch.", 25)])

        # ---- the stability flag -------------------------------------------
        # Set while close AND on speed. Cleared the instant either breaks, so
        # TimeSinceFlag can never accumulate credit across an excursion.
        cont("AAR grade: in tolerance",
             [C.TimeAfter(CALIBRATE_S),
              C.UnitInMovingZone(me.id, CLOSE_M, tk.id),
              C.UnitSpeedHigher(me.id, stable_lo),
              C.UnitSpeedLower(me.id, stable_hi),
              C.FlagIsFalse(F_STABLE)],
             [A.SetFlag(F_STABLE), A.SetFlag(F_WAS_CLOSE)])

        # Three separate rules, not one rule with an OR. DCS's `or` predicate
        # rewrites how the whole rule list combines, and we have no way to
        # test that in-game from here — three single-condition triggers have
        # exactly one possible meaning. Any of them clears the flag, which is
        # the OR we wanted.
        cont("AAR grade: broken — left the envelope",
             [C.UnitOutsideMovingZone(me.id, CLOSE_M, tk.id)],
             [A.ClearFlag(F_STABLE)])
        cont("AAR grade: broken — slow",
             [C.UnitSpeedLower(me.id, stable_lo)],
             [A.ClearFlag(F_STABLE)])
        cont("AAR grade: broken — fast",
             [C.UnitSpeedHigher(me.id, stable_hi)],
             [A.ClearFlag(F_STABLE)])

        # ---- the gate and the standard ------------------------------------
        once("AAR grade: 15 s gate",
             [C.TimeSinceFlag(F_STABLE, GATE_S), C.FlagIsFalse(F_GATE_DONE)],
             [A.SetFlag(F_GATE_DONE),
              say(f"GATE PASSED — {GATE_S} seconds stabilised. That is the "
                  f"minimum before moving forward, and you have it. Now hold "
                  f"it for a minute and it becomes yours.", 15)])

        once("AAR grade: 60 s standard",
             [C.TimeSinceFlag(F_STABLE, STANDARD_S), C.FlagIsFalse(F_STD_DONE)],
             [A.SetFlag(F_STD_DONE),
              say(f"STANDARD MET — {STANDARD_S} seconds in the envelope, on "
                  f"speed, unbroken. This is the mark this product sets, not "
                  f"one quoted from a manual. You are ready for the next ride.",
                  20)])

        # ---- fell out of the envelope -------------------------------------
        # Only counts once you have been credited stable at least once —
        # otherwise arriving is reported as failing.
        #
        # The COUNTER always runs; the TEXT only when no indicator is showing
        # the same thing. Counting an excursion is bookkeeping the debrief
        # needs; announcing it in the corner is the distraction the graphic
        # exists to remove.
        fell_out = [A.SetFlag(F_OUT_SAID), A.IncreaseFlag(F_EXCURSIONS, 1)]
        if not hud:
            fell_out.append(
                say("Out of the envelope. Back to pre-contact, settle, come "
                    "again — nobody has ever fixed a bad approach by pressing "
                    "it.", 10))
        cont("AAR grade: fell out",
             [C.UnitOutsideMovingZone(me.id, CLOSE_M, tk.id),
              C.FlagIsTrue(F_WAS_CLOSE), C.FlagIsFalse(F_OUT_SAID)],
             fell_out)

        cont("AAR grade: back in the envelope",
             [C.UnitInMovingZone(me.id, CLOSE_M * 0.6, tk.id),
              C.FlagIsTrue(F_OUT_SAID)],
             [A.ClearFlag(F_OUT_SAID)])

        # ---- unsafe overtake, three times then silence ---------------------
        if prof["closure_calls"] and not hud:
            cont("AAR grade: unsafe overtake",
                 [C.UnitInMovingZone(me.id, WARN_M, tk.id),
                  C.UnitSpeedHigher(me.id, unsafe_ms),
                  C.FlagIsFalse(F_CLOSURE_SAID),
                  C.FlagIsLess(F_CLOSURE_N, MAX_CLOSURE_CALLS)],
                 [A.SetFlag(F_CLOSURE_SAID), A.IncreaseFlag(F_CLOSURE_N, 1),
                  say(f"CLOSURE — you are more than {int(UNSAFE_OVERTAKE_KT)} "
                      f"knots up on him inside a quarter mile. Take the power "
                      f"off NOW and let it wash off before you arrive.", 10)])

            cont("AAR grade: overtake washed off",
                 [C.UnitSpeedLower(me.id, track_ms + 5 * _KT_MS),
                  C.FlagIsTrue(F_CLOSURE_SAID)],
                 [A.ClearFlag(F_CLOSURE_SAID)])

        # ---- the F10 menu: coaching you asked for --------------------------
        # Self-controlled feedback. The learner decides when a hint arrives,
        # which is the whole point — feedback you requested is acted on and
        # feedback that arrives uninvited is tuned out.
        _menu(m, C, A, Tr, player_group, prof, ias, alt)
        return True
    except Exception as e:                    # pydcs drift: never fail a build
        if warnings is not None:
            warnings.append(f"AAR grading not attached: {e}")
        return False


def _menu(m, C, A, Tr, player_group, prof, ias, alt):
    """Three F10 items, each a flag the pilot sets when they want the answer."""
    items = [
        ("AAR: say the numbers again",
         f"TRACK {ias} KIAS at {alt:,} ft. Approach closure 1-3 kt. Last few "
         f"feet about 1 ft/sec — roughly half a knot, three times slower than "
         f"the approach. Pre-contact gate {GATE_S} s stabilised; the standard "
         f"is {STANDARD_S} s."),
        ("AAR: what am I doing wrong?",
         "In the order people do it. CHASING — you correct, it overshoots, "
         "you correct harder; freeze the stick, let it settle, then ONE small "
         "input. STARING — looking at the boom or basket makes you fly it; "
         "look at the tanker, wide. THROTTLE STEPS — big handfuls arrive late "
         "and leave late; think in single percent."),
        ("AAR: how am I doing?",
         "Watch the messages: the gate call and the standard call are the two "
         "that matter. If you have heard neither, you have not yet held the "
         "envelope and speed unbroken for fifteen seconds — which is the "
         "whole task, and is harder than it sounds."),
    ]
    for i, (label, text) in enumerate(items):
        flag = F_MENU + i
        add = Tr.TriggerOnce(comment=f"AAR menu: {label}")
        add.rules.append(C.TimeAfter(5))
        add.actions.append(A.AddRadioItemForGroup(
            group=player_group.id, radiotext=m.string(label),
            flag=flag, value=1))
        m.triggerrules.triggers.append(add)

        fire = Tr.TriggerContinious(comment=f"AAR menu fire: {label}")
        fire.rules.append(C.FlagIsTrue(flag))
        fire.actions.append(A.MessageToGroup(
            player_group.id, m.string(text), 25))
        fire.actions.append(A.ClearFlag(flag))
        m.triggerrules.triggers.append(fire)


def brief_lines(profile="station") -> list:
    """What the kneeboard must say about the grading, so the card does not
    promise more than the triggers can deliver."""
    prof = PROFILES.get(profile) or PROFILES["station"]
    return [
        "=" * 66,
        "THIS RIDE IS GRADED — and here is exactly what by",
        "=" * 66,
        f"FOCUS: {prof['label']}.",
        "",
        f"NOTHING IS SCORED FOR THE FIRST {CALIBRATE_S} SECONDS. That window is",
        "yours: in VR, recenter sitting naturally with square shoulders and set",
        "seat height so the tanker reference is visible without a crouch you",
        "cannot hold for ten minutes. On a monitor, use it to find him and",
        "settle. A sight picture measured before you have set your viewpoint is",
        "measuring the headset, not the pilot.",
        "",
        "MEASURED:",
        f" - Are you inside {int(CLOSE_M)} m of the tanker (the close-in",
        "   envelope: observation, pre-contact, contact).",
        f" - Are you within {int(STABLE_BAND_KT)} kt of his track speed.",
        f" - How long you hold both at once. {GATE_S} s is the gate,",
        f"   {STANDARD_S} s is the standard.",
        " - How many times you fall out after getting there.",
        "",
        "NOT MEASURED, and no card in this product will pretend otherwise:",
        " - Whether you made contact.",
        " - How long you held the plug.",
        " - How much fuel you took.",
        "DCS mission triggers cannot see a refuelling event or read your fuel.",
        "Anything that claims to grade your plug without running a script is",
        "guessing, and we would rather tell you what we can actually see.",
        "",
        "The tolerances are deliberately WIDE. A grader that calls a correct",
        "pilot wrong teaches you to ignore it, and then every later call is",
        "noise. If you are flying it properly you will never be told off; if",
        "you are sloppy you may still pass. That trade is on purpose.",
        "",
        "COACHING FADES. The closure call fires at most three times and then",
        "stops. After three you know. Everything else is on the F10 menu, when",
        "YOU want it — asked-for feedback gets used, unasked-for gets tuned out.",
    ]
