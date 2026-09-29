#!/usr/bin/env python3
"""Semantic fingerprint of generated missions — the tool for library decisions.

WHY THIS EXISTS, and why it is not a byte diff.

Evaluating a pydcs fork (docs/pydcs-fork-evaluation.md) surfaced 2,218 differing
lines in `planes.py` alone. A byte comparison of the resulting .miz files would
be enormous, mostly noise (ids, payload keys, positions nudged by new parking
data) — and the honest failure mode is that whoever reviews it starts
rationalising diffs at about number forty.

More fundamentally: **a byte diff tells you THAT something changed, never
whether it is WORSE.** For that you need the properties a pilot would notice.

So this extracts the things we actually promise, from a real generated mission:

    ramp        parked aircraft per airfield, and per squadron identity
    player      spawn kind, altitude, speed, and geometry vs the nearest threat
    threats     SAM sites, AAA, enemy CAP, by count
    support     tanker / AWACS / carrier presence
    loadout     the player's pylon count and store ids
    documents   briefing and kneeboard presence

Two runs of this over the same recipe set can then be compared field by field,
and every difference is in language a human can adjudicate: "Balad went from 41
parked aircraft to 12" is a bug; "the F-16's cruise moved 8 kt" is a fact.

Usage:
    python3 scripts/mission_semantics.py --out before.json
    # ...change the library...
    python3 scripts/mission_semantics.py --out after.json
    python3 scripts/mission_semantics.py --compare before.json after.json
"""
import argparse
import json
import math
import os
import sys
import tempfile
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

# A deliberately BROAD sweep: every map, both coalitions, each era the map has.
# A narrow sweep is how a library change gets waved through — the map you did
# not sample is the one that breaks.
SWEEP_SEEDS = (7, 42)

# "ST <airfield> <slot_key> ..." — the slot key is always x<digits>
_ST_RE = re.compile(r"^ST (.+?) x\d+ ")


def _recipes():
    from missiongen.resolver import load_json
    maps = load_json("maps")
    era_ac = {"wwii": "P_51D", "coldwar": "F_5E_3", "modern": "F_16C_50",
              "gwot": "A_10C_2"}
    out = []
    for map_key, cfg in maps.items():
        if map_key.startswith("_"):
            continue
        for era in cfg.get("presets", {}):
            for seed in SWEEP_SEEDS:
                out.append(dict(map=map_key, era=era, aircraft=era_ac[era],
                                coalition="blue", slots=1, seed=seed))
    return out


def fingerprint(miz_path):
    """The properties a pilot would notice, extracted from a built mission."""
    import dcs.lua as lua
    with zipfile.ZipFile(miz_path) as z:
        m = lua.loads(z.read("mission").decode())["mission"]
        names = set(z.namelist())
    fp = {"ramp": {}, "threats": {}, "support": {}, "player": {},
          "documents": {}, "counts": {}}

    player = None
    ramp = {}
    threats = {"sam_units": 0, "aaa_units": 0, "enemy_air_groups": 0}
    support = {"tanker": 0, "awacs": 0, "carrier": 0}
    for side, coal in m["coalition"].items():
        if not isinstance(coal, dict):
            continue
        for c in coal.get("country", {}).values():
            for g in c.get("static", {}).get("group", {}).values():
                nm = g.get("name") or ""
                if nm.startswith("ST "):
                    # dressing.py names these
                    #   "ST <airfield> <slot_key> <type_id>[ · <squadron>]"
                    # and BOTH the airfield and the squadron tag can contain
                    # spaces. Splitting on whitespace produced ramp keys like
                    # "Akrotiri x10 Tornado IDS · RAF No." — which would have
                    # shown up as a hundred phantom airfields differing between
                    # runs, i.e. exactly the noise this script exists to avoid.
                    # The slot key is the anchor: it is always x<digits>.
                    mt = _ST_RE.match(nm)
                    field = mt.group(1) if mt else "?"
                    ramp[field] = ramp.get(field, 0) + 1
            for kind in ("plane", "helicopter"):
                for g in c.get(kind, {}).get("group", {}).values():
                    units = list(g["units"].values())
                    nm = (g.get("name") or "").upper()
                    if any(u.get("skill") in ("Player", "Client") for u in units):
                        u = units[0]
                        pts = list(g.get("route", {}).get("points", {}).values())
                        p0 = pts[0] if pts else {}
                        player = {
                            "type": u.get("type"),
                            "start": p0.get("action"),
                            "alt_m": round(u.get("alt") or 0),
                            "speed_kmh": round((p0.get("speed") or 0) * 3.6),
                            "x": round(u["x"]), "y": round(u["y"]),
                            "pylons": len((u.get("payload") or {}).get("pylons") or {}),
                            "stores": sorted(
                                str(v.get("CLSID")) for v in
                                ((u.get("payload") or {}).get("pylons") or {}).values()),
                        }
                    elif side == "red":
                        threats["enemy_air_groups"] += 1
                    if "TANKER" in nm or "TEXACO" in nm or "SHELL" in nm or "ARCO" in nm:
                        support["tanker"] += 1
                    if "AWACS" in nm or "MAGIC" in nm or "OVERLORD" in nm:
                        support["awacs"] += 1
            for g in c.get("vehicle", {}).get("group", {}).values():
                nm = (g.get("name") or "").upper()
                n = len(g.get("units", {}))
                if "SAM" in nm or "SA-" in nm or "HAWK" in nm or "PATRIOT" in nm:
                    threats["sam_units"] += n
                elif "AAA" in nm or "SHORAD" in nm:
                    threats["aaa_units"] += n
            support["carrier"] += len(c.get("ship", {}).get("group", {}))

    # player geometry: how far to the nearest opposing unit
    if player:
        best = None
        for c in m["coalition"].get("red", {}).get("country", {}).values():
            for kind in ("vehicle", "plane", "helicopter", "ship"):
                for g in c.get(kind, {}).get("group", {}).values():
                    for u in g["units"].values():
                        d = math.hypot(player["x"] - u["x"], player["y"] - u["y"])
                        best = d if best is None or d < best else best
        player["nearest_threat_km"] = round(best / 1000.0, 1) if best else None

    fp["ramp"] = dict(sorted(ramp.items()))
    fp["counts"]["ramp_total"] = sum(ramp.values())
    fp["counts"]["ramp_fields"] = len(ramp)
    fp["threats"] = threats
    fp["support"] = support
    fp["player"] = player
    fp["documents"] = {
        "kneeboard_pages": sum(1 for n in names if "KNEEBOARD" in n.upper()),
        "has_briefing": any("dictionary" in n for n in names),
        "entries": len(names),
    }
    return fp


def build_all():
    from missiongen import Recipe, generate
    out = {}
    for rc in _recipes():
        key = f"{rc['map']}/{rc['era']}/{rc['seed']}"
        path = os.path.join(tempfile.mkdtemp(), "m.miz")
        try:
            generate(Recipe.from_dict(rc), path)
            out[key] = fingerprint(path)
        except Exception as e:                       # a map that cannot build
            out[key] = {"ERROR": f"{type(e).__name__}: {e}"}
        print(f"  {key:34s} {'ERROR' if 'ERROR' in out[key] else 'ok'}", flush=True)
    return out


def _walk(a, b, path=""):
    """Every leaf that differs, in dotted-path form."""
    diffs = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            diffs += _walk(a.get(k), b.get(k), f"{path}.{k}" if path else str(k))
    elif a != b:
        diffs.append((path, a, b))
    return diffs


def compare(before_path, after_path):
    before = json.load(open(before_path))
    after = json.load(open(after_path))
    gone = sorted(set(before) - set(after))
    new = sorted(set(after) - set(before))
    if gone:
        print(f"MISSIONS THAT NO LONGER BUILD: {gone}")
    if new:
        print(f"new missions: {new}")
    total = 0
    for key in sorted(set(before) & set(after)):
        diffs = _walk(before[key], after[key])
        if not diffs:
            continue
        total += len(diffs)
        print(f"\n{key}")
        for p, a, b in diffs[:25]:
            print(f"   {p}: {a!r} -> {b!r}")
        if len(diffs) > 25:
            print(f"   ... and {len(diffs) - 25} more")
    print(f"\n{total} semantic differences across "
          f"{len(set(before) & set(after))} missions")
    # An error appearing where there was none is the one unambiguous failure.
    broke = [k for k in set(before) & set(after)
             if "ERROR" in after[k] and "ERROR" not in before[k]]
    if broke:
        print(f"REGRESSION — these built before and do not now: {broke}")
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    args = ap.parse_args()
    if args.compare:
        raise SystemExit(compare(*args.compare))
    data = build_all()
    out = args.out or "mission_semantics.json"
    json.dump(data, open(out, "w"), indent=1, sort_keys=True)
    ok = sum(1 for v in data.values() if "ERROR" not in v)
    print(f"\nwrote {out}: {ok}/{len(data)} missions fingerprinted")


if __name__ == "__main__":
    main()
