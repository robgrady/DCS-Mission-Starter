# Runbook: exporting Afghanistan terrain data for pydcs

Goal: produce the two generated files pydcs needs for a new map — `airports.py` and `projection.py` — plus a small hand-written metadata class. Your part is two trips through the beta Mission Editor to dump raw data from the install. Everything after that is repo work I do.

Do Afghanistan first end-to-end. Iraq is the same runbook with the name swapped.

---

## Part A — Airport / parking export (produces `standlist.lua`)

This is 95% of the value. It dumps every airport, runway, parking slot, ATC radio, and beacon on the map.

### A1. Back up the file you're about to edit

    <DCS install>\MissionEditor\modules\me_map_window.lua

Copy it somewhere safe first. You'll revert this after the export — it's a temporary hack, not a permanent change.

### A2. Paste the official export function

Open `me_map_window.lua` and paste this function in verbatim (this is pydcs's own exporter, unchanged):

    function dumpairportdata()
        local S = require('Serializer')
        local airdromedump = {}
        for k, v in pairs(terrainDATA.getTerrainDATA('Airdromes')) do
            local sList = Terrain.getStandList(v.roadnet, {"SHELTER","FOR_HELICOPTERS","FOR_AIRPLANES","WIDTH","LENGTH","HEIGHT"})
            info = {}
            info["airport"] = v
            info["standlist"] = sList
            info["frequencies"] = AirdromeData.getAirdrome(AirdromeData.getAirdromeId(k))
            airdromedump[k] = info
        end
        local f = base.io.open("standlist.lua", 'w')
        if f then
            local s = S.new(f)
            s:serialize_simple2('airports', airdromedump)
            f:close()
        else
            showWarningMessageBox(_('Error saving standlist'))
        end
    end

### A3. Call it when an aircraft is placed

Find the `createAircraft()` function in the same file and add a call to `dumpairportdata()` inside it. The dump then fires the moment you drop an aircraft in the editor.

### A4. Run the dump

1. Launch DCS. If the ME won't let you place aircraft (clicking does nothing), the Lua edit is broken — check `Saved Games/DCS/Logs/dcs.log` and fix before continuing.
2. New mission in the editor, **Afghanistan** map.
3. Place any one aircraft, anywhere. Any type works.
4. `standlist.lua` is written to the **DCS installation directory** (not Saved Games — the install root).

### A5. Revert

Restore `me_map_window.lua` from your A1 backup. Done in the game.

### A6. Send me `standlist.lua`

That's the only file I need from this part. I run:

    python tools/airport_import.py -t afghanistan C:\standlist.lua

which writes `dcs/terrain/afghanistan/airports.py`.

> **The one risk:** Afghanistan is a newer map and may use a parking/beacon `slot_version` the importer doesn't parse yet. If it errors, I patch the importer — and that patch is itself a useful upstream PR. We'll only know once your `standlist.lua` is in hand.

---

## Part B — Projection export (produces `projection.py`)

This derives the map's transverse-mercator parameters (false easting/northing). It needs a provisional Terrain stub to exist first, so the order is: **A → stub → B.**

### B0. (My step) Provisional terrain stub

Before you run this pass I commit a stub `afghanistan.py`: guessed UTM central meridian, zero false easting/northing, real map bounds and center. The projection tool needs a Terrain instance to build its probe mission; it then computes the true offsets and validates them against the airports from Part A.

### B1. Run the probe

I hand you a small mission file (or you run `python tools/export_map_projection.py --map afghanistan`, which builds it). Then:

1. Load the probe mission in DCS.
2. Let it run a few seconds — it dumps the lat/lon + x/z of the 0/0 point and every airport via Lua.
3. Close DCS.

### B2. Send me the exported coordinate file

The tool reads it, computes `projection.py`, and validates projection error against the real airport positions. Low error = correct.

---

## Part C — Metadata (my step, ~1–2 hrs, no ME needed)

I hand-write the ~40-line `afghanistan.py` Terrain subclass: center lat/long, map bounds Rectangle, 12-month temperature table, UTC offset, bullseye. Then wire `__init__.py`, register the terrain, and smoke-test that `Mission(Afghanistan())` builds and a flight lands on a parking slot.

---

## What I need from you, in order

1. **`standlist.lua`** (Part A) — the big one.
2. **The projection coordinate dump** (Part B) — after I hand you the stub + probe mission.

Then Iraq: repeat A and B with "iraq" in place of "afghanistan".

## Upstream

No pydcs issue or PR covers either map. I'll open an "Add Afghanistan / Iraq terrain" issue to flag intent and confirm format expectations with the maintainers, then submit the generated files + metadata as a PR. Data is derived from the install exactly as pydcs already does for every official map, so there's clear precedent.
