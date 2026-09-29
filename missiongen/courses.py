"""Training COURSES — the pipeline above the tracks.

WHY A COURSE AND NOT MORE TRACKS
--------------------------------
Rob: "Most training is piecemeal at best." The product had four syllabus
islands — the Refuelling Academy, the White Knights, Case III, Timing —
each a good track and none of them a pipeline. A course is the pipeline:
the order every air force runs, with the missions attached.

    School 1  UPT   — fly an airplane   (ground school incl. the history
                                          chapter, then module-agnostic:
                                          formation, timing, the tanker)
    School 2  FRS   — learn THIS one     (contact, systems,
                                          the squadron checkout, weapons,
                                          a check ride)
    School 3  MQT   — fight it           (employment)

A course is DATA (courses.json) laid over things that already exist. Every
unit is one of four kinds:

    reading   a chapter under missiongen/data/courses/<doc>.md
    track     an existing track, optionally a ride range and a preferred
              aircraft/era for the track wizard
    card      an existing Library template, optionally a preferred aircraft
    planned   a unit that is NOT built, with the reason — printed as such,
              never hidden. A syllabus that shows only what exists looks
              complete; one that shows the gaps is honest about being a beta.

`resolve()` checks every reference against the shelf, so a course cannot
claim a ride the Library does not have: an unknown key is a build error
(test_courses), not a dead link somebody finds in six months.

WHAT IS DELIBERATELY NOT HERE
-----------------------------
Progress. The student's record lives in his own browser (localStorage) and
the squadron's in its gradesheet. Nothing is stored server-side — the same
line our analytics draw. The kit (course_kit.py) is how a squadron takes
the syllabus away: the printed program, the gradesheet, the readings.
"""
from __future__ import annotations

from pathlib import Path

from .resolver import load_json
from . import tracks as _tracks

DOCS = Path(__file__).parent / "data" / "courses"
KINDS = ("reading", "track", "card", "planned")


def all_courses() -> dict:
    return {k: v for k, v in load_json("courses").items() if not k.startswith("_")}


def get(course_id: str) -> dict | None:
    return all_courses().get(course_id)


def reading_path(doc: str) -> Path | None:
    """The markdown for a reading, or None. `doc` is a bare name, never a path."""
    if not doc or "/" in doc or "\\" in doc or ".." in doc:
        return None
    p = DOCS / f"{doc}.md"
    return p if p.is_file() else None


def reading_text(doc: str) -> str | None:
    p = reading_path(doc)
    return p.read_text(encoding="utf-8") if p else None


def _templates() -> dict:
    return {k: v for k, v in load_json("mission_templates").items()
            if isinstance(v, dict) and "recipe" in v}


def _card(unit: dict, tpls: dict) -> dict:
    key = unit["key"]
    v = tpls.get(key)
    if v is None:
        raise ValueError(f"course unit {unit.get('id')!r} names an unknown card {key!r}")
    lib = v.get("library") or {}
    rc = v.get("recipe") or {}
    aircraft = unit.get("aircraft") or rc.get("aircraft")
    # A preferred aircraft must be one the card can be flown in.
    if unit.get("aircraft") and unit["aircraft"] != rc.get("aircraft"):
        choices = v.get("aircraft_choices") or {}
        era = unit.get("era") or (v.get("eras") or ["modern"])[0]
        if unit["aircraft"] not in (choices.get(era) or []):
            raise ValueError(
                f"course unit {unit.get('id')!r}: card {key!r} cannot be flown "
                f"in {unit['aircraft']} in the {era} era")
    return {
        "kind": "card", "id": unit["id"], "key": key,
        "label": unit.get("label") or v.get("label", key),
        "premise": lib.get("premise", ""),
        "aircraft": aircraft, "era": unit.get("era") or (v.get("eras") or [None])[0],
        # Graded means a coach in the file, not a good intention: the AAR
        # grades, the Case III coach, the timing coach, the formation coach,
        # or a White Knights ride whose key says it is the coached one.
        "graded": bool(v.get("aar_grade") or v.get("cq_ride")
                       or rc.get("timing_coach") or rc.get("formation")
                       or "coach" in key),
        "check": bool(unit.get("check")),
        "track": (v.get("track") or {}).get("id"),
        "status": "ready", "rides": 1,
    }


def _track(unit: dict) -> dict:
    tid = unit["track"]
    s = _tracks.summary(tid)
    if not s:
        raise ValueError(f"course unit {unit.get('id')!r} names an unknown track {tid!r}")
    lo, hi = unit.get("from", 0), unit.get("to", 10 ** 6)
    rides = [r for r in s["rides"] if lo <= r["n"] <= hi]
    if not rides:
        raise ValueError(f"course unit {unit.get('id')!r}: track {tid!r} has no rides {lo}-{hi}")
    aircraft = unit.get("aircraft") or s.get("aircraft")
    era = unit.get("era") or (s.get("eras") or [None])[0]
    if unit.get("aircraft") and s.get("configurable"):
        # The wizard must be able to reach the preferred combination.
        tree = s.get("picker") or {}
        if unit["aircraft"] not in (tree.get(era) or {}):
            raise ValueError(
                f"course unit {unit.get('id')!r}: track {tid!r} cannot be flown "
                f"in {unit['aircraft']} in the {era} era")
    label = unit.get("label") or s["label"]
    if ("from" in unit or "to" in unit) and not unit.get("label"):
        label = f"{s['label']} — rides {rides[0]['n']}–{rides[-1]['n']}"
    return {
        "kind": "track", "id": unit["id"], "track": tid, "label": label,
        "premise": s.get("premise", ""), "aircraft": aircraft, "era": era,
        "rides": len(rides), "ride_keys": [r["key"] for r in rides],
        "ride_n": [rides[0]["n"], rides[-1]["n"]],
        "graded": any(r.get("graded") or "coach" in r["key"] for r in rides)
                  or tid in ("timing_f4e", "cq_case3_f14", "cq_case3_hornet"),
        "requires": s.get("requires"), "status": "ready",
        "check": bool(unit.get("check")),
    }


def _reading(unit: dict) -> dict:
    doc = unit["doc"]
    if reading_path(doc) is None:
        raise ValueError(f"course unit {unit.get('id')!r} names a missing reading {doc!r}")
    return {"kind": "reading", "id": unit["id"], "doc": doc,
            "label": unit.get("label") or doc, "minutes": unit.get("minutes"),
            "status": "ready", "rides": 0}


def _planned(unit: dict) -> dict:
    return {"kind": "planned", "id": unit["id"], "label": unit["label"],
            "why": unit.get("why", ""), "status": "planned", "rides": 0}


def resolve(course_id: str) -> dict | None:
    """The course with every unit checked against the shelf. Raises on a
    reference the shelf cannot honor — that is a data error to fix, not a
    card to render."""
    c = get(course_id)
    if not c:
        return None
    tpls = _templates()
    schools, seen = [], set()
    for s in c.get("schools") or []:
        phases = []
        for p in s.get("phases") or []:
            units = []
            for u in p.get("units") or []:
                kind = u.get("kind")
                if kind not in KINDS:
                    raise ValueError(f"course unit {u.get('id')!r} has unknown kind {kind!r}")
                uid = f"{s['id']}.{p['id']}.{u['id']}"
                if uid in seen:
                    raise ValueError(f"course unit id {uid!r} is used twice")
                seen.add(uid)
                if kind == "card":
                    r = _card(u, tpls)
                elif kind == "track":
                    r = _track(u)
                elif kind == "reading":
                    r = _reading(u)
                else:
                    r = _planned(u)
                r["uid"] = uid
                units.append(r)
            phases.append({"id": p["id"], "label": p["label"],
                           "intro": p.get("intro", ""), "units": units})
        schools.append({"id": s["id"], "n": s.get("n"), "label": s["label"],
                        "tagline": s.get("tagline", ""), "intro": s.get("intro", ""),
                        "module_agnostic": bool(s.get("module_agnostic")),
                        "requires_school": s.get("requires_school"),
                        "phases": phases})
    units = [u for s in schools for p in s["phases"] for u in p["units"]]
    return {
        "id": course_id, "label": c["label"], "short": c.get("short") or c["label"],
        "aircraft": c.get("aircraft"), "module": c.get("module"),
        "era": c.get("era"), "map": c.get("map"), "featured": bool(c.get("featured")),
        "premise": c.get("premise", ""), "blurb": c.get("blurb") or [],
        "schools": schools,
        "counts": {
            "units": len(units),
            "ready": sum(1 for u in units if u["status"] == "ready"),
            "planned": sum(1 for u in units if u["status"] == "planned"),
            "rides": sum(u.get("rides", 0) for u in units),
            "readings": sum(1 for u in units if u["kind"] == "reading"),
        },
    }


def summaries() -> dict:
    out = {}
    for cid in all_courses():
        r = resolve(cid)
        out[cid] = {k: r[k] for k in ("id", "label", "short", "aircraft", "module",
                                      "era", "featured", "premise", "counts")}
        out[cid]["schools"] = [{"id": s["id"], "n": s["n"], "label": s["label"],
                                "tagline": s["tagline"]} for s in r["schools"]]
    return out


def gradesheet_rows(course: dict) -> list[dict]:
    """One row per ride (and per reading), for the squadron's CSV/PDF."""
    rows = []
    tpls = _templates()
    for s in course["schools"]:
        for p in s["phases"]:
            for u in p["units"]:
                base = {"school": s["label"], "phase": p["label"], "unit": u["uid"]}
                if u["kind"] == "track":
                    for k in u["ride_keys"]:
                        v = tpls.get(k) or {}
                        rows.append({**base, "ride": k,
                                     "label": v.get("label", k).split("— ", 1)[-1],
                                     "kind": "ride", "check": bool(u.get("check"))})
                elif u["kind"] == "card":
                    # A track ride's label is "Track n — Ride name"; a loose
                    # card's is "Name — descriptor". The row wants the name.
                    parts = u["label"].split(" — ", 1)
                    name = parts[-1] if u.get("track") else parts[0]
                    rows.append({**base, "ride": u["key"], "label": name,
                                 "kind": "ride", "check": u["check"]})
                elif u["kind"] == "reading":
                    rows.append({**base, "ride": u["doc"], "label": u["label"],
                                 "kind": "reading", "check": False})
                else:
                    rows.append({**base, "ride": "", "label": u["label"] + " (planned)",
                                 "kind": "planned", "check": False})
    return rows
