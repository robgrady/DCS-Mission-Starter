"""Formation flying: you fly as Dash 2 on an AI lead.

WHY THIS IS A MODULE AND NOT A TEMPLATE
---------------------------------------
Every other Library card is a recipe preset — a set of options the engine
already had. Formation training needs something the engine could not do: the
player has to be the WINGMAN, flying on a lead that is AI, independent, and
runs a scripted, predictable profile.

So: TWO groups. "Formation Lead" is a single AI aircraft at Excellent skill
with its own route. "Dash 2" is you. The first version of this module put the
lead inside the player's own flight, which is backwards — aircraft in your
group are your wingmen, under your F-key command structure — and the observed
result was no lead to fly on at all.

Whatever you fly, lead flies. This is not an F-16 feature.

WHAT IS ACTUALLY BEING TAUGHT
-----------------------------
Formation keeping is a SIGHT PICTURE and CLOSURE RATE skill, not a stick and
rudder one. The novice failure mode is invariant: notice you are out of
position, make a large power correction, overshoot, correct back, oscillate.
Everything here attacks that one behavior.

The wingman controls three axes, and they are nearly independent:

    fore/aft   a bearing line on lead's airframe   THROTTLE, and only throttle
    lateral    wingtip clearance                   a few degrees of bank
    vertical   step-down below lead                very small stick inputs

A learner fixing all three at once is task-saturated and will chase. So the
sorties below isolate them: PROFILES are ordered so each one adds exactly one
new variable, and the first is deliberately, unapologetically boring.
"""
import math

from dcs import mapping, task
from dcs.mission import StartType
from dcs.unit import Skill

from . import formation_hud as _hud
from .resolver import load_json

# Sortie profiles, in teaching order. `legs` are (heading change, minutes,
# altitude change in feet, speed change in knots) applied in sequence to the
# lead's route — a script the AI flies the same way every time, which is the
# point: a learner cannot build a sight picture against a lead that improvises.
PROFILES = {
    "route": {
        "label": "Route Position",
        "stage": 1,
        "start": "route",
        "ground": False,
        "legs": [(0, 4, 0, 0), (-30, 3, 0, 0), (0, 3, 0, 0), (30, 3, 0, 0),
                 (0, 4, 0, 0)],
        "teaches": "The workhorse position. Wide enough to breathe, close "
                   "enough to be a formation.",
        "why": "Pilots fly ROUTE almost all the time and close formation "
               "almost never. Teaching fingertip first — as the previous "
               "version of this syllabus did — starts a learner at the "
               "highest-workload position they will hardly ever use.",
    },
    "close": {
        "label": "Close Formation",
        "stage": 2,
        "start": "fingertip",
        "ground": False,
        "legs": [(0, 3, 0, 0), (-60, 3, 0, 0), (0, 2, 0, 0), (90, 3, 0, 0),
                 (0, 2, 0, 0), (-90, 3, 0, 0), (0, 3, 0, 0)],
        "teaches": "Tighten it up, then hold it through turns. Inside you go "
                   "low and slow; outside you go high and fast.",
        "why": "Now the sight picture exists, shrink it. Turns come in the "
               "same sortie because a close position you cannot hold in a "
               "turn is not a position you hold.",
    },
    "energy": {
        "label": "Climbs, Descents and Speed",
        "stage": 3,
        "start": "fingertip",
        "ground": False,
        "legs": [(0, 3, 0, 0), (0, 4, 4000, 0), (0, 2, 0, 40), (0, 3, 0, -60),
                 (0, 4, -4000, 0), (0, 3, 0, 30)],
        "teaches": "Anticipation. By the time you SEE the change you are late.",
        "why": "Energy is the axis a learner cannot see coming, so it gets a "
               "sortie of its own once position is automatic.",
    },
    "rejoin": {
        "label": "The Rejoin",
        "stage": 4,
        "start": "spread",
        "ground": False,
        "legs": [(0, 4, 0, 0), (-45, 3, 0, 0), (0, 3, 0, 0), (45, 3, 0, 0),
                 (0, 4, 0, 0)],
        "teaches": "Closure control. Come in fast and you fly through him, or "
                   "into him.",
        "why": "The most-used formation skill in multiplayer and the one most "
               "likely to hurt somebody.",
    },
    "takeoff": {
        "label": "Takeoff to Landing",
        "stage": 5,
        "start": "fingertip",
        "ground": True,
        "legs": [(0, 5, 0, 0), (-40, 4, 0, 0), (0, 4, 0, 0), (40, 4, 0, 0),
                 (0, 5, 0, 0)],
        "teaches": "The whole sortie: ramp, runway, departure rejoin, the "
                   "route, and back.",
        "why": "The capstone, and the sortie the previous syllabus skipped "
               "entirely by air-starting everything. Getting airborne together "
               "and rejoining after gear-up is the part people actually need "
               "on a multiplayer server.",
    },
    # THE CHECK PROFILE. Everything the block taught, in one sortie, with
    # lead doing each thing long enough to grade: level, a turn each way, a
    # climb, two speed changes, a descent, level again — then the pitchout
    # and the rejoin, which the engine times. Flown twice: once as the
    # PRE-CHECK with the coach on, once as the CHECK in silence
    # (checkride.py). Same legs both times: nobody is surprised on a check.
    "precheck": {
        "label": "Pre-Check",
        "stage": 6,
        "start": "fingertip",
        "ground": False,
        "check": "practice",
        "legs": [(0, 3, 0, 0), (-45, 2, 0, 0), (0, 1, 0, 0), (45, 2, 0, 0),
                 (0, 2, 3000, 0), (0, 2, 0, 30), (0, 2, 0, -50),
                 (0, 2, -3000, 0), (0, 2, 0, 0)],
        "teaches": "The check profile with the coach still talking, and the "
                   "check's own card at the end so you know exactly what it "
                   "will score.",
        "why": "The last dual ride before a check flies the check profile. "
               "The point of a check is that it holds no surprises.",
    },
    "check": {
        "label": "Check Ride — Fingertip",
        "stage": 7,
        "start": "fingertip",
        "ground": False,
        "check": "check",
        "legs": [(0, 3, 0, 0), (-45, 2, 0, 0), (0, 1, 0, 0), (45, 2, 0, 0),
                 (0, 2, 3000, 0), (0, 2, 0, 30), (0, 2, 0, -50),
                 (0, 2, -3000, 0), (0, 2, 0, 0)],
        "teaches": "Nothing. It measures: time in the band while lead is "
                   "level, turning, and changing energy; the rejoin on the "
                   "clock; the critical items. U / F / G / E per item, "
                   "Q / Q- / U overall.",
        "why": "A block without a check is a set of missions. The check is "
               "what makes it a course.",
    },
}


def profile_seconds(profile_key: str) -> int:
    """Seconds lead spends on the scripted legs — when the pitchout is called."""
    prof = PROFILES.get(profile_key) or PROFILES["route"]
    return int(sum(minutes for _dh, minutes, _dft, _dkt in prof["legs"]) * 60)


# Where Dash 2 starts, relative to lead: (metres right, metres back, feet down).
# Fingertip is the real thing — close enough that the sight picture works.
# Spread starts you outside it so the rejoin sortie has something to rejoin.
# Where you start relative to lead: (metres right, metres back, feet down).
# ROUTE is the wide, comfortable working position — deliberately the first one
# a learner sees. FINGERTIP is close. SPREAD is out where a rejoin starts.
START_OFFSETS = {"route": (150, 60, 0),
                 "fingertip": (25, 15, 10),
                 "spread": (1800, 900, 0)}

# Radius (metres) of the moving zone around lead inside which you count as "in
# position" for that stage. Generous — this is a nudge, not a grade.
IN_POSITION_M = {"route": 400, "fingertip": 120, "spread": 2500}

# Mission flag used to remember "lead has already called you out of position",
# so the drift call fires once per excursion instead of once per second. High
# number to stay clear of anything a hand-edited mission is likely to use.
FORMATION_FLAG = 8801

# --- the patient lead (v1.104.0) -------------------------------------------
#
# Rob, on the old ride: "too difficult to watch and navigate". Half of that is
# the display, which formation_hud.py fixes. The other half is that the sortie
# did not care where you were: lead flew a fixed script off a stopwatch, so the
# first turn arrived whether or not you had ever got aboard, and a student who
# was slow off the join spent the whole sortie chasing a leader who had already
# gone. Task saturation is far more cheaply cured by removing task than by
# displaying more.
#
# So lead now HOLDS at each of the first two route points until you have been in
# the slot for HOLD_SETTLE_S, then flies the profile exactly as before. He is
# still perfectly predictable — that is what makes a sight picture possible —
# he is simply patient about when he starts.
#
# NOT on the check rides. A check must be comparable between attempts, and one
# that starts when the candidate is ready is not the same test twice.
F_READY = (8802, 8803)      # released hold 1, released hold 2
F_SETTLE = 8804             # you are in the slot; the settle timer runs on it
HOLD_SETTLE_S = 15
# ... and never for ever. A student who cannot find lead at all must still get
# a sortie rather than an airplane orbiting until fuel exhaustion.
HOLD_MAX_S = (300, 600)

_FT = 0.3048
_KT = 1.852            # knots -> km/h


def refs() -> dict:
    """Airframe-specific sight-picture references."""
    return {k: v for k, v in load_json("formation_refs").items()
            if not k.startswith("_")}


def sight_picture(type_id: str) -> dict | None:
    """Airframe references, or the generic principles for anything unlisted.

    Reads the RAW pack for the fallback: `refs()` strips underscore-prefixed
    keys as comments, which quietly made `_generic` unreachable — so an
    unlisted airframe got no instruction at all rather than the principles.
    """
    r = refs().get(type_id)
    if r:
        return r
    return load_json("formation_refs").get("_generic") or None


def _offset(p, east, north):
    return mapping.Point(p.x + north, p.y + east, p._terrain)


def cruise_for(aircraft_cls) -> tuple:
    """Lead's cruise as (altitude ft, speed kt), scaled to the AIRFRAME.

    The first version hard-coded 12,000 ft and 300 kt, which is a reasonable
    fast-jet number and a nonsense one for anything else: a Yak-52 tops out
    around 145 kt, so lead would have been flying a speed the student's
    airplane physically cannot reach. That is the mechanism by which this
    became "an F-16 tool" — not the card list, the numbers.

    pydcs carries `max_speed` in km/h for every airframe. 45% of it lands close
    to a real formation cruise across the whole spread (P-51 ~185 kt, A-10
    ~175, L-39 ~185, F-16 clamped to 320), and the clamp keeps both ends sane
    when `max_speed` is missing or silly. Slower airplanes also get a lower
    block, because a piston trainer at 12,000 ft is doing circuits of the
    service ceiling instead of flying formation.
    """
    try:
        vmax = float(getattr(aircraft_cls, "max_speed", 0) or 0)
    except (TypeError, ValueError):
        vmax = 0.0
    kt = vmax * 0.45 / _KT if vmax > 0 else 300.0
    kt = int(max(120.0, min(320.0, kt)))
    alt = 5000 if kt < 150 else (8000 if kt < 220 else 12000)
    return alt, kt


def build(m, recipe, country, home_airport, profile_key, aircraft_cls,
          warnings=None):
    """Create the lead and the player. Returns (player_group, stats).

    THE LEAD IS ITS OWN GROUP. The first version put the AI lead in the
    player's flight, which is fighting the grain of DCS: the aircraft in your
    group are your WINGMEN — they sit under your F-key command structure and
    the sim treats your group as player-led whichever slot you occupy. Rob's
    report was that no aircraft turned up to fly formation with at all.

    A separate group also happens to be the correct training set-up: the thing
    you fly on is an independent airplane flying its own route, not a member
    of your own flight you could order somewhere else.
    """
    prof = PROFILES.get(profile_key) or PROFILES["route"]
    ground = bool(prof.get("ground"))
    alt_ft, spd_kt = cruise_for(aircraft_cls)
    alt, spd = alt_ft * _FT, spd_kt * _KT
    dx, dy, ddown = START_OFFSETS.get(prof["start"], START_OFFSETS["route"])

    start = _offset(home_airport.position, 25000, 0)

    # ---- the LEAD ------------------------------------------------------
    if ground:
        try:
            lead_g = m.flight_group_from_airport(
                country, "Formation Lead", aircraft_cls, home_airport,
                start_type=StartType.Warm)
        except Exception:
            ground = False
    if not ground:
        lead_g = m.flight_group_inflight(
            country, "Formation Lead", aircraft_cls, start,
            altitude=alt, speed=spd, group_size=1)
    lead_g.units[0].skill = Skill.Excellent

    hdg, pos = 0.0, start
    cur_alt, cur_spd = alt, spd
    lead_wps = []
    for dh, minutes, dft, dkt in prof["legs"]:
        hdg = (hdg + dh) % 360
        # Floors are RELATIVE to this airframe's cruise, not absolute. A fixed
        # 150 kt floor would have silently sped a Yak-52 up above its own
        # briefed cruise every time the energy sortie asked lead to slow down.
        cur_alt = max(600.0, cur_alt + dft * _FT)
        cur_spd = max(0.7 * spd, cur_spd + dkt * _KT)
        dist = cur_spd / 3.6 * minutes * 60
        rad = math.radians(hdg)
        pos = mapping.Point(pos.x + dist * math.cos(rad),
                            pos.y + dist * math.sin(rad), pos._terrain)
        lead_wps.append(lead_g.add_waypoint(pos, altitude=cur_alt, speed=cur_spd))
    lead_g.add_waypoint(home_airport.position, altitude=alt, speed=spd)

    # ---- YOU -----------------------------------------------------------
    if ground:
        player_g = m.flight_group_from_airport(
            country, "Dash 2", aircraft_cls, home_airport,
            start_type=StartType.Warm,
            group_size=max(1, min(4, recipe.slots or 1)))
        # Same route as lead, so you have an F10 flight plan to navigate by if
        # you lose him off the departure — which, on the capstone sortie, you
        # will. Without this the player sits on a single ramp waypoint and the
        # map shows nothing to fly toward.
        player_g.add_waypoint(pos, altitude=alt, speed=spd)
        player_g.add_waypoint(home_airport.position, altitude=alt, speed=spd)
    else:
        your_pos = mapping.Point(start.x - dy, start.y + dx, start._terrain)
        player_g = m.flight_group_inflight(
            country, "Dash 2", aircraft_cls, your_pos,
            altitude=max(300.0, alt - ddown * _FT), speed=spd,
            group_size=max(1, min(4, recipe.slots or 1)))
        # A steer toward lead's first turn point so the flight plan is not a
        # single orphan waypoint hanging in space.
        player_g.add_waypoint(pos, altitude=alt, speed=spd)
    if (recipe.slots or 1) <= 1:
        player_g.units[0].set_player()
    else:
        for u in player_g.units:
            u.set_client()

    # THE CHECK RIDES. The pre-check keeps the coach and runs the engine as
    # practice; the check runs the engine alone. Everything else is coached.
    check = prof.get("check")
    holds = 0 if check else _patient_lead(m, prof, lead_g, player_g, lead_wps,
                                          alt, spd, warnings)
    ladder = ""
    if check != "check" and profile_key in _hud.profiles_with_hud():
        ladder = _hud.attach(m, player_g, lead_g, prof, alt, spd, warnings)
    n_check = 0
    if check:
        from . import checkride as _ck
        n_check = _ck.attach(m, player_g, lead_g, profile_seconds(profile_key),
                             warnings, practice=(check == "practice"),
                             label="Fingertip")
    if check != "check":
        _coach(m, prof, lead_g, player_g, warnings, ladder=bool(ladder))

    return player_g, {
        "formation_profile": profile_key,
        "formation_label": prof["label"],
        "formation_stage": prof["stage"],
        "formation_start": prof["start"],
        "formation_lead_group": lead_g.name,
        "formation_ground_start": ground,
        "lead_alt_ft": alt_ft,
        "lead_speed_kt": spd_kt,
        "formation_check": check,
        "checkride_triggers": n_check,
        "formation_ladder": ladder,
        "formation_holds": holds,
    }


def _patient_lead(m, prof, lead_g, player_g, lead_wps, alt, spd, warnings=None) -> int:
    """Hold lead at the first two route points until the student is aboard.

    An orbit rather than a straight leg because that is what a real lead does
    while his wingman joins, and because DCS has no "fly on and wait" — a
    ControlledTask with a stop-on-flag is the only way to hand the AI a task it
    will abandon the moment a condition is met.
    """
    try:
        from dcs import action as A
        from dcs import condition as C
        from dcs import task as K
        from dcs import triggers as Tr

        wps = [w for w in lead_wps[:2] if w is not None]
        if not wps:
            return 0
        b = _hud.bands(prof["start"])
        me, lead = player_group_unit(player_g), lead_g.units[0]
        n = 0
        # ALL OR NOTHING — see formation_hud.attach. The orbit tasks are held
        # back too: a lead told to hold by a flag that nothing will ever set
        # orbits until he runs out of fuel, which is worse than no hold at all.
        pending, holds = [], []

        for k, wp in enumerate(wps):
            hold = K.ControlledTask(K.OrbitAction(
                altitude=alt, speed=spd, pattern=K.OrbitAction.OrbitPattern.RaceTrack))
            hold.stop_if_user_flag(str(F_READY[k]), True)
            holds.append((wp, hold))

        def rule(comment, conds, acts, once=True):
            nonlocal n
            t = (Tr.TriggerOnce if once else Tr.TriggerContinious)(comment=comment)
            for c in conds:
                t.rules.append(c)
            for a in acts:
                t.actions.append(a)
            pending.append(t)
            n += 1

        inside = C.UnitInMovingZone(me.id, b["slot_hi"], lead.id)
        outside = C.UnitOutsideMovingZone(me.id, b["slot_hi"], lead.id)
        rolling = 'LEAD: "Two, you\'re aboard. Here we go."'

        for k in range(len(wps)):
            prev = [C.FlagIsTrue(F_READY[k - 1])] if k else []
            gate = prev + [C.FlagIsFalse(F_READY[k])]
            rule(f"Formation hold {k + 1}: settling", gate + [inside, C.FlagIsFalse(F_SETTLE)],
                 [A.SetFlag(F_SETTLE)], once=False)
            rule(f"Formation hold {k + 1}: lost it", gate + [outside, C.FlagIsTrue(F_SETTLE)],
                 [A.ClearFlag(F_SETTLE)], once=False)
            rule(f"Formation hold {k + 1}: release",
                 gate + [C.TimeSinceFlag(F_SETTLE, HOLD_SETTLE_S)],
                 [A.SetFlag(F_READY[k]), A.ClearFlag(F_SETTLE),
                  A.MessageToGroup(player_g.id, m.string(rolling), 8)])
            # the backstop: lead goes anyway rather than orbit for ever
            rule(f"Formation hold {k + 1}: timeout",
                 gate + [C.TimeAfter(HOLD_MAX_S[k])],
                 [A.SetFlag(F_READY[k]), A.ClearFlag(F_SETTLE),
                  A.MessageToGroup(player_g.id, m.string(
                      'LEAD: "Two, I\'m rolling out — catch me up."'), 10)])
        for wp, hold in holds:
            wp.add_task(hold)
        m.triggerrules.triggers.extend(pending)
        return n
    except Exception as e:                    # pydcs drift: never fail a build
        if warnings is not None:
            warnings.append(f"formation hold not attached: {e}")
        return 0


def player_group_unit(player_g):
    """The unit the coaching watches. Always the first slot: in a multi-slot
    formation ride the others are flying on YOU, not on lead."""
    return player_g.units[0]


def _coach(m, prof, lead_g, player_g, warnings=None, ladder=False):
    """In-mission coaching, because a PDF is not an instructor.

    A learner flying alone has no way to know whether they are ten feet out or
    forty. Real instruction is a voice saying "Two, you're sucked." DCS gives us
    a MOVING zone locked to lead, so "are you in position" is answerable at
    runtime rather than only in a debrief that never happens.

    Deliberately gentle: one nudge when you drift out, one word when you get
    back, and a fixed opening call.

    WITH THE LADDER FITTED THE TWO DRIFT CALLS GO AWAY (v1.104.1). They say
    exactly what the card says, one second later, in the corner the card exists
    to get you out of — the "two channels for one message" mistake this codebase
    fixed on the AAR grader (`aar_grade.attach(hud=...)`) and on the check-ride
    debrief, and then shipped here anyway. The opening call stays and now names
    the ladder, so a pilot who sees that line and no card knows instantly which
    half is broken: the wiring ran, the picture did not.

    THE FLAG IS THE WHOLE TRICK. A continuous trigger in DCS re-evaluates every
    second and fires every time its condition is true, so a bare "you are
    outside the zone" rule shouts at you once a second for as long as you are
    out — which is exactly when you are busiest and is the fastest way to teach
    somebody to tune the instructor out. Flag FORMATION_FLAG carries the state
    "I have already told him": the drift call requires it clear and then sets
    it, the recovery call requires it set and then clears it. One call per
    transition, in each direction, no matter how long you sit there.

    Two radii, not one, for the same reason a thermostat has a deadband: you
    fall out at `radius` and are only credited back inside 60% of it, so
    hovering on the boundary cannot ping-pong the calls.
    """
    try:
        from dcs import condition as C, action as A, triggers as Tr

        radius = IN_POSITION_M.get(prof["start"], 300)
        me = player_g.units[0]
        lead = lead_g.units[0]
        flag = FORMATION_FLAG

        pending = []

        def rule(comment, conds, acts):
            t = Tr.TriggerContinious(comment=comment)
            for c in conds:
                t.rules.append(c)
            for a in acts:
                t.actions.append(a)
            pending.append(t)          # all or nothing; see formation_hud

        def say(text, secs):
            return A.MessageToGroup(player_g.id, m.string(str(text)), secs)

        opening = Tr.TriggerOnce(comment="Formation: lead's brief")
        opening.rules.append(C.TimeAfter(20))
        tail = (" Your position ladder is on the left at eye level — fly off "
                "the card. F10 shows one on demand." if ladder else "")
        opening.actions.append(say(
            f"LEAD: \"Two, {prof['label']}. Look at me, not at your "
            f"instruments. Small corrections, early — and take them out before "
            f"you arrive.\"{tail}", 20))
        pending.append(opening)

        if not ladder:
            rule("Formation: out of position",
                 [C.UnitOutsideMovingZone(me.id, radius, lead.id),
                  C.FlagIsFalse(flag)],
                 [say('LEAD: "Two, you\'re out of position — get back in and '
                      'settle before you fix anything else."', 10),
                  A.SetFlag(flag)])

            rule("Formation: back in position",
                 [C.UnitInMovingZone(me.id, radius * 0.6, lead.id),
                  C.FlagIsTrue(flag)],
                 [say('LEAD: "Good position. Hold that."', 6),
                  A.ClearFlag(flag)])
        m.triggerrules.triggers.extend(pending)
    except Exception as e:                    # pydcs drift: never fail a build
        if warnings is not None:
            warnings.append(f"formation coaching not attached: {e}")


# --------------------------------------------------------------------- brief
def brief_lines(profile_key: str, type_id: str) -> list:
    """The instruction sheet. Written to be read BEFORE the sortie and glanced
    at during it, which is why the standards are numbers and the errors are
    symptoms rather than causes — in the air you notice the symptom first."""
    prof = PROFILES.get(profile_key) or PROFILES["route"]
    sp = sight_picture(type_id) or {}
    L = [
        f"=== FORMATION: STAGE {prof['stage']} — {prof['label'].upper()} ===",
        "",
        f"You are DASH 2. Lead is AI and flies the same profile every time —",
        "that is deliberate. You cannot build a sight picture against a leader",
        "who improvises.",
        "",
        f"THIS SORTIE TEACHES: {prof['teaches']}",
        "",
        "--- THE THREE AXES, AND WHAT CONTROLS EACH ---",
        "  FORE/AFT   your bearing line on lead      THROTTLE, and only throttle",
        "  LATERAL    wingtip clearance             a few degrees of bank",
        "  VERTICAL   step-down below lead          very small stick inputs",
        "Fix ONE at a time. Chasing all three is what task-saturates people.",
        "",
    ]
    if sp:
        L += ["--- YOUR SIGHT PICTURE ---"]
        if sp.get("bearing"):
            L.append(f"  Bearing line: {sp['bearing']}")
        if sp.get("lateral"):
            L.append(f"  Wingtip:      {sp['lateral']}")
        if sp.get("vertical"):
            L.append(f"  Step-down:    {sp['vertical']}")
        if sp.get("note"):
            L.append(f"  Note:         {sp['note']}")
        L.append("")
    L += [
        "--- HOW TO FLY IT ---",
        "  1. LOOK AT LEAD. Not at your instruments, not at the ground. Your",
        "     speed and altitude are lead's problem now; your only job is the",
        "     picture. Glancing inside is the most common cause of drift.",
        "  2. Corrections are SMALL and EARLY. If you can feel the throttle",
        "     move, it was too big. Set a correction, then TAKE IT OUT before",
        "     you arrive — otherwise you carry the rate through the position.",
        "  3. Never fix two axes with one input. Aft and low is two separate",
        "     problems: add a little power, then raise the nose a fraction.",
        "  4. If it all goes wrong: ease out and down, away from lead, get",
        "     stable, then rejoin. Nobody has ever fixed a bad position by",
        "     staying in it.",
        "",
        "--- STANDARD (grade yourself honestly) ---",
        "  Position held within roughly half a wingspan, fore and aft.",
        "  Step-down constant — lead should not appear to rise and fall.",
        "  No visible throttle hunting. Small continuous trims, not pumps.",
        "  You can hold it for two minutes without looking inside the cockpit.",
        "",
        "--- IF IT IS GOING WRONG ---",
        "  Sliding aft and adding lots of power     you are chasing. Set a",
        "                                           SMALL power increase and",
        "                                           leave it. Wait.",
        "  Oscillating fore and aft                 you are removing each",
        "                                           correction too late.",
        "  Drifting out in the turns                you are late on power on",
        "                                           the outside of the turn.",
        "  Losing step-down in the climb            you are flying altitude,",
        "                                           not the picture. Look at",
        "                                           lead.",
        "  Creeping closer and closer               a classic. You are chasing",
        "                                           the picture forward. Take a",
        "                                           breath and back off.",
        "",
        "No enemy, no tasking, no threats. Fly it until it is boring, then fly",
        "the next stage.",
    ]
    if profile_key in _hud.profiles_with_hud():
        L += [""] + _hud.brief_lines(prof)
    if not prof.get("check"):
        L += [
            "",
            "--- LEAD WAITS FOR YOU ---",
            f"  At the first two route points lead ORBITS until you have been in",
            f"  the slot for {HOLD_SETTLE_S} s, then rolls out and flies the profile. You",
            "  cannot fall behind the sortie in the first two minutes and spend",
            "  the rest of it chasing. He gives up waiting after a few minutes",
            "  and goes anyway, so a join you cannot make does not strand you.",
        ]
    if prof.get("check"):
        from . import checkride as _ck
        L += [""] + _ck.brief_lines(practice=(prof["check"] == "practice"))
    return L
