#!/usr/bin/env python3
"""Scenery keep-out SURVEY mission builder (Class-3 fix: statics on buildings).

pydcs exposes runways and parking slots but ZERO building/hangar geometry, so our
placement can drop a GSE truck or static on top of a hangar without ever knowing
the hangar is there (the occupancy registry only keeps OUR objects off each other).
DCS itself DOES know where the scenery is — `world.searchObjects` can enumerate it.

This builds a throwaway mission that, 15 s in, sweeps a sphere around each target
airfield and logs one line per scenery object to the DCS log:

    SCNKEEP|<airfield>|<typeName>|<x_north>|<z_east>|<footprint_radius_m>

`footprint_radius_m` = half the larger AABB side from the object's descriptor
(-1 if DCS didn't give a box). Hand the dcs.log to scripts/import_scenery.py, which
bakes the big footprints into missiongen/data/scenery_keepout.json; the placement
keep-out then rejects anything landing inside a building. No shipped file contains
Lua — offline developer/data tool only, same pattern as the parking survey.

Usage:
  python3 scripts/build_scenery_survey.py <map_key> [Airfield ...]
  # default airfields = every PRESET field on the map (blue+red, all eras)

Then in DCS: Missions -> load scenery_survey_<map>.miz -> fly/wait ~20 s -> exit.
Objects are in dcs.log (filter "SCNKEEP").
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "vendor"))

try:
    import dcs
    from dcs import planes
    from dcs.mission import StartType
    from dcs.triggers import TriggerStart
    from dcs.action import DoScript
    from dcs.translation import String
except ModuleNotFoundError as e:
    missing = getattr(e, "name", str(e))
    raise SystemExit(
        f"Missing dependency '{missing}'. Use the app's venv:\n"
        "    source .venv/bin/activate\n"
        f"or: pip3 install {missing} --break-system-packages")

from missiongen.resolver import load_json, resolve_terrain, resolve_country

# Sweep radius around each field reference point — covers the ramp + surrounding
# hangar line at a large base like Nellis without pulling in the whole map.
SWEEP_RADIUS_M = 2600


def _preset_fields(map_key, maps):
    """Union of blue+red airbases across every era preset for the map."""
    names = set()
    for era_preset in maps[map_key].get("presets", {}).values():
        for side in ("blue", "red"):
            for f in era_preset.get(side, {}).get("airbases", []) or []:
                names.add(f)
    return names


def _lua(fields):
    # fields: list of (name, x_north, z_east). Embedded verbatim as a Lua table.
    rows = ",\n".join(
        f'  {{name="{n}", x={x:.1f}, z={z:.1f}}}' for n, x, z in fields)
    return (
        "local FIELDS = {\n" + rows + "\n}\n" + r"""
local function _export()
  local out = {}
  for _, fld in pairs(FIELDS) do
    local h = 0
    pcall(function() h = land.getHeight({x = fld.x, y = fld.z}) or 0 end)
    local vol = {id = world.VolumeType.SPHERE,
                 params = {point = {x = fld.x, y = h, z = fld.z}, radius = """
        + str(SWEEP_RADIUS_M) + r"""}}
    local n = 0
    world.searchObjects(Object.Category.SCENERY, vol, function(obj)
      local ok, p = pcall(function() return obj:getPoint() end)
      if ok and p then
        local tn = "?"
        pcall(function() tn = obj:getTypeName() or "?" end)
        local rad = -1
        local ok2, desc = pcall(function() return obj:getDesc() end)
        if ok2 and desc and desc.box and desc.box.min and desc.box.max then
          local dx = desc.box.max.x - desc.box.min.x
          local dz = desc.box.max.z - desc.box.min.z
          rad = math.max(dx, dz) / 2.0
        end
        env.info(string.format("SCNKEEP|%s|%s|%.1f|%.1f|%.1f",
                               fld.name, tn, p.x, p.z, rad))
        n = n + 1
      end
      return true
    end)
    env.info("SCNKEEP_FIELD|" .. fld.name .. "|" .. tostring(n))
    out[#out + 1] = fld.name .. ":" .. n
  end
  env.info("SCNKEEP_DONE|fields=" .. tostring(#FIELDS))
  trigger.action.outText(
    "Scenery survey done (" .. table.concat(out, "  ") .. ").\n" ..
    "Now EXIT and send Saved Games/DCS/Logs/dcs.log", 120)
end
timer.scheduleFunction(function() _export() end, nil, timer.getTime() + 15)
""")


def build(map_key, airfields=None):
    maps = load_json("maps")
    if map_key not in maps:
        raise SystemExit(f"unknown map '{map_key}'. Known: {', '.join(maps)}")
    terrain_cls = resolve_terrain(maps[map_key]["terrain_class"])
    m = dcs.Mission(terrain_cls())

    try:
        country = resolve_country("USA")()
        m.coalition["blue"].add_country(country)
    except Exception as e:
        raise SystemExit(f"could not add country: {e}")

    all_ports = m.terrain.airports
    wanted = set(airfields) if airfields else _preset_fields(map_key, maps)
    if not wanted:
        wanted = set(all_ports.keys())
    missing = [a for a in wanted if a not in all_ports]
    if missing:
        print(f"WARNING: not on {map_key}: {', '.join(sorted(missing))}")
    targets = [all_ports[a] for a in sorted(wanted) if a in all_ports]
    if not targets:
        raise SystemExit("no valid target airfields")

    fields = [(ap.name, ap.position.x, ap.position.y) for ap in targets]

    # player slot so it's flyable in SP (export fires once the mission is live)
    player_field = targets[0]
    player_field.set_blue()
    try:
        pg = m.flight_group_from_airport(
            country, "SURVEY PILOT", planes.Su_25T, player_field,
            start_type=StartType.Cold, group_size=1)
        pg.units[0].set_player()
    except Exception as e:
        print(f"  (no player slot: {e} — still runnable via ME)")

    trig = TriggerStart(comment="scenery keep-out survey export")
    trig.add_action(DoScript(String(_lua(fields))))
    m.triggerrules.triggers.append(trig)

    out = f"scenery_survey_{map_key}.miz"
    m.save(out)
    print(f"built {out}: sweeping {len(fields)} field(s) — "
          f"{', '.join(n for n, _, _ in fields)}")
    print("Load in DCS, wait ~20 s, exit. Then run scripts/import_scenery.py on dcs.log.")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    build(sys.argv[1], sys.argv[2:] or None)
