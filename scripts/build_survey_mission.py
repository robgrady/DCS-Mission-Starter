#!/usr/bin/env python3
"""Parking-heading SURVEY mission builder.

pydcs does not expose the painted parking-line heading, but DCS DOES orient an
aircraft to that line when it spawns one from a ramp slot. This builds a throwaway
mission that:

  1. drops one uncontrolled aircraft on EVERY airplane parking spot of the chosen
     airfield(s) — DCS seats each at the painted-line heading on load, and
  2. embeds a Lua script that (15 s in) reads every unit's heading and writes one
     line per spot to the DCS log:  PSURVEY_OUT|<airport>|<slot>|<heading>

You run it once in DCS, then hand the log (or Saved Games/DCS/parking_survey.txt)
to scripts/import_survey.py, which bakes the exact per-spot headings into
missiongen/data/parking_headings.json. No file the tool ships ever contains Lua —
this is an offline developer/data tool only.

Usage:
  python3 scripts/build_survey_mission.py <map_key> [Airfield Name] [Another Field] ...
  # no airfield names => ALL airfields on the map (heavy; prints a warning)

Then in DCS: Missions -> load survey_<map>.miz -> fly/wait 20 s -> exit.
Headings are in dcs.log (filter "PSURVEY_OUT") and in Saved Games/DCS/parking_survey.txt.
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
        f"Missing dependency '{missing}'. This tool needs the same packages as the "
        "app.\nEasiest fix — use the environment the launcher built:\n"
        "    source .venv/bin/activate   (run run_mac.command once first if there is no .venv)\n"
        "    python3 scripts/build_survey_mission.py <map> [Airfield ...]\n"
        f"Or install it directly:  pip3 install {missing}"
        "   (add --user or --break-system-packages on recent macOS)")

from missiongen.resolver import load_json, resolve_terrain, resolve_country

# Compact, widely-available jet — small footprint seats on virtually any airplane
# stand. Heading is a property of the slot, not the airframe, so type is arbitrary.
SURVEY_TYPE = planes.MiG_15bis

# Embedded exporter. Reads each PSURVEY-tagged unit's true heading from its
# orientation vector (DCS world: x=North, z=East => heading = atan2(x.z, x.x)).
LUA_EXPORT = r"""
local function _export()
  local out = {}
  for _, side in pairs({0, 1, 2}) do
    local groups = coalition.getGroups(side)
    if groups then
      for _, grp in pairs(groups) do
        local ok, units = pcall(function() return grp:getUnits() end)
        if ok and units then
          for _, u in pairs(units) do
            local name = u:getName()
            if name and string.sub(name, 1, 8) == "PSURVEY|" then
              local p = u:getPosition()
              local hdg = math.deg(math.atan2(p.x.z, p.x.x))
              if hdg < 0 then hdg = hdg + 360 end
              local a, s = string.match(name, "^PSURVEY|(.-)|(.+)$")
              if a and s then
                local line = "PSURVEY_OUT|" .. a .. "|" .. s .. "|" .. string.format("%.1f", hdg)
                env.info(line)
                table.insert(out, line)
              end
            end
          end
        end
      end
    end
  end
  env.info("PSURVEY_DONE|count=" .. tostring(#out))
  -- tidy file if the install allows it (most don't — io/lfs are sanitized by
  -- default); dcs.log via env.info above ALWAYS works and is the reliable output.
  if io and lfs then
    local ok, f = pcall(io.open, lfs.writedir() .. "parking_survey.txt", "w")
    if ok and f then f:write(table.concat(out, "\n")); f:close() end
  end
  trigger.action.outText("Parking survey done: " .. #out .. " spots.\n" ..
    "Now just EXIT. Send the file:\n" ..
    "Saved Games/DCS/Logs/dcs.log", 120)
end
timer.scheduleFunction(function() _export() end, nil, timer.getTime() + 15)
"""


def build(map_key, airfields=None):
    maps = load_json("maps")
    if map_key not in maps:
        raise SystemExit(f"unknown map '{map_key}'. Known: {', '.join(maps)}")
    terrain_cls = resolve_terrain(maps[map_key]["terrain_class"])
    m = dcs.Mission(terrain_cls())

    usa = resolve_country("USA")
    m.coalition["blue"].add_country(usa())
    country = list(m.coalition["blue"].countries.values())[0]

    all_ports = m.terrain.airports
    if airfields:
        missing = [a for a in airfields if a not in all_ports]
        if missing:
            print(f"WARNING: not on {map_key}: {', '.join(missing)}")
        targets = [all_ports[a] for a in airfields if a in all_ports]
    else:
        targets = list(all_ports.values())
        print(f"WARNING: surveying ALL {len(targets)} airfields on {map_key} — "
              "the mission may be slow to load. Name specific fields to narrow it.")

    # A player slot so the mission is flyable in single-player (the export timer
    # runs once the mission is live). Su-25T ships FREE with DCS — everyone has it.
    player_field = targets[0] if targets else list(all_ports.values())[0]
    player_field.set_blue()
    try:
        pg = m.flight_group_from_airport(
            country, "SURVEY PILOT", planes.Su_25T, player_field,
            start_type=StartType.Cold, group_size=1)
        pg.units[0].set_player()
    except Exception as e:
        print(f"  (could not add player slot: {e} — mission still runnable via ME)")

    total_spots = 0
    total_placed = 0
    for ap in targets:
        ap.set_blue()
        spots = [s for s in ap.parking_slots if s.unit_id is None and s.airplanes]
        total_spots += len(spots)
        placed_here = 0
        for slot in spots:
            gname = f"PSURVEY|{ap.name}|{slot.slot_name}"
            try:
                grp = m.flight_group_from_airport(
                    country, gname, SURVEY_TYPE, ap,
                    start_type=StartType.Cold, group_size=1,
                    parking_slots=[slot])
            except Exception:
                continue                     # type can't seat here — skip
            grp.uncontrolled = True          # inert: parked, never taxis
            grp.units[0].name = gname        # unit name is the export key
            placed_here += 1
        total_placed += placed_here
        print(f"  {ap.name:<28} {placed_here}/{len(spots)} spots")

    # embed the exporter at mission start
    trig = TriggerStart(comment="parking-heading survey export")
    trig.add_action(DoScript(String(LUA_EXPORT)))
    m.triggerrules.triggers.append(trig)

    out = f"survey_{map_key}.miz"
    m.save(out)
    print(f"\nbuilt {out}: {total_placed}/{total_spots} spots placed across "
          f"{len(targets)} airfield(s)")
    print("Load it in DCS, wait ~20 s, exit. Then run scripts/import_survey.py "
          "on your dcs.log or parking_survey.txt.")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    build(sys.argv[1], sys.argv[2:] or None)
