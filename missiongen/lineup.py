"""AI runway line-up: a section that lines up on the runway and departs as a
formation, the way a real four-ship does, instead of DCS's one-at-a-time
interval departures.

WHAT DCS SHIPPED
  2.9.24 (5 Feb 2026)   advanced waypoint action "AI Runway Line Up" — AI
                        aircraft perform a formation takeoff; the AI picks
                        the formation from runway width and skill.
  2.9.30 (30 Sep 2026)  "AI runway lineup" option added for AI groups; it
                        commands the group takeoff.
  Same 2.9.30 patch     Reflected's F-4E Red Flag campaign: "AI runway
                        lineup feature removed"; Fight's On's Fangs Out:
                        every mission "updated to remove possible issue with
                        Runway Line Up task". The February bug thread (number
                        two rolls before lead) is still open.

WHAT pydcs HAS
  Nothing. Upstream master's task.py is the file we vendor and carries no
  line-up task or option; PyPI's last release is from 2023; the Retribution
  fork has nothing either. That is not a blocker: pydcs serializes whatever
  task dict we hand it, so support is one verified dict in THIS file.

WHY `TASK` IS None
  The Lua this action writes into a .miz is not published anywhere we can
  read — not the changelog, not the ED scripting FAQ, not the Hoggit tables.
  The one honest source is a mission saved by the Mission Editor with the
  option on. Until that file has been diffed against the same mission with
  the option off, the encoding is a guess, and a guess written into
  somebody's mission is the one thing this generator never does. So:

    TASK is None      -> the recipe field is refused with a sentence that
                         says why, /api/options says lineup_supported=false
                         and the Builder shows no checkbox. Nothing silently
                         half-works.
    TASK is a dict    -> every departing section in the pattern carries it
                         on its takeoff waypoint and the brief says so.

  To light it up: save two 2-ship AI groups from the ME at the same field,
  one with the option on and one without, unzip both, diff `mission`, and
  paste the task table (the entry under route.points[1].task.params.tasks
  that only the "on" file has) into TASK below. Then run
  scripts/mutate_lineup.sh — the tests already cover the supported branch
  through a stand-in dict, so the moment TASK is real they prove the real
  thing.

WHERE IT APPLIES
  Pattern traffic departures (BB-23) — "aircraft coming and going" at the
  player's field. With the knob on, departing pattern aircraft are placed as
  two-ship sections instead of singles, and each section carries the
  line-up action. The player's own flight is never touched: it is the
  player's runway, and a formation takeoff is theirs to fly or not.
"""
from __future__ import annotations

import copy

from dcs.task import Task

# The verified task table from a Mission-Editor-saved .miz. See the module
# docstring for exactly how to obtain it. Shape, once known, will be the task
# entry itself: {"id": ..., "params": {...}} (auto/enabled/number are added by
# pydcs on write).
TASK: dict | None = None

SECTION = 2             # aircraft per departing section when the option is on
WAYPOINT = 0            # the takeoff waypoint (the ME's "advanced" entry lives there)

NOT_SUPPORTED = ("pattern_lineup is not available in this build: DCS 2.9.30's "
                 "AI runway line-up encoding has not been verified against a "
                 "Mission-Editor-saved file yet (missiongen/lineup.py).")


def supported() -> bool:
    return isinstance(TASK, dict) and bool(TASK.get("id"))


def register() -> None:
    """Teach pydcs the id so a .miz carrying it LOADS again. pydcs raises
    KeyError on any task id it has no class for (pydcs/dcs#337), which would
    break our own round-trip tests and every pydcs-based tool that opens one
    of our files. A WrappedAction carries its real id one level down."""
    if not supported():
        return
    from dcs import task as _t
    if TASK["id"] == "WrappedAction":
        aid = (TASK.get("params") or {}).get("action", {}).get("id")
        if aid and aid not in _t.wrappedactions:
            cls = type(f"RunwayLineUp_{aid}", (_t.WrappedAction,), {"Key": aid})
            _t.wrappedactions[aid] = cls
    elif TASK["id"] not in _t.tasks_map:
        cls = type(f"RunwayLineUp_{TASK['id']}", (_t.Task,), {"Id": TASK["id"]})
        _t.tasks_map[TASK["id"]] = cls


def task() -> Task:
    """A fresh pydcs Task carrying the verified table. Raises when unsupported
    so a caller can never write a placeholder by accident."""
    if not supported():
        raise RuntimeError(NOT_SUPPORTED)
    t = Task(TASK["id"])
    t.params = copy.deepcopy(TASK.get("params") or {})
    return t


def apply(group) -> bool:
    """Put the line-up action on the group's takeoff waypoint. Returns True
    when written; False (and writes nothing) when unsupported."""
    if not supported():
        return False
    pts = getattr(group, "points", None) or []
    if len(pts) <= WAYPOINT:
        return False
    pts[WAYPOINT].tasks.append(task())
    return True


def carries(group) -> bool:
    """Does this group hold the line-up action where apply() puts it?"""
    if not supported():
        return False
    pts = getattr(group, "points", None) or []
    if len(pts) <= WAYPOINT:
        return False
    return any(t.id == TASK["id"] and t.params == (TASK.get("params") or {})
               for t in pts[WAYPOINT].tasks)


register()      # no-op until TASK is real; then pydcs round-trips our files
