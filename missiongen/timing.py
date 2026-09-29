"""Waypoint timing: every point on the card gets a clock time, and the clock
is anchored the way a mission planner anchors it.

WHY
---
The card has always carried heading, distance, altitude, speed and leg time
(routing.leg_card). It never carried a CLOCK. A pilot could add the legs up
himself; nothing told him wheels-up was 06:18:30 or that the target was
06:42:00, and nothing in the file held him to it. Every expert campaign on
the shelf does the opposite: Reflected's flight-plan card carries leg and
accumulated time, groundspeed, the TOT, and a HOLD whose push time is a
locked ETA in the file — the mission and the paperwork run on one timeline.

HOW A PLANNER TIMES A ROUTE
---------------------------
Timing is ANCHORED, not accumulated. One time is fixed and everything else
is derived from it, backwards and forwards:

  takeoff   the default. Wheels up N minutes after the mission clock starts
            (cold 8, warm 3, runway 1, air 0) and every ETA counts from there.
  push      the time the flight leaves the push point (WP1) and starts the
            run. Given as a clock time; takeoff — and the mission start — are
            solved backwards from it.
  tot       time on target. Same solve, from the TARGET point.

Per waypoint the card then shows leg time, cumulative time and ETA as a
clock time; a hold at the push point (Reflected's technique for absorbing an
early arrival) simply adds its minutes to that leg. The first leg is flown
on a climb schedule, not at cruise: the climb takes longer than the cruise
number says, and a card that ignores it is a card that makes you late at
the IP by the same minute every time.

WHAT THE FILE DOES WITH IT
--------------------------
The player's waypoints receive the ETA as advisory (`ETA_locked` false —
DCS does not fly the player). An AI package member receives the same ETAs
LOCKED, so the SEAD or the sweep really flies the timeline the card shows
and the pilot fits in behind it. The say/do check (saydo.check_timing)
recomputes card vs file vs mission clock after the build and refuses a
disagreement.

WIND
----
Groundspeed includes the mission's winds aloft when the weather has any
(our presets only set wind in a storm). The .miz stores the direction the
wind blows TO; the Editor displays FROM. We read the file's number as
"blowing to", which is the reading pydcs writes. If that assumption is
wrong the error is symmetric — a headwind reads as a tailwind of the same
size — and the brief says the numbers include wind so a pilot can judge.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta

ANCHORS = ("takeoff", "push", "tot")
ANCHOR_WP = {"push": "WP1", "tot": "TARGET"}

# Start of the mission clock to wheels-up, by start type. Cold is a full
# alignment and a taxi; warm is a taxi; runway is line-up and roll.
GROUND_S = {"cold": 8 * 60, "warm": 3 * 60, "runway": 60, "air": 0}

# Climb schedule per era: (feet per minute, groundspeed in the climb, kt).
# A Phantom at military power climbs ~5,000 fpm at 350 kt; a Mustang does
# 1,500 at 170. Applied to the first leg only — that is the one that starts
# on the runway.
CLIMB = {
    "wwii": (1500, 170),
    "coldwar": (5000, 350),
    "gwot": (4000, 300),
    "modern": (6000, 350),
}
CLIMB_DEFAULT = (4000, 320)

TOL_S = 30            # ±30 s: the strike-package TOT standard
PUSH_TOL_S = 60       # ±60 s at a push or rendezvous point

_MS_PER_KT = 0.514444


def hhmmss(secs_of_day: float) -> str:
    s = int(round(secs_of_day)) % 86400
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def mmss(secs: float) -> str:
    s = int(round(secs))
    sign = "-" if s < 0 else ""
    s = abs(s)
    return f"{sign}{s // 60:02d}:{s % 60:02d}"


def parse_hhmm(text) -> int | None:
    """'06:42' or '06:42:00' -> seconds of day; None when it is not a time."""
    if text is None:
        return None
    parts = str(text).strip().split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 2:
        h, mi, s = nums[0], nums[1], 0
    elif len(nums) == 3:
        h, mi, s = nums
    else:
        return None
    if not (0 <= h < 24 and 0 <= mi < 60 and 0 <= s < 60):
        return None
    return h * 3600 + mi * 60 + s


def wind_component_kt(track_deg: float, wind) -> float:
    """Tailwind (+) or headwind (-) along `track_deg` for wind (speed m/s,
    dir blowing-to). Zero for no wind."""
    if not wind:
        return 0.0
    speed, to_deg = wind
    if not speed:
        return 0.0
    return float(speed) / _MS_PER_KT * math.cos(math.radians(to_deg - track_deg))


def _wind_for(alt_ft: float, winds):
    """Pick the layer nearest the leg altitude from [(alt_m, speed, dir)]."""
    if not winds:
        return None
    alt_m = alt_ft * 0.3048
    alt, spd, d = min(winds, key=lambda w: abs(w[0] - alt_m))
    return (spd, d)


def leg_seconds(row, era, first_leg, winds=None) -> tuple[float, float]:
    """(seconds, groundspeed kt) for a card row. The first leg climbs."""
    nm = float(row["nm"])
    tas = float(row["kt"])
    tail = wind_component_kt(row["heading"], _wind_for(row["alt_ft"], winds))
    gs = max(60.0, tas + tail)
    if not first_leg or nm <= 0:
        return (nm / gs * 3600.0 if gs else 0.0), gs
    fpm, climb_kt = CLIMB.get(era, CLIMB_DEFAULT)
    climb_min = float(row["alt_ft"]) / fpm
    climb_gs = max(60.0, climb_kt + tail)
    climb_nm = climb_min / 60.0 * climb_gs
    if climb_nm >= nm:
        # Still climbing at the waypoint: the whole leg is at climb speed.
        return nm / climb_gs * 3600.0, climb_gs
    rest = (nm - climb_nm) / gs * 3600.0
    total = climb_min * 60.0 + rest
    return total, nm / (total / 3600.0)


def plan(rows, start="cold", era="coldwar", anchor="takeoff", anchor_hhmm=None,
         mission_start: datetime | None = None, hold_s: int = 0, winds=None) -> dict | None:
    """Time the card. Returns the timeline, or None without rows.

    rows            routing.leg_card output (from, to, heading, nm, alt_ft, kt).
    anchor          takeoff | push | tot.
    anchor_hhmm     the clock time the anchor point must be crossed. Only
                    meaningful for push/tot; with takeoff the anchor IS the
                    ground block after the mission clock.
    mission_start   the mission's start datetime; may be MOVED by this
                    function when the anchor needs it (result["mission_start"]).
    hold_s          seconds held at the push point before continuing.
    winds           [(alt_m, speed_ms, dir_to_deg)] from the mission weather.
    """
    if not rows:
        return None
    anchor = anchor if anchor in ANCHORS else "takeoff"
    ground = GROUND_S.get(start, GROUND_S["cold"])
    timed, cum = [], 0
    for i, r in enumerate(rows):
        secs, gs = leg_seconds(r, era, first_leg=(i == 0), winds=winds)
        held = int(hold_s) if (hold_s and r["to"] == ANCHOR_WP["push"]) else 0
        # Whole seconds per leg, summed — the way a card is added up, so the
        # CUM column is always the sum of the LEG column above it.
        leg = int(round(secs))
        cum += leg + held
        t = dict(r)
        t.update({"leg_s": leg, "gs_kt": int(round(gs)),
                  "hold_s": held, "cum_s": cum})
        timed.append(t)

    # Where the anchor sits on the card, in seconds after wheels-up.
    anchor_wp = ANCHOR_WP.get(anchor)
    anchor_row = next((t for t in timed if t["to"] == anchor_wp), None) if anchor_wp else None
    anchor_after_takeoff = anchor_row["cum_s"] if anchor_row else 0

    start_secs = None
    if mission_start is not None:
        start_secs = mission_start.hour * 3600 + mission_start.minute * 60 + mission_start.second
    shift_s = 0
    want = parse_hhmm(anchor_hhmm) if anchor_wp else None
    if want is not None and start_secs is not None:
        # Solve backwards: mission start = anchor - time to anchor - ground.
        new_start = want - anchor_after_takeoff - ground
        shift_s = new_start - start_secs
        mission_start = mission_start + timedelta(seconds=shift_s)
        start_secs = new_start % 86400
    takeoff_s = ground

    if start_secs is not None:
        for t in timed:
            t["eta_s"] = takeoff_s + t["cum_s"]                   # from mission start
            t["eta"] = hhmmss(start_secs + t["eta_s"])
    else:
        for t in timed:
            t["eta_s"] = takeoff_s + t["cum_s"]
            t["eta"] = mmss(t["eta_s"])

    tol = TOL_S if anchor == "tot" else PUSH_TOL_S if anchor == "push" else TOL_S
    out = {
        "anchor": anchor,
        "anchor_wp": anchor_wp or "TAKEOFF",
        "anchor_s": takeoff_s + anchor_after_takeoff,           # from mission start
        "anchor_clock": hhmmss(start_secs + takeoff_s + anchor_after_takeoff) if start_secs is not None else None,
        "tolerance_s": tol,
        "ground_s": ground,
        "takeoff_s": takeoff_s,
        "takeoff_clock": hhmmss(start_secs + takeoff_s) if start_secs is not None else None,
        "start_clock": hhmmss(start_secs) if start_secs is not None else None,
        "shift_s": shift_s,
        "mission_start": mission_start,
        "hold_s": hold_s,
        "wind": bool(winds and any(w[1] for w in winds)),
        "rows": timed,
    }
    return out


def windows(tl: dict) -> dict:
    """Per waypoint: (early_before_s, late_after_s) from mission start — the
    coach's on-time window. The anchor gets the anchor tolerance; the push
    point gets the push tolerance; everything else the wider of the two."""
    out = {}
    for t in tl["rows"]:
        if t["to"] == tl["anchor_wp"]:
            tol = tl["tolerance_s"]
        elif t["to"] == ANCHOR_WP["push"]:
            tol = PUSH_TOL_S
        else:
            tol = max(TOL_S, PUSH_TOL_S)
        out[t["to"]] = (t["eta_s"] - tol, t["eta_s"] + tol)
    return out


def apply_to_group(group, tl: dict, locked: bool = False, offset_s: int = 0) -> int:
    """Write ETAs onto a pydcs flying group whose points were laid from the
    same card (routing.apply adds one point per row after the start point).
    Returns how many points received a time. Never raises."""
    n = 0
    try:
        by_name = {t["to"]: t for t in tl["rows"]}
        for p in getattr(group, "points", []) or []:
            t = by_name.get(getattr(p, "name", None))
            if t is None:
                continue
            p.ETA = int(t["eta_s"] + offset_s)
            p.ETA_locked = bool(locked)
            # DCS will not save a mission whose waypoint has BOTH a locked time
            # and a locked speed between two locked times ("Mission cannot be
            # saved due to errors ... have locked speed and surrounded by
            # waypoints with locked time"). A point flown to a time flies
            # whatever speed meets it, so the speed lock comes off with the
            # time lock on. pydcs locks speed on every point by default.
            if locked:
                p.speed_locked = False
            n += 1
    except Exception:
        return n
    return n


def brief_lines(tl: dict, home_name: str = "HOME") -> list[str]:
    """The timing block for the in-game brief and the PDF. Plain text."""
    if not tl:
        return []
    a = tl["anchor"]
    L = ["TIMING"]
    if a == "takeoff":
        L.append(f"  Anchor: TAKEOFF. Wheels up {tl['takeoff_clock'] or mmss(tl['takeoff_s'])} "
                 f"({tl['ground_s'] // 60} min after the mission clock starts, "
                 f"{'cold' if tl['ground_s'] >= 480 else 'quick'} start). Every ETA counts from there.")
    else:
        L.append(f"  Anchor: {a.upper()} {tl['anchor_clock']} at {tl['anchor_wp']}, "
                 f"tolerance +/-{tl['tolerance_s']} s. Wheels up {tl['takeoff_clock']} "
                 f"(mission clock {tl['start_clock']}, {tl['ground_s'] // 60} min on the ground).")
        if tl["shift_s"]:
            L.append(f"  The mission clock was moved {mmss(abs(tl['shift_s']))} "
                     f"{'earlier' if tl['shift_s'] < 0 else 'later'} so that time can be met.")
    if tl["hold_s"]:
        L.append(f"  HOLD {tl['hold_s'] // 60} min at WP1. You will arrive early on purpose; "
                 f"push at the WP1 ETA below, not when you get there.")
    L.append(f"  {'TO':<8}{'GS':>4}  {'LEG':>5}  {'CUM':>6}  ETA")
    for t in tl["rows"]:
        hold = f"  (+{t['hold_s'] // 60} min hold)" if t["hold_s"] else ""
        L.append(f"  {t['to']:<8}{t['gs_kt']:>4}  {mmss(t['leg_s']):>5}  "
                 f"{mmss(t['cum_s']):>6}  {t['eta']}{hold}")
    L.append("  Groundspeeds include the mission's winds aloft." if tl["wind"] else
             "  No wind in this mission: groundspeed is the briefed speed.")
    L.append("  First leg is timed on a climb schedule, not at cruise.")
    return L


def known_issue_lines(tl: dict, package: bool = False) -> list[str]:
    """What DCS will get wrong about timing — true lines for the brief."""
    if not tl:
        return []
    out = ["Your waypoint ETAs are advisory: DCS does not fly the player to a "
           "time. The coach grades you against them; nothing else will."]
    if package:
        out.append("The AI package flies LOCKED ETAs and will honor them only "
                   "within its speed envelope — an impossible time is silently "
                   "ignored, not reported.")
    return out
