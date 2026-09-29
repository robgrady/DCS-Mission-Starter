#!/usr/bin/env python3
"""Dissect any .miz and report how it was built.

    PYTHONPATH=.:vendor python3 scripts/dissect_miz.py <file.miz> [--full]

WHY THIS EXISTS
---------------
Two jobs, and they turn out to be the same job.

1. LEARNING. To get better at authoring missions you have to read missions
   written by people who are better at it, and "opening it in the Mission
   Editor" is a terrible way to read one — the ME shows you a map with icons on
   it and hides the architecture, which is where the craft actually lives. A
   good designer's expertise is in his TRIGGER GRAPH, his flag discipline, his
   AI tasking and his pacing, and none of those are visible on a map.

2. THE PRODUCT. Roadmap bet 1 is "upload any .miz and get our paperwork back,
   including a say/do report". That needs a reader for missions we did not
   author. This is that reader's prototype, and every mission it fails to parse
   is a requirement it has not met yet.

DESIGN NOTE: RAW LUA, NOT `Mission.load_file`.
pydcs's loader instantiates terrain and unit types, so it refuses a mission on
a map we do not have installed, and dies on a unit type its version does not
know — which is exactly the mission most worth reading. This parses the Lua
tables directly and never constructs a pydcs object, so an unknown airframe on
an unknown map is a string it prints rather than an exception it raises.

Everything printed is READ, never inferred. Where something cannot be
determined the report says so rather than guessing — the whole point of the
exercise is to see what is actually in the file.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import zipfile
from pathlib import Path

sys.path[:0] = [".", "vendor"]
import dcs.lua as lua                                          # noqa: E402

FT = 3.28084
KT = 1.94384


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load(path):
    z = zipfile.ZipFile(path)
    names = set(z.namelist())

    def lua_at(name, key):
        if name not in names:
            return {}
        try:
            return lua.loads(z.read(name).decode("utf-8", "replace")).get(key, {})
        except Exception as e:                                  # pragma: no cover
            print(f"  !! could not parse {name}: {e}")
            return {}

    return {
        "zip": z,
        "names": names,
        "mission": lua_at("mission", "mission"),
        "dict": lua_at("l10n/DEFAULT/dictionary", "dictionary"),
        "mapres": lua_at("l10n/DEFAULT/mapResource", "mapResource"),
        "options": lua_at("options", "options"),
        "warehouses": lua_at("warehouses", "warehouses"),
    }


def txt(d, v):
    """Resolve a DictKey_ reference into the real string."""
    if isinstance(v, str) and v.startswith("DictKey_"):
        return d.get(v, f"<missing {v}>")
    return v


# --------------------------------------------------------------------------- #
# Walking
# --------------------------------------------------------------------------- #
CATEGORIES = ("plane", "helicopter", "ship", "vehicle", "static")


def groups(m):
    """Yield (coalition, country, category, group)."""
    for cname, coal in (m.get("coalition") or {}).items():
        for c in (coal.get("country") or {}).values():
            for cat in CATEGORIES:
                for g in ((c.get(cat) or {}).get("group") or {}).values():
                    yield cname, c.get("name", "?"), cat, g


def units_of(g):
    return list((g.get("units") or {}).values())


def points_of(g):
    pts = (g.get("route") or {}).get("points") or {}
    return [pts[k] for k in sorted(pts)]


def wrapped_actions(point):
    """Every WrappedAction on a waypoint: (id, params)."""
    tasks = ((point.get("task") or {}).get("params") or {}).get("tasks") or {}
    out = []
    for t in tasks.values():
        p = t.get("params") or {}
        act = p.get("action") or {}
        if act.get("id"):
            out.append((act["id"], act.get("params") or {}))
        elif t.get("id") and t.get("id") != "WrappedAction":
            out.append((t["id"], p))
    return out


# --------------------------------------------------------------------------- #
# Report sections
# --------------------------------------------------------------------------- #
def head(s):
    print(f"\n\033[1m{s}\033[0m\n" + "-" * min(len(s), 78))


def identity(D):
    m, d = D["mission"], D["dict"]
    head("1. IDENTITY")
    print(f"  theater        {m.get('theater', '?')}")
    st = m.get("start_time", 0)
    print(f"  start time     {st // 3600:02d}:{(st % 3600) // 60:02d} "
          f"({st} s past midnight)")
    dt = m.get("date") or {}
    print(f"  date           {dt.get('Year','?')}-{dt.get('Month','?'):0>2}-"
          f"{dt.get('Day','?'):0>2}")
    print(f"  editor version {m.get('version', '?')}   "
          f"required modules: {', '.join((m.get('requiredModules') or {}).values()) or 'none declared'}")
    w = m.get("weather") or {}
    cl = w.get("clouds") or {}
    print(f"  weather        QNH {w.get('qnh','?')} mmHg · clouds base "
          f"{cl.get('base','?')} m thickness {cl.get('thickness','?')} "
          f"preset {cl.get('preset','(manual)')} · "
          f"wind@GRND {((w.get('wind') or {}).get('atGround') or {}).get('speed','?')} m/s")
    print(f"  fog/dust       fog {'on' if w.get('enable_fog') else 'off'} · "
          f"dust {'on' if w.get('enable_dust') else 'off'} · "
          f"visibility {((w.get('visibility') or {}).get('distance','?'))} m")
    print(f"  files in zip   {len(D['names'])}")


def players(D):
    m, d = D["mission"], D["dict"]
    head("2. THE PLAYER'S SEAT")
    found = 0
    for coal, country, cat, g in groups(m):
        for u in units_of(g):
            if u.get("skill") not in ("Player", "Client"):
                continue
            found += 1
            pts = points_of(g)
            first = pts[0] if pts else {}
            pylons = (u.get("payload") or {}).get("pylons") or {}
            stores = ", ".join(
                f"{k}:{(v or {}).get('CLSID','?').split('{')[-1].strip('}')[:26]}"
                for k, v in sorted(pylons.items())) or "clean"
            print(f"  [{coal}/{country}] {g.get('name')} — {u.get('type')} "
                  f"({u.get('skill')})")
            print(f"      start      {first.get('type','?')} / "
                  f"{first.get('action','?')}  alt {first.get('alt',0):.0f} m "
                  f"({first.get('alt',0)*FT:.0f} ft)")
            print(f"      radio      group freq {g.get('frequency','?')} "
                  f"({'radios preset' if u.get('Radio') else 'NO preset table'})"
                  f"  callsign {json.dumps(u.get('callsign'))[:40]}")
            print(f"      fuel       {(u.get('payload') or {}).get('fuel','?')}"
                  f"   flare {(u.get('payload') or {}).get('flare','?')}"
                  f"   chaff {(u.get('payload') or {}).get('chaff','?')}")
            print(f"      stores     {stores}")
            if u.get("livery_id"):
                print(f"      livery     {u['livery_id']}")
    if not found:
        print("  none — this mission has no Player or Client slot")


def orbat(D):
    m = D["mission"]
    head("3. ORDER OF BATTLE")
    per = collections.defaultdict(collections.Counter)
    types = collections.defaultdict(collections.Counter)
    for coal, country, cat, g in groups(m):
        per[coal][cat] += 1
        for u in units_of(g):
            types[coal][u.get("type", "?")] += 1
    for coal in sorted(per):
        cats = " · ".join(f"{k} {v}" for k, v in sorted(per[coal].items()))
        print(f"  {coal:<8} groups: {cats}")
        top = ", ".join(f"{t}×{n}" for t, n in types[coal].most_common(12))
        print(f"           units:  {top}")
    # AI skill distribution is a real design lever and rarely looked at
    skills = collections.Counter()
    for _c, _n, _cat, g in groups(m):
        for u in units_of(g):
            if u.get("skill"):
                skills[u["skill"]] += 1
    print(f"  skills   {dict(skills)}")


def routes(D, full=False):
    m, d = D["mission"], D["dict"]
    head("4. ROUTES AND AI TASKING")
    shown = 0
    for coal, country, cat, g in groups(m):
        if cat in ("static",):
            continue
        pts = points_of(g)
        acts = [a for p in pts for a in wrapped_actions(p)]
        human = any(u.get("skill") in ("Player", "Client") for u in units_of(g))
        # Interesting = flown by a human, or carrying real tasking
        if not full and not human and len(pts) <= 2 and not acts:
            continue
        shown += 1
        tag = " ★PLAYER" if human else ""
        print(f"  [{coal}] {g.get('name')} ({cat}, {len(units_of(g))} unit(s)){tag}"
              f"  late-activation={bool(g.get('lateActivation'))}"
              f"  uncontrolled={bool(g.get('uncontrolled'))}")
        for i, p in enumerate(pts):
            nm = p.get("name")
            nm = txt(d, nm) if nm else ""
            print(f"      {i:>2} {str(p.get('type','?'))[:16]:<16}"
                  f"{p.get('alt',0)*FT:>7.0f}ft "
                  f"{p.get('speed',0)*KT:>5.0f}kt  {nm}")
            for aid, ap in wrapped_actions(p):
                bits = {k: v for k, v in ap.items()
                        if k not in ("id",) and not isinstance(v, (dict, list))}
                print(f"         └ {aid}: {json.dumps(bits)[:110]}")
    if not shown:
        print("  (nothing with real tasking; re-run with --full for every group)")


def scripting(D):
    m = D["mission"]
    head("5. SCRIPTING — Lua, and what it is doing")
    lua_files = sorted(n for n in D["names"] if n.lower().endswith(".lua"))
    print(f"  .lua in zip    {len(lua_files)}")
    for n in lua_files[:20]:
        try:
            size = D["zip"].getinfo(n).file_size
        except Exception:
            size = -1
        print(f"      {n}  ({size} bytes)")
    # DoScript / DoScriptFile anywhere in the trigger tree
    blob = json.dumps(m.get("trigrules") or {})
    counts = {k: blob.count(k) for k in
              ("a_do_script", "a_do_script_file", "a_activate_group",
               "a_out_sound", "a_out_text", "a_set_flag", "a_ai_task")}
    print(f"  trigger verbs  {counts}")
    # The frameworks a mission author is most likely to be standing on
    hay = " ".join(lua_files).lower()
    try:
        for n in lua_files[:12]:
            hay += " " + D["zip"].read(n)[:4000].decode("utf-8", "replace").lower()
    except Exception:
        pass
    for fw in ("moose", "mist", "ctld", "csar", "splash damage", "mapsop",
               "veaf", "skynet", "dcs-simplemenu"):
        if fw.replace(" ", "") in hay.replace(" ", ""):
            print(f"  framework      {fw.upper()} referenced")


def triggers(D, full=False):
    m, d = D["mission"], D["dict"]
    head("6. TRIGGER ARCHITECTURE — where the craft actually lives")
    rules = (m.get("trigrules") or {})
    if not rules:
        print("  no triggers at all")
        return
    kinds = collections.Counter()
    preds = collections.Counter()
    acts = collections.Counter()
    flags_set, flags_read = collections.Counter(), collections.Counter()
    for r in rules.values():
        kinds[r.get("predicate", "?")] += 1
        for c in (r.get("rules") or {}).values():
            preds[c.get("predicate", "?")] += 1
            if "flag" in c:
                flags_read[str(c["flag"])] += 1
        for a in (r.get("actions") or {}).values():
            acts[a.get("predicate", "?")] += 1
            if "flag" in a:
                flags_set[str(a["flag"])] += 1
    print(f"  {len(rules)} triggers   {dict(kinds)}")
    print(f"  conditions used ({len(preds)} kinds):")
    for p, n in preds.most_common(18):
        print(f"      {n:>4}  {p}")
    print(f"  actions used ({len(acts)} kinds):")
    for p, n in acts.most_common(18):
        print(f"      {n:>4}  {p}")
    print(f"  flags: {len(set(flags_set) | set(flags_read))} distinct "
          f"({len(flags_set)} written, {len(flags_read)} read)")
    # WRITTEN BUT NEVER READ, AND READ BUT NEVER WRITTEN. Both are design
    # smells worth seeing: the first is dead state, the second is a trigger
    # waiting for something that never happens.
    orphan_w = sorted(set(flags_set) - set(flags_read), key=str)[:15]
    orphan_r = sorted(set(flags_read) - set(flags_set), key=str)[:15]
    if orphan_w:
        print(f"      set but never tested: {orphan_w}")
    if orphan_r:
        print(f"      tested but never set: {orphan_r}  "
              f"(mission start / external script?)")
    if full:
        print("\n  every trigger, in order:")
        for k in sorted(rules, key=lambda x: int(x) if str(x).isdigit() else 0):
            r = rules[k]
            cs = [c.get("predicate") for c in (r.get("rules") or {}).values()]
            as_ = [a.get("predicate") for a in (r.get("actions") or {}).values()]
            print(f"    [{r.get('predicate','?')[:16]:<16}] "
                  f"{str(r.get('comment','') or '(no comment)')[:44]:<44} "
                  f"IF {','.join(cs)[:52]} -> {','.join(as_)[:52]}")


def immersion(D):
    m, d = D["mission"], D["dict"]
    head("7. IMMERSION — what the pilot sees and hears")
    media = collections.Counter()
    for n in D["names"]:
        ext = Path(n).suffix.lower()
        if ext in (".ogg", ".wav", ".mp3"):
            media["audio"] += 1
        elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".dds"):
            media["image"] += 1
        elif ext in (".mp4", ".avi", ".webm"):
            media["video"] += 1
    print(f"  media in zip   {dict(media) or 'none'}")
    kb = [n for n in D["names"] if "kneeboard" in n.lower()]
    print(f"  kneeboard      {len(kb)} page(s)")
    for n in kb[:10]:
        print(f"      {n}")
    blob = json.dumps(m.get("trigrules") or {})
    for verb, label in (("a_out_text", "text messages"),
                        ("a_out_sound", "sounds"),
                        ("a_out_picture", "pictures"),
                        ("a_radio_transmission", "radio transmissions"),
                        ("a_set_frequency", "frequency changes"),
                        ("a_start_wait_user_response", "user prompts"),
                        ("a_show_route_gates", "helper gates")):
        n = blob.count(verb)
        if n:
            print(f"  {label:<22} {n}")


def briefing(D):
    m, d = D["mission"], D["dict"]
    head("8. THE BRIEFING — the say half of say/do")
    for key, label in (("descriptionText", "general"),
                       ("descriptionBlueTask", "blue tasking"),
                       ("descriptionRedTask", "red tasking"),
                       ("descriptionNeutralsTask", "neutral tasking")):
        v = txt(d, m.get(key))
        if v and str(v).strip():
            print(f"\n  --- {label} ({len(str(v))} chars) ---")
            for line in str(v).splitlines()[:40]:
                print(f"  {line}")
    sortie = txt(d, m.get("sortie"))
    if sortie:
        print(f"\n  sortie name: {sortie}")


def claims(D):
    """Numbers the briefing states, next to numbers the mission contains.

    NOT an automatic verdict — a prototype of the say/do report, printed so a
    human can put the two columns beside each other. Every value on the right
    is read out of the file.
    """
    m, d = D["mission"], D["dict"]
    head("9. SAY/DO — the briefing's claims, and the file's facts")
    import re
    text = " ".join(str(txt(d, m.get(k)) or "") for k in
                    ("descriptionText", "descriptionBlueTask",
                     "descriptionRedTask"))
    pats = {
        "frequencies (MHz)": r"\b(\d{2,3}\.\d{1,3})\s*(?:MHz|mhz)?\b",
        "TACAN channels": r"\b(\d{1,3}\s*[XY])\b",
        "headings/bearings": r"\b(\d{3})\s*(?:°|deg|degrees)\b",
        "times (Z/L)": r"\b(\d{2}:?\d{2})\s*(?:Z|L|hrs|zulu)\b",
    }
    for label, p in pats.items():
        hits = sorted(set(re.findall(p, text, re.I)))[:14]
        print(f"  brief says {label:<20} {hits or '—'}")
    freqs = sorted({round(g["frequency"] / 1e6, 3) if g.get("frequency", 0) > 1e5
                    else g.get("frequency")
                    for _c, _n, _cat, g in groups(m) if g.get("frequency")})
    print(f"  file contains group frequencies  {freqs[:20]}")
    beacons = []
    for _c, _n, _cat, g in groups(m):
        for p in points_of(g):
            for aid, ap in wrapped_actions(p):
                if aid in ("ActivateBeacon", "ActivateICLS", "ActivateLink4",
                           "ActivateACLS"):
                    beacons.append((g.get("name"), aid,
                                    {k: ap.get(k) for k in
                                     ("channel", "modeChannel", "callsign",
                                      "frequency", "system")
                                     if ap.get(k) is not None}))
    print(f"  file contains navaids            {beacons or '—'}")


def options(D):
    o = D["options"]
    head("10. FORCED OPTIONS — the difficulty the author chose for you")
    if not o:
        print("  none (mission uses the player's own settings)")
        return
    diff = o.get("difficulty") or {}
    interesting = {k: v for k, v in diff.items()
                   if k in ("labels", "easyRadar", "fuel", "weapons",
                            "immortal", "unrestrictedSATNAV", "map",
                            "userMarks", "easyCommunication", "geffect",
                            "padlock", "iconsTheme", "birds", "cockpitVisualRM",
                            "reports", "spectatorExternalViews", "externalViews",
                            "setGlobal", "miscellaneous", "optionsView")}
    print(f"  {json.dumps(interesting, indent=2)[:900]}")


def warehouse(D):
    w = D["warehouses"]
    head("11. WAREHOUSES — finite resources, a real campaign technique")
    ab = (w.get("airports") or {})
    if not ab:
        print("  not configured (unlimited everything)")
        return
    limited = 0
    for aid, a in ab.items():
        if a.get("unlimitedFuel") is False or a.get("unlimitedAircrafts") is False \
                or a.get("unlimitedMunitions") is False:
            limited += 1
    print(f"  {len(ab)} airbase records; {limited} with a limited resource")
    if limited:
        print("  → the author is modeling attrition. Worth reading in full.")


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("miz")
    ap.add_argument("--full", action="store_true",
                    help="every group and every trigger, not just the notable ones")
    a = ap.parse_args()
    path = Path(a.miz)
    print(f"\n\033[1m═══ {path.name} — {path.stat().st_size / 1024:.0f} KB ═══\033[0m")
    D = load(path)
    if not D["mission"]:
        print("  !! no parsable `mission` table — is this a .miz?")
        return 2
    for fn in (identity, players, orbat):
        fn(D)
    routes(D, a.full)
    scripting(D)
    triggers(D, a.full)
    for fn in (immersion, briefing, claims, options, warehouse):
        fn(D)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
