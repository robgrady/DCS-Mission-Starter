#!/usr/bin/env python3
"""F-14B(U) release-readiness SURVEY mission builder.

Same pattern as the parking-heading surveys: a plain .miz with an embedded Lua
exporter that writes everything we need to dcs.log — no dependencies for the
person flying it.

What it collects (for the Day-0 patch on release day):
  * The EXACT DCS type id of the F-14B(U)  (our provisional guess is "F-14B-U";
    if Heatblur shipped anything else, every generated mission would break)
  * Display name, category, and the bounding box -> real length/span/height
    (feeds the occupancy registry so GSE/statics keep clear of parked B(U)s)
  * The unit's attributes table (carrier-capable flags etc.)

How Rob uses it:
  1. Drop f14bu_survey.miz into Saved Games/DCS/Missions.
  2. Open it in the BETA Mission Editor and add ONE F-14B(U) anywhere
     (player or client, parked at Kutaisi is fine). Bonus: also try giving
     one a "Takeoff from ship" waypoint on the Stennis offshore — if the ME
     allows it, that confirms carrier clearance.
  3. SAVE the mission (the saved .miz itself captures the type id AND the
     Radio preset table if the module supports ME presets).
  4. Run the mission for ~1 minute. The exporter fires at +15 s and logs one
     BUSURVEY_OUT line per air unit.
  5. Send back BOTH files: the saved .miz and Saved Games/DCS/Logs/dcs.log.

A released F-14B is parked at Kutaisi as a CONTROL ROW — its line shows the
format working even before the B(U) is added.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))

import dcs
from dcs import planes, ships
from dcs.mission import StartType
from dcs.triggers import TriggerStart
from dcs.action import DoScript
from dcs.translation import String

# Reads every AIR unit in the mission (all sides + neutrals) and dumps its
# identity + geometry to dcs.log. env.info always works (io/lfs are sanitized
# on most installs, dcs.log is the reliable channel — same as the parking
# survey).
LUA_EXPORT = r"""
local function _dump()
  local n = 0
  for _, side in pairs({0, 1, 2}) do
    local groups = coalition.getGroups(side)
    if groups then
      for _, grp in pairs(groups) do
        local ok, units = pcall(function() return grp:getUnits() end)
        if ok and units then
          for _, u in pairs(units) do
            local ok2, desc = pcall(function() return u:getDesc() end)
            if ok2 and desc then
              local tn = desc.typeName or "?"
              local dn = desc.displayName or "?"
              local box = desc.box
              local L, S, H = -1, -1, -1
              if box and box.min and box.max then
                L = box.max.x - box.min.x
                S = box.max.z - box.min.z
                H = box.max.y - box.min.y
              end
              local attrs = {}
              if desc.attributes then
                for a, _v in pairs(desc.attributes) do attrs[#attrs+1] = a end
              end
              table.sort(attrs)
              env.info(string.format(
                "BUSURVEY_OUT|%s|%s|len=%.2f|span=%.2f|hgt=%.2f|attrs=%s",
                tn, dn, L, S, H, table.concat(attrs, ",")))
              n = n + 1
            end
          end
        end
      end
    end
  end
  env.info("BUSURVEY_DONE|units=" .. tostring(n))
  trigger.action.outText(
    "F-14B(U) survey: " .. n .. " air units dumped to dcs.log.\n" ..
    "Now just EXIT and send BOTH files:\n" ..
    "  1. this mission's SAVED .miz (after you added the B-U in the ME)\n" ..
    "  2. Saved Games/DCS/Logs/dcs.log", 120)
end
timer.scheduleFunction(function() _dump() end, nil, timer.getTime() + 15)
timer.scheduleFunction(function() _dump() end, nil, timer.getTime() + 45)
"""


def main():
    m = dcs.Mission(dcs.terrain.caucasus.Caucasus())
    from dcs.countries import USA
    usa = m.country(USA().name)

    kutaisi = m.terrain.airports["Kutaisi"]
    kutaisi.set_blue()

    # CONTROL ROW: a released F-14B parked cold — proves the exporter format
    # before the B(U) is added, and gives a same-family baseline to compare.
    m.flight_group_from_airport(
        usa, "CONTROL F-14B", planes.F_14B, kutaisi,
        start_type=StartType.Cold, group_size=1).uncontrolled = True

    # Stennis offshore so the ME "Takeoff from ship" clearance test is one
    # drag-and-drop away (base-game hull -> loads for everyone).
    from dcs import mapping
    anchor = mapping.Point(-310000, 530000, m.terrain)   # validated Black Sea box
    m.ship_group(usa, "SURVEY CVN", ships.Stennis, anchor, heading=240)

    trig = TriggerStart(comment="F-14B(U) survey export")
    trig.add_action(DoScript(String(LUA_EXPORT)))
    m.triggerrules.triggers.append(trig)

    m.set_description_text(
        "F-14B(U) RELEASE SURVEY\n"
        "1. In the (beta) Mission Editor: add ONE F-14B(U), parked anywhere.\n"
        "   Bonus: give a second one 'Takeoff from ship' on SURVEY CVN.\n"
        "2. SAVE the mission.\n"
        "3. Fly/run it for one minute (exporter fires at +15s and +45s).\n"
        "4. Send back the SAVED .miz AND Saved Games/DCS/Logs/dcs.log.\n"
        "The parked F-14B is a control row - its BUSURVEY_OUT line shows the "
        "export working.")

    out = ROOT / "f14bu_survey.miz"
    m.save(str(out))
    print(f"built {out}")


if __name__ == "__main__":
    main()
