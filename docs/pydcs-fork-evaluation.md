# The Retribution fork: evaluated

*Findings, 13 Aug 2026. Answers the open question in `docs/pydcs-strategy.md`.*

**Verdict: switch. The fork carries Afghanistan *and* Iraq, every airbase our
templates already name, and every API we call. The migration has exactly one
breaking change and one real risk, both identified below.**

---

## 1. The decisive question, answered

| | Our vendored pydcs (upstream) | dcs-retribution/pydcs |
|---|---|---|
| Terrains | 11 | **14** |
| Afghanistan | ✗ — **we hand-built 4,602 lines** | ✅ `dcs/terrain/afghanistan` (4,584-line airports table) |
| **Iraq** | ✗ — queued as "Iraq terrain exports" | ✅ `dcs/terrain/iraq` (20 airports) |
| Last commit | upstream release 0.13.0, **Jan 2021** | **25 Jul 2026** — three weeks ago |
| License | LGPL-3.0 | **LGPL-3.0** (verified: `LICENSE.txt` is LGPL v3) |

**All nine Afghanistan airbases our templates name** — Bagram, Camp Bastion,
Dwyer, Gardez, Herat, Jalalabad, Kabul, Kandahar, Shindand — are present in the
fork's data. So the swap deletes `missiongen/terrains/afghanistan/` outright and
cancels the Iraq job before it starts.

**Every Mission API we call exists.** Of 20 call sites extracted from our
engine, 17 are real pydcs methods and all 17 are present; the other three were
regex false positives (`dict.get`, `re.Match.group`, `dict.setdefault`).

## 2. The one breaking change

**Germany was renamed.** `dcs.terrain.germany.Germany` →
`dcs.terrain.germanycoldwar.GermanyColdWar`. Our `maps.json` names the class
path directly, so this is a one-line data edit — but it must not be missed,
because Germany carries the Fulda Gap Cold War templates.

Checked: **all 26 Germany airbases our presets name are present** in the fork's
`germanycoldwar` data (whose airports table is 24,145 lines against our
smaller one — it is a newer, richer export, which is also a *risk*, see below).

## 3. The real risk: the missions will change

Divergence from our copy, by module:

| Module | Differing lines |
|---|---|
| `planes.py` | **2,218** |
| `mission.py` | 333 |
| `task.py` | 133 |
| `unitgroup.py` | 38 |
| `helicopters.py` | 5 |

2,218 differing lines in `planes.py` means unit definitions moved — payload
tables, performance figures, possibly type ids. Our engine reads `max_speed`
(cruise scaling), `width`/`length` (stand fitting), and the per-pylon legal
store lists (loadouts). **Generated missions will not be byte-identical**, and
that is not automatically wrong — but every change must be seen and explained,
not discovered by a pilot.

The Germany airports table being three times larger than ours is the same
issue in data form: parking slots and airbase geometry may differ, which is
exactly the input to the ramp-dressing work of the last few releases.

## 4. What does NOT change

**The `patrol_flight` bug is still there** — `dcs/mission.py:1600` still spawns
an in-flight patrol at `Point(pos1.x - 10*1000, pos1.y)`. Our v1.66.0 workaround
(build with `flight_group_inflight` at the exact point, then
`patrol_flight_to_group`) stays necessary on either library, and the upstream
PR is still worth filing — now against the fork, where it will actually be seen.

**Aircraft coverage is a wash.** A-29B and UH-60L are missing from both. The
helicopters we care about (AH-64D BLK II, OH-58D, CH-47F) are already in our
copy.

## 5. Recommended migration

1. **Build the adapter seam first** (`missiongen/dcslib.py`) — unchanged
   recommendation from the strategy memo. It turns the swap into a bounded
   change and gives the library-quirk knowledge one home.
2. **Swap the vendored copy**, update `PYDCS_PROVENANCE.md` to name the fork
   and its commit, keep it byte-for-byte unmodified as now (the LGPL posture is
   identical — same license, still separable, still replaceable).
3. **Fix the Germany class path** in `maps.json`.
4. **Byte-compare before and after** across a broad recipe sweep. Anything that
   changes gets a named reason: "the F-16's max_speed moved, so cruise scaling
   moved" is fine; "the ramp emptied on Germany" is a bug. We already hash
   artifacts this way, so the tooling exists.
5. **Then delete** `missiongen/terrains/afghanistan/` (4,602 lines) and add
   Iraq as a normal map entry rather than a terrain-building project.
6. **Re-run the full suite**, especially the geometry guards
   (`test_bfm_ladder`, `test_time_to_first_action`) and the ramp/parking tests —
   those are the ones that would notice changed airport data.

## 6. Sizing

The swap itself is small. The verification is the work: a recipe sweep across
every map and era, with every diff explained. Realistically one focused
session, and it should be its own release with nothing else in it, so that if
something surfaces in the wild the cause is unambiguous.

The prize: **~4,600 lines deleted, the Iraq terrain job cancelled, and a
library that had a commit three weeks ago instead of a release five years ago.**
