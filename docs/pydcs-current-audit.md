# PyDCS and parking data audit

Verified 2026-10-02 against freshly fetched upstream Git repositories.

## What the application uses

Sortie Starter imports `vendor/dcs`, not an installed PyPI package. All 108
Python files match upstream `pydcs/dcs` commit
[`412952c5ad5688783d8d53830280f316dbe311ff`](https://github.com/pydcs/dcs/commit/412952c5ad5688783d8d53830280f316dbe311ff)
(2026-06-29), with no extra or missing Python modules. The exact revision is now
recorded in `vendor/dcs/PYDCS_PROVENANCE.md`.

The latest fetched upstream master is
[`55dc18adbd6907ea17d87de559445c4f9bc39146`](https://github.com/pydcs/dcs/commit/55dc18adbd6907ea17d87de559445c4f9bc39146)
(2026-09-05), four commits ahead. Seven Python files differ:
`planes.py`, `helicopters.py`, `countries.py`, `vehicles.py`,
`weapons_data.py`, `task.py`, and `terrain/kola/airports.py`.

The newer code adds the `F_14BU` aircraft class (`F-14BU` DCS id), updated unit
and weapon exports, Kola airport geometry, and corrects TACAN Y-channel beacon
system selection. We already support the F-14B(U) through our pending-aircraft
extension, so that class alone does not unlock a new user-facing aircraft.

[PyPI](https://pypi.org/project/pydcs/) still publishes 0.15.0 from 2023-04-15.
Its version number does not identify the source revision this product uses.
Installing that release would replace our newer source with older data.

The current fetched [Retribution fork](https://github.com/dcs-retribution/pydcs)
remains `3a79b8edf923042a5b933feb64543da9e6bdfd37` (2026-07-25). Our Afghanistan
and Iraq terrain extensions already cite that revision. It provides weapon
settings metadata and automatic-fog support, among other differences. These
are candidate capabilities to evaluate separately, not a reason to combine an
engine replacement with the reliability refactor. Earlier August strategy
notes are historical: their "frozen since 2021" claim was corrected in
`pydcs-fork-feature-review.md`, and Afghanistan has since been replaced with
exported data too.

## Parking coverage

Every supported map has exported parking positions and dimensions. The table
below counts the terrain's declared slots and our separately measured static
parking headings. These are distinct datasets: a declared slot is not
necessarily suitable for every aircraft, in a supported coalition preset, or
surveyed for static-aircraft facing. No percentages imply full visual accuracy.

| Map | Declared slots | Measured slot headings | Airfields with per-slot measurements |
|---|---:|---:|---:|
| Caucasus | 900 | 844 | 19 |
| The Channel | 572 | 0 | 0 |
| Persian Gulf | 1,289 | 1,018 | 18 |
| Nevada | 632 | 571 | 16 |
| Normandy 2 | 3,434 | 784 | 18 |
| Syria | 3,976 | 1,027 | 28 |
| Sinai | 3,383 | 1,545 | 22 |
| Marianas | 264 | 248 | 5 |
| Cold War Germany | 6,773 | 2,212 | 26 |
| Kola | 1,150 | 816 | 18 |
| South Atlantic | 277 | 0 | 0 |
| Afghanistan | 1,381 | 459 | 2 |
| Iraq | 1,397 | 0 | 0 |

The live data file contains **9,524** measured slot headings across ten maps.
The approximate 9,550 cited by older documentation is not its current exact
count. The Channel, South Atlantic, and Iraq have no per-slot measurements;
other maps have partial coverage. Missing measurements use a field default
where available, then a geometric facing estimate. Player/AI parking uses the
terrain's parking model; measured headings primarily orient static aircraft.

`tests/test_parking_headings.py` checks that measured fields and slot names
still exist. `tests/test_player_parking.py` checks fit and preservation of wide
stands for heavy aircraft. The phase refactor preserves terrain exports, parking measurements, player-slot
fitting, and placement order. The subsequent direction change keeps measured
static headings exact, removing the former ±3° variation. It also adds
id/coordinate-bound imports for new surveys; existing measured values remain
unchanged. See `parking-direction-survey.md` for the prepared missing-map files.

## Upgrade recommendation

Keep the verified library during the refactor. Evaluate an upstream update as
its own change, pinned to a full commit. Compare slot **names, crossroad ids,
coordinates, dimensions, and eligibility**, in addition to mission outputs.
Names alone are insufficient: in the newer Kola export all 816 measured names
survive, but 90 measured stands have changed metadata and 86 have moved. For
example, Rovaniemi F03 moved 10.86 metres and F04 moved 11.22 metres. These
changes do not prove headings are wrong, but they require visual verification
against the current DCS map before claiming exact placement.

Run the existing parking, geometry, loadout, and deterministic-generation
checks on an upgrade branch; inspect generated missions in DCS for affected
maps. Do not discard our hand-measured headings to make an update pass.
