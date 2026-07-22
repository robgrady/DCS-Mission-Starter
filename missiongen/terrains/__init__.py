"""Mission Starter terrain extensions — maps not yet in upstream pydcs.

These live OUTSIDE vendor/dcs (which stays a pristine, unmodified pydcs copy per
its LGPL provenance). Each terrain is generated from a real DCS install export
exactly the way pydcs's own tools generate official maps, and is destined for an
upstream PR. maps.json points at these classes via resolve_terrain().

`install()` runtime-patches pydcs's Mission.load_file theatre chain (a hardcoded
if/elif) to fall back to EXTRA_TERRAINS for theatres pydcs doesn't know — the
same keep-vendor-pristine pattern as missiongen._determinism. If the pydcs
source ever drifts and the patch can't apply, we leave the original intact and
only lose *loading* extension-terrain .miz files (saving never needs the patch).
"""
from .afghanistan import Afghanistan  # noqa: F401

EXTRA_TERRAINS = {
    "Afghanistan": Afghanistan,
}

_installed = False


def install():
    global _installed
    if _installed:
        return
    _installed = True
    import inspect
    import textwrap
    import dcs.mission as _mm

    try:
        src = textwrap.dedent(inspect.getsource(_mm.Mission.load_file))
        line = next((l for l in src.splitlines() if "Unknown theatre" in l), None)
        if line is None:
            return                      # pydcs drifted — degrade gracefully
        indent = line[:len(line) - len(line.lstrip())]
        target = line.strip()
        replacement = (
            'if imp_mission["theatre"] in __XT: self.terrain = '
            '__XT[imp_mission["theatre"]]()\n'
            + indent + "else: " + target)
        src = src.replace(indent + target, indent + replacement, 1)
        ns = dict(_mm.__dict__)
        ns["__XT"] = EXTRA_TERRAINS      # inject the registry directly
        exec(compile(src, _mm.__file__, "exec"), ns)
        _mm.Mission.load_file = ns["load_file"]
    except Exception:
        pass                            # never break generation over a loader nicety
