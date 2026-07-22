#!/usr/bin/env python3
"""Projection PROBE mission builder (extension terrains: Afghanistan, Iraq...).

v2: logs through env.info() to dcs.log — NO MissionScripting de-sanitization
needed (the upstream coord_export.lua writes a file via io/lfs, which stock DCS
sandboxes to nil). Same survey pattern as the parking/scenery/B(U) probes.

Usage:  python scripts/build_projection_probe.py afghanistan
Then:   fly probe_<map>.miz ~30 s on a STOCK install, send Saved Games/DCS/Logs/dcs.log
Import: python scripts/import_projection.py <map> dcs.log
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))

LUA = r"""
local function dump_coords()
    local n = 0
    local bases = world.getAirbases()
    for i = 1, #bases do
        local ok, err = pcall(function()
            local p = Airbase.getPoint(bases[i])
            local lat, lon, alt = coord.LOtoLL(p)
            env.info(string.format("PROJPROBE|%s|%.9f|%.9f|%.3f|%.3f",
                     Airbase.getName(bases[i]), lat, lon, p.x, p.z))
        end)
        if ok then n = n + 1 else env.info("PROJPROBE_ERR|" .. tostring(err)) end
    end
    local lat, lon = coord.LOtoLL({x = 0, y = 0, z = 0})
    env.info(string.format("PROJPROBE|__ZERO__|%.9f|%.9f|0.000|0.000", lat, lon))
    env.info("PROJPROBE_DONE|" .. tostring(n))
end
timer.scheduleFunction(function()
    local ok, err = pcall(dump_coords)
    if not ok then env.info("PROJPROBE_ERR|" .. tostring(err)) end
end, nil, timer.getTime() + 10)
"""


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "afghanistan"
    import missiongen  # registers extension terrains + loader patch
    from dcs.mission import Mission
    from dcs.triggers import TriggerStart
    from dcs.action import DoScriptFile
    from missiongen.resolver import resolve_terrain, load_json
    terrain_cls = resolve_terrain(load_json("maps")[key]["terrain_class"])
    m = Mission(terrain_cls())
    import tempfile
    lua_path = Path(tempfile.mkdtemp()) / "projprobe.lua"
    lua_path.write_text(LUA)
    t = TriggerStart(comment="Projection probe (env.info -> dcs.log)")
    # resource-file + DoScriptFile is the PROVEN execution path (v1 ran this
    # way); inline DoScript via m.string() serializes as a dictionary key that
    # DCS compiles literally -> "'=' expected near '<eof>'".
    t.add_action(DoScriptFile(m.map_resource.add_resource_file(str(lua_path))))
    m.triggerrules.triggers.append(t)
    out = ROOT / f"probe_{key}.miz"
    m.save(str(out))
    print(f"built {out.name} — fly ~30 s on a stock install, then send "
          f"Saved Games/DCS/Logs/dcs.log (filter PROJPROBE)")


if __name__ == "__main__":
    main()
