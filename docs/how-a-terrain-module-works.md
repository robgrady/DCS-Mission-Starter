# How a pydcs terrain module works

A reference for understanding what a DCS map looks like to pydcs (and therefore to Mission Starter), how the data gets there, and what actually matters for our product. Written against the real Syria module and pydcs's own `airport_import.py`.

---

## 1. The shape: three files, two generated, one authored

A terrain module (`dcs/terrain/<map>/`) is four files:

| File | Size (Syria) | Origin | Contains |
|---|---|---|---|
| `airports.py` | 15,465 lines | **generated** by `airport_import.py` | every airport: radios, runways, beacons, parking slots |
| `projection.py` | 10 lines | **generated** by `export_map_projection.py` | transverse-mercator parameters (lat/lon ↔ meters) |
| `<map>.py` | ~40 lines | **hand-written** | center, bounds, climate table, timezone, bullseye |
| `__init__.py` | 1 line | trivial | exports the Terrain class |

The intimidating file is the harvested one. The authored file is small. That inversion is the whole reason this contribution is feasible.

---

## 2. Anatomy of one airport record

This is Bassel Al-Assad from Syria, exactly as the importer emitted it (trimmed):

```python
class Bassel_Al_Assad(Airport):
    id = 21
    name = "Bassel Al-Assad"
    tacan = None
    slot_version = 2
    atc_radio = AtcRadio(hf_hz=4075000, vhf_low_hz=39050000, vhf_high_hz=118100000, uhf_hz=250600000)

    def __init__(self, terrain: Terrain) -> None:
        super().__init__(mapping.Point(42236.56, 5836.23, terrain), terrain)
        self.beacons.append(AirportBeacon(id='airfield21_2'))
        self.runways.append(Runway(id=2, name='17R-35L',
            main=RunwayApproach(name='17R', heading=170, beacons=[RunwayBeacon(...)]),
            opposite=RunwayApproach(name='35L', heading=350, beacons=[])))
        self.parking_slots.append(ParkingSlot(
            crossroad_idx=0, position=mapping.Point(43250.79, 5899.35, self._terrain),
            large=False, heli=True, airplanes=True, slot_name='27',
            length=26.0, width=24.0, height=11.0, shelter=False))
```

Field by field:

- **`id`** — the airport's numeric ID *in the DCS mission file's warehouse table*. This is not cosmetic: when a `.miz` references a home base, it references this ID. Get it wrong and DCS can't resolve the field.
- **`name`** — the human name; what a recipe's `home_airbase` matches against.
- **`tacan`** — a field-level TACAN channel string, or `None`. Most land airfields are `None`; TACAN mostly lives on carriers and specific navaids. Comes from a dedicated `tacan` key in the dump.
- **`slot_version`** — a schema version tag. **Important subtlety:** the importer writes this as the literal constant `2` every time — it does *not* read it from the map. So it's a marker of "which importer wrote this," not a live capability flag. (See §7 on why that matters for drift.)
- **`atc_radio`** — the tower's four-band frequency set (HF / VHF-low / VHF-high / UHF), stored in raw Hz. This feeds comms and kneeboard generation.
- **`super().__init__(Point(x, y))`** — the airport's reference point on the map's local meter grid (its origin marker).

---

## 3. Parking slots — the load-bearing data for Mission Starter

Every dressing and placement decision we make keys off `parking_slots`. Each slot:

- **`crossroad_idx`** — the *unique* stand identifier. We learned the hard way that `slot_name` is **not** unique (Syria's Ramat David has six stands literally named "02"); keying on `slot_name` produced duplicate unit names and under-placed the field. We key on `crossroad_idx` everywhere now.
- **`position`** — the stand's location on the local meter grid.
- **`large` / `heli` / `airplanes`** — compatibility flags. Can a heavy fit here? Can a helo use it? Is it a fixed-wing stand at all? A B-52 must not be assigned to a small GA stand.
- **`length` / `width` / `height`** — the physical stand box in meters. **This is what our occupancy registry reads** to decide GSE and static offsets. The v1.10.3 collision fix — trucks no longer spawning inside a parked heavy's footprint — runs entirely on these three numbers.

### The `flag` bitfield

In the raw dump each stand has an integer `flag`. The importer derives `large` from it with a single bit test:

```python
large_bit = 1 << 3        # = 8, i.e. bit 3
large = slot["flag"] & large_bit == large_bit
```

So "large" is bit 3 of the flag. The other booleans — `heli`, `airplanes`, `shelter` — do **not** come from the flag; they come from a separate `params` table as string `"1"`/`"0"` values that DCS returns from `Terrain.getStandList(...)` when we ask for `SHELTER`, `FOR_HELICOPTERS`, `FOR_AIRPLANES`, `WIDTH`, `LENGTH`, `HEIGHT`. That list of requested params is literally in the Lua hook you paste — it's why the hook names exactly those six.

---

## 4. The radio / frequency model

The tower frequencies arrive as a `frequencyList` — a table of `[index, value]` pairs. The importer does something deceptively simple:

```python
atc_freqs = [v[1] for v in frequencyList.values()]
hf, vhf_low, vhf_high, uhf = sorted(atc_freqs)
```

It takes the four frequencies, **sorts them ascending**, and assigns them positionally to HF < VHF-low < VHF-high < UHF. That works because those bands don't overlap — HF is ~4 MHz, VHF-low ~39 MHz, VHF-high ~118 MHz, UHF ~250 MHz — so sort order equals band order. It's elegant but rigid: it assumes **exactly four** frequencies. (See §7.)

This four-band set is what our comms/kneeboard code turns into tower presets.

---

## 5. Beacons and TACAN

Two beacon kinds get separated at import time:

- **`AirportBeacon`** — field-level (e.g. an NDB), identified by a string `id` like `airfield21_2`.
- **`RunwayBeacon`** — attached to a specific runway *and side* (`runway_id`, `runway_side` like `'17R'`), which is how ILS/approach aids bind to one landing direction.

The parser routes each beacon by whether it carries a `runwayId`. `TACAN` is separate again — a top-level per-airport field, usually `None` on land. This is why "some maps carry TACAN on the field and some don't" — it's simply whether ED populated that key for that airfield.

---

## 6. The coordinate system and the projection math

DCS places everything on a **flat local grid in meters** — Bassel's stand 27 is at `(43250.79, 5899.35)`, meaning meters from the map's origin. But the Earth is curved, so to recover a stand's real **lat/lon** — which we need for sun angle, magnetic variation, and the QNH/altimeter work — you need a projection. That is the entire job of `projection.py`.

DCS uses a **transverse mercator** grid (same family as UTM). It has four parameters:

1. **Scale factor** — 0.9996 for essentially every map (the UTM standard).
2. **Central meridian** — which of the 60 UTM zones the map sits in. Easy to guess from the map's longitude.
3–4. **False easting / false northing** — the offset between UTM's mathematical origin and wherever DCS decided to put its `0,0`. These *cannot* be guessed.

The projection tool derives 3 and 4 empirically: it builds a mission that dumps the lat/lon **and** x/z of the `0,0` point, computes the offset that makes them line up, then **validates** by projecting every airport and checking the error against the airports' known positions. Low error across all airports = the projection is right. It's self-checking, which is why this step is low-risk once the airports exist.

This is also why the build order is airports → terrain stub → projection: the projection tool needs a Terrain object *and* the airport list to validate against.

---

## 7. What Mission Starter actually reads vs. ignores

Not all terrain data matters to us. The map of what we touch:

**We depend on:**
- `parking_slots` — `crossroad_idx`, `position`, `large/heli/airplanes`, `length/width/height`. (Dressing, placement, occupancy/collision.)
- `atc_radio` — tower comms & kneeboards.
- `runways` — headings, for ambient traffic and runway waypoints.
- The projection — indirectly, for lat/lon-derived briefing values (sun, magvar, QNH).

**We mostly ignore:**
- `civilian`, `unit_zones`, most field-level beacon IDs, `tacan` on land fields (we manage carrier TACAN ourselves in `carrier_decks.json`).

The practical read: **a new map is only as good to us as its parking-slot geometry.** If the geometry harvests cleanly, everything our product does on that map works.

---

## 8. Where format drift would actually bite (the real risk, precisely)

The single unknown in adding a new map is whether the importer's assumptions still hold on a newer map. Three concrete places it could break, in order of likelihood:

1. **Frequency count.** `hf, vhf_low, vhf_high, uhf = sorted(atc_freqs)` unpacks **exactly four** values. If a newer airport exposes three or five, this line throws. Fix: handle variable counts by band, not by position.
2. **Missing `params` keys.** The slot parser reads `HEIGHT/LENGTH/WIDTH/FOR_HELICOPTERS/FOR_AIRPLANES/SHELTER`. If ED renamed or dropped one, `KeyError`. Fix: `.get()` with defaults.
3. **Beacon shape.** `parse_beacons` asserts `runway_id != -1`. A new beacon convention could trip the assert. Fix: relax to name-indexing (the code comment already anticipates this).

Note what is *not* a risk: `slot_version` is a written constant, so it never causes a parse failure — it just labels the output. Any real break shows up as a Python exception during import, not as silently-wrong data. That's good: we'll know immediately, and each fix above is a small, clean upstream PR.

---

## 9. How you'd extend or contribute

The mechanism, end to end:

1. **Harvest** (`standlist.lua`) via the ME Lua hook → run `airport_import.py -t <map>` → `airports.py`.
2. **Stub** a `<map>.py` Terrain with guessed projection + real bounds/center/climate.
3. **Project**: run `export_map_projection.py --map <map>`, fly the probe, get validated `projection.py`.
4. **Finalize** the metadata class, register the terrain, smoke-test `Mission(<Map>())` + a flight on a parking slot.
5. **Upstream**: open an issue, then PR the generated files + metadata. Data is derived from the install exactly as pydcs already does for every official map.

The only human-in-the-loop steps are the two ME passes (harvest + projection probe). Everything else is repo work.
