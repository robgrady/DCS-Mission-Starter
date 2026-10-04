# Sources

*Where the facts in this product came from. Served at `/api/sources`.*

**Why this page exists.** DCS Sortie Starter makes a lot of specific claims — a
SAM's engagement radius, a squadron's callsign, the heading a stand's painted
lines run, the bearing of a 1981 raid, a contrast ratio. Every one of them is
either measured, cited, or an admitted estimate, and the difference matters. A
number nobody can trace is a number nobody should trust, including us.

**Rule of the page:** anything the product asserts as fact gets an entry here.
If a claim can't be traced to a source, a measurement, or a stated estimate, it
is a bug — file it. `tests/test_sources.py` fails the build if a data pack with
external provenance has no entry.

---

## 1. The simulator and the library

### pydcs
The mission-file framework everything is built on.

- **Upstream:** https://github.com/pydcs/dcs
- **License:** LGPL-3.0. Full text ships in `vendor/dcs/COPYING.LESSER` and
  `vendor/dcs/COPYING`.
- **Our copy is byte-for-byte unmodified.** Behavioral changes we need
  (deterministic onboard numbers, a frozen ambient-random default) are applied
  at runtime in `missiongen/_determinism.py` — 33 lines of monkey-patch —
  precisely so the vendored library stays separable and replaceable, which is
  what LGPL-3.0 §4/§5 requires. Full statement: `vendor/dcs/PYDCS_PROVENANCE.md`.

### F-14B(U) TARPS compatibility store

`missiongen/data/scenario_stores.json` supplies the verified TARPS store absent
from vendored PyDCS. It does not modify the vendor library.

- [Heatblur TARPS manual](https://f14.manuals.heatblur.se/f14ab/systems/tarps.html)
  describes controls, imagery and simulator limitations.
- [DCS exported F-14BU unit data](https://github.com/Quaggles/dcs-lua-datamine/blob/fdd11ed960d5402909a876558b7bec3b2653b268/_G/db/Units/Planes/Plane/F-14BU.lua)
  lists `{F14-TARPS}` on pylon Number 6. Pinned export SHA-256:
  `609df992ca93abd820068d121ebb3b0e6f3516c7bef2fe0686406cedee93c526`.
- This is the F-14B(U) encoding only; unsupported reconnaissance aircraft fail
  with a clear message. Image recording is operated manually in the module.

### The dcs-retribution pydcs fork
Two terrain packages are lifted from a fork, not from upstream.

- **Source:** https://github.com/dcs-retribution/pydcs
- **Commit:** `3a79b8edf923042a5b933feb64543da9e6bdfd37` (25 July 2026)
- **License:** LGPL-3.0, same as upstream.
- **Used for:** `missiongen/terrains/iraq/` (v1.67.0) and
  `missiongen/terrains/afghanistan/` (v1.68.0).
- **One adaptation each,** marked in the source: our `Terrain.__init__`
  requires a `utc_offset` and the fork's does not. Iraq gets UTC+3 (Arabia
  Standard Time), Afghanistan UTC+04:30. Nothing else is changed.
- **Why not swap the whole library:** the two have *diverged*, not raced — ours
  is the only one of the two with `Terrain.utc_offset`. Reasoning in
  `docs/pydcs-fork-feature-review.md`.

### Eagle Dynamics, on their own maps
Product state, airfield lists, what is modelled and what is planned.
Full research with per-claim citations: **`docs/dcs-iraq-map-state.md`**.

- [DCS: Iraq release FAQ](https://forum.dcs.world/topic/365676-dcs-iraq-release-faq/)
- [Iraq is now available (13 Dec 2024)](https://www.digitalcombatsimulator.com/en/news/2024-12-13/)
- [Iraqi map development progress (29 Aug 2025)](https://www.digitalcombatsimulator.com/en/news/2025-08-29/)
- [Iraq and Afghanistan dev reports (16 May 2026)](https://www.digitalcombatsimulator.com/en/news/2026-05-16/)
- [Changelog 2.9.28.26283 (22 Jul 2026)](https://www.digitalcombatsimulator.com/en/news/changelog/release/2.9.28.26283/) — Kharg Island, the nine named dams
- [MOOSE `AIRBASE` enum](https://flightcontrol-master.github.io/MOOSE_DOCS_DEVELOP/Documentation/Wrapper.Airbase.html) — an independent, code-derived airfield list we cross-check against

---

## 2. Measured in the simulator — our own instrumentation

These are not cited because nobody has published them. They are **measured**,
by us, with the method and the date recorded.

| Data | What it is | Method |
|---|---|---|
| `data/parking_headings.json` | **10,921 painted-line stand headings** (degrees TRUE) across eleven maps | 9,524 legacy measurements after removing 26 dead stand names, plus 1,397 identified Iraq stands captured in DCS on 2026-10-03. Iraq IDs, names and coordinates match the terrain export and all headings cross-check against the supplied debrief within 0.088°. Guarded by `tests/test_parking_headings.py` and `tests/test_parking_directions.py`. Source hashes: `docs/iraq-parking-liveries-2026-10-03.md`. |
| `data/static_liveries.json` | Exact-model, era/country static livery choices | Stock F-4E `af standard` folder is recorded in [DCS updater output](https://forum.dcs.world/topic/273353-installer-freezing/). Heatblur F-4E-45MC `421st_TFS_SEA_68-336` is recorded in the user's Iraq DCS log. Only Cold War USA choices are currently authored. The broader guessed `liveries.json` stays disabled; these sources do not establish exact squadron/date/base accuracy or validate rendered appearance on every installation. |
| `data/airframe_dimensions.json` | Real in-sim bounding boxes (m) | `BUSURVEY` export read out of `dcs.log`. pydcs models the F-14's span as 10.15 m (swept); the real envelope is 20.34 m. Survey `f14bu_survey2`, 21 July 2026. |
| `missiongen/terrains/afghanistan/projection.py` | Transverse Mercator parameters | Originally derived by us from an in-sim probe mission (`probe_afghanistan.miz` → `scripts/import_projection.py`) and marked *provisional*. v1.68.0 replaced it with ED's official export — which **agreed with ours to 2.3 × 10⁻⁵ m of false easting.** The label was over-cautious, not wrong. |
| `docs/mission-semantics-baseline.json` | Semantic fingerprint of 52 generated missions | `scripts/mission_semantics.py`. Not a source so much as a control: it is how we prove a data swap changed what we think it changed. |

### `aar.TERRAIN_MAX_FT` — the refuelling track floor

A refuelling track you can fly into a mountain is not a training aid. pydcs
exposes **no** terrain elevation (`terrain` carries no height attributes and an
airport's `alt` is `None`), so the highest ground on each map is a table, and
each row is labelled with where the number came from.

- **`"cited"` rows are published summit elevations**, taken as the map's
  ceiling because the peak is inside the playable area:
  [Mount Elbrus, 5,642 m / 18,510 ft](https://en.wikipedia.org/wiki/Mount_Elbrus)
  on Caucasus, and
  [Noshaq, 7,492 m / 24,580 ft](https://en.wikipedia.org/wiki/Noshaq)
  on Afghanistan.
- **`"ours"` rows are our own conservative estimates** — a round number at or
  above the highest terrain we can identify within the map bounds. They are
  labelled as estimates precisely because they are not measurements, per the
  honest-numbers rule.
- **A map that is not in the table gets the worst row in it.** Failing closed
  gives an unlisted map an unrealistically high track; failing open gives it a
  track inside a mountain. Those are not comparable costs.

Track altitude is `max(tanker's own block, highest ground + 3,000 ft)`, rounded
up to the next thousand, and clamped to the tanker's ceiling. The 3,000 ft is
clearance for the **receiver**, who starts each ride 1,000 ft below the track.
A tanker that cannot reach the resulting altitude is not offered for that map,
and the reason is printed beside the ones the era gate removed.

### The era gate — `data/aircraft_service.json` and `data/weapon_service.json`

The hard filter that keeps a Hornet out of 1978 and an AIM-120 off a 1965
Phantom is two tables of `[from_year, to_year | null]`, one per pydcs aircraft
class and one per weapon CLSID.

- **Compiled by hand from public service-entry and retirement dates.** There is
  no single authoritative machine-readable source for this; each entry is a
  judgement about when a type or store entered and left service.
- **Where the judgement is contestable, it is recorded as a product decision
  rather than smuggled in.** The F-14B(U) community variant carries a
  deliberately widened window so it can fly the Cold War; the stock F-14B does
  not, and `tests/test_pending_aircraft.py` asserts that split so it cannot
  drift. The F-14A remains the period-correct Cold War Tomcat.
- **Gaps are reported, not hidden.** An aircraft with no entry passes the gate
  and is listed in `/api/health` under `service_data_gaps`. Racks (LAU-7,
  APU-60-2M) inherit their family's window by prefix rather than being listed
  individually.

### `data/air_corridors.json`

Curated tactical lanes per map and era: a compass bearing from the friendly
base centroid and a reach in metres. Every lane traces to a published
operation — see §3 below, and `docs/iraq-air-corridors.md` for the full
citations, the places sources disagree, and the four candidates we rejected.
Corridors that cross terrain a map's developer has not detailed yet carry a
`terrain_note` that is briefed to the pilot verbatim.


### The F-16 B-Course track — `bc_*` Library cards

Eleven Library cards follow the phase architecture, task lists and setup
geometry of **AETC Syllabus F16C0B00PL (56 FW), "F-16C/D Initial
Qualification", April 2014** — the Luke AFB Combined Wingman Syllabus. Every
card names the document and the paragraph it came from, and
`tests/test_bcourse.py` fails the build if one stops doing so.

- The **BFM perch ranges** (9,000 / 6,000 / 3,000 ft, offensive and defensive)
  are the syllabus's, from BFM-1 through BFM-6 task 6. They are asserted in
  feet against a distance measured out of a generated `.miz`.
- The **G-awareness profile** (4 G warm-up, a 180 at 6–8 G, a 180 at 8–9 G,
  two AGSM cycles per hard turn) is TR-1 Note 2.
- The **500 ft AGL low-level floor** and the 1,000→500 ft LOWAT CAT I band are
  5-16f(1) and LASDT-2 Note 3.

**What the syllabus does not contain, we did not invent.** Chapter 5 is a set
of gradesheets, not a tactics manual: it states no dive angles, release
altitudes, pop parameters or safe-escape numbers, no engagement counts, and —
notably — **no BFM floor value**, even though floor awareness is a graded task.
Full accounting, including the 42 sorties deliberately not built and why:
`docs/f16-bcourse-track.md`.

**The 5,000 ft hard deck is now cited, not ours.** It was labelled an invention
until two further documents turned up stating it for exactly this activity: the
**48 OG / 493 FS F-15C Flying Training Syllabus** (Feb 2009 — "Floor: 5,000 ft
AWL/AGL" on every BFM ride) and **AFMAN 11-2F-22A Vol 3**, *F-22A Operations
Procedures*, 20 Sep 2018, Table 3.2 ("Aerobatics / Air Combat Training /
Advanced Handling: 5,000"). Same figure, two commands, two airframes. That
manual is also the source of the training-rules gates worth adopting more
widely — 300 KCAS minimum for low-level navigation, 350 KCAS for low-altitude
maneuvering below 5,000 ft AGL, 1,000 ft deconfliction reducing to 500 ft below
5,000 ft AGL. Review of the whole source library, with what to build from it:
`docs/source-library-proposals.md`.

### Air refuelling — `missiongen/aar.py`

Six tankers, each on a track its receivers can actually fly. Every entry
carries a **`basis`** field, because these are a different kind of number from
the BFM perches: **tuned operating points, not quotations.** No document in
this library states AAR airspeed bands, so the table says so next to each value
rather than implying doctrine.

What *is* sourced is the instruction. The pre-contact zero-closure gate is
ATP-56; the 1-3 kt closure figure is from Stephenson's *Air Refueling
Receiver*; the boom-vs-drogue hookup benchmark (40.8 s vs 85.0 s) is a CARI
study; and the pilot-induced-oscillation explanation — phase lag, loop gain,
the 0.5-1 Hz danger band — is the standard PIO literature. Full working and
citations: `docs/aar-training.md`.

**The card deliberately refuses to give a control-curve number.** Published
recommendations for the same task span 0 to 30 depending on gimbal type and
stick length. A single figure would be confidently wrong for most readers,
which is the same failure mode as an invented range.

**Admitted estimates, labelled as such.** Where we could not measure or cite, we
say so in the product rather than rounding a guess into a fact:

- **Magnetic variation.** Flight-plan cards publish TRUE headings and say so.
  pydcs exposes no declination, and a bundled WMM/IGRF model would silently
  expire. Labelling is the honest answer until a per-map table is checked
  against the sim. (`docs/ROADMAP.md`, "Verified magnetic variation".)
- **Aircraft performance figures** in briefing and kneeboard text are given as a
  band plus the method, never as a single authoritative number. Values *we*
  control — ranges, times, hard decks — are exact.
- **Terrain temperature tables.** Afghanistan's comes from ED's export verbatim,
  including an oddity (June's minimum is warmer than July's). We deliberately do
  not hand-smooth vendored data; a silent local "fix" is how a vendored file
  stops being vendored.

---

## 3. History — mission and corridor design

Each corridor and scenario traces to a published account. Full write-ups with
per-claim citations, source disagreements, and the candidates we *rejected*:
**`docs/iraq-air-corridors.md`**.

**Iran–Iraq War (1980–88)**

- CSIS, *Lessons of the Iran-Iraq War* — [Ch. 7](https://csis-website-prod.s3.amazonaws.com/s3fs-public/legacy_files/files/media/csis/pubs/9005lessonsiraniraqii-chap07.pdf) · [Ch. 14](https://csis-website-prod.s3.amazonaws.com/s3fs-public/legacy_files/files/media/csis/pubs/9005lessonsiraniraqii-chap14.pdf) — the Kharg strike campaign, low-level pop-up profiles, HAWK coverage
- Human Rights Watch, [*Genocide in Iraq* — The First Anfal](https://www.hrw.org/reports/1993/iraqanfal/ANFAL3.htm) — the Jafati valley, Dukan Dam, aircraft types and sortie counts
- [H-3 airstrike](https://en.wikipedia.org/wiki/H-3_airstrike) · [Atlantic Council](https://www.atlanticcouncil.org/blogs/iransource/how-iranian-phantoms-pulled-off-one-of-the-most-daring-airstrikes-in-recent-memory/) — the 4 April 1981 route, and the distance/tanker discrepancy between the two accounts
- [Operation Opera](https://en.wikipedia.org/wiki/Operation_Opera) · [Operation Kaman 99](https://en.wikipedia.org/wiki/Operation_Kaman_99) · [War of the cities](https://en.wikipedia.org/wiki/War_of_the_cities)

**Coalition operations (1991–2011)**

- Air & Space Forces Magazine — ["Package Q"](https://www.airandspaceforces.com/article/package-q/) · ["Scud War, Round Two"](https://www.airandspaceforces.com/article/0492scud/) · ["Ambush at Najaf"](https://www.airandspaceforces.com/article/1003najaf/)
- Army University Press — [Task Force Normandy staff-ride packet](https://www.armyupress.army.mil/Portals/7/educational-services/staff-rides/VSR/Task-Force-Normandy/1.%20Task%20Force%20Normandy%20Read%20Ahead%20Guidance%20and%20Packet.pdf)
- Haulman, [*Crisis in Iraq: Operation PROVIDE COMFORT*](https://media.defense.gov/2012/Aug/23/2001330108/-1/-1/0/Op%20Provide%20Comfort.pdf), AFHSD — the 36th parallel
- [GlobalSecurity — Southern Watch](https://www.globalsecurity.org/military/ops/southern_watch.htm) — the 32nd, then the 33rd parallel
- Wathen, ["The Miracle of Operation Iraqi Freedom Airspace Management"](https://www.airuniversity.af.edu/Portals/10/ASPJ/journals/Chronicles/wathen.pdf), Air University · [CENTAF, *OIF – By The Numbers*](https://mronline.org/wp-content/uploads/2020/03/oifcentaf.pdf) · [CGSC, "Joint Doctrine and the Kill Box"](https://cgsc.contentdm.oclc.org/digital/api/collection/p4013coll3/id/108/download)
- ARSOF History — [Operation Ugly Baby](https://arsof-history.org/articles/v1n1_op_ugly_baby_page_1.html) · [Operation Viking Hammer](https://arsof-history.org/articles/v1n1_op_viking_hammer_page_1.html)
- [From Balloons to Drones — Iraqi air defenses in Desert Storm](https://balloonstodrones.com/2022/10/19/looking-back-at-iraqi-air-defences-during-operation-desert-storm/) — the KARI battery counts

**NTTR corridors (`data/nttr_corridors.json`, `nttr.py`, v1.99.0).** Every
routed flight plan on the Nevada map is threaded through the published
structure — the FLEX turnout, the Sally Corridor, the Alamo Corridor, the
FYTTR departure west, the recoveries. Structure and rules:

- 57th Wing, [NELLISAFBI 11-250, *Local Flying Procedures*](https://static.e-publishing.af.mil/production/1/nellisafb/publication/nellisafbi11-250/nellisafbi11-250.pdf) — §2.8.1 "Sally Corridor is exclusively owned by NATCF to vector aircraft in and out of the north ranges"; NATCF "has limited radar coverage below 10,000 ft"; §4.6 FLEX departures to FYTTR / HAYFORD PEAK / DREAM / MORMON PEAK / MMM; §4.13 the JAYSN, STRYK, TORYE/ARCOE, MINTT and ALAMO recoveries; §4.6.13.4 north-west bound via FYTTR then BTY
- NTTR, [AFMAN 13-212V1 ACC Sup NTTR Addendum A](https://static.e-publishing.af.mil/production/1/nellisafb/publication/afi13-212v1_accsup_nttrsup_add_a/afman13-212v1_nttr_add_a.pdf) — Table 2.1: Desert MOA = Coyote A–D, Caliente A–C, Elgin, Sally Corridor; note 3: "a corridor within Alamo A/B/C (FL190 to FL210) is identified as 'Alamo Corridor'"; §3.1.1.1 entry via NATCF then Range Monitoring, exit in reverse
- 99 ABW, [*Nellis AFB Local Flying Procedures* excerpts (NTSB docket)](https://data.ntsb.gov/Docket/Document/docBLOB?ID=16098950&FileExtension=pdf&FileName=Nellis+AFB++Local+Flying+Procedures+Excerpts-Rel.pdf) — §4.14.5: STRYK from the west, ACTON from the Elgin MOA (RWY 21), ARCOE north ranges (RWY 21), MINTT north ranges (RWY 03), ALAMO when the Alamo corridor is active
- vJaBoG66, [*Flight Information Publication — Nevada*](https://www.vjabog66.de/downloads/66-FLIP-NV-005-P.pdf) — the DCS community's transcription of the procedures: FLEX at LSV 338/4 crossed at or below 4,000; FYTTR via the LSV 15 DME arc at or below 8,000 then R-269; STRYK at or above 9,500 direct GASS PEAK; JAYSN via Beatty at FL190/FL210; ALAMO recovery heading 165 direct HAYFORD
- [opennav.com](https://opennav.com/waypoint/US/STRYK) — FYTTR, STRYK, JAYSN, INS, LSV, LAS, MMM, BLD positions
- [Dreamland Resort, *Groom Range flight*](https://www.dreamlandresort.com/info/range_flight.html) — a civilian flight up the corridor: "parallel to I-15 north and then over Rt.93 north towards Alamo in what is known as Sally corridor"

- [60 FR 20625–20626 — Realignment of R-4807A and R-4808N](https://www.govinfo.gov/content/pkg/FR-1995-04-27/html/95-10388.htm) — the legal boundary descriptions drawn on the corridor chart (`nttr_chart.py`, `/api/nttr/chart.png`); every other outline on that chart is curated and marked `~`
- [Nellis / Creech / NTTR MACA pamphlet (FAASTeam)](https://www.faasafety.gov/files/events/WP/WP19/2019/WP1992982/KLSV_MACA_Pamphlet_12_Mar_19_V2.pdf) — the seven restricted areas, the Desert and Reveille MOAs as VFR-transitable, Alert Area 481 (7,000–17,000, 25 miles west), NATCF frequencies (Desert MOA 126.65 south / 124.45 north)

The corridor charts themselves (Figures 4.1–4.9 of 11-250, the FLIP's
pages 103–111) are drawings we could not transcribe. Where a point's position
comes from those charts — DREAM, MINTT, ARCOE, ACTON, APEX, the gates — it is
placed by geography, flagged `approx:true`, marked `~` on the F10 map and
listed in the brief as curated. The far-west road goes round R-4808N because
the straight line from Indian Springs to Beatty runs through the Box.

**Levant corridors (`data/corridors/syria.json`, `corridors.py`, v1.102.0).**
The same standard on the Syria map — one data file per map, four home
clusters (the Galilee fields, Akrotiri and the Cyprus fields, Incirlik and
the Adana MTMA, Muwaffaq Salti and the Jordanian fields), six target sectors
(Lebanon, Damascus, the coast, the north, the east, central Syria). The
structure is the published one — airways, FIR-boundary fixes, TMAs, the
Israeli training blocks — and the roads are the ones the IAF and the
coalition are reported to have flown. Sources:

- AIP Israel (gov.il eAIP) — [ENR 2.1 FIR/TMA/sectors](https://e-aip.azurefd.net/2025-10-02-AIRAC/html/eAIP/LL-ENR-2.1-en-GB.html) (Tel Aviv FIR, PLUTO control in the north), [ENR 3.1 ATS routes](https://e-aip.azurefd.net/2024-10-31-AIRAC/html/eAIP/LL-ENR-3.1-en-GB.html) (J14 NAT–MOCEV–GAFAZ–BARZI–ROP; the coast; MERVA/MUVIN), [ENR 3.3](https://e-aip.azurefd.net/2025-10-02-AIRAC/html/eAIP/LL-ENR-3.3-en-GB.html), [ENR 1.5](https://e-aip.azurefd.net/2022-11-03-AIRAC/html/eAIP/LL-ENR-1.5-en-GB.html), [ENR 5.1 restricted areas](https://e-aip.azurefd.net/2025-10-02-AIRAC/html/eAIP/LL-ENR-5.1-en-GB.html) (LLR01 offshore training 7,000–40,000; LLR02; LLR83 Jordan Valley; LLP15 Dimona and LLP19 Gaza prohibited; the LLR36/500/800-series Negev ranges, merged on the chart), [ENR 6-1 route chart](https://www.gov.il/BlobFolder/guide/aip/he/LL_ENR_6_1_en.pdf), [the AIP index](https://www.gov.il/en/Departments/Guides/aip-israel)
- CARC Jordan — [ENR 2.1 FIR/UIR/TMA](https://www.carc.gov.jo/pdf/ENR_2.1_FIR_UIR_TMA.pdf) (Amman TMA 5,500–FL155 Class C), [ENR 3.1 lower ATS routes](https://carc.gov.jo/pdf/ENR_3.1_LOWER_ATS_ROUTES.pdf) (L200 ASLON–NADEK–DAXEN–KUMLO–DAPUK; L513 to BUSRA; L412 to ZELAF), [AIRAC AMDT 19/2022](https://carc.gov.jo/sites/default/files/inline-files/airac-aip-amdt-19-_2022.pdf), [ENR 1.5](https://carc.gov.jo/pdf/9-7/ENR%201.5%20Holding,%20Approach%20and%20Departure.pdf), [ENR 6-1](https://carc.gov.jo/pdf/ENR_6-1.pdf), [Eurocontrol RAIS 10.00 Israel–Jordan](https://www.eurocontrol.int/sites/default/files/2021-09/eurocontrol-rais-10.00-special-israel-jordan-wef-29sep2021.pdf) (the MUVIN crossing)
- AIP Türkiye (DHMİ) — [ENR 2.1](https://dhmi.gov.tr/AIPDocuments/LT_ENR_2_1_en.pdf) (Adana MTMA 50 NM 2,000–FL280; Diyarbakır MTMA), [ENR 3.1](https://dhmi.gov.tr/AIPDocuments/LT_ENR_3_1_en.pdf) (W74 ADA–MILBA–GAZ–SURUC–OZBEY–DYB), [ENR 3.2](https://www.dhmi.gov.tr/AIPDocuments/LT_ENR_3_2_en.pdf), [ENR 4.4](https://dhmi.gov.tr/AIPDocuments/LT_ENR_4_4_en.pdf) (NISAP, TUNLA, TUSYR, LESRI on the FIR boundary), [ENR 5.1](https://www.dhmi.gov.tr/AIPDocuments/LT_ENR_5_1_en.pdf) (LTD13 Adana air-to-air firing), [ENR 6.2](https://www.dhmi.gov.tr/AIPDocuments/LT_ENR_6_2_en.pdf), [LTAG İncirlik](https://www.dhmi.gov.tr/AIPDocuments/LT_AD_2_LTAG_en.pdf), [LTAJ Gaziantep](https://www.dhmi.gov.tr/AIPDocuments/LT_AD_2_LTAJ_en.pdf)
- [UK Mil AIP — LCRA Akrotiri combined](https://www.aidu.mod.uk/aip/pdf/ad/LCRA-Akrotiri-Combined.pdf) (the SIDs to IREFA and ANANE, the TACAN STAR via AKR HOLD, the ARFA, Flamingo Ops); [Cyprus AMC — Nicosia FIR maps](https://cyprusamc.cy/operational-maps-for-the-nicosia-fir/) and [library](https://cyprusamc.cy/aviation-library-reference-documents/); [LCD47 SOTIA NOTAM](https://notamify.com/notams/LCCC/d59adb48-39bd-411d-a751-15ed75ba20d9) (a 33-NM circle — the polygon is not published, drawn `~`); [IFALPA/IFATCA Ankara–Nicosia FIR leaflet](https://www.ifalpa.org/media/3920/23atsbl01-ankara-nicosia-fir-boundary-joint-ifatca.pdf); [Eurocontrol ERC04L](https://www.eurocontrol.int/sites/default/files/2025-08/erc04l-07aug2025.pdf)
- Syria GACA eAIP — [ENR 2.1](https://eaip.gaca.gov.sy/section/6) (Damascus FIR; Latakia CTR 15 NM on 35°28'49"N 035°56'32"E, 119.9), [ENR 3 routes](https://eaip.gaca.gov.sy/enr-routes) and [ENR 3.2](https://eaip.gaca.gov.sy/section/23) (L601 TUNLA–SALIM–KTN), [ENR 4.1](https://eaip.gaca.gov.sy/section/28) and [ENR 4.4](https://eaip.gaca.gov.sy/section/31) (DAM, RDIMA, ABBAS, BUSRA, NIKAS, TUNLA, SALIM), [ENR 5.1](https://eaip.gaca.gov.sy/section/33) (every P/R/D row blank — "published by NOTAM"), [OSDI](https://eaip.gaca.gov.sy/section/59), [OSLK](https://eaip.gaca.gov.sy/section/61) (SID NIKAS 1-J "needs military coordination"), [OSDZ](https://eaip.gaca.gov.sy/section/62)
- Lebanon (DGCA via IVAO mirror) — [AD 2 OLBA](https://lb.ivao.aero/wp-content/uploads/2023/12/LB-AD-2.OLBA-en-GB.pdf) (Beirut CTR 20 NM on KAD), [AD 2 OLKA Rayak](https://lb.ivao.aero/wp-content/uploads/2023/12/LB-AD-2.OLKA-en-GB.pdf), [ENR 1.2](https://lb.ivao.aero/wp-content/uploads/2024/01/LB-ENR-1.2-en-GB.pdf)
- The IAF roads, as reported — [Wikipedia, 1973 Syrian General Staff HQ raid](https://en.wikipedia.org/wiki/1973_Syrian_General_Staff_Headquarters_raid) ("out over the Mediterranean, before turning north towards Lebanon and then east towards Damascus"); [Wikipedia, Operation Mole Cricket 19](https://en.wikipedia.org/wiki/Operation_Mole_Cricket_19) (the Bekaa, the coastline Sidon–Beirut); [GlobalSecurity, *MML* 1973](https://www.globalsecurity.org/military/library/report/1985/MML.htm); [Al Jazeera 31 Jan 2013](https://www.aljazeera.com/news/2013/1/31/syria-confirms-israeli-airstrike), [25 Nov 2020 (from the Golan)](https://www.aljazeera.com/news/2020/11/25/israel-strikes-southern-damascus-from-occupied-golan-heights), [5 May 2021 (Latakia from the sea)](https://www.aljazeera.com/amp/news/2021/5/5/syria-intercepts-israel-attacks-near-latakia-by-the-mediterranean), [28 Dec 2021](https://www.aljazeera.com/amp/news/2021/12/28/israeli-air-raid-targets-syrian-port-of-latakia-state-media), [2 Jul 2022 (Tartus)](https://www.aljazeera.com/news/2022/7/2/syria-says-israeli-strike-on-tartus-coast-wounds-two-civilians), [17 Sep 2022 (Damascus airport)](https://www.aljazeera.com/news/2022/9/17/syria-says-five-killed-in-israeli-air-strike-on-damascus-airport), [20 Nov 2024 (Palmyra)](https://www.aljazeera.com/news/2024/11/20/at-least-36-killed-in-israeli-attack-on-syrias-palmyra-state-media); [Gulf News (from Lebanese airspace)](https://gulfnews.com/world/mena/israel-strikes-syria-from-lebanese-airspace-1.1937831), [Jerusalem Post (same)](https://www.jpost.com/breaking-news/alleged-israeli-airstrike-targets-syria-from-lebanese-airspace-670476), [CBS (over southern Lebanon)](https://www.cbsnews.com/news/israel-jets-keep-up-flights-over-southern-lebanon-after-air-strike-in-neighboring-syria); [Times of Israel — T-4](https://www.timesofisrael.com/russia-syria-blame-israel-for-deadly-strike-on-syrian-air-base/), [Masyaf by day](https://www.timesofisrael.com/syria-accuses-israel-of-conducting-rare-daylight-strike-near-masyaf/), [Aleppo](https://www.timesofisrael.com/airstrikes-attributed-to-israel-target-iran-linked-defense-factories-near-aleppo/), [Al-Bukamal](https://www.timesofisrael.com/syrian-official-blames-israel-us-for-strike-on-base-near-iraq-border/); [The Defense Post — T-4 2018](https://thedefensepost.com/2018/04/09/missile-strike-syria-t4-airbase-homs-israel/); [TASS on the Il-20](https://tass.com/defense/1022031) ("approached the target from the Mediterranean at a low altitude"), [TWZ on the Il-20](https://www.twz.com/23655/russian-il-20-surveillance-plane-went-down-off-syrian-coast-during-israeli-missile-barrage); [Yahoo/AFP low-level attack](https://news.yahoo.com/israel-launches-attack-syria-low-140108220.html); [Frantzman on Masyaf](https://sethfrantzman.com/2019/08/15/syrian-air-defense-say-they-confronted-targets-over-masyaf/)
- Northern Watch and the W74 road — [A&SF, "Northern Watch" Feb 2000](https://www.airandspaceforces.com/article/0200northern/) (the ROZ over eastern Turkey), [A&SF Aug 2002](https://www.airandspaceforces.com/article/0802norwatch/), [GlobalSecurity ONW](https://www.globalsecurity.org/military/ops/northern_watch.htm), [Jamieson, *Northern Iraq*](https://www.dafhistory.af.mil/Portals/16/documents/Airmen-at-War/Jamieson_NorthernIraq30Sep15.pdf), [Haulman, *Provide Comfort*](https://media.defense.gov/2012/Aug/23/2001330108/-1/-1/0/Op%20Provide%20Comfort.pdf), [USMC *Provide Comfort*](https://www.marines.mil/Portals/1/Publications/Humanitarian%20Operations%20in%20Nothern%20Iraq,%20Operation%20Provide%20Comfort%20PCN%2019000316500_3.pdf), [Smithsonian, "Cleared in Hot"](https://www.smithsonianmag.com/air-space-magazine/above-amp-beyond-cleared-in-hot-42511374/), [PBS at Incirlik](https://www.pbs.org/newshour/show/on-the-front-line-incirlik-air-base-in-turkey), [The Aviationist — the Tornados leave Akrotiri](https://theaviationist.com/2019/02/05/raf-tornado-gr4-jets-return-home-after-flying-their-final-operational-sortie-from-raf-akrotiri-cyprus/)
- Al-Tanf, the 55 km zone and the Euphrates line — [Wikipedia, Al-Tanf](https://en.wikipedia.org/wiki/Al-Tanf), [GlobalSecurity](https://www.globalsecurity.org/military/facility/tanf.htm), [VOA 2017](https://www.voanews.com/a/us-led-coalition-strikes-pro-syrian-government-forces-/3860332.html), [Military Times 2017](https://www.militarytimes.com/news/pentagon-congress/2017/05/30/a-showdown-is-looming-between-the-us-syria-and-iran-at-tanf/), [Brookings](https://www.brookings.edu/articles/al-tanf-garrison-americas-strategic-baggage-in-the-middle-east/), [Washington Institute](https://www.washingtoninstitute.org/policy-analysis/future-al-tanf-garrison-syria), [Stimson — Tower 22](https://www.stimson.org/2024/tower-22-us-disputed-triangle-jordan-syria-iraq-border/), [TASS 2019](https://tass.com/world/1035441), [TWZ — F-35s to Jordan](https://www.twz.com/33093/two-air-force-f-35s-make-rapid-deployment-to-jordan-to-get-closer-to-syria-action), [Wikipedia, Muwaffaq Salti AB](https://en.wikipedia.org/wiki/Muwaffaq_Salti_Air_Base), [Rukban](https://en.wikipedia.org/wiki/Rukban); [Atlantic Council — the Euphrates buffer](https://www.atlanticcouncil.org/blogs/syriasource/syria-s-buffer-zone-along-the-euphrates/), [Al Jazeera 19 Jun 2017](https://www.aljazeera.com/news/2017/6/19/russia-threatens-to-target-coalition-planes-in-syria), [MEI](https://mei.edu/publication/us-russia-standoffs-northeast-syria-just-getting-started/), [Al-Monitor 2020](https://www.al-monitor.com/originals/2020/02/russia-expansion-roadblocks-northeast-syria-zones-control.html)
- Risk pages that summarise the structure — [safeairspace Syria](https://safeairspace.net/syria/), [Cyprus](https://safeairspace.net/cyprus/), [Jordan](https://safeairspace.net/jordan/); [OPSGROUP on the Il-20](https://ops.group/blog/passenger-plane-almost-shot-down-over-syria/) and [Turkey/Syria/Iraq](https://ops.group/blog/turkey-syria-and-iraq-airspace-risk/)

What the sources do not give: the IAF's own routes (none are published —
every "road" over Lebanon, the Golan or the sea is a reported track placed on
the named town, summit or coastline and flagged `approx:true`, `~` on the
chart, listed in the brief as curated); Syria's P/R/D areas (the eAIP prints
none); the Lebanese ATS routes in usable detail. The coast and the borders on
the chart are schematic polylines, not surveyed.

**Central Region corridors (`data/corridors/germany.json`, v1.103.0).** The
Cold War Germany map, Cold War era only, both sides of the line. Seven NATO
clusters (the Eifel, the Hunsrück, the Pfalz, Rhein-Main, the Rhineland, the
Weser, the Elbe) and three Warsaw Pact clusters (the Berlin ring, the southern
fields, Mecklenburg) share six curated crossing gates — Boizenburg, Dömitz,
Helmstedt, Herleshausen, Point Alpha, Hof. What is drawn from the printed
figure and what is placed:

- The ADIZ / Flugüberwachungszone — [de.wikipedia "Air Defense Identification Zone" (dewiki.de mirror)](https://dewiki.de/Lexikon/Air_Defense_Identification_Zone): "eine Tiefe von 25 bis 30 Seemeilen bzw. später durchschnittlich 40 km Tiefe", the 1963 FlugÜZ rules, Braunschweig's 1958 exception; [DHV-Info 49 (1989)](https://www.dhv.de/media/jahre/2024/01_mitgliedschaft/DHVmagazin/Archiv/1989/dhvinfo49.pdf) — "usafe clearance" numbers still issued in 1989; [NATO AIRCOM — Germany as a special case](https://ac.nato.int/archive/2021/germany-as-a-special-case-in-the-history-of-nato-air-policing-). Drawn as a 40 km band on a schematic border (`~`).
- The belts — [relikte.com, Nike in Niedersachsen](https://www.relikte.com/nds_flarak_nike/index.htm) ("die vorderen Nike-Stellungen ca. 150 km westlich des Eisernen Vorhangs"), [HAWK in Niedersachsen](https://www.relikte.com/nds_flarak_hawk/index.htm) (the HAWK belt in front of the Nike belt's eastern edge, battalion sites by town), [the FlaRak overview](https://www.relikte.com/nds_flarak/index.htm) and [the radar sites](https://www.relikte.com/nds_radar/index.htm) (SOC 1 Brockzetel FLYFISH, SOC 2 Uedem MANDRIL, CRC Brekendorf BUGLE, Visselhövede SILVERCORK, Uedem CRABTREE, Auenhausen BACKWASH, Erndtebrück LONESHIP, RP Uelzen UNITY); [nl.wikipedia Groepen Geleide Wapens](https://nl.wikipedia.org/wiki/Groepen_Geleide_Wapens) (LOMEZ "ca. 50 km diep direct achter het IJzeren Gordijn", the KLu sites); [de.wikipedia Nike (Rakete)](https://de.wikipedia.org/wiki/Nike_(Rakete)) and [Nike-Feuerstellung Albach](https://de.wikipedia.org/wiki/Nike-Feuerstellung_Albach) (70 sites); [FlaRakGrp 38](https://de.wikipedia.org/wiki/Flugabwehrraketengruppe_38); [Air & Space Forces, "Air Defense" Jul 1983](https://www.airandspaceforces.com/article/0783air/); [CBO 1978](https://www.globalsecurity.org/military/library/report/cbo/78-cbo-029.pdf); usarmygermany.com — [32nd AADCOM](https://www.usarmygermany.com/Units/Air%20Defense/USAREUR_32nd%20AADCOM.htm), [10th ADA Bde](https://www.usarmygermany.com/units/Air%20Defense/USAREUR_10th%20ADA%20Bde.htm), [69th ADA Bde](https://www.usarmygermany.com/units/Air%20Defense/USAREUR_69th%20ADA%20Bde.htm), [94th ADA Group](https://www.usarmygermany.com/units/Air%20Defense/USAREUR_94th%20ADA%20Bde%201.htm), [108th ADA Bde](https://www.usarmygermany.com/units/Air%20Defense/USAREUR_108th%20ADA%20Bde.htm); [ACE High Journal — the CRC bunkers with printed coordinates](https://www.ace-high-journal.eu/info-seite,-crc-in-deutschland.html); [en.wikipedia List of Nike missile sites](https://en.wikipedia.org/wiki/List_of_Nike_missile_sites). Drawn as bands (`~`).
- Airspace control measures — [FM 100-103 (1987) Ch. 2](https://www.globalsecurity.org/military/library/policy/army/fm/100-103/f1001_3.htm): the LLTR "a temporary corridor of defined dimensions which allows the low-level passage of friendly aircraft through friendly air defenses", "activated for specified times only and changed frequently"; MRR, SAAFR, HIDACZ, BDZ, WFZ; [FM 44-100](https://www.globalsecurity.org/space/library/policy/army/fm/44-100/ch5.htm) ("Low-level transit routes are the NATO equivalent of MRR"); [FM 3-52 Ch. 4](https://www.globalsecurity.org/military/library/policy/army/fm/3-52/ch4.htm). No trace was ever published — the gates and the roads to them are ours.
- The corps sectors and the seam — [GlobalSecurity, Cold War NATO Army Groups](https://www.globalsecurity.org/military/world/int/nato-ag.htm) ("Gottingen (FRG)-Liege"), [NORTHAG](https://www.globalsecurity.org/military/world/int/nato-northag.htm) (I BR "from Goslar to Paderborn"), [the Fulda Gap](https://www.globalsecurity.org/military/world/war/ww3-fulda-gap.htm), [the Hof corridor](https://www.globalsecurity.org/military/world/war/ww3-hof-corridor.htm); [en.wikipedia 2 ATAF](https://en.wikipedia.org/wiki/Second_Allied_Tactical_Air_Force) ("north of the city of Kassel"), [4 ATAF](https://en.wikipedia.org/wiki/Fourth_Allied_Tactical_Air_Force), [NORTHAG](https://en.wikipedia.org/wiki/Northern_Army_Group), [NORTHAG 1989 order of battle](https://en.wikipedia.org/wiki/Northern_Army_Group_(1989)_order_of_battle); [warhistory.org — NATO's Central Region ground forces](https://warhistory.org/article/natos-central-region-ground-forces-i); [JMSS — the Minden Gap](https://jmss.org/article/download/58117/43734/158257); [BAOR July 1989 (orbat85)](https://www.orbat85.nl/documents/BAOR-July-1989.pdf); coldwardecoded — [I NL Corps](https://coldwardecoded.blogspot.com/2013/07/dutch-lions-i-netherlands-corps-in-west.html), [I BE Corps](http://coldwardecoded.blogspot.com/2013/07/shield-of-belgians-i-belgian-corps-in.html); [en.wikipedia III Corps (Bundeswehr)](https://en.wikipedia.org/wiki/III_Corps_(Bundeswehr)).
- The Berlin corridors — [FRUS 1945 vol. III doc. 1206](https://history.state.gov/historicaldocuments/frus1945v03/d1206) ("20 English miles (32 kilometers) wide, i.e., 10 miles (16 kilometers) each side of the center line"; the Control Zone "a radius of 20 miles (32 kilometers)"); [en.wikipedia West Berlin Air Corridor](https://en.wikipedia.org/wiki/West_Berlin_Air_Corridor); [Berlin Air Safety Center](https://en.wikipedia.org/wiki/Berlin_Air_Safety_Centre); [the Air Directorate report (UW digital library)](https://search.library.wisc.edu/digital/ASQ64ZF4MRHPYH8X/text/AIG64JD2VL7KA683). Drawn from the border crossing to the Control Zone.
- The GDR's own structure — [nva-flieger.de, Luftraum der DDR](https://www.nva-flieger.de/index.php/theorie/navigation/luftraum-ddr.html): the Grenzsperrstreifen's 27 reference towns, the corridors from the east ("mindestens 300m Flughöhe", "bei 10'000 Fuß"), the Control Zone "bis zu einer Höhe von 3000m", the 99 örtliche Fluglinien with their NDB bearings; [nva-flieger.de Typausbildung](https://www.nva-flieger.de/index.php/chronik/fa/typausbildung.html) (Zone 064 Rathenow); [nva-futt.de Faktensammlung](http://www.nva-futt.de/besonderheiten/info/fakten2.html); [d-d-r.de NVA Luftstreitkräfte](https://d-d-r.de/ddr-politisches-system-nva-luftstreitkraefte.html) (Bunker Fuchsbau); [mil-airfields.de Wittstock](https://www.mil-airfields.de/de/wittstock-airbase.htm) (the 1989 training routes 023–029, the Wulfersdorf SAM site); [Veith, NVA airfield list](https://home.snafu.de/veith/flugplatz.htm) (NDB idents); [coldwardecoded — LSK/LV 1989](https://coldwardecoded.blogspot.com/2013/07/east-german-luftstreitkrafte-der-nva.html). The eastern fixes are the named towns, placed (`~`).
- The 16th Air Army and the SAM ring — [en.wikipedia 16th Air Army](https://en.wikipedia.org/wiki/16th_Air_Army), [16 GvIAD](https://en.wikipedia.org/wiki/16th_Guards_Fighter_Aviation_Division), [6 GvIAD](https://en.wikipedia.org/wiki/6th_Guards_Fighter_Aviation_Division), [105 ADIB](https://en.wikipedia.org/wiki/105th_Fighter-Bomber_Aviation_Division), [gsvg88 16 VA](https://gsvg88.narod.ru/gsvg/16va.htm), [gsvg88 army aviation and SAM brigades](https://gsvg88.narod.ru/gsvg/army_gsvg.htm); [de.wikipedia Flugabwehrraketentruppen (NVA)](https://de.wikipedia.org/wiki/Flugabwehrraketentruppen_(NVA)) (the 41., 43., 51. FRBr and the FRR sites by town — the 41. FRBr ring is drawn as a 30-NM circle, `~`); [Sperenberg](https://en.wikipedia.org/wiki/Sperenberg_Airfield), [Jüterbog](https://en.wikipedia.org/wiki/J%C3%BCterbog_Airfield), [Alt Daber](https://en.wikipedia.org/wiki/Alt_Daber_Airfield), [Templin/Groß Dölln](https://www.mil-airfields.de/germany/templin-gross-doelln-airbase.html), [Parchim](https://www.mil-airfields.de/de/parchim-airbase.htm), [Oranienburg](https://www.mil-airfields.de/deutschland/oranienburg-flugplatz.html), [Werneuchen](https://www.forgottenairfields.com/airfield-werneuchen-411.html), [Stendal-Borstel](https://de.wikipedia.org/wiki/Flugplatz_Stendal-Borstel).
- The ranges — [de.wikipedia TrÜbPl Wittstock](https://de.wikipedia.org/wiki/Truppen%C3%BCbungsplatz_Wittstock) ("53° 5′ 10″ N, 12° 38′ 42″ O", 118.99 km²), [mil-airfields.de — the Bitburg replica](https://www.mil-airfields.de/de/wittstock-firing-range-gadow.htm) (N530503 E0124004), [forgottenairfields Wittstock](https://www.forgottenairfields.com/airfield-wittstock-406.html), [16va.be LABS](https://www.16va.be/labs_eng.html), [16va.be Retzow](https://www.16va.be/4.2_hind_retzow_eng.html), [16va.be ranges](https://www.16va.be/page_ranges.html); [TrÜbPl Altmark](https://de.wikipedia.org/wiki/Truppen%C3%BCbungsplatz_Altmark) ("52° 25′ 48″ N, 11° 34′ 12″ O", 232 km²); [Lieberoser Heide](https://de.wikipedia.org/wiki/Lieberoser_Heide) ("51° 56′ 7″ N, 14° 19′ 40″ O", 28 x 12 km); [urbex.nl Altes Lager](https://www.urbex.nl/altes-lager/). West: [AIP Germany ENR 5.1, AIRAC 03/24 (mirror)](https://dlapilota.pl/sites/default/files/dlapilota/upld/ED_ENR_5_1_en_2024-03-21.pdf) — ED-R 37 Nordhorn, 31 Bergen-Hohne, 32 Munster, 33 Unterlüss, 34 Meppen, 10 Todendorf-Putlos, 11 Ostsee, 13 Meldorfer Bucht, printed vertices; [RAF Nordhorn](https://en.wikipedia.org/wiki/RAF_Nordhorn); openaip [ED-R 116 Baumholder](https://www.openaip.net/data/airspaces/67dbee0da7f2a48e4ee04fc6) and [ED-R 136 Grafenwöhr](https://www.openaip.net/data/airspaces/67dbee0da7f2a48e4ee04fe7) (limits; boxes on the point, `~`); [Bundestag 16/10116](https://dserver.bundestag.de/btd/16/101/1610116.pdf) (TRA 204/304 Eifel absorbed into Lauter 2003), [de.wikipedia TRA Lauter](https://de.wikipedia.org/wiki/TRA_Lauter), [flugzeugforum TRA 205/305](https://www.flugzeugforum.de/threads/flugbetrieb-in-der-tra-205-305-und-ed-r116.49323/) (outline approximate, `~`).
- The Low Flying Areas — [NfL 2025-1-3686, Bekanntmachung über Tiefflüge](https://www.bundeswehr.de/resource/blob/6045194/3390b6f894b32299ae0e8d93533405d6/download-bekanntmachung-ueber-tieffluege-data.pdf) (the seven areas with full coordinates, re-activated 2025; [Luftwaffe — Tiefflugregeln](https://www.bundeswehr.de/de/organisation/luftwaffe/team-luftwaffe-auf-uebung/tiefflugregeln-luftwaffe)); [de.wikipedia Tiefflug](https://de.wikipedia.org/wiki/Tiefflug) (the Cold War list: Borken, Cloppenburg, Nördlingen, Holzminden, Schneverdingen, Itzehoe; 500 ft everywhere, 250 ft in the areas); [Bundestag 13/1892](https://dserver.bundestag.de/btd/13/018/1301892.pdf) ("Prinzip der freien Streckenwahl" — day low flying was free-routed); [Wissenschaft & Frieden, Risiko Tiefflug](https://wissenschaft-und-frieden.de/artikel/risiko-tiefflug/). The polygons are today's re-publication of the named areas; whether they match the 1980s outlines exactly is not stated.
- Navaids — OurAirports: [Spangdahlem SPA](https://ourairports.com/navaids/SPA/Spangdahlem_TACAN_DE/), [Nattenheim NTM](https://ourairports.com/navaids/NTM/Nattenheim_VORTAC_DE/), [Büchel BUE](https://ourairports.com/navaids/BUE/Buchel_TACAN_DE/), [Hahn HND](https://ourairports.com/navaids/HND/Hahn_DME_DE/), [Kirn KIR](https://ourairports.com/navaids/KIR/Kirn_VORTAC_DE/), [Ramstein RMS](https://ourairports.com/navaids/RMS/Ramstein_TACAN_DE/), [Zweibrücken ZWN](https://ourairports.com/navaids/ZWN/Zweibrucken_VOR-DME_DE/), [Wiesbaden WIB](https://ourairports.com/navaids/WIB/Wiesbaden_TACAN_DE/), [Taunus TAU](https://ourairports.com/navaids/TAU/Taunus_VORTAC_DE/), [Cola COL](https://ourairports.com/navaids/COL/Cola_VORTAC_DE/), [Germinghausen GMH](https://ourairports.com/navaids/GMH/Germinghausen_VOR-DME_DE/), [Hamm HMM](https://ourairports.com/navaids/HMM/Hamm_VOR-DME_DE/), [Fritzlar FTZ](https://ourairports.com/navaids/FTZ/Fritzlar_NDB_DE/), [Warburg WRB](https://ourairports.com/navaids/WRB/Warburg_VOR-DME_DE/), [Osnabrück OSB](https://ourairports.com/navaids/OSB/Osnabruck_TACAN_DE/), [Bückeburg BYC](https://ourairports.com/navaids/BYC/Buckeburg_NDB_DE/), [Wunstorf WUN](https://ourairports.com/navaids/WUN/Wunstorf_TACAN_DE/), [Leine DLE](https://ourairports.com/navaids/DLE/Leine_VOR-DME_DE/), [Nienburg NIE](https://ourairports.com/navaids/NIE/Nienburg_VOR_DE/), [Celle CEL](https://ourairports.com/navaids/CEL/Celle_NDB_DE/), [Fassberg FSB](https://ourairports.com/navaids/FSB/Fassberg_NDB_DE/), [Braunschweig BRU](https://ourairports.com/navaids/BRU/Braunschweig_NDB_DE/), [Hehlingen HLZ](https://ourairports.com/navaids/HLZ/Hehlingen_VOR-DME_DE/), [Bremen BMN](https://ourairports.com/navaids/BMN/Bremen_VOR-DME_DE/), [Nordholz NDO](https://ourairports.com/navaids/NDO/Nordholz_TACAN_DE/), [Hamburg HAM](https://ourairports.com/navaids/HAM/Hamburg_VORTAC_DE/), [Elbe LBE](https://ourairports.com/navaids/LBE/Elbe_VOR-DME_DE/), [Lübeck LUB](https://ourairports.com/navaids/LUB/Lubeck_VOR_DE/), [Kiel KHD](https://ourairports.com/navaids/KHD/Kiel_Holtenau_DME_DE/). Current data; the Cold War idents that no longer exist (Bitburg, Sembach, Gütersloh, Nörvenich TACANs) are not in it — those fields are placed at their DCS positions.
- The wings of 1985 — [36th Wing](https://en.wikipedia.org/wiki/36th_Wing), [Spangdahlem](https://en.wikipedia.org/wiki/Spangdahlem_Air_Base), [Hahn](https://military-history.fandom.com/wiki/Hahn_Air_Base), [Ramstein](https://en.wikipedia.org/wiki/Ramstein_Air_Base) / [526 TFS](https://en.wikipedia.org/wiki/526th_Fighter_Squadron), [81 TFW FOLs](https://en.wikipedia.org/wiki/81st_Tactical_Fighter_Wing), [Zweibrücken](https://en.wikipedia.org/wiki/Zweibr%C3%BCcken_Air_Base), [RAF Gütersloh](https://en.wikipedia.org/wiki/RAF_G%C3%BCtersloh), [TaktLwG 31](https://en.wikipedia.org/wiki/Taktisches_Luftwaffengeschwader_31), [JG 71](https://en.wikipedia.org/wiki/Taktisches_Luftwaffengeschwader_71_%22Richthofen%22), [Crested Cap 83](https://nsarchive2.gwu.edu/NSAEBB/NSAEBB427/docs/9.Reforger83-Crested%20Cap%2083-Display%20Determination,%203%20December%201983.pdf), [Autumn Forge 83](https://en.wikipedia.org/wiki/Autumn_Forge_83).

What the sources do not give: a published ADIZ boundary (the 1963 Bekanntmachung is not online); any LLTR/MRR trace, width or crossing procedure for the Central Region; the Cold War TRA outlines; the DFS AIP's ENR 3/4/5 for the east (robots-blocked); Soviet (as opposed to NVA) SAM sites; documented Warsaw Pact attack routings. Every crossing gate, every road over the GDR and every eastern fix is therefore placed on a named town, checkpoint or river crossing and flagged `~`; the ADIZ and the belts are bands on a schematic border; the border, the Elbe, the coast and the autobahns are schematic.

**Other theatres.** `data/historical_airspace.json` carries the Berlin air
corridors, the Syria/Euphrates deconfliction line, OEF airspace control and the
Groom box. `data/theater_identity.json` carries per-map/era national ownership
of each airbase.

**What we deliberately did not use.** Two things are widely repeated and have no
citable authority we could find: a named post-2003 **Baghdad restricted
operating zone**, and the **BIAP "corkscrew" approach**. They are folk
knowledge, so they are not in the product. Documented in
`docs/iraq-air-corridors.md`.

---

## 4. Training and doctrine

- **`missiongen/bfm.py` — the three-perch ladder.** Geometry (range, aspect,
  altitude offset) is the difficulty knob rather than an AI skill slider, and
  every standards card is generated from the rung actually flown. Design and
  instructional rationale: `docs/skillwork-syllabus.md`.
- **`data/comms_plan.json`** — one comm ladder used by every generated mission,
  so a pilot learns a single plan that holds across all starters. All UHF/VHF-AM
  values sit on real, legal frequencies.
- **`data/callsigns.json`** — each entry is tagged `documented` (a real squadron
  or flight radio callsign with a known source: incident audio, callsign
  registries) or `flavor` (plausible, invented). The tag ships with the data so
  the distinction survives.
- **`data/squadrons.json`** — real squadron identities per base, used to fill
  ramps in contiguous single-type blocks the way a real flight line reads.
- **The Training Pipeline (`data/courses.json`, `missiongen/courses.py`).**
  The three-school shape — UPT, FRS, MQT — is the order the US services train
  a pilot, and the course is laid over rides whose sources are recorded above
  (the White Knights documents, the AAR Academy, the timing track). The
  readings under `data/courses/` are original writing for this product:
  - `f4e_history.md` draws on Peter E. Davies, *F-4 Phantom II vs MiG-21*
    (Osprey, 2008) and *USAF F-4 Phantom II MiG Killers 1972–73* (Osprey,
    2005); Marshall L. Michel III, *Clashes: Air Combat over North Vietnam
    1965–1972* (Naval Institute Press, 1997) — the Sparrow/Sidewinder
    probability-of-kill figures and the training story; Robert F. Dorr and
    Anthony M. Thornborough, *Phantom: A Legend in Its Own Time*; the National
    Museum of the USAF fact sheets for the F-4C/D/E/G; the Heatblur *DCS: F-4E*
    manual for what the Block 45 airframe models. Dates and production totals
    are the commonly published ones (first flight 27 May 1958; F-4E first
    flight 30 June 1967; 5,195 built) and the chapter avoids figures the
    sources disagree on.
  - `aviation_basics.md` and `pipeline_howto.md` are general airmanship and
    product description; nothing in them is a measured claim.

---

## 5. Design, typography and accessibility

- **Flightline Technical design system** — one token source,
  `data/brand/flightline.json`, generated into the frontend by
  `scripts/gen_theme.py`. Contrast ratios are **computed, not claimed**.
- **WCAG 2.2 AA** — the standard the product is audited against. Audit and
  remediation: `docs/wcag-audit-2026-08-12.md`. Enforced in the suite by
  `tests/test_a11y.py` and `scripts/axe_check.js` (axe-core, vendored at
  `vendor/axe-core/`, MPL-2.0 — see its `LICENSE`).
- **Apple Human Interface Guidelines** — the reference for the Library's color
  semantics (v1.61.0).
- **Fonts**, all vendored under the SIL Open Font License 1.1, license text
  alongside each file in `data/brand/fonts/`: IBM Plex Mono, Source Sans 3,
  Source Serif 4, Barlow Condensed, Bangers.
- **Lucide icons** — ISC license, `data/brand/LICENSE-lucide.txt`.

---

## 6. Licensing summary

| Component | License |
|---|---|
| DCS Sortie Starter (our code) | MIT © Authentic Media LLC — `LICENSE` |
| `vendor/dcs` (pydcs) | LGPL-3.0, unmodified — `vendor/dcs/COPYING.LESSER` |
| `missiongen/terrains/{iraq,afghanistan}` | LGPL-3.0, from the dcs-retribution fork |
| `vendor/axe-core` | MPL-2.0 |
| Vendored fonts | SIL OFL 1.1 |
| Lucide icons | ISC |

Full third-party notices: `THIRD-PARTY-NOTICES.md`.

**Not affiliated with Eagle Dynamics.** DCS World and its terrain modules are
their products; this tool generates mission files for them.

---

## 7. Thanks

**The Thanks list is rendered below this section when this page is served, and
it is not in this file.** That is deliberate. Everything above is a citation —
a pinned commit, a license, a published source — and belongs in the repository
where it is versioned, reviewed and guarded byte-for-byte. Gratitude is a
living list: it changes between releases, and the person who should be writing
it is the one who knows the community, not the one who knows the build system.

So it lives on the server's data volume, is edited from the password-gated
`/admin` under **Thanks**, and is injected into this page at request time.
Also available as JSON at `/api/credits`. See `missiongen/credits.py`.

---

## 8. Where the deeper write-ups live

| Document | What it covers |
|---|---|
| `docs/dcs-iraq-map-state.md` | What ED has actually shipped for Iraq, with per-claim citations and an explicit list of what we could *not* verify |
| `docs/iraq-air-corridors.md` | The corridor research: every lane, its sources, the disagreements between them, and the four candidates rejected |
| `docs/skillwork-syllabus.md` | The training progression and its instructional design |
| `docs/pydcs-strategy.md`, `-fork-evaluation.md`, `-fork-feature-review.md`, `-plan-critique.md` | The library question, from first look to standing conclusion ("take the data, leave the engine") |
| `docs/wcag-audit-2026-08-12.md` | Accessibility audit and remediation |
| `docs/how-a-terrain-module-works.md`, `docs/afghanistan-terrain-export-runbook.md` | How terrain data is exported and verified |
| `docs/chart-authenticity-evaluation.md` | How close the theatre chart gets to a real aeronautical product, and where it deliberately stops |
| `vendor/dcs/PYDCS_PROVENANCE.md` | The vendoring discipline and the LGPL reasoning |


## Historical airspace coverage research (v1.113.0)

The [coverage register](/api/historical-coverage/report) separates routing
networks, tactical axes and overlays for all 26 supported map-era pairs.
The canonical dataset is `missiongen/data/historical_coverage.json`; the
[research record](research/HISTORICAL_AIRSPACE_RESEARCH.md) includes primary
links, access limitations, unresolved coordinates and date conflicts.

The Falklands circle follows the [28 April 1982 Hansard announcement](https://hansard.parliament.uk/Commons/1982-04-28/debates/03f1abe8-1b23-49a6-ab51-dc740649cc5e/FalklandIslands):
200 nautical miles around 51°40′S, 59°30′W, effective 30 April at 1100 GMT.
A later Naval War College reprint has a conflicting longitude; the published
Hansard coordinate is used. Termination and later changes are not inferred.

Normandy's transport reference uses **USAF Historical Study 97**, printed
pages 11–12 ([official host](https://www.dafhistory.af.mil/Portals/16/documents/Studies/51-100/AFD-090602-016.pdf),
[reviewed primary-document mirror](https://www.ibiblio.org/hyperwar/NHC/NewPDFs/USArmy/USAF%20Airborne%20Ops%20in%20WWII,%20ETO.pdf)).
HOBOKEN's coordinate is transcribed; Portland Bill and Portbail are reconstructed
geographic terminals. No width is invented and no fighter clearance is inferred.

Iraq's parallels follow [Canada DND](https://www.canada.ca/en/department-national-defence/services/military-history/history-heritage/past-operations/middle-east/iraq-1992.html)
and [US Army FY1997 history](https://history.army.mil/portals/143/Images/Publications/catalog/101-28-1.pdf).
September 1996 is month precision; an exact amendment day is not asserted.
Finite drawing endpoints are diagram extents, not an authenticated border polygon.

ICAO RASMAG/15 WP09 identifies six Afghan ATS route designators. Its old
original URL returns 404; indexed official text establishes their names,
not coordinates or today's validity. UN annex-map fetches were unavailable;
no precise Sinai treaty polygons were manufactured. Reference dates never
substitute for operational start/end dates. No map is claimed exhaustive.


## Historical document additions (v1.114.0)

The [Historical Library](/api/historical-library) publishes 18 bounded readings
from selected documents in the supplied archive. Its canonical register is
`missiongen/data/historical_library.json`; sources carry the supplied filename,
edition SHA-256, physical PDF page count, publication precision where known,
and access limits. Original scans and private filesystem paths are not served.
The archive inventory is broader than the targeted page review; this is not an
exhaustive reading of every document.

February 1981 Nevada ATC/navaid coordinates, eight tanker reference rows and
LOTUS/PLAZA/FLEX procedure notes remain separate from the 2014 recall gates and
Elgin/Sally activation conditions. Unknown datum, closed-track geometry and
operational validity are retained. Printed mixed level notation is not silently
converted into a universal altitude basis.

USAF lineage records and the 36th Wing retrospective distinguish 1944 group
moves from squadron arrivals, Bitburg aircraft transitions and temporary GULLY
JUMP basing. Official squadron fact sheets provide independent corroboration.
1973 VF-14 histories preserve original designations and aircraft variants;
VF-11's 2003 training/workups are not relabelled as an OIF deployment. GWAPS
monthly 1991 strength records and the dated 2003 USCENTAF assessment establish
snapshots and campaign structure, not exact theater corridors.

The 1978–80 F-4 pamphlets provide period systems and crew context. The ARN-101
forecast is not a universal fielding date; a planned 1979 DACT visit is not proof
of execution. CHECO weather/weapon lessons remain dated off-map context. The
Afghanistan 1989–2001 overview is secondary background based on selected early
pages, not authenticated airspace geometry. Unverified virtual-unit SOPs,
undated adaptations, the restricted MTTP and unrelated music/link files remain
explicitly held or excluded. No restricted tables or supplied scans are copied.

Iraq Gulf carrier coverage: [ED's Iraq Release FAQ](https://forum.dcs.world/topic/365676-dcs-iraq-release-faq/)
distinguishes entire-map flyability from regional scenery detail. The selected
anchor, screen and steaming window are authored geometry checked against the
Iraq projection/bounds and existing Gulf shoreline schematic; these are not a
simulator land-mask survey or a historical naval station. A public author's
[native Iraq mission](https://github.com/loreair/MISSIONE-DINAMICA-IRAQ-2026)
corroborates Gulf carrier placement. Its scripts and mission content are not
imported into our generator. See `docs/dcs-iraq-map-state.md` for the dated
research snapshot and coverage correction.
