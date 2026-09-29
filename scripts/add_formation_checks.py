#!/usr/bin/env python3
"""Insert the formation PRE-CHECK and CHECK RIDE cards into
mission_templates.json, and put them at the end of the F-4E course's
Formation phase. IDEMPOTENT — same contract as add_white_knights.py.

Both cards are copies of form_close's recipe (air start, no threats, the
same aircraft choices per era) with the formation profile swapped: the
profiles themselves live in formation.PROFILES, the engine in checkride.py.
"""
import copy
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "missiongen" / "data"

CARDS = {
    "form_precheck": {
        "profile": "precheck",
        "label": "Formation 6: Pre-Check — the check profile, coach on",
        "premise": "The check ride's exact profile — level, a turn each way, a "
                   "climb, two speed changes, a descent, then the pitchout and "
                   "rejoin — with lead still calling you out of position, and "
                   "the check's own card at the end so you know what it will score.",
        "brief": [
            "=== FORMATION SYLLABUS — PRE-CHECK ===",
            "You are DASH 2 on an AI lead flying the CHECK profile, unchanged.",
            "The coach is still on: lead calls you out of position and back in.",
            "The check-ride engine runs alongside and prints its card at the end,",
            "labeled PRACTICE — items U / F / G / E, overall Q / Q- / U.",
            "The last dual ride before a check flies the check profile. Fly this",
            "until the card says Q, then fly the check.",
        ],
    },
    "form_check": {
        "profile": "check",
        "label": "Formation 7: Check Ride — Fingertip, silent",
        "premise": "The same profile, and nobody talks. Time in the band while "
                   "lead is level, turning and changing energy; the rejoin on the "
                   "clock; three critical items. U / F / G / E per item, "
                   "Q / Q- / U overall. The sim grades what it can see; the "
                   "gradesheet leaves the wingline and the radio to the IP.",
        "brief": [
            "=== FORMATION SYLLABUS — CHECK RIDE ===",
            "You are DASH 2. Lead flies the check profile and says three things:",
            "the brief, the pitchout, and the card. Nothing else.",
            "Grading arms 20 s after you settle in the 60 m band and runs until",
            "the pitchout; then the rejoin is timed. Inside 12 m of lead, lost",
            "for 30 s, or not rejoined in 300 s is a critical item — a U.",
            "Record the card on the gradesheet. An instructor in the other",
            "seat, or watching in multiplayer, grades line, corrections and",
            "radio; alone, grade those yourself against the Standards.",
        ],
    },
}


def main():
    tpl_path = DATA / "mission_templates.json"
    tpls = json.loads(tpl_path.read_text())
    base = tpls["form_close"]
    for key, spec in CARDS.items():
        v = copy.deepcopy(base)
        v["label"] = spec["label"]
        v["recipe"]["formation"] = spec["profile"]
        v["brief"] = spec["brief"]
        v["library"] = dict(v.get("library") or {})
        v["library"].update({"premise": spec["premise"], "new": True,
                             "featured": False, "role": "training"})
        tpls[key] = v
    tpl_path.write_text(json.dumps(tpls, indent=1, ensure_ascii=False) + "\n")

    c_path = DATA / "courses.json"
    courses = json.loads(c_path.read_text())
    upt = courses["f4e_pipeline"]["schools"][0]
    form = next(p for p in upt["phases"] if p["id"] == "formation")
    form["units"] = [u for u in form["units"] if u["id"] not in ("form_precheck", "form_check")]
    form["units"] += [
        {"kind": "card", "id": "form_precheck", "key": "form_precheck",
         "aircraft": "F_4E_45MC", "era": "coldwar"},
        {"kind": "card", "id": "form_check", "key": "form_check",
         "aircraft": "F_4E_45MC", "era": "coldwar", "check": True},
    ]
    form["intro"] = ("Five stages, each an AI lead you fly on, then the check "
                     "profile twice: once with the coach on, once in silence. "
                     "The Library card lets you pick the airframe; the pipeline "
                     "pre-selects the Phantom.")
    c_path.write_text(json.dumps(courses, indent=1, ensure_ascii=False) + "\n")
    print("wrote form_precheck, form_check; course formation phase now",
          [u["id"] for u in form["units"]])


if __name__ == "__main__":
    main()
