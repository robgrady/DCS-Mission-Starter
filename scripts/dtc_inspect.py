#!/usr/bin/env python3
"""DTC / DTM inspector — reverse-engineer where DCS stores the Data Transfer
Cartridge inside a .miz, so Mission Starter can emit it.

DCS stores the cartridge "as data within the mission itself" (default), but the
exact schema is undocumented and brand-new for the F-14B(U)'s DTM. This tool
finds it two ways:

  DIFF MODE (best):  python scripts/dtc_inspect.py plain.miz dtc.miz
     Save the SAME mission twice - once untouched, once after configuring a DTC
     in the ME (a couple of plot lines + a bullseye + a waypoint). This reports
     exactly which zip members and which mission-tree paths appeared/changed ->
     that IS the DTC payload, isolated.

  SURVEY MODE:       python scripts/dtc_inspect.py dtc.miz
     One DTC-configured mission: lists every zip member and hunts the parsed
     mission tree for DTC-ish keys/paths, dumping the subtrees it finds.

Output: a human-readable report + `dtc_payload.lua` (the isolated subtree, ready
to study / templatize). No writing back — read-only.
"""
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))

import dcs.lua  # noqa: E402
from dcs.lua.serialize import dumps  # noqa: E402

# tokens that betray a cartridge/DTM/plot-line payload anywhere in the tree
DTC_TOKENS = ("dtc", "dtm", "cartridge", "datacartridge", "data_cartridge",
              "plot", "plotline", "plot_line", "waypoint", "wpt", "steerpoint",
              "bullseye", "fixpoint", "fix_point", "mdl", "asq", "cdms",
              "lantirn", "lts", "navgrid", "nav_grid", "jdam", "preplan",
              "hb_", "cdnu", "route_dtm")
MEMBER_ORDER = ["mission", "options", "warehouses",
                "l10n/DEFAULT/dictionary", "l10n/DEFAULT/mapResource"]


def _members(miz):
    with zipfile.ZipFile(miz) as z:
        return {n: z.read(n) for n in z.namelist()}


def _parse(name, raw):
    try:
        return dcs.lua.loads(raw.decode("utf-8", "ignore"))
    except Exception:
        return None


def _walk(node, path=""):
    """Yield (path, key, value) for every dict entry in the tree."""
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}.{k}"
            yield p, k, v
            yield from _walk(v, p)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{path}[{i}]")


def _looks_dtc(key):
    ks = str(key).lower()
    return any(tok in ks for tok in DTC_TOKENS)


def _flat(node, path=""):
    """Flatten a parsed tree to {path: leaf_repr} for structural diffing."""
    out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(_flat(v, f"{path}.{k}"))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.update(_flat(v, f"{path}[{i}]"))
    else:
        out[path] = repr(node)
    return out


def survey(miz):
    print(f"\n=== SURVEY: {Path(miz).name} ===")
    mem = _members(miz)
    print(f"\n[zip members] {len(mem)}")
    for n in sorted(mem, key=lambda x: (x not in MEMBER_ORDER, x)):
        tag = "" if n in MEMBER_ORDER else "  <-- non-standard (candidate DTC file!)"
        print(f"  {len(mem[n]):>9} B  {n}{tag}")

    hits = []
    for name, raw in mem.items():
        tree = _parse(name, raw)
        if tree is None:
            continue
        for path, key, val in _walk(tree):
            if _looks_dtc(key):
                size = len(dumps(val)) if isinstance(val, (dict, list)) else 0
                hits.append((name, path, key, size, val))

    print(f"\n[DTC-ish keys in parsed trees] {len(hits)}")
    seen = set()
    for name, path, key, size, val in sorted(hits, key=lambda h: -h[3])[:40]:
        short = path if len(path) < 90 else "…" + path[-88:]
        print(f"  {name:28} {short}   ({size} B)")
        seen.add((name, path))

    # dump the biggest DTC-ish subtree for study
    if hits:
        name, path, key, size, val = max(hits, key=lambda h: h[3])
        out = ROOT / "dtc_payload.lua"
        out.write_text(dumps(val, varname=key.replace(" ", "_"), indent=1))
        print(f"\n[wrote] {out.name}  (largest DTC-ish subtree: {name}:{path})")
    else:
        print("\n(no DTC-ish keys found by name — run DIFF MODE, which finds it")
        print(" structurally even if the keys are opaque)")


def diff(plain, dtcm):
    print(f"\n=== DIFF: {Path(plain).name}  ->  {Path(dtcm).name} ===")
    ma, mb = _members(plain), _members(dtcm)

    # 1) new / changed / removed ZIP MEMBERS (a sidecar DTC file shows here)
    new = [n for n in mb if n not in ma]
    changed = [n for n in mb if n in ma and ma[n] != mb[n]]
    removed = [n for n in ma if n not in mb]
    print("\n[zip members]")
    for n in new:
        print(f"  + NEW      {len(mb[n]):>9} B  {n}   <-- candidate DTC file")
    for n in changed:
        print(f"  ~ CHANGED  {len(ma[n]):>9}->{len(mb[n])} B  {n}")
    for n in removed:
        print(f"  - REMOVED  {n}")
    if not (new or changed):
        print("  (identical member set & bytes — DTC may be saved-games-side, not in-miz)")

    # 2) structural DIFF of the parsed 'mission' tree — isolates the DTC subtree
    ta, tb = _parse("mission", ma.get("mission", b"")), _parse("mission", mb.get("mission", b""))
    added_paths = []
    if ta is not None and tb is not None:
        fa, fb = _flat(ta), _flat(tb)
        added = [p for p in fb if p not in fa]
        chg = [p for p in fb if p in fa and fa[p] != fb[p]]
        # collapse to the shallowest new subtree roots
        roots = sorted({".".join(p.split(".")[:6]) for p in added})
        added_paths = added
        print(f"\n[mission tree]  +{len(added)} new leaves · ~{len(chg)} changed")
        print("  new subtree roots (the DTC payload lives under one of these):")
        for r in roots[:30]:
            print(f"    {r}")
        for p in chg[:12]:
            print(f"    ~ {p}: {fa[p]} -> {fb[p]}")

    # 3) isolate + dump the largest NEW subtree from the mission dict
    if ta is not None and tb is not None and added_paths:
        # find the top-level-ish new key by walking tb for keys absent in ta
        def subtrees(node_b, node_a, path=""):
            res = []
            if isinstance(node_b, dict):
                for k, v in node_b.items():
                    ap = node_a.get(k) if isinstance(node_a, dict) else None
                    if ap is None:
                        res.append((f"{path}.{k}", k, v))
                    else:
                        res += subtrees(v, ap, f"{path}.{k}")
            return res
        cand = subtrees(tb["mission"], ta["mission"])
        cand = [c for c in cand if isinstance(c[2], (dict, list))]
        if cand:
            path, key, val = max(cand, key=lambda c: len(dumps(c[2])))
            out = ROOT / "dtc_payload.lua"
            out.write_text(dumps(val, varname=str(key).replace(" ", "_"), indent=1))
            print(f"\n[wrote] {out.name}  (new mission subtree at {path}, "
                  f"{len(dumps(val))} B) — this is the DTC payload to templatize")

    # also dump any brand-new zip member verbatim (sidecar cartridge)
    for n in new:
        safe = n.replace("/", "_")
        (ROOT / f"dtc_member_{safe}").write_bytes(mb[n])
        print(f"[wrote] dtc_member_{safe}  (verbatim new zip member)")


def main(argv):
    if len(argv) == 2:
        survey(argv[1])
    elif len(argv) == 3:
        diff(argv[1], argv[2])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
