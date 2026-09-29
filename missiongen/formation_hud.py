"""The formation position ladder: a card you glance at, instead of a sentence
you have to read.

WHAT WAS WRONG
--------------
Rob: "The formation training sucks. It has a continuous display of information
that happens quickly that is too difficult to watch and navigate."

The coach was three lines of `MessageToGroup`. One fired when you left a sphere
around lead, one when you came back. Every property of that design is wrong for
the task:

  * BINARY — in or out. Ten metres and a hundred read identically.
  * DIRECTIONLESS — it never said which axis, or which way.
  * LATE — it spoke only at the boundary, when the error is already big, so the
    correction has to be big too. A boundary alarm does not merely fail to
    prevent the novice oscillation `formation.py` describes; it CAUSES it.
  * IN THE WRONG PLACE — top-right corner text, which needs foveal vision and
    the language center at the one moment both are committed to looking at
    another airplane thirty metres away.

WHAT THIS IS
------------
A COMMAND display. Each card names the single input to make now — ADD POWER,
EASE OFF, COME UP — rather than reporting a condition and leaving the pilot to
work out the fix. That translation from state to action is precisely the step a
novice cannot spare attention for, and a status display makes them do it in the
air. Eight cards, one at a time, on the left at eye level — the side lead is
already on — read with peripheral vision.

THE IMPORTANT CARD IS `good`
----------------------------
STEADY, drawn when you are out of position but already closing at a sensible
rate: the correction you have in is working, so add nothing. That cue is what
separates a wingman who settles from one who porpoises, and no volume of "you
are out of position" can ever produce it. It is drawn as a tick rather than an
arrow for exactly that reason — every other glyph on the set means *move*.

ONE AXIS AT A TIME, BECAUSE THE BRIEF SAYS SO
---------------------------------------------
`formation.brief_lines()` has taught "Fix ONE at a time" since v1.60, and the
old coach then handed you an undifferentiated "out of position". Here fore/aft
outranks height — throttle is the axis that owns the error, per the module
docstring — so the height cards appear only once fore/aft is clean. The pilot
is never shown two problems.

WHAT IT REFUSES TO DRAW
-----------------------
Left/right. The only range check the Mission Editor gives us is a SPHERE around
lead: it cannot tell abeam from astern. A lateral arrow would look complete and
be a guess, and a training aid that invents a cue is worse than one that admits
a gap. `aar_hud` refuses on the same ground. Lateral comes from the sight
picture, as it does in the airplane.

AND WHEN IT REFUSES THE WHOLE SPEED AXIS
----------------------------------------
The fore/aft and height cards compare you against LEAD'S SCRIPTED speed and
altitude, which is honest only while those are constant. On the energy sortie
lead deliberately climbs, descends and changes speed, so the reference moves and
the cue would lie. Rather than gate every card on which leg lead is flying, that
profile gets the RANGE-ONLY ladder — which is true regardless, because a moving
zone measures range and nothing else. It is also the right pedagogy: the energy
sortie teaches anticipation, and a speed cue would do the anticipating for you.

Flag block 8760-8779. NOT 8860 — that is `timing_coach`'s, and a coached
formation ride that also carried a timing card would have quietly shared arm
flags with it. The handbook's registry is the only reason that was caught
before it shipped; add a new block to it, and to
`test_the_flag_blocks_do_not_overlap`, before using one.
"""
from __future__ import annotations

import math
from pathlib import Path

ASSET_DIR = Path(__file__).parent / "data" / "formation_hud"

_KT_MS = 0.514444
_FT_M = 0.3048

# The eight cards, drawn by scripts/build_formation_hud.py.
STATES = ["danger", "ease", "hold", "high", "low", "power", "good", "lost"]

# --- placement -------------------------------------------------------------
#
# LEFT, VERTICALLY CENTERED — the same place and the same size as the AAR
# indicator, and that is the whole reason.
#
# v1.104.0 put this bottom-left at 9% on a human-factors argument: lead sits up
# and to the left, so a card under him is a short glance rather than a
# head-turn. Rob flew it and no card appeared at all, while the coach's text
# still arrived — so the triggers ran and the picture did not draw. Every other
# variable checked out (the art is the same mode and size as the AAR card, the
# resource map is correct, the actions target the player's group, and the
# mission's own start state satisfies the HOLD rule), which left the two values
# that differ from the one configuration this product has ever seen render in a
# cockpit: `Bottom` instead of `Center`, and 9 instead of 10.
#
# So this is now byte-for-byte the AAR indicator's placement. If the card still
# does not draw, the fault is not in these two numbers and we have spent
# nothing finding that out; if it does, the argument for bottom-left was worth
# less than the evidence for eye level — which is also where the AAR one ended
# up after cockpit feedback, and bottom-left in DCS is where the comms menu and
# the message log already live.
HORZ = "Left"
VERT = "Center"
SIZE_PCT = 10

# --- how often it may redraw ----------------------------------------------
#
# A state change is necessary to redraw and, on its own, not sufficient: a pilot
# sitting on a band boundary crosses it several times a second, and a card that
# redrew each time would strobe. Three seconds turns that flutter into one
# honest update. Shorter than the AAR indicator's four because formation
# corrections are quicker, and the two SAFETY states skip the limit entirely —
# a collision cue must never wait for a timer.
MIN_REDRAW_S = 3

# --- flags -----------------------------------------------------------------
F_ARM = 8760              # 8760..8767, one per state
F_DRAWN = 8768            # restarted on every draw; gates MIN_REDRAW_S
F_OFF = 8769              # F10 toggle: the pilot turned it off
F_LIVE = 8770             # you have been within range of lead at least once
F_SHOW = 8771             # F10: draw the card now


# --- the bands -------------------------------------------------------------
#
# Everything scales off the MAGNITUDE of the start offset, because that is the
# distance the correct position actually sits at. The slot is a SHELL, not a
# ball: too close is as wrong as too far, and on a sphere check that is the only
# honest way to say so.
def bands(start: str) -> dict:
    from .formation import START_OFFSETS
    dx, dy, ddown = START_OFFSETS.get(start, START_OFFSETS["route"])
    r = math.sqrt(dx * dx + dy * dy + (ddown * _FT_M) ** 2)
    return {
        "r": r,
        # 12 m is the check ride's own collision band; the cap keeps the rejoin
        # sortie from calling 800 m of clear air a near miss.
        "danger": max(12.0, min(120.0, 0.40 * r)),
        "slot_lo": 0.60 * r,
        "slot_hi": 1.55 * r,
        # 400 m floor: on fingertip, four times the offset is 117 m, and being
        # told you are LOST while sitting in route position is nonsense.
        "far": max(4.0 * r, 400.0),
        "speed_kt": {"fingertip": 5.0, "route": 8.0, "spread": 15.0}.get(start, 8.0),
        # Coarse on purpose. Lead's altitude wanders a little around the
        # scripted figure, and calling a good pilot wrong is worse than missing
        # the last twenty feet — which the sight picture owns anyway.
        "vert_ft": {"fingertip": 120.0, "route": 200.0, "spread": 400.0}.get(start, 200.0),
    }


def asset(name: str) -> Path:
    return ASSET_DIR / f"formation_hud_{name}.png"


def full_ladder(prof: dict) -> bool:
    """True when lead holds one speed and one altitude for the whole profile,
    which is what makes the fore/aft and height cards true."""
    return all(dft == 0 and dkt == 0 for _dh, _mins, dft, dkt in prof["legs"])


def profiles_with_hud() -> set:
    """Every coached profile. Not the check — that ride is silent by design,
    and an aid that never fades is one the pilot learns to fly instead of the
    airplane."""
    return {"route", "close", "energy", "rejoin", "takeoff", "precheck"}


def attach(m, player_group, lead_group, prof, ref_alt_m, ref_spd_kmh,
           warnings=None) -> str:
    """Wire the ladder in. Returns "full", "range" or "" (not attached).

    Never raises: a missing asset or pydcs drift degrades the sortie to the
    text coach, it does not fail the build.
    """
    try:
        from dcs import action as A
        from dcs import condition as C
        from dcs import triggers as Tr

        missing = [s for s in STATES if not asset(s).is_file()]
        if missing:
            raise FileNotFoundError(
                f"ladder art missing: {missing[:3]} — run "
                f"scripts/build_formation_hud.py")

        b = bands(prof["start"])
        me, lead = player_group.units[0], lead_group.units[0]
        full = full_ladder(prof)

        ref_ms = ref_spd_kmh / 3.6
        sb = b["speed_kt"] * _KT_MS
        # You fly the slot a step DOWN on lead, so the height reference is
        # lead's altitude less the step — not lead's altitude.
        from .formation import START_OFFSETS
        step_m = START_OFFSETS.get(prof["start"], (0, 0, 0))[2] * _FT_M
        ref_m = ref_alt_m - step_m
        vb = b["vert_ft"] * _FT_M

        # ALL OR NOTHING. Triggers go into a local list and reach the mission
        # only once the whole set has been built. pydcs's own
        # TriggerContinious.action_str() reads TriggerOnce.predicate at SAVE
        # time, so a set that is half attached when the API drifts does not
        # merely lose its coaching — it makes the mission unsaveable. Caught by
        # test_coaching_failure_never_fails_the_build, which is the only reason
        # that contract was ever real rather than accidental.
        pending = []
        res = {s: m.map_resource.add_resource_file(str(asset(s)))
               for s in STATES}
        idx = {s: i for i, s in enumerate(STATES)}

        def show(state):
            # `.value`, NOT the enum member: pydcs writes whatever it is handed
            # straight into the Lua, and an Enum stringifies to an undefined
            # variable that DCS refuses to compile. Same trap as aar_hud.
            return A.PictureToGroup(
                player_group, res[state], 900,
                True,                          # clearview: replace, never stack
                0,
                getattr(A.PictureAction.HorzAlignment, HORZ).value,
                getattr(A.PictureAction.VertAlignment, VERT).value,
                SIZE_PCT, A.PictureAction.SizeUnits.WindowSize.value)

        def rearm(state):
            acts = [A.ClearFlag(F_ARM + idx[state])]
            acts += [A.SetFlag(F_ARM + i) for s, i in idx.items() if s != state]
            # clear-then-set is what restarts TimeSinceFlag; setting an already
            # set flag does nothing, so the clear is not redundant.
            acts += [A.ClearFlag(F_DRAWN), A.SetFlag(F_DRAWN)]
            return acts

        n = 0

        def rule(state, conds, urgent=False, tag=""):
            nonlocal n
            t = Tr.TriggerContinious(
                comment=f"Formation ladder: {state}{tag}")
            t.rules.append(C.FlagIsTrue(F_ARM + idx[state]))
            t.rules.append(C.FlagIsFalse(F_OFF))
            t.rules.append(C.FlagIsTrue(F_LIVE))
            if not urgent:
                t.rules.append(C.TimeSinceFlag(F_DRAWN, MIN_REDRAW_S))
            for c in conds:
                t.rules.append(c)
            t.actions.append(show(state))
            for a in rearm(state):
                t.actions.append(a)
            pending.append(t)
            n += 1

        inside = lambda r: C.UnitInMovingZone(me.id, r, lead.id)        # noqa: E731
        outside = lambda r: C.UnitOutsideMovingZone(me.id, r, lead.id)  # noqa: E731
        fast = C.UnitSpeedHigher(me.id, ref_ms + sb)
        slow = C.UnitSpeedLower(me.id, ref_ms - sb)
        notfast = C.UnitSpeedLower(me.id, ref_ms + sb)
        notslow = C.UnitSpeedHigher(me.id, ref_ms - sb)
        high = C.UnitAltitudeHigher(me.id, ref_m + vb)
        low = C.UnitAltitudeLower(me.id, ref_m - vb)
        nothigh = C.UnitAltitudeLower(me.id, ref_m + vb)
        notlow = C.UnitAltitudeHigher(me.id, ref_m - vb)

        # everything armed at the start, so the first state entered draws
        arm = Tr.TriggerOnce(comment="Formation ladder: arm")
        arm.rules.append(C.TimeAfter(10))
        for i in idx.values():
            arm.actions.append(A.SetFlag(F_ARM + i))
        arm.actions.append(A.SetFlag(F_DRAWN))
        pending.append(arm)
        n += 1

        # The ladder does not go live until you have been within range of lead
        # once. Without this the capstone sortie draws REJOIN at you all the way
        # through the taxi, before there is any formation to be out of.
        live = Tr.TriggerOnce(comment="Formation ladder: go live")
        # the flag guard is belt and braces on a TriggerOnce, and it keeps the
        # invariant every moving-zone trigger in the product holds to: a guard
        # in the conditions, a flip in the actions.
        live.rules.append(C.FlagIsFalse(F_LIVE))
        live.rules.append(inside(b["far"]))
        live.actions.append(A.SetFlag(F_LIVE))
        pending.append(live)
        n += 1

        # --- safety first, and it never waits for the redraw timer ---------
        rule("danger", [inside(b["danger"])], urgent=True)
        rule("lost", [outside(b["far"])], urgent=True)

        too_close = [inside(b["slot_lo"]), outside(b["danger"])]
        in_slot = [inside(b["slot_hi"]), outside(b["slot_lo"])]
        too_far = [outside(b["slot_hi"]), inside(b["far"])]

        if full:
            # Too close: already opening is the correction working; anything
            # else needs the throttle back.
            rule("good", too_close + [slow], tag=" (opening)")
            rule("ease", too_close + [notslow], tag=" (closing in)")
            # In the slot: fore/aft first, height only once it is clean.
            rule("ease", in_slot + [fast], tag=" (overtaking)")
            rule("power", in_slot + [slow], tag=" (dropping back)")
            rule("high", in_slot + [notfast, notslow, high])
            rule("low", in_slot + [notfast, notslow, low])
            rule("hold", in_slot + [notfast, notslow, nothigh, notlow])
            # Too far: closing is the correction working.
            rule("good", too_far + [fast], tag=" (closing)")
            rule("power", too_far + [notfast], tag=" (not closing)")
        else:
            rule("ease", too_close)
            rule("hold", in_slot)
            rule("power", too_far)

        # --- the pilot's off switch ---------------------------------------
        off = Tr.TriggerOnce(comment="Formation ladder: menu toggle")
        off.rules.append(C.TimeAfter(5))
        off.actions.append(A.AddRadioItemForGroup(
            group=player_group.id,
            radiotext=m.string("FORMATION: turn the position ladder OFF"),
            flag=F_OFF, value=1))
        pending.append(off)
        n += 1

        # --- and a way to prove it is there --------------------------------
        #
        # v1.104.0 shipped a card nobody could see and it took a whole sortie to
        # find that out. This draws one on demand, so the question "is the
        # ladder rendering at all?" costs five seconds on the ramp instead of
        # twenty minutes in the air. It doubles as the recall for a pilot whose
        # card got cleared by something else's message.
        add = Tr.TriggerOnce(comment="Formation ladder: menu show")
        add.rules.append(C.TimeAfter(5))
        add.actions.append(A.AddRadioItemForGroup(
            group=player_group.id,
            radiotext=m.string("FORMATION: show the position ladder now"),
            flag=F_SHOW, value=1))
        pending.append(add)
        n += 1

        shown = Tr.TriggerContinious(comment="Formation ladder: show on request")
        shown.rules.append(C.FlagIsTrue(F_SHOW))
        shown.actions.append(show("hold"))
        shown.actions.append(A.ClearFlag(F_SHOW))
        # re-arm everything, so the next real state change redraws over it
        for i in idx.values():
            shown.actions.append(A.SetFlag(F_ARM + i))
        shown.actions.append(A.ClearFlag(F_DRAWN))
        shown.actions.append(A.SetFlag(F_DRAWN))
        pending.append(shown)
        n += 1
        m.triggerrules.triggers.extend(pending)
        return "full" if full else "range"
    except Exception as e:                      # pydcs drift: never fail a build
        if warnings is not None:
            warnings.append(f"formation ladder not attached: {e}")
        return ""


def brief_lines(prof: dict) -> list:
    """What the kneeboard says about the ladder, including its blind axis."""
    b = bands(prof["start"])
    full = full_ladder(prof)
    L = [
        "=" * 66,
        "THE POSITION LADDER — on your LEFT at eye level, not the corner",
        "=" * 66,
        "A small card on the left at eye level, the same side as lead, so",
        "reading it is a flick of the eye rather than a look away, and it sits",
        "clear of the comms menu and the message log. Read it with the",
        "edge of your vision. Every card names ONE input to make — that is the",
        "whole design. It never tells you what is wrong without telling you",
        "what to do about it.",
        "",
        "THE LADDER at the top is your RANGE on lead: CLOSE, SLOT, OUT, LOST.",
        f"  SLOT is {int(b['slot_lo'])}-{int(b['slot_hi'])} m from lead. Inside {int(b['danger'])} m is the collision band;",
        f"  past {int(b['far'])} m you are no longer in a formation.",
        "",
        "THE CARDS:",
        "  HOLD        green. In the slot, on speed, on height. Change nothing.",
        "  ADD POWER   you are out the back and not closing. Small, and early.",
        "  EASE OFF    you are closing on a position you are already in, or",
        "              inside it. Take the power out BEFORE you arrive.",
        "  STEADY      a tick, not an arrow, and the one people miss: you are",
        "              out of position but already closing at the right rate.",
        "              The correction you have in is working. ADD NOTHING —",
        "              putting a second correction on top of a good one is how",
        "              the fore-and-aft oscillation starts.",
        "  COME UP /   the ball is off the datum bars. Only ever shown once",
        "  COME DOWN   fore/aft is already clean: one axis at a time.",
        "  OPEN OUT    red. You are inside the collision band. Do it now.",
        "  REJOIN      you have lost the formation. Get back to a position you",
        "              can see him from, then rejoin.",
        "",
        f"IT UPDATES AT MOST ONCE EVERY {MIN_REDRAW_S} SECONDS, on purpose — a card that",
        "redrew the instant anything changed would strobe every time you sat on",
        "a boundary, which is most of the time. OPEN OUT and REJOIN are exempt;",
        "a safety cue never waits for a timer.",
        "",
        "IT DOES NOT SHOW LEFT/RIGHT, and that is deliberate rather than",
        "unfinished. The mission knows how FAR you are from lead, not which",
        "side you are on — the check is a sphere. Drawing a lateral arrow would",
        "make the card look complete and make it a liar. Your lateral position",
        "comes from the sight picture, the way it does in the jet.",
        "",
        "Color is never the only cue: every card is also a shape, a ladder rung",
        "and a word, so it reads the same if you are color-blind.",
        "",
        "CAN'T SEE IT? F10 -> 'FORMATION: show the position ladder now' draws one",
        "immediately, on the ramp, before you have to go and find out in the air.",
        "Don't want it? F10 -> 'FORMATION: turn the position ladder OFF'.",
    ]
    if not full:
        L += [
            "",
            "THIS SORTIE RUNS THE RANGE-ONLY LADDER — CLOSE / SLOT / OUT / LOST",
            "and nothing else. Lead changes speed and altitude on this ride, so",
            "a fore/aft or height cue would be measured against a reference that",
            "is moving, and it would lie to you. It is also the point of the",
            "sortie: anticipation is the skill, and a speed cue would do the",
            "anticipating for you.",
        ]
    return L
