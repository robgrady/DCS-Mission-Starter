"""The timing coach: grades every timed point on the card, then the score.

WHY A COACH AND NOT A LUA CLOCK
-------------------------------
The Mission Editor cannot read "how late was he" and print a number — that
is Lua, and Rob's call on Lua is still open. What the Editor CAN do is what
the cq_coach already does for the Case III push: a zone at the point, and a
window of TimeAfter/TimeBefore around the ETA the card printed. Inside the
window you were on time; before it early; after it late. That is the same
test a range controller applies with a stopwatch, and it works in every
module without a line of script.

WHAT IT GRADES
--------------
  takeoff   first time above 50 m AGL, against the wheels-up time
  WP1       the push point (a hold, when the card has one, is inside its ETA)
  IP        the initial point
  TARGET    the aim point — the TOT when the anchor is the TOT

A point never reached within five minutes of its ETA is graded as missed,
so a pilot who flies past outside the zone still gets a line.

THE SCORECARD
-------------
Base 50, same convention as the Case III ride. On time earns; early and
late cost; the anchor point costs double. Opens a minute after the TARGET
point is scored (or missed).

FLAG BLOCK 8860-8879. `aar_hud` owns 8840-8859, `wk_coach` 8880-8899.
"""
from __future__ import annotations

from . import timing as _tm

F_ARRIVE = 8860         # 8860 + i: point i has been scored (i < 6)
F_GRADE = 8866          # 8866 + 3*i + {0 early, 1 ontime, 2 late}, i < 4
F_DEBRIEF = 8878
F_ARM = 8879
F_TIGHT = 8980          # 8980 + i: point i was inside the E window (check rides)
TIGHT_S = 10            # +/-10 s: the E window on a check ride

POINTS = ("TAKEOFF", "WP1", "IP", "TARGET")
ZONE_NM = {"WP1": 2.0, "IP": 1.5, "TARGET": 1.5}
MISS_AFTER_S = 300
AGL_M = 50
BASE_SCORE = 50
DEBRIEF_AFTER_S = 60
TEXT_S = 12
NM_M = 1852.0

# (points, text) per grade key
SCORE = {
    "early": (-5, "early — arrived before the window"),
    "ontime": (+10, "on time"),
    "late": (-10, "late — arrived after the window"),
}
ANCHOR_MULT = 2         # the anchor point counts double


def _idx(name: str) -> int:
    return POINTS.index(name)


def grade_flag(name: str, key: str) -> int:
    return F_GRADE + 3 * _idx(name) + ("early", "ontime", "late").index(key)


def arrive_flag(name: str) -> int:
    return F_ARRIVE + _idx(name)


def score_lines(tl: dict) -> list[str]:
    """The debrief lines, one per (point, grade), for the brief and the file."""
    out = []
    for name in POINTS:
        mult = ANCHOR_MULT if name == tl["anchor_wp"] else 1
        for key, (pts, text) in SCORE.items():
            p = pts * mult
            out.append(f"{'+' if p > 0 else ''}{p}  {name} {text}")
    return out


def attach(m, player_group, tl: dict, warnings=None, package_group=None,
           package_label: str = "the package", check: bool = False) -> int:
    """Wire cues, grades and the scorecard. Returns trigger count. NEVER RAISES."""
    warnings = warnings if warnings is not None else []
    if m is None or player_group is None or not tl:
        return 0
    try:
        from dcs import action as A
        from dcs import condition as C
        from dcs import triggers as Tr

        me = player_group.units[0]
        n = 0

        def msg(text, secs=TEXT_S):
            return A.MessageToGroup(player_group.id, m.string(text), secs)

        def rule(comment, conds, actions, once=True):
            nonlocal n
            t = (Tr.TriggerOnce if once else Tr.TriggerContinious)(comment=comment)
            for c in conds:
                t.rules.append(c)
            for a in actions:
                t.actions.append(a)
            m.triggerrules.triggers.append(t)
            n += 1
            return t

        armed = C.FlagIsTrue(F_ARM)
        win = _tm.windows(tl)
        eta = {t["to"]: t["eta_s"] for t in tl["rows"]}
        clock = {t["to"]: t["eta"] for t in tl["rows"]}
        eta["TAKEOFF"] = tl["takeoff_s"]
        clock["TAKEOFF"] = tl["takeoff_clock"] or _tm.mmss(tl["takeoff_s"])
        win["TAKEOFF"] = (tl["takeoff_s"] - _tm.PUSH_TOL_S, tl["takeoff_s"] + _tm.PUSH_TOL_S)

        # --- arm, and the hack ------------------------------------------ #
        a = tl["anchor"]
        head = (("CHECK RIDE — TIMING. Silent until the card. " if check else "")
                + f"TIMING — anchor {a.upper()}"
                + (f" {tl['anchor_clock']} at {tl['anchor_wp']}" if a != "takeoff" else "")
                + f". Wheels up {clock['TAKEOFF']}. "
                + " ".join(f"{t['to']} {t['eta']}" for t in tl["rows"]) + ".")
        rule("Timing: arm", [C.TimeAfter(1)], [A.SetFlag(F_ARM), msg(head, 30)])
        if tl["takeoff_s"] >= 90 and not check:
            rule("Timing: one minute to wheels-up",
                 [armed, C.TimeAfter(tl["takeoff_s"] - 60)],
                 [msg(f"ONE MINUTE to wheels-up ({clock['TAKEOFF']}).", 10)])
        if tl.get("hold_s") and not check:
            rule("Timing: hold reminder",
                 [armed, C.TimeAfter(tl["takeoff_s"] + 30)],
                 [msg(f"HOLD at WP1 for {tl['hold_s'] // 60} min. Push WP1 at "
                      f"{clock['WP1']} — not when you get there.", 15)])

        # --- zones ------------------------------------------------------- #
        pts = {t["to"]: t["point"] for t in tl["rows"] if t.get("point") is not None}
        zones = {}
        for name, r_nm in ZONE_NM.items():
            if name in pts:
                zones[name] = m.triggers.add_triggerzone(
                    pts[name], radius=r_nm * NM_M, hidden=True, name=f"TIMING {name}")

        def present(name):
            if name == "TAKEOFF":
                return C.UnitAltitudeHigherAGL(me.id, AGL_M)
            return C.UnitInZone(me.id, zones[name].id)

        # --- the grades -------------------------------------------------- #
        for name in POINTS:
            if name != "TAKEOFF" and name not in zones:
                continue
            lo, hi = win[name]
            arrived = arrive_flag(name)
            tol = (hi - lo) // 2
            what = "WHEELS UP" if name == "TAKEOFF" else name
            cases = {
                "early": ([C.TimeBefore(lo)],
                          f"{what} — EARLY. Window {clock[name]} +/-{tol} s. "
                          f"Take the time out before the next point."),
                "ontime": ([C.TimeAfter(lo), C.TimeBefore(hi)],
                           f"{what} — ON TIME. {clock[name]} +/-{tol} s."),
                "late": ([C.TimeAfter(hi)],
                         f"{what} — LATE. Window closed {clock[name]} +{tol} s. "
                         f"Push it up."),
            }
            if check:
                # The E window sits inside the on-time window; it sets its
                # own flag and never the arrived flag, so the ordinary
                # on-time rule still records the point.
                rule(f"Timing grade: {name} tight",
                     [armed, C.FlagIsFalse(arrived), present(name),
                      C.TimeAfter(eta[name] - TIGHT_S), C.TimeBefore(eta[name] + TIGHT_S)],
                     [A.SetFlag(F_TIGHT + _idx(name))])
            for key, (conds, text) in cases.items():
                rule(f"Timing grade: {name} {key}",
                     [armed, C.FlagIsFalse(arrived), present(name)] + conds,
                     [A.SetFlag(arrived), A.SetFlag(grade_flag(name, key))]
                     + ([] if check else [msg(text)]))
            if name != "TAKEOFF":
                rule(f"Timing grade: {name} missed",
                     [armed, C.FlagIsFalse(arrived), C.TimeAfter(hi + MISS_AFTER_S)],
                     [A.SetFlag(arrived), A.SetFlag(grade_flag(name, "late"))]
                     + ([] if check else [msg(f"{name} — NOT REACHED within 5 min of "
                                              f"{clock[name]}. Graded late.")]))

        # --- the package, when there is one ------------------------------ #
        if package_group is not None and "IP" in zones and not check:
            try:
                lead = package_group.units[0]
                rule("Timing: package at the IP",
                     [armed, C.UnitInZone(lead.id, zones["IP"].id)],
                     [msg(f"{package_label} is at the IP now. On time, you are "
                          f"{_tm.mmss(tl.get('package_lead_s', 0))} behind.", 10)])
            except Exception:
                pass

        # --- the scorecard ----------------------------------------------- #
        last = arrive_flag("TARGET") if "TARGET" in zones else arrive_flag("IP")
        if check:
            # THE CHECK CARD: U / F / G / E per point, Q / Q- / U overall.
            # E inside +/-10 s, G inside the window, F early (the error a
            # planner can absorb), U late or missed. The anchor late is a
            # critical item.
            F_ANY_F, F_ANY_U = 8984, 8985
            rule("Timing check: open the card",
                 [armed, C.TimeSinceFlag(last, DEBRIEF_AFTER_S)],
                 [A.SetFlag(F_DEBRIEF),
                  msg(f"CHECK RIDE DEBRIEF — TIMING, anchor {a.upper()}. Items "
                      f"U / F / G / E; overall Q, Q- or U.", 40)])
            for name in POINTS:
                if name != "TAKEOFF" and name not in zones:
                    continue
                i = _idx(name)
                on, early, late = (grade_flag(name, "ontime"), grade_flag(name, "early"),
                                   grade_flag(name, "late"))
                rule(f"Timing check: {name} E", [C.TimeSinceFlag(F_DEBRIEF, 2), C.FlagIsTrue(on), C.FlagIsTrue(F_TIGHT + i)],
                     [msg(f"E  {name} — inside +/-{TIGHT_S} s of {clock[name]}.", 40)])
                rule(f"Timing check: {name} G", [C.TimeSinceFlag(F_DEBRIEF, 2), C.FlagIsTrue(on), C.FlagIsFalse(F_TIGHT + i)],
                     [msg(f"G  {name} — inside the window at {clock[name]}.", 40)])
                rule(f"Timing check: {name} F", [C.TimeSinceFlag(F_DEBRIEF, 2), C.FlagIsTrue(early)],
                     [msg(f"F  {name} — early; the time was there to take out.", 40), A.SetFlag(F_ANY_F)])
                rule(f"Timing check: {name} U", [C.TimeSinceFlag(F_DEBRIEF, 2), C.FlagIsTrue(late)],
                     [msg(f"U  {name} — late or not reached.", 40), A.SetFlag(F_ANY_U)])
            anchor_late = grade_flag(tl["anchor_wp"], "late") if tl["anchor_wp"] in POINTS else None
            if anchor_late:
                rule("Timing check: critical", [C.TimeSinceFlag(F_DEBRIEF, 4), C.FlagIsTrue(anchor_late)],
                     [msg(f"CRITICAL ITEM — late at the anchor ({tl['anchor_wp']}). The check is a U.", 40)])
            rule("Timing check: overall U", [C.TimeSinceFlag(F_DEBRIEF, 6), C.FlagIsTrue(F_ANY_U)],
                 [msg("OVERALL: U — re-fly the check.", 60)])
            rule("Timing check: overall Q-", [C.TimeSinceFlag(F_DEBRIEF, 6), C.FlagIsFalse(F_ANY_U), C.FlagIsTrue(F_ANY_F)],
                 [msg("OVERALL: Q- — qualified with discrepancies; more work on the F points.", 60)])
            rule("Timing check: overall Q", [C.TimeSinceFlag(F_DEBRIEF, 6), C.FlagIsFalse(F_ANY_U), C.FlagIsFalse(F_ANY_F)],
                 [msg("OVERALL: Q — qualified. Record it on the gradesheet.", 60)])
            return n
        rule("Timing debrief: open the card",
             [armed, C.TimeSinceFlag(last, DEBRIEF_AFTER_S)],
             [A.SetFlag(F_DEBRIEF),
              msg(f"TIMING DEBRIEF — anchor {a.upper()}. Base score {BASE_SCORE}.", 30)])
        for name in POINTS:
            if name != "TAKEOFF" and name not in zones:
                continue
            mult = ANCHOR_MULT if name == tl["anchor_wp"] else 1
            for key, (pts_, text) in SCORE.items():
                p = pts_ * mult
                rule(f"Timing debrief: {name} {key}",
                     [C.TimeSinceFlag(F_DEBRIEF, 2), C.FlagIsTrue(grade_flag(name, key))],
                     [msg(f"{'+' if p > 0 else ''}{p}  {name} {text}", 30)])
        return n
    except Exception as exc:                              # pragma: no cover
        warnings.append(f"timing coach not attached: {exc}")
        return 0


def brief_lines(tl: dict, package: bool = False) -> list[str]:
    tol = tl["tolerance_s"]
    L = ["TIMING COACH",
         f"  Graded at wheels-up, WP1, IP and TARGET: on time, early or late "
         f"against the ETAs above. The anchor point ({tl['anchor_wp']}) is "
         f"+/-{tol} s and counts double; the others +/-{_tm.PUSH_TOL_S} s.",
         f"  Score: base {BASE_SCORE}; on time +10, early -5, late -10 "
         f"(anchor x2). The card opens a minute after the target."]
    if package:
        L.append("  The package flies a LOCKED timeline; its IP call tells you "
                 "how far behind you should be.")
    return L
