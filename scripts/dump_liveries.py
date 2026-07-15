#!/usr/bin/env python3
"""Harvest REAL DCS livery ids from your install and write missiongen/data/liveries.json.

Why: DCS livery_id is a folder name on disk; pydcs bundles none of them, so the
curated pack ships best-effort guesses. This script replaces those guesses with
verified strings pulled straight from your install (including paid/3rd-party
liveries you own), tagged by nation from each livery's description.lua.

Dependency-free — standard library only. Run it once, then rebuild a mission.

Usage:
    python3 scripts/dump_liveries.py                 # auto-detect common install paths
    python3 scripts/dump_liveries.py "C:/Program Files/Eagle Dynamics/DCS World" "%USERPROFILE%/Saved Games/DCS"
    python3 scripts/dump_liveries.py --merge          # keep existing entries, add found ones
    python3 scripts/dump_liveries.py --dry-run        # print what it would write, change nothing

Point it at BOTH your install root and your Saved Games/DCS folder for full coverage.
"""
import os
import re
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "vendor"))
OUT = os.path.join(ROOT, "missiongen", "data", "liveries.json")

# description.lua fields we read
_NAME_RE = re.compile(r'name\s*=\s*"([^"]+)"')
_COUNTRIES_RE = re.compile(r'countries\s*=\s*\{([^}]*)\}', re.DOTALL)
_COUNTRY_TOKEN_RE = re.compile(r'"([^"]+)"')

# DCS description.lua country codes -> the Country.name pydcs/our presets use.
# Only the ones our maps use need mapping; unknown codes pass through untouched.
COUNTRY_CODE = {
    "USA": "USA", "RUS": "Russia", "RUSSIA": "Russia", "USSR": "Russia",
    "GER": "Germany", "GERMANY": "Germany", "DEU": "Germany",
    "ISR": "Israel", "ISRAEL": "Israel",
    "EGY": "Egypt", "EGYPT": "Egypt",
    "IRN": "Iran", "IRAN": "Iran",
    "SYR": "Syria", "SYRIA": "Syria",
    "GBR": "UK", "UK": "UK", "RAF": "UK",
    "JPN": "Japan", "JAPAN": "Japan",
    "CHN": "China", "CHINA": "China",
    "ARG": "Argentina", "ARGENTINA": "Argentina",
}


def _type_id_by_livery_dir():
    """{ LIVERY_FOLDER_NAME.upper(): our_type_id } from pydcs.

    livery_name is the on-disk Liveries/<dir> name for each unit type, so this
    maps a real install folder back to the type id our catalog/themes use.
    """
    from dcs import planes, helicopters
    out = {}
    wanted = set(json.load(open(_seed_path())).get("types", {}))
    # include every catalog type too, not just seeded ones
    try:
        cat = json.load(open(os.path.join(ROOT, "missiongen", "data",
                                          "static_catalog.json"))).get("types", {})
        wanted |= set(cat)
    except Exception:
        pass
    for mod in (planes, helicopters):
        for tid in wanted:
            t = getattr(mod, tid, None)
            if t is None:
                continue
            ln = getattr(t, "livery_name", None) or t.id
            out[str(ln).upper()] = tid
    return out


def _seed_path():
    return OUT


def _parse_description(path):
    """(display_name_or_None, [Country.name, ...]) from a description.lua."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read()
    except Exception:
        return None, []
    name = None
    m = _NAME_RE.search(txt)
    if m:
        name = m.group(1)
    countries = []
    cm = _COUNTRIES_RE.search(txt)
    if cm:
        for tok in _COUNTRY_TOKEN_RE.findall(cm.group(1)):
            countries.append(COUNTRY_CODE.get(tok.strip().upper(), tok.strip()))
    return name, countries


def _walk_liveries(root, type_map, found):
    """Find every .../Liveries/<typedir>/<livery>/description.lua under root.

    found: { type_id: { COUNTRY: set(livery_id) } } (COUNTRY '' = untagged).
    The livery_id we store is the LIVERY FOLDER NAME (what a saved .miz uses).
    """
    for dirpath, dirnames, filenames in os.walk(root):
        base = os.path.basename(dirpath)
        if base.lower() != "liveries":
            continue
        for typedir in list(dirnames):
            tid = type_map.get(typedir.upper())
            if not tid:
                continue
            tpath = os.path.join(dirpath, typedir)
            for livery in os.listdir(tpath):
                lpath = os.path.join(tpath, livery)
                if not os.path.isdir(lpath):
                    continue
                desc = os.path.join(lpath, "description.lua")
                _, countries = (_parse_description(desc)
                                if os.path.isfile(desc) else (None, []))
                bucket = found.setdefault(tid, {})
                keys = countries or [""]
                for c in keys:
                    bucket.setdefault(c, set()).add(livery)
        # don't descend BELOW a Liveries dir looking for more Liveries
        dirnames[:] = []


def _autodetect():
    home = os.path.expanduser("~")
    cands = [
        r"C:\Program Files\Eagle Dynamics\DCS World",
        r"C:\Program Files\Eagle Dynamics\DCS World OpenBeta",
        os.path.join(home, "Saved Games", "DCS"),
        os.path.join(home, "Saved Games", "DCS.openbeta"),
        # macOS / crossover / wine common spots
        os.path.join(home, "Library", "Application Support", "DCS"),
    ]
    return [p for p in cands if os.path.isdir(p)]


def main(argv):
    merge = "--merge" in argv
    dry = "--dry-run" in argv
    roots = [a for a in argv if not a.startswith("--")]
    roots = [os.path.expandvars(os.path.expanduser(r)) for r in roots]
    if not roots:
        roots = _autodetect()
    roots = [r for r in roots if os.path.isdir(r)]
    if not roots:
        print("No DCS folders found. Pass your install root and Saved Games/DCS path:")
        print('  python3 scripts/dump_liveries.py "<install>" "<Saved Games/DCS>"')
        return 2

    type_map = _type_id_by_livery_dir()
    found = {}
    for r in roots:
        print(f"scanning {r} ...")
        _walk_liveries(r, type_map, found)

    if not found:
        print("Found 0 liveries. Check the paths point at DCS folders "
              "(look for a 'Liveries' or 'CoreMods' subfolder).")
        return 1

    # assemble pack
    pack = {"_note": "Harvested from a DCS install by scripts/dump_liveries.py. "
                     "livery_id values are real folder names; nation keys come "
                     "from each livery's description.lua 'countries'.",
            "_verified": True, "types": {}}
    if merge and os.path.isfile(OUT):
        try:
            pack["types"] = json.load(open(OUT)).get("types", {})
        except Exception:
            pass

    total = 0
    for tid, byc in sorted(found.items()):
        entry = pack["types"].setdefault(tid, {})
        all_ids = set()
        for c, ids in byc.items():
            all_ids |= ids
            if c:  # tagged with a country -> nation-specific list
                cur = set(entry.get(c, []))
                entry[c] = sorted(cur | ids)
        # 'default' = union of everything found (covers untagged liveries too)
        cur = set(entry.get("default", []))
        entry["default"] = sorted(cur | all_ids)
        total += len(all_ids)

    print(f"\n{len(found)} aircraft types, {total} liveries harvested.")
    for tid in sorted(found):
        cs = ", ".join(f"{c or 'untagged'}:{len(v)}" for c, v in found[tid].items())
        print(f"  {tid}: {cs}")

    if dry:
        print("\n--dry-run: nothing written.")
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(pack, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {OUT}")
    print("Rebuild a mission to see nation-correct skins on the ramp.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
