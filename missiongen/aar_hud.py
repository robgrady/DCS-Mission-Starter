"""The AAR position indicator: a graphic, in the middle of the screen, instead
of text in the corner you cannot look at.

WHY THIS REPLACED TEXT. DCS renders `MessageToGroup` in the top-right corner,
and that corner is unreadable exactly when it matters — you are twenty feet
from a tanker with your eyes locked on a reference, and the one thing you must
not do is look away. Text there is not feedback, it is a distraction that
arrives dressed as help.

`PictureToGroup` is a native Mission Editor action — a PNG from the mission's
own resources, placed by alignment and sized as a percentage of the window. No
Lua, no script inside the .miz. So the coaching can be a shape in the lower
field of view that you read with peripheral vision, which is how you read an
instrument you are not staring at.

WHAT IT SHOWS, AND THE ONE THING IT REFUSES TO.

  * FORE/AFT — the receiver's speed against the tanker's known constant track
    speed. On a straight leg that IS the closure rate, and fore/aft is the
    axis the throttle owns: the research calls it the least understood part of
    the task.
  * HIGH/LOW — `UnitAltitudeHigher/Lower` against the track altitude.
  * LEFT/RIGHT — **never.** The envelope check is a SPHERE centered on the
    tanker unit; it cannot tell abeam from astern. Drawing a lateral cue would
    make the graphic look complete and make it a liar, and a training aid that
    invents a cue is worse than one that admits a gap. Every card says so.

HOW IT REFRESHES. Not on a timer. Each state owns an ARM flag: entering the
state fires its trigger, which draws the picture, disarms itself and re-arms
every other state. Stay put and nothing redraws; change and exactly one
trigger fires. That is the same edge-triggered discipline the text calls
already used, for the same reason — a continuous DCS trigger re-evaluates
every second, and a picture that redraws every second is a strobe.

Flag block 8840-8859. `aar_grade` owns 8810-8839.
"""
from __future__ import annotations

from pathlib import Path

ASSET_DIR = Path(__file__).parent / "data" / "hud"

_KT_MS = 0.514444
_FT_M = 0.3048

# --- how far off is "off" --------------------------------------------------
#
# Tighter than the GRADER's bands on purpose. The grader must never call a
# correct pilot wrong, so its tolerances are wide; the indicator is guidance
# rather than a verdict, so it can lead. A pilot holding contact is inside
# 1-2 kt and a few feet, so these still never light up on a good position.
FORE_BAND_KT = 5.0        # grader's stability band is 10
VERT_BAND_FT = 200.0
# The safety state. Same threshold the grader uses, so the picture and the
# (retained) spoken warning cannot disagree.
UNSAFE_OVERTAKE_KT = 25.0

# How long a picture stays up. Long, because it is replaced by the next state
# rather than expiring — an indicator that vanishes mid-approach is worse than
# no indicator. `clearview` makes each new picture replace the last.
HOLD_S = 900

# --- placement and size, from flying it ------------------------------------
#
# v1.75.0 put this bottom-center at 22% and both were wrong in the cockpit.
#
# BOTTOM-CENTER is where the nose is. You are looking up and slightly left at a
# tanker, and a panel directly under your gaze competes with the sight picture
# instead of sitting beside it. LEFT-CENTER is where a naval aviator's eye
# already goes — it is where the meatball lives on an approach — so the glance
# is one the muscle memory already owns.
#
# 22% was roughly double what it needed to be. 10% is about half, which was the
# top of the range asked for; the art below was redrawn for that size rather
# than merely scaled, because shrinking a card with three lines of prose on it
# produces three lines of nothing.
HORZ = "Left"
VERT = "Center"
SIZE_PCT = 10

# --- how often it may redraw -----------------------------------------------
#
# The arm/re-arm design only fires on a state CHANGE, which is not the same as
# firing rarely: a pilot sitting on a band boundary crosses it several times a
# second and the picture strobes. So a state change is necessary but no longer
# sufficient — nothing may draw until MIN_REDRAW_S has passed since the last
# draw, which turns a boundary flutter into one honest update every few
# seconds. The cost is that a genuine change can wait up to MIN_REDRAW_S to
# appear, and that is the right trade: an indicator you can read late beats one
# you cannot read at all.
MIN_REDRAW_S = 4

# --- flags -----------------------------------------------------------------
F_ARM = 8840              # 8840..8850, one ARM flag per state
F_DRAWN = 8854            # restarted on every draw; gates MIN_REDRAW_S
F_HUD_OFF = 8855          # F10 toggle: pilot turned the indicator off

# --- the states ------------------------------------------------------------
# (key, fore, vert) where fore/vert are -1 / 0 / +1, plus the two specials.
CELLS = [(f, v) for v in (1, 0, -1) for f in (-1, 0, 1)]
STATES = ([f"f{f}_v{v}" for f, v in CELLS] + ["out", "breakoff"])


def asset(name: str) -> Path:
    return ASSET_DIR / f"aar_hud_{name}.png"


def profiles_with_hud() -> set:
    """Which grading profiles get the indicator.

    `quiet` does not: that is the qualification and the night ride, where the
    plan's own design calls for silent evaluation. Assistance that never fades
    is assistance the pilot learns to fly instead of the airplane.
    """
    return {"station", "closure", "contact"}


def attach(m, player_group, tanker_group, aar_key, profile="station",
           warnings=None, receiver_id="", map_key="") -> bool:
    """Wire the indicator in. Returns True if it attached.

    Never raises, same contract as `aar_grade.attach`: a missing asset or a
    pydcs drift degrades the ride to text-only, it does not fail the build.
    """
    try:
        if profile not in profiles_with_hud():
            return False
        from dcs import condition as C, action as A, triggers as Tr
        from . import aar as _aar, aar_grade as _grade

        missing = [s for s in STATES if not asset(s).is_file()]
        if missing:
            raise FileNotFoundError(
                f"indicator art missing: {missing[:3]} — run "
                f"scripts/build_aar_hud.py")

        me = player_group.units[0]
        tk = tanker_group.units[0]
        track_ms = _aar.track_speed_kmh(aar_key, receiver_id, map_key) / 3.6
        track_m = _aar.track_alt_m(aar_key, map_key)

        def spd(delta_kt):
            return track_ms + delta_kt * _KT_MS

        def alt(delta_ft):
            return track_m + delta_ft * _FT_M

        # Register every picture once; the ResourceKey is what the action
        # stores, and DCS carries the file inside the .miz.
        res = {s: m.map_resource.add_resource_file(str(asset(s)))
               for s in STATES}

        idx = {s: i for i, s in enumerate(STATES)}

        def show(state):
            # `.value`, NOT the enum member. pydcs stores whatever it is
            # handed straight into the Lua table, and an Enum stringifies as
            # "HorzAlignment.Center" — an undefined variable that DCS refuses
            # to compile. The mission built fine and would not have OPENED.
            # Caught only because two suites re-read the generated .miz.
            return A.PictureToGroup(
                player_group, res[state], HOLD_S,
                True,                     # clearview: replace, never stack
                0,
                getattr(A.PictureAction.HorzAlignment, HORZ).value,
                getattr(A.PictureAction.VertAlignment, VERT).value,
                SIZE_PCT, A.PictureAction.SizeUnits.WindowSize.value)

        def rearm(state):
            """Disarm this state, arm every other, and restart the redraw clock.

            Clear-then-set on F_DRAWN is what restarts `TimeSinceFlag`; setting
            an already-set flag does nothing, so the clear is not redundant.
            Same pattern the grader uses for its stability timer.
            """
            acts = [A.ClearFlag(F_ARM + idx[state])]
            acts += [A.SetFlag(F_ARM + i) for s, i in idx.items()
                     if s != state]
            acts += [A.ClearFlag(F_DRAWN), A.SetFlag(F_DRAWN)]
            return acts

        # everything armed at start, so the first state entered draws
        opening = Tr.TriggerOnce(comment="AAR HUD: arm")
        opening.rules.append(C.TimeAfter(_grade.CALIBRATE_S))
        for i in idx.values():
            opening.actions.append(A.SetFlag(F_ARM + i))
        opening.actions.append(A.SetFlag(F_DRAWN))
        m.triggerrules.triggers.append(opening)

        def rule(state, conds):
            t = Tr.TriggerContinious(comment=f"AAR HUD: {state}")
            t.rules.append(C.FlagIsTrue(F_ARM + idx[state]))
            t.rules.append(C.FlagIsFalse(F_HUD_OFF))
            # The rate limit. A state change is necessary to redraw; this makes
            # it not sufficient, so a boundary flutter cannot strobe.
            t.rules.append(C.TimeSinceFlag(F_DRAWN, MIN_REDRAW_S))
            for c in conds:
                t.rules.append(c)
            t.actions.append(show(state))
            for a in rearm(state):
                t.actions.append(a)
            m.triggerrules.triggers.append(t)

        # --- the safety state, checked first and drawn loudest --------------
        rule("breakoff", [
            C.UnitInMovingZone(me.id, _grade.WARN_M, tk.id),
            C.UnitSpeedHigher(me.id, spd(UNSAFE_OVERTAKE_KT)),
        ])

        # --- out of the working envelope -----------------------------------
        rule("out", [C.UnitOutsideMovingZone(me.id, _grade.CLOSE_M, tk.id)])

        # --- the nine position cells ---------------------------------------
        for f, v in CELLS:
            conds = [C.UnitInMovingZone(me.id, _grade.CLOSE_M, tk.id),
                     C.UnitSpeedLower(me.id, spd(UNSAFE_OVERTAKE_KT))]
            if f > 0:
                conds.append(C.UnitSpeedHigher(me.id, spd(FORE_BAND_KT)))
            elif f < 0:
                conds.append(C.UnitSpeedLower(me.id, spd(-FORE_BAND_KT)))
            else:
                conds.append(C.UnitSpeedHigher(me.id, spd(-FORE_BAND_KT)))
                conds.append(C.UnitSpeedLower(me.id, spd(FORE_BAND_KT)))
            if v > 0:
                conds.append(C.UnitAltitudeHigher(me.id, alt(VERT_BAND_FT)))
            elif v < 0:
                conds.append(C.UnitAltitudeLower(me.id, alt(-VERT_BAND_FT)))
            else:
                conds.append(C.UnitAltitudeHigher(me.id, alt(-VERT_BAND_FT)))
                conds.append(C.UnitAltitudeLower(me.id, alt(VERT_BAND_FT)))
            rule(f"f{f}_v{v}", conds)

        # --- the pilot's off switch ----------------------------------------
        # Self-controlled, like the hints. Somebody who finds it distracting
        # must be able to kill it without leaving the mission.
        add = Tr.TriggerOnce(comment="AAR HUD: menu toggle")
        add.rules.append(C.TimeAfter(5))
        add.actions.append(A.AddRadioItemForGroup(
            group=player_group.id,
            radiotext=m.string("AAR: turn the position indicator OFF"),
            flag=F_HUD_OFF, value=1))
        m.triggerrules.triggers.append(add)
        return True
    except Exception as e:
        if warnings is not None:
            warnings.append(f"AAR indicator not attached: {e}")
        return False


def brief_lines() -> list:
    """What the kneeboard says about the graphic, including its blind axis."""
    return [
        "=" * 66,
        "THE POSITION INDICATOR — left of your screen, not the corner",
        "=" * 66,
        "A small panel on the LEFT, level with your eye line — roughly where a",
        "naval aviator already looks for the ball. Read it with the edge of",
        "your vision; you should never have to leave the tanker to use it.",
        "",
        "HOW TO READ IT, and it is one glance:",
        " - THE BALL against the two datum bars is your HEIGHT. Above the bars",
        f"   you are high, below them you are low, between them you are within",
        f"   {int(VERT_BAND_FT)} ft of the track. Same idea as the meatball, same",
        "   glance.",
        " - THE CHEVRONS are FORE/AFT. Pointing up at the top: you are CLOSING.",
        "   Pointing down at the bottom: you are FALLING BACK. No chevrons: you",
        f"   are within {int(FORE_BAND_KT)} kt of his speed.",
        " - THE WORD backs up the fore/aft state, because that is the axis your",
        "   throttle has to act on. FAST means overtaking, SLOW means dropping",
        "   back. Only when both axes are clean does it say HOLD, in green.",
        " - A RED PANEL WITH THREE ARROWS and POWER OFF is the safety state:",
        "   more than 25 kt of overtake inside a quarter mile. Act on that one",
        "   immediately.",
        "",
        f"IT UPDATES AT MOST ONCE EVERY {MIN_REDRAW_S} SECONDS, deliberately. An",
        "indicator that redrew the instant anything changed would strobe every",
        "time you sat on a band boundary, which is most of the time. The cost",
        "is that a real change can take a moment to appear — worth it, because",
        "a flickering panel is one you learn to ignore.",
        "",
        "IT DOES NOT SHOW LEFT/RIGHT, and that is deliberate rather than",
        "unfinished. The mission knows how far you are from the tanker, not",
        "which side you are on — the check is a sphere. We could draw a",
        "lateral arrow and it would be guessing, and a training aid that",
        "invents a cue is worse than one that admits a gap. Your lateral",
        "position comes from the sight picture, the way it does in the jet.",
        "",
        "Color is never the only cue: every state is also a shape, a position",
        "and a word, so it reads the same if you are color-blind or the",
        "contrast is poor.",
        "",
        "TURN IT OFF from the F10 menu whenever you like. It does not appear",
        "at all on the qualification ride — that one is silent by design.",
    ]


# --------------------------------------------------------------------------- #
# Helper gates — the floating rings DCS's own training missions use
# --------------------------------------------------------------------------- #
GATE_COUNT = 3
GATE_SPACING_M = 3704.0        # 2 nm between gates
GATE_BELOW_M = 305.0           # a thousand feet under the track, like the join


def attach_gates(m, player_group, tanker_group, aar_key, warnings=None,
                 map_key="") -> bool:
    """Lay helper gates on the run-in to the tanker, for the RENDEZVOUS ride.

    ONE RIDE ONLY, and the reason matters. Ride 7 is the one about finding him
    and arriving already matched — a path in space is exactly the right aid for
    that. On the close-in rides it would be the wrong aid entirely: the whole
    syllabus argues you should be flying the TANKER, and a pilot chasing a ring
    is a pilot who has swapped one thing to stare at for another.

    NOT VERIFIED IN-SIM. Everything else in the Academy is either measured out
    of a generated file or quoted; this is the one piece whose in-game
    appearance nobody here has seen, and it is wrapped so a wrong signature
    costs the ride its gates and nothing else.
    """
    try:
        import math
        from dcs import action as A, condition as C, triggers as Tr
        from . import aar as _aar
        from .dressing import _offset as _off

        tk = tanker_group.units[0]
        # The tanker's ROUTE, not its unit heading — the same field that put
        # the pre-contact air start abeam instead of astern. Gates laid off a
        # heading of 0.0 run due south of a tanker flying anywhere else.
        pts = list(getattr(tanker_group, "points", []) or [])
        if len(pts) >= 2 and (pts[1].position.x - pts[0].position.x
                              or pts[1].position.y - pts[0].position.y):
            hdg = math.degrees(math.atan2(pts[1].position.y - pts[0].position.y,
                                          pts[1].position.x - pts[0].position.x)) % 360.0
        else:
            hdg = math.degrees(getattr(tk, "heading", 0.0) or 0.0) % 360.0
        alt = _aar.track_alt_m(aar_key, map_key) - GATE_BELOW_M

        t = Tr.TriggerOnce(comment="AAR gates: the run-in to the tanker")
        t.rules.append(C.TimeAfter(10))
        for i in range(GATE_COUNT, 0, -1):
            pos = _off(tk.position, GATE_SPACING_M * i, (hdg + 180.0) % 360.0)
            # x/z are the ground plane and y is altitude in the gate action,
            # while pydcs positions carry (x north, y east) — so `position.y`
            # is the gate's Z. Getting this pair the wrong way round puts the
            # gates in the sea at right angles to the run-in.
            t.actions.append(A.ShowHelperGate(x=pos.x, z=pos.y, y=alt,
                                              course=hdg))
        m.triggerrules.triggers.append(t)
        return True
    except Exception as e:
        if warnings is not None:
            warnings.append(f"AAR helper gates not attached: {e}")
        return False


def gate_brief_lines() -> list:
    return [
        "=" * 66,
        "HELPER GATES — a path, for this ride only",
        "=" * 66,
        "Three gates lead back along the tanker's track, stepped down, to the",
        "position you are joining from. Fly through them and you will arrive",
        "behind and below him at roughly the right speed.",
        "",
        "THEY ARE ON THIS RIDE AND NO OTHER, on purpose. Finding him is a",
        "navigation problem and a path in space is the right tool for it.",
        "Everything from observation forward is a FORMATION problem, and a",
        "pilot chasing a floating ring has simply swapped one thing to stare",
        "at for another — which is the failure mode this whole syllabus is",
        "built against.",
        "",
        "Once you are at observation, forget they existed and fly the tanker.",
    ]
