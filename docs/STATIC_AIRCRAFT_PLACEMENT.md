# Static aircraft placement in Sortie Starter — a handoff

*Written 3 October 2026 at v1.106.0 for an agent picking this subsystem up.
Everything below is read out of the code, the data packs and the changelog;
file paths are relative to the repository root.*

## 1. What the subsystem does

"Airfield dressing" (building blocks BB-1..3) makes the ramps of a generated
mission look occupied: era- and nation-correct aircraft parked on the field's
real parking stands, facing the painted line, in squadron rows, with ground
equipment beside them and infrastructure clutter near the ramp — and nothing
on a runway, a taxiway, an occupied stand or (where surveyed) a building.
It runs on every friendly and enemy field the mission uses, after every
flying group has claimed its stands, and it is deterministic: the same recipe
and seed produce the same ramp byte for byte.

The whole problem exists because of three gaps in pydcs, the mission
framework the generator is built on. pydcs exposes each airport's parking
stands (position, size, name, a `large` flag) but **not the stand's parking
heading**, **not the airfield's buildings**, and **not the field's
elevation**. DCS itself knows all three. Every design below is a way of
getting at that knowledge honestly.

## 2. The decisions, in order of importance

**Aircraft go on surveyed stands only; nothing else is ever on a stand.**
Parking stands are the one piece of ground pydcs can vouch for. Free-placed
objects (ground equipment, infrastructure) are validated against runway
keep-out corridors, occupied stands and, when a scenery survey exists for the
map, building footprints (`missiongen/placement.py`, `AirfieldKeepOut`).
Runways are modelled as corridors through the airport reference point —
1,900 m half-length, 150 m half-width — because pydcs gives runway headings
but not geometry.

**Two placement modes, and static is the default.** `dress_aircraft_mode`:
- `static` — DCS static objects. Instant, inert, no radar contacts, no
  spawn-in pop-in. Facing is *ours* to get right (see §3).
- `parked_ai` — uncontrolled AI flights on the real stand. DCS applies the
  painted-line heading itself, so facing is exact, but each one is a live
  unit: FPS, map contacts, and they stream in over the first seconds.
The caps differ per mode (`AUTO_CAP_PER_FIELD`: static 10/18/28 per field for
sparse/normal/busy, parked_ai 5/8/14); an explicit fill percentage overrides
the cap.

**Facing is measured, not guessed, wherever it has been measured.** This is
the expensive part of the subsystem and the reason it works (§3).

**A stand is judged by the airframe, not a magic number** (v1.47.0).
`stand_fits()` compares the aircraft's real box — pydcs `width` is wingspan,
`length` is fuselage — against the stand, with a tolerance of 1.25 for
statics (an apron continues past the painted box; a KC-135's tail over the
taxi lane is how a real one sits) and 1.0 for parked AI (DCS may taxi it).
`slot.large` is honoured as a hard yes. Surveyed boxes in
`data/airframe_dimensions.json` override pydcs where pydcs is wrong: the F-14
is modelled swept at 10.15 m span; the real envelope is 20.34 m.

**Heavies get a reservation** (`RAMP_HEAVIES`: none / light / auto / surge).
Without one the fighter pool takes every big stand and no tanker parks.
`auto` is 12% of the field's aircraft target with a floor of 4 stands and a
ceiling of 8; `surge` (the Red Flag look) is 28%, floor 10, ceiling 16;
never more than 55% of the target. The floor is what gets a tanker onto
Nellis; the ceiling is what stopped a 60% fill parking thirty heavies.

**Ramps are squadron rows, not dice rolls** (v1.5.0, v1.52.0). Stands are
filled in `slot_key` (crossroad index) order, which runs along the ramp
rows, in contiguous blocks of one type and one livery: 4–6 fighters, 2–3
heavies, 2–4 helicopters per block, at most `SQUADRON_MAX = 6` statics per
squadron identity per field (an explicit high fill percentage lets the cap
escalate in waves). Real squadron identities from `data/squadrons.json`
fill first where a base has them (Syria, Nevada, Afghanistan).

**Who parks is data, era-gated by structure.** `data/ramp_themes.json`
holds weighted lists per era and side; a theme only exists under its era, so
a WWII field cannot draw a modern ramp. Map presets can set a side theme
and per-field themes (Nellis is the Red Flag ramp; Groom Lake and Tonopah
Test Range must not inherit it). Theater alignment (`alignment.py`,
`data/theater_identity.json`) swaps the fast-jet types for the owning
nation's roster (`data/nation_rosters.json`) — an Israeli base parks F-15s
and F-16s, Iran the F-14A, the GDR MiGs — while transports and helicopters
stay side-generic.

**Liveries are written only from a verified pack.** `data/liveries.json`
is hand-authored and ships `_verified: false`; a wrong livery id gives a
blank or wrong aircraft, so until `scripts/dump_liveries.py --merge` has
read ids out of a real DCS install the engine leaves `livery_id` unset
(v1.46.4). Everything downstream of liveries — squadron identity, the
`aggressors` / `clean` / `random` styles — is built and inert.

**Nothing is written on a guess.** A field with no measured heading keeps
the geometric guess (nothing regresses); a field with no scenery survey
gets no building keep-out; a field with no elevation on record (a separate
subsystem, pattern traffic) gets no airborne spawn. Each gap is named in a
warning or a comment rather than papered over.

## 3. Facing: how the headings were measured

Three layers, each winning over the next:

1. **Exact per-stand measured heading** — `data/parking_headings.json`,
   `map -> airfield -> {"default": n, "slots": {"<stand name>": heading}}`.
   About 9,500 individually measured stands across ten maps (Nevada,
   Germany, Caucasus, Kola, Marianas, Normandy, Persian Gulf, Sinai, Syria,
   Afghanistan). Every airfield on those maps has a default; most have every
   stand.
2. **Field-wide measured default** — the dominant apron heading, used for
   any stand of a surveyed field that the survey missed.
3. **Geometric guess** (`AirfieldKeepOut.slot_headings()`, v1.5.1) — a
   stand's row is its neighbours within 90 m; the row axis is the principal
   axis of the neighbour offsets; aircraft park perpendicular to the row with
   the nose toward the runway; an isolated pad faces the runway directly.
   Keyed by the unique `slot_key`, never `slot_name` (Syria's Ramat David has
   six stands named "02"). Falls back to the runway axis.

A ±3° jitter is added to statics so a row does not look stamped.

**How the measurements were taken.** `scripts/build_survey_mission.py <map>`
builds a throwaway mission with one uncontrolled aircraft on every airplane
stand of the chosen fields plus a Lua exporter that, 15 s in, logs each
unit's heading as `PSURVEY_OUT|<airport>|<slot>|<heading>`. DCS seats each
aircraft on the painted line when the mission loads, so the log *is* the
terrain's own heading. Rob flies it once; `scripts/import_survey.py <map>
dcs.log` bakes the headings into the JSON. No shipped mission ever contains
Lua — the survey is an offline data tool. (The first entry, Nellis 219°, was
measured by hand in the Mission Editor in v1.6.1; the per-stand survey
replaced it in v1.6.6, 247/247 Nellis statics verified against their spot.)

**The guard** (`tests/test_parking_headings.py`, v1.67.0): every measured
field exists on its map, every measured stand name still exists on the
terrain, headings are plausible bearings, and the corpus has not silently
shrunk below ~9,000. This exists because 26 orphaned sub-slot measurements
(`02-1`, `D09-1`) sat dead in the file for a month — pydcs flattens DCS's
parent/child stands to the parent — and several disagreed with their parent
by 180°. Orphaned data does not throw; it just stops being data.

## 4. The placement pipeline, per field

`dressing.dress_airfield(...)`, called from `builder.py` for each field
**after** the player flight, pattern traffic and ambient AI have claimed
stands (handbook §build order: "dressing last among the stand-claiming
blocks").

1. Build the keep-out (`AirfieldKeepOut`): runway corridors, stand set,
   scenery footprints if `data/scenery_keepout.json` has the field.
2. Start the **occupancy registry** (v1.10.3): every placed object records
   `(x, y, radius)`; every later placement must clear it. Stands already
   claimed by other systems are registered from their own dimensions.
3. List **eligible free stands** — unclaimed, not used by another field
   pass, and fillable by the theme (a helipad on a WWII field with no
   helicopters in the era list does not dilute the fill percentage) — in
   `slot_key` order.
4. Compute the target: explicit `dress_fill` percentage (no cap), else
   `DENSITY_FILL` (25/45/70%) capped per mode; or, in Ramp Composer mode,
   the exact `dress_mix` counts, round-robin so a short field truncates
   proportionally.
5. Reserve the heavy line, then fill **squadron blocks**: real squadrons
   first, then weighted theme draws with the per-squadron cap and the
   "drain the heavy pool before repeating a type" rule (measured: 1.8 B-1Bs
   per mission and 0.6 KC-135s from equal weights before it).
6. For each stand: collision gate against the registry at 0.6 × the
   airframe's circumscribing half-extent (wingtip-to-wingtip rows pass,
   one aircraft inside another fails); then place a static with the facing
   from §3, or an uncontrolled flight in `parked_ai` mode; group name
   `ST <field> <slot_key> <type>` (unique — `slot_name` collisions once
   made DCS drop duplicate-named units silently).
7. **GSE** beside it with 50% probability — a fuel or utility truck offset
   from the *aircraft footprint* plus 3–6 m (the old stand-based 4–9 m put
   the truck inside any airframe bigger than a fighter), validated against
   the keep-out and the registry.
8. **Infrastructure** clusters on the side of the ramp away from the runway
   axis, validated the same way.

The player's own flight does not go through this code; it parks via pydcs.
`builder._fitting_slots` (v1.68.0) re-sorts pydcs's free-stand list by
`(helicopter, width, name)` so a fighter takes the narrowest adequate stand
instead of stand "01", which is usually the widest on the field — 22 of 144
fields handed the F-16 the only heavy stand before this.

## 5. The data packs

| File | What it is | Status |
|---|---|---|
| `data/parking_headings.json` | ~9,500 measured per-stand headings, 10 maps | Measured; guarded |
| `data/airframe_dimensions.json` | surveyed real boxes where pydcs is wrong (F-14 family) | From the F-14B(U) survey log |
| `data/ramp_themes.json` | who parks, per era and side, weighted | Hand-authored, era-gated |
| `data/nation_rosters.json` | fast-jet types per owning nation per era | Hand-authored, refs verified by test |
| `data/squadrons.json` | real squadron identities per base (Syria, Nevada, Afghanistan) | Hand-authored |
| `data/liveries.json` | livery ids per type per country | **Unverified** — engine writes none until `dump_liveries.py --merge` |
| `data/scenery_keepout.json` | building footprints per field | **Not shipped** — tooling exists, no survey baked |
| `data/airfield_elevations.json` | field elevation per map (v1.107.0, in progress) | Caucasus and Nevada only |
| `data/maps.json` presets | `<side>_theme`, `<side>_field_themes` per map | Hand-authored |

Survey tooling, all offline, all the same pattern (a throwaway `.miz` with
a Lua exporter writing to `dcs.log`, an importer that bakes the JSON):
`build_survey_mission.py` / `import_survey.py` (headings),
`build_scenery_survey.py` / `import_scenery.py` (buildings),
`build_bu_survey.py` (airframe boxes and type ids), `dump_liveries.py`
(livery folder names from an install).

## 6. Guards

87 tests across `test_parking_headings.py`, `test_player_parking.py`,
`test_ramp_heavies.py`, `test_alignment_ramps.py` and `test_regressions.py`,
plus the dressing checks inside `test_every_map_builds.py` and
`test_determinism.py`. The properties they hold: measured data points at
real stands; NTTR flags no stand `large` (so the airframe test, not the
flag, is load-bearing); pydcs still reports the dimensions the code reasons
from; Nellis reliably has tankers or AWACS and Groom Lake never does; a
surge ramp is visibly bigger; no single heavy type takes the ramp; an aligned
base never parks the enemy's aircraft; the player's fighter takes the
tightest stand that fits and never a helicopter pad; the same seed rebuilds
the same ramp.

## 7. Known gaps and open items

- **Buildings.** The scenery keep-out is wired but no survey has been baked,
  so a free-placed truck can still land on a hangar. One survey flight per
  map closes it (`build_scenery_survey.py`); Nellis's was delivered to Rob
  in v1.12.0 and never imported.
- **Liveries.** Verified pack still pending one command against a real
  install. Everything livery-dependent (squadron paint variety, aggressors)
  is inert until then.
- **Elevation.** pydcs has none; `ParkingSlot.height` is the stand's
  clearance height, which pattern traffic mistook for field elevation until
  v1.107.0. The elevation table covers Caucasus and Nevada; other maps need
  a DCS dump (`land.getHeight(Airbase.getPoint())`).
- **Maps without a heading survey**: Iraq, Falklands, The Channel — the
  geometric guess only.
- **Headings are TRUE** as DCS reports them; the kneeboard labels them so.
- **Carrier decks** are a separate module (`deck.py`, `carrier_decks.json`)
  with its own layouts; not covered here.

## 8. Where to read next

`missiongen/dressing.py` (877 lines, the comments carry the history),
`missiongen/placement.py`, `builder.py` around `_fitting_slots` and the
dressing call, `docs/AGENT_HANDBOOK.md` §"build order", and the CHANGELOG
entries for 1.5.0, 1.5.1, 1.6.1, 1.6.6, 1.10.1, 1.10.3, 1.12.0, 1.47.0,
1.52.0, 1.67.0 and 1.68.0.
