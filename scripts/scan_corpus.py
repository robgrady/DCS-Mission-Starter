#!/usr/bin/env python3
"""Scan a corpus of missions and emit one record per mission.

    PYTHONPATH=.:vendor python3 scripts/scan_corpus.py <root> [-o out.json]

<root> holds either .miz files or directories that contain a .miz's inner
files (mission, options, warehouses, l10n/DEFAULT/dictionary, mapResource,
l10n/DEFAULT/*.lua, and a zipindex.txt from `unzip -l`). The directory form
exists because a 2.5 GB corpus of commercial campaigns does not move through
a device bridge, but the 40 MB of text inside it does.

WHAT A RECORD HOLDS
-------------------
Everything dissect_miz.py prints, as data: identity, the player's seat and
route, trigger census, flag discipline, scripting footprint, media counts,
briefing lengths, forced options, warehouse limits — plus the automatic
say/do checks that Bet 1 promises: briefed frequencies against presets and
transmissions, briefed TACANs against beacons, briefed times against the
mission clock, briefed dates against the file date. Each check reports what
it compared, so a human can disagree with the verdict.

Every value is READ from the file. Where a check cannot run (no briefing,
protected logic) it says "n/a" rather than "pass".
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dissect_miz import groups, points_of, units_of, wrapped_actions, txt  # noqa: E402
import dcs.lua as lua  # noqa: E402


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def _parse(text, key):
    try:
        return lua.loads(text).get(key, {})
    except Exception:
        return {}


def load_dir(d: Path):
    def rd(rel):
        p = d / rel
        return p.read_text("utf-8", "replace") if p.exists() else ""
    names = []
    zi = d / "zipindex.txt"
    if zi.exists():
        for line in zi.read_text("utf-8", "replace").splitlines():
            parts = line.split(None, 3)
            if len(parts) == 4 and parts[0].isdigit():
                names.append(parts[3])
    luas = {p.name: p.read_text("utf-8", "replace")
            for p in (d / "l10n" / "DEFAULT").glob("*.lua")} if (d / "l10n").exists() else {}
    return {
        "names": names,
        "mission": _parse(rd("mission"), "mission"),
        "dict": _parse(rd("l10n/DEFAULT/dictionary"), "dictionary"),
        "mapres": _parse(rd("l10n/DEFAULT/mapResource"), "mapResource"),
        "options": _parse(rd("options"), "options"),
        "warehouses": _parse(rd("warehouses"), "warehouses"),
        "lua": luas,
    }


def load_miz(p: Path):
    z = zipfile.ZipFile(p)
    names = z.namelist()

    def rd(n):
        return z.read(n).decode("utf-8", "replace") if n in names else ""
    luas = {n.split("/")[-1]: rd(n) for n in names
            if n.startswith("l10n/DEFAULT/") and n.endswith(".lua")}
    return {
        "names": names,
        "mission": _parse(rd("mission"), "mission"),
        "dict": _parse(rd("l10n/DEFAULT/dictionary"), "dictionary"),
        "mapres": _parse(rd("l10n/DEFAULT/mapResource"), "mapResource"),
        "options": _parse(rd("options"), "options"),
        "warehouses": _parse(rd("warehouses"), "warehouses"),
        "lua": luas,
    }


# --------------------------------------------------------------------------- #
# Pieces
# --------------------------------------------------------------------------- #
def hm(secs):
    secs = int(secs or 0)
    return f"{(secs // 3600) % 24:02d}:{(secs % 3600) // 60:02d}"


def player_seat(m, d):
    for coal, country, cat, g in groups(m):
        for u in units_of(g):
            if u.get("skill") in ("Player", "Client"):
                pts = points_of(g)
                cs = u.get("callsign")
                cs = cs.get("name") if isinstance(cs, dict) else str(cs)
                radios = {}
                for rid, r in (u.get("Radio") or {}).items():
                    radios[str(rid)] = {str(k): v for k, v in (r.get("channels") or {}).items()}
                pyl = u.get("payload", {}).get("pylons") or {}
                return {
                    "coalition": coal, "group": txt(d, g.get("name")),
                    "type": u.get("type"), "skill": u.get("skill"),
                    "callsign": cs, "livery": u.get("livery_id"),
                    "start_action": pts[0].get("action") if pts else None,
                    "start_alt_ft": round((pts[0].get("alt") or 0) * 3.281) if pts else None,
                    "waypoints": len(pts),
                    "named_wps": [txt(d, p.get("name")) for p in pts if p.get("name")],
                    "locked_etas": [(txt(d, p.get("name")) or f"wp{i}", hm(p.get("ETA")))
                                    for i, p in enumerate(pts) if p.get("ETA_locked") and i > 0],
                    "pylons": sorted({str(v.get("CLSID")) for v in pyl.values()}),
                    "fuel": u.get("payload", {}).get("fuel"),
                    "radios": radios,
                    "group_size": len(units_of(g)),
                }
    return None


def trigger_census(m):
    rules = m.get("trigrules") or {}
    out = {"count": len(rules), "kinds": {}, "conds": {}, "acts": {},
           "flags": 0, "flags_orphan_set": 0, "flags_orphan_read": 0,
           "comments_numbered": 0}
    if not rules:
        return out
    kinds, conds, acts = collections.Counter(), collections.Counter(), collections.Counter()
    fs, fr = set(), set()
    for r in rules.values():
        kinds[r.get("predicate", "?")] += 1
        c = str(r.get("comment") or "")
        if re.match(r"^\s*\d+\s*-", c) or re.search(r"-\s*\d+\s*$", c):
            out["comments_numbered"] += 1
        for cc in (r.get("rules") or {}).values():
            conds[cc.get("predicate", "?")] += 1
            if "flag" in cc:
                fr.add(str(cc["flag"]))
        for a in (r.get("actions") or {}).values():
            acts[a.get("predicate", "?")] += 1
            if "flag" in a:
                fs.add(str(a["flag"]))
    out.update(kinds=dict(kinds), conds=dict(conds), acts=dict(acts),
               flags=len(fs | fr), flags_orphan_set=len(fs - fr),
               flags_orphan_read=len(fr - fs))
    return out


def route_facts(m, d):
    single_unit_air = 0
    air_groups = 0
    follow = 0
    beacons = []
    freqs = set()
    transmit_wps = 0
    for coal, country, cat, g in groups(m):
        if cat in ("plane", "helicopter"):
            air_groups += 1
            if len(units_of(g)) == 1:
                single_unit_air += 1
        if g.get("frequency"):
            f = g["frequency"]
            freqs.add(round(f / 1e6, 3) if f > 1e5 else round(f, 3))
        for t in (g.get("tasks") or {}).values():
            s = json.dumps(t)
            if '"Follow"' in s:
                follow += 1
        for p in points_of(g):
            for aid, ap in wrapped_actions(p):
                if aid in ("ActivateBeacon", "ActivateICLS", "ActivateLink4", "ActivateACLS"):
                    beacons.append({"group": txt(d, g.get("name")), "kind": aid,
                                    "channel": ap.get("channel"), "mode": ap.get("modeChannel"),
                                    "callsign": ap.get("callsign")})
                if aid == "TransmitMessage":
                    transmit_wps += 1
    return {"air_groups": air_groups, "single_unit_air_groups": single_unit_air,
            "follow_tasks": follow, "beacons": beacons,
            "group_freqs": sorted(freqs), "transmit_waypoints": transmit_wps}


def transmission_freqs(m):
    out = set()
    for r in (m.get("trigrules") or {}).values():
        for a in (r.get("actions") or {}).values():
            if a.get("predicate") == "a_radio_transmission" and a.get("frequency"):
                out.add(round(float(a["frequency"]), 3))
    return sorted(out)


def briefing_text(m, d):
    parts = [str(txt(d, m.get(k)) or "") for k in
             ("descriptionText", "descriptionBlueTask", "descriptionRedTask")]
    return "\n".join(parts), {"general": len(parts[0]), "blue": len(parts[1]), "red": len(parts[2])}


def saydo(m, d, seat, rf, text):
    """Automatic checks. Each returns (verdict, compared) so it can be argued with."""
    checks = {}
    if not text.strip():
        return {"n/a": "no briefing text"}
    # frequencies
    said = sorted({round(float(x), 3) for x in re.findall(r"\b(\d{2,3}\.\d{1,3})\b", text)
                   if 100 <= float(x) <= 400})
    presets = set()
    for r in (seat or {}).get("radios", {}).values():
        presets |= {round(float(v), 3) for v in r.values() if isinstance(v, (int, float))}
    known = presets | set(rf["group_freqs"]) | set(transmission_freqs(m))
    if said:
        miss = [f for f in said if f not in known]
        checks["frequencies"] = {"verdict": "gap" if miss else "ok",
                                 "briefed": said, "unmatched": miss}
    else:
        checks["frequencies"] = {"verdict": "n/a", "briefed": []}
    # tacan
    said_t = sorted({(int(n), b.upper()) for n, b in re.findall(r"\b(\d{1,3})\s*([XYxy])\b", text)
                     if 1 <= int(n) <= 126})
    beac = {(int(b["channel"]), (b.get("mode") or "X").upper()) for b in rf["beacons"]
            if isinstance(b.get("channel"), (int, float))}
    if said_t:
        miss = [t for t in said_t if t not in beac]
        checks["tacan"] = {"verdict": "gap" if (miss and beac) else ("n/a" if not beac else "ok"),
                           "briefed": said_t, "file": sorted(beac), "unmatched": miss}
    else:
        checks["tacan"] = {"verdict": "n/a"}
    # times: the briefed start-ish time vs the mission clock
    start = m.get("start_time", 0)
    # Four-digit tokens that are years (1900-2099) are narrative, not clock.
    times = [t for t in re.findall(r"\b([01]\d|2[0-3])([0-5]\d)\b(?!\.\d)", text)
             if not (t[0] in ("19", "20") and t[0] + t[1] != "2000" and int(t[0] + t[1]) >= 1900)]
    tmins = sorted({int(h) * 60 + int(mm) for h, mm in times})
    if tmins:
        smin = (int(start) // 60) % 1440
        near = [t for t in tmins if abs(t - smin) <= 90]
        checks["clock"] = {"verdict": "ok" if near else "gap",
                           "mission_start": hm(start),
                           "briefed": [f"{t // 60:02d}{t % 60:02d}" for t in tmins][:12]}
    else:
        checks["clock"] = {"verdict": "n/a", "mission_start": hm(start)}
    # date
    date = m.get("date") or {}
    fd = (date.get("Year"), date.get("Month"), date.get("Day"))
    months = "jan feb mar apr may jun jul aug sep oct nov dec".split()
    said_d = []
    for dd, mo, yy in re.findall(r"\b(\d{1,2})\s+([A-Za-z]{3})[A-Za-z]*\s+(\d{4})\b", text):
        if mo.lower()[:3] in months:
            said_d.append((int(yy), months.index(mo.lower()[:3]) + 1, int(dd)))
    for mo, dd, yy in re.findall(r"\b([A-Za-z]{3})[A-Za-z]*\s+(\d{1,2}),?\s+(\d{4})\b", text):
        if mo.lower()[:3] in months:
            said_d.append((int(yy), months.index(mo.lower()[:3]) + 1, int(dd)))
    if said_d:
        checks["date"] = {"verdict": "ok" if fd in said_d else "gap",
                          "file": fd, "briefed": sorted(set(said_d))[:6]}
    else:
        checks["date"] = {"verdict": "n/a", "file": fd}
    # callsign
    # The name the mission USES is the group/unit name (Reflected leaves the
    # callsign table at a stock value and names the group "ROCKET 11"), so the
    # check accepts either the callsign root or the group-name root.
    cs = (seat or {}).get("callsign") or ""
    gn = (seat or {}).get("group") or ""
    roots = {re.sub(r"[\s\-]*\d+$", "", str(x)).strip().lower() for x in (cs, gn) if x}
    roots = {r for r in roots if len(r) > 2}
    if roots and len(text) > 400:
        hit = any(r in text.lower() for r in roots)
        checks["callsign"] = {"verdict": "ok" if hit else "gap", "file": sorted(roots)}
    elif roots:
        checks["callsign"] = {"verdict": "n/a", "file": sorted(roots), "why": "briefing defers to a PDF"}
    return checks


def media(names):
    audio = sum(1 for n in names if n.lower().endswith((".ogg", ".wav", ".mp3")))
    kb = sum(1 for n in names if n.startswith("KNEEBOARD/"))
    imgs = sum(1 for n in names if n.lower().endswith((".jpg", ".png", ".jpeg")) and not n.startswith("KNEEBOARD/"))
    return {"audio": audio, "kneeboard": kb, "images": imgs, "files": len(names)}


def dictionary_facts(d):
    subs = [v for k, v in d.items() if k.startswith("DictKey_subtitle") and str(v).strip() not in ("", ".")]
    acts = [v for k, v in d.items() if k.startswith("DictKey_ActionText") and str(v).strip() not in ("", ".")]
    speakers = collections.Counter()
    for s in subs + acts:
        mm = re.match(r"\s*\[?([A-Za-z][^\]:]{1,24})[\]:]", str(s))
        if mm:
            speakers[mm.group(1).strip().upper()] += 1
    player_lines = sum(v for k, v in speakers.items() if k in ("PLAYER", "YOU"))
    return {"subtitles": len(subs), "action_texts": len(acts),
            "speakers": len(speakers), "player_lines": player_lines,
            "top_speakers": speakers.most_common(6),
            "radio_items": sorted({str(v).strip() for k, v in d.items()
                                   if k.startswith("DictKey_ActionRadioText") and str(v).strip()})[:30]}


def lua_facts(luas):
    tot = sum(len(v) for v in luas.values())
    apis = collections.Counter()
    for v in luas.values():
        for k in ("getDrawArgumentValue", "getFuel", "TransmitMessage", "setUserFlag",
                  "S_EVENT_SHOT", "addCommand", "outText", "outSound", "dostring_in",
                  "scheduleFunction", "mist", "MOOSE", "getAmmo"):
            if k in v:
                apis[k] += 1
    return {"files": len(luas), "bytes": tot, "apis": dict(apis)}


def warehouse_facts(w):
    n = 0
    for cat in ("airports", "warehouses"):
        for a in (w.get(cat) or {}).values():
            if a.get("unlimitedFuel") is False or a.get("unlimitedMunitions") is False \
                    or a.get("unlimitedAircrafts") is False:
                n += 1
    return n


def techniques(m, tc, rf, luas, seat):
    c, a = tc["conds"], tc["acts"]
    t = {
        "cockpit_arg_gates": c.get("c_argument_in_range", 0),
        "cockpit_param_gates": c.get("c_cockpit_param_equal_to", 0),
        "cockpit_clicks": a.get("a_cockpit_perform_clickable_action", 0),
        "random_flags": a.get("a_set_flag_random", 0),
        "missile_in_zone": c.get("c_missile_in_zone", 0) + c.get("c_bomb_in_zone", 0),
        "explosions": a.get("a_explosion_unit", 0) + a.get("a_explosion", 0),
        "radio_items": a.get("a_add_radio_item", 0),
        "wait_for_user": a.get("c_start_wait_for_user", 0),
        "radio_transmissions": a.get("a_radio_transmission", 0),
        "pictures": a.get("a_out_picture", 0),
        "moving_zones": c.get("c_unit_in_moving_zone", 0) + c.get("c_unit_outside_moving_zone", 0),
        "do_script": a.get("a_do_script", 0) + a.get("a_do_script_file", 0),
        "follow_tasks": rf["follow_tasks"],
        "single_unit_air_groups": rf["single_unit_air_groups"],
        "locked_etas": len((seat or {}).get("locked_etas") or []),
        "protected": bool(m.get("ext_loader")),
        "lua_files": len(luas),
    }
    return t


def scan_one(path: Path, D):
    m, d = D["mission"], D["dict"]
    seat = player_seat(m, d)
    tc = trigger_census(m)
    rf = route_facts(m, d)
    text, blen = briefing_text(m, d)
    opts = (m.get("forcedOptions") or {})
    date = m.get("date") or {}
    return {
        "path": str(path),
        "campaign": path.parent.name if path.is_dir() else path.parent.name,
        "name": path.name.replace(".miz", ""),
        "sortie": txt(d, m.get("sortie")),
        "theater": m.get("theater"),
        "date": f"{date.get('Year')}-{date.get('Month'):02d}-{date.get('Day'):02d}" if date else None,
        "start": hm(m.get("start_time")),
        "protected": bool(m.get("ext_loader")),
        "seat": seat,
        "triggers": tc,
        "routes": rf,
        "media": media(D["names"]),
        "dictionary": dictionary_facts(d),
        "lua": lua_facts(D["lua"]),
        "brief_len": blen,
        "forced": {k: opts.get(k) for k in ("immortal", "labels", "easyCommunication", "fuel", "weapons", "externalViews")},
        "warehouses_limited": warehouse_facts(D["warehouses"]),
        "saydo": saydo(m, d, seat, rf, text),
        "techniques": techniques(m, tc, rf, D["lua"], seat),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("-o", "--out", default="corpus_scan.json")
    args = ap.parse_args()
    root = Path(args.root)
    items = []
    if root.is_file():
        items = [root]
    else:
        items = sorted(p for p in root.rglob("*") if (p.is_dir() and (p / "mission").exists()) or p.suffix == ".miz")
    recs = []
    for p in items:
        try:
            D = load_dir(p) if p.is_dir() else load_miz(p)
            if not D["mission"]:
                print(f"!! no mission table: {p}", file=sys.stderr)
                continue
            recs.append(scan_one(p, D))
            print(f"ok  {p.parent.name} / {p.name}", file=sys.stderr)
        except Exception as e:  # keep going; the corpus is the point
            print(f"!! {p}: {e}", file=sys.stderr)
    Path(args.out).write_text(json.dumps(recs, indent=1, default=str))
    print(f"{len(recs)} records -> {args.out}")


if __name__ == "__main__":
    main()
