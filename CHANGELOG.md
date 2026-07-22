# Changelog — DCS Mission Starter

All notable changes are documented here. This project follows
[Semantic Versioning](https://semver.org/) as of 1.0.0.

**Versioning policy**
- **MAJOR (X.0.0)** — breaking changes: recipe/share-link format changes that
  invalidate existing links, removed templates or building blocks, API breaks.
- **MINOR (1.X.0)** — new capability, backwards compatible: new maps, templates,
  building blocks, carriers, crew scenarios, aircraft.
- **PATCH (1.0.X)** — fixes and data corrections: airfield/preset fixes, deck
  offset tuning, warning text, doc updates.

The version lives in one place — `missiongen/__init__.py` (`__version__`) — and
is surfaced in the web UI header, `/api/options`, `/api/health`, and the PDF
guide cover.

---

## [1.22.1] — 2026-07-22 — Crew Ops honour the start setting (no more forced air start)

**Fix.** All three Crew Ops templates (`backseat_izlid`, `backseat_intercept`,
`rio_fleet_defense`, land-base path) always spawned the player flight *airborne*
via `flight_group_inflight`, ignoring the wizard's Start choice. Selecting Cold,
Warm (ramp), or Runway still put you in the air — the exact bug Rob hit on the
F-14B(U) IZLID mission, where the brief said "Start warm · Kandahar" but the jet
launched already flying. New `backseat._player_flight()` helper ground-starts the
flight from the home base honouring `recipe.start` (cold/warm/runway), then flies
the same steerpoint route; it falls back to an air start only if the base has no
free parking. Fleet-defense solo start messages and the RIO briefing block now
describe the ground start instead of assuming an air start.

Byte-affecting for Crew Ops recipes (player group start type + first waypoint
change). Determinism preserved: same recipe+seed → byte-identical `.miz`.

## [1.22.0] — 2026-07-22 — Afghanistan Theater Identity + 4 COIN-era Library missions

### Added — Afghanistan gets its real identity (Theater Identity P1/P3)

- **Alignment** (`theater_identity.json`): ISAF-era south/west — Kandahar,
  Camp Bastion and Dwyer dress as **USA**; Shindand and Herat as the **Afghan
  Air Force** (US-supplied types under the Afghanistan country — historically
  right for the ANA).
- **Real squadrons** (`squadrons.json`): the **74th EFS "Flying Tigers"**
  (A-10Cs, Kandahar — they really flew from KAF) and **VMA-211 "Wake Island
  Avengers"** (AV-8Bs, Camp Bastion). Contiguous squadron rows, tagged groups.
- **OEF airspace control** (`historical_airspace.json`): **Kabul TMA** (30 sm
  terminal zone) + **ROZ HELMAND** (representative ACO restricted operating
  zone), drawn on the F10 map and briefed. Toggle: Historical airspace.

### Added — 4 Afghanistan Library missions (map-locked, all verified)

- **Troops in Contact — Ridge-Line CAS** (A-10C, Kandahar; JTAC tasking,
  SHORAD/MANPADS threat, featured card)
- **Bastion Scramble — Harrier Alert** (AV-8B, runway alert from Camp Bastion)
- **Helmand Convoy Overwatch** (F-16 night, tight-ROE tasking)
- **Hindu Kush QRA — Northern Intercept** (air-to-air over the passes)

All four generate cleanly (0 warnings) with tasking briefs, no player waypoints.
Scenario recipes can now pin a **home airbase** (Bastion card starts you at
Bastion) — applies to all future map-locked templates.

---

## [1.21.2] — 2026-07-22 — Afghanistan parking survey baked (Kandahar + Bagram)

Rob's survey flight (460/460 spots reported) also delivered the first in-sim
proof that a mission built on our Afghanistan terrain module loads and runs.

- `parking_headings.json` += **Kandahar (281 spots, default 54°)** and **Bagram
  (179 spots, default 116°)** — parked statics on both fields now face their
  exact painted lines (verified: generated headings cluster in the real ramp
  orientations instead of a geometric guess).
- Remaining Afghanistan fields fall back to the geometric guess until surveyed;
  Falklands + The Channel remain the only wholly-unsurveyed maps.

---

## [1.21.1] — 2026-07-22 — Afghanistan projection calibrated: beta tag dropped

The in-sim projection probe came back and the computed transverse-mercator
parameters (central meridian 63, false easting −300150, false northing
−3759657) validate against all 28 probed airbases with **0.00 m** worst-case
reprojection error. Cross-checked against real-world coordinates: pydcs now
places Kandahar at 31.5058N 65.8477E vs the real 31.5058N 65.8478E.

- `terrains/afghanistan/projection.py` — probe-derived values installed.
- Map label is now just **"Afghanistan"** — kneeboard coordinates, the brief
  chart, and DTC lat/lon points are exact.
- The terrain module is complete and upstream-PR-ready (airports + projection +
  metadata, all generated per pydcs convention from a real install).

---

## [1.21.0] — 2026-07-22 — ★ AFGHANISTAN — first Mission Starter-authored map

### Added — Afghanistan terrain (beta), generated from a real install export

Rob's `standlist.lua` export (pydcs's own ME exporter) parsed clean on the first
try: **25 airports** — Bagram, Kandahar (316 stands), Kabul, Camp Bastion,
Jalalabad, FOB Salerno, Khost… — with runways, parking stands, and ATC radios,
generated via upstream `tools/airport_import.py`.

- **`missiongen/terrains/afghanistan/`** — the terrain lives in OUR package;
  `vendor/dcs` stays a pristine pydcs copy (LGPL provenance). A documented
  runtime patch (same pattern as `_determinism`) teaches pydcs's theatre loader
  about extension terrains, with graceful degradation if pydcs drifts.
- **Selectable map:** "Afghanistan (beta — nav coords pending calibration)",
  modern era; USA (Kandahar/Bastion/Shindand/Dwyer/Herat) vs Russia
  (Bagram/Kabul/Jalalabad/Gardez). Full engine verified: dressing (618 statics),
  SAMs, support air, comms, kneeboards — zero warnings; save + reload
  round-trips. Regression test added.
- **Provisional projection:** placement geometry is exact; lat/lon-derived
  output (kneeboard coords, brief, DTC points) is approximate until the Part B
  probe (`export_afghanistan.miz`) computes the true transverse-mercator
  parameters. Marked clearly in the map label.
- Upstream: files generated exactly per pydcs convention → PR-ready once the
  projection lands. Iraq next, same runbook.

---

## [1.20.0] — 2026-07-22 — squadron-block ramps + real squadron identities

### Changed — ramps now look like squadrons live there (⚠ byte-affecting)

Airfield dressing no longer rolls a weighted die per stand (statistically
correct, visually random). Stands fill in **adjacency order** with **contiguous
same-type blocks** — 4-8 fighters, 2-3 heavies, 2-4 helos per block — and each
block picks **one livery** shared by every aircraft in it. The result reads as
"a unit is based here" instead of a shuffled yard sale.

- **⚠ Determinism:** changes generated bytes for all dressed recipes; pre-1.20
  share links won't reproduce byte-identically (accepted during beta).

### Added — `squadrons.json`: real squadron identities per base

When a base has squadron entries, its plane stands fill with those blocks FIRST
(type, count, one livery, squadron name tagged on the group), then fall back to
the theme. Entries are nation-gated so alignment flips never park the wrong
side's squadron. Seeded: RAF No. 31 Sqn at Akrotiri, IAF 110/69 Sqn at Ramat
David, TuAF 181 Filo at Incirlik, 64th AGRS + 17th/66th WPS at Nellis.
Validated in `validate_data_packs` (refs, counts, nations). Community-extendable.

### Note on blank skins

Liveries remain best-effort guesses until `scripts/dump_liveries.py --merge` is
run against a real DCS install — unknown ids fall back to the default skin.
Uniform-per-block picking ships now; verified ids arrive with the harvest.

---

## [1.19.3] — 2026-07-22 — F-14B(U) roster fixes + HTML roadmap

### Fixed — "the F-14B(U) isn't always available"

Two causes, both real:

- **Era mismatch between UI and server.** Pending-module roster entries carried
  no `service` dates, so the UI offered the F-14B(U) in **every** era — but the
  server correctly rejected non-modern eras (`EraViolation` → 400), so the
  download failed. The UI now receives the same service data the server
  validates with, and era-filters the B(U) identically (Modern only, by design).
- **Sort-order discoverability.** Pending modules were appended *after* the
  roster sort, so the B(U) dangled at the bottom of the aircraft dropdown
  instead of alphabetizing into the F-14 cluster. Roster now re-sorts after
  appending.

(Also by design: on a carrier start the B(U) only appears for catapult decks —
not the Invincible or the Essex.)

### Changed — roadmap is now a styled HTML page

`/api/roadmap` serves `docs/roadmap.html` — a dark-themed, card-based page
matching the app (shipped / now / next / pillars / new maps), refreshed to
v1.19.x reality. `docs/ROADMAP.md` remains the plain-text source for GitHub.

---

## [1.19.2] — 2026-07-22 — surface Historical Airspace + Theater Identity in the UI

### Fixed

- **Air-corridor graphics were unreachable from the web UI.** The engine's
  `bb_historical_airspace` flag (Berlin Air Corridors, Syria Euphrates
  deconfliction) was never exposed as a frontend toggle, and the scenario-preset
  copier didn't include it — so even the Berlin Corridor Transit card generated
  **without** its corridors when built through the UI (engine tests passed
  because they bypass the frontend). Now: a **Historical airspace** toggle under
  Briefing aids, included in share-link defaults, and copied from template
  recipes — the Berlin card generates its corridors again.
- **`bb_alignment` surfaced** as a "Theater identity (nation alignment)" toggle
  on the Airfields screen (default on), so users can see/control why Akrotiri
  parks RAF jets.
- `bb_dtc` intentionally remains auto (on for the F-14B(U)) rather than a UI
  toggle — its None/auto default is tri-state.

Verified end-to-end in a headless browser: toggles render, and the Library's
Berlin card now carries `bb_historical_airspace: true` into the generated recipe.

---

## [1.19.1] — 2026-07-21 — every template is guaranteed a Library card

- **Library completeness:** the Library now renders **all** scenario templates,
  not just those with hand-written card metadata — a template with no `library`
  block gets a synthesized card (role inferred from its key/label, premise from
  the label, threat from its recipe). Since the wizard no longer has a Scenario
  step, this guarantees no template can become unreachable.
- **README deployment contract:** explicit hosting instructions (run the app
  as-is; do not regenerate) plus non-negotiable product requirements for any
  agent that re-skins the UI — two entry paths, ALL templates in the Mission
  Library, no scenario step in the builder, full builder preserved, on-demand
  generation, visible backend version. Written for the Replit upload workflow.

---

## [1.19.0] — 2026-07-21 — Mission Library (two paths: pick or build)

### Added — Library front door

A new entry with two paths: **Pick from the Library** (curated, ready-to-fly
scenarios) or **Build a Mission** (the full builder, unchanged). The **Scenario
step is removed from the wizard** and now lives entirely in the Library.

- **Library gallery** — card per scenario, colour-coded by role (air-to-air,
  strike, SEAD, CAS, carrier, training, historic), with a fantasy-forward title,
  one-line premise, and scannable chips (era · threat meter · SP/MP · carrier).
  Role tabs + Era + Difficulty filters, plus an "only what I own" toggle
  (heuristic on free maps) that surfaces "requires <map>" honestly.
- **Detail → pick/preview/tweak** — era selector (Era shapes both paths), crew
  difficulty for crew-ops, "what's set up for you", then **Generate & Download**
  or **Open in Builder to tweak**. Both reuse the existing engine: generation is
  **on-demand** (recipe is the artifact; preserves seed/re-roll variation and the
  tweak handoff — not pre-baked).
- **Initial library (8 missions):** Carrier Qualification, ACLS Practice, CAP /
  Alert-5, SEAD / Wild Weasel, Berlin Corridor Transit, plus the F-14B(U) crew-ops
  (Jester IZLID, Iceman GCI Intercept) and F-14 Fleet Defense. Each is a real,
  tested preset that generates a valid `.miz` (verified 8/8).
- Backend: `mission_templates.json` entries carry `library` card metadata +
  `default_map`; `/api/options` exposes it. Builder wizard otherwise untouched.

---

## [1.18.0] — 2026-07-21 — F-14B(U) launch-ready + full DTM cartridge injection

Release cut for the F-14B(U) launch (Jul 22). Folds in three in-sim survey
findings and completes the Data Transfer System.

### Added — real DTM cartridge injection (`dtc.emit_dtm`)

Reverse-engineered the DTM format from a plain-vs-cartridge `.miz` pair: DCS
stores the F-14B(U) cartridge as a **JSON sidecar** at `DTC/<name>.dtc`, matched
to the jet by its internal `"type": "F-14BU"`. Mission Starter now **writes that
sidecar** so a generated mission opens with the cartridge pre-loaded in the DTM
page — no hand-transcription.

- Populates only **NAV** reference data — `additional_points` (bullseye,
  homeplate, CDNU fix points, threat centres, support anchors) and `lines`
  (threat WEZ rings as closed plot lines, point-budget-simplified). **Waypoints
  stay empty and JDAM/weapon targets stay empty** — never the player's route or
  loadout (regression-tested). CMDS/TIS come from a scrubbed template skeleton.
- Deterministic (sorted-key JSON, fixed zip timestamp): same recipe+seed → a
  byte-identical cartridge, so share links reproduce it.
- The `.dtc` setup card still ships alongside for reference.

### Fixed — verified F-14B(U) type id + real footprint

- Real DCS type id is **`F-14BU`** (survey-confirmed); the pre-release guess
  `F-14B-U` would have broken every generated B(U) mission. Marked verified;
  flight data inherits F-14B until pydcs adds a native class. Radio presets (UHF
  radio [1]) and carrier catobar confirmed end-to-end.
- Applied the surveyed real bounding box (19.62 × 20.34 × 6.29 m) to the whole
  flyable Tomcat family via `airframe_dimensions.json`; pydcs understated span as
  10.15 m (swept), so parked Tomcats could get GSE/statics under the wingtips.
  **⚠ Byte-affecting** for existing parked-F-14 missions (accepted during beta).
- `airframe_dimensions.json` validated in `validate_data_packs` (fails
  `/api/health` on a bad entry).

---

## [1.17.0] — 2026-07-21

### Added — F-14B(U) DTC setup card (`missiongen/dtc.py`)

First slice of the F-14B(U) Data Transfer System support, timed to the module's
release week. Ships the **schema-independent** half now; the actual DTM byte
injection stays gated on the (undocumented) cartridge format.

- **DTC Setup Card** — a printable "punch this into the DTM" reference the RIO
  would otherwise transcribe by hand from the map: **bullseye**, **homeplate +
  TACAN**, **CDNU fix points** (from BB-22 nav points), **threat areas** (SAM
  WEZ rings), **support anchors** (tanker/AWACS/CV), and the **comm/TACAN plan**
  mirroring the generated card. Written as a sidecar `DTC_Setup_Card.md` and
  bundled into the `/api/brief` pack.
- **Philosophy-safe by construction:** the card emits battlespace *reference*
  only — never the player's waypoints, ingress/egress route, target run, or
  loadout. A regression test asserts none of those tokens can appear.
- **Point-budget simplifier** — Douglas–Peucker decimation (`dtc.simplify`) so
  plot-line geometry fits the DTM's group/point limits; over-budget threats are
  logged, never silently dropped.
- **Gating & determinism:** new `bb_dtc` recipe flag, default *auto* (on only for
  the F-14B(U)). The card is a sidecar file, so `.miz` bytes — and the share-link
  determinism contract — are unchanged.
- `dtc.emit_dtm()` is a deliberate, documented stub: it raises rather than
  fabricate a DTM byte format. Unblocks once a plain-vs-cartridge `.miz` pair is
  run through `scripts/dtc_inspect.py`. Design spec: `claude/f14bu-dtc-design.md`.

---

## [1.16.3] — 2026-07-21

### Fixed — code-review remediation (release blockers + reliability)

External code review of 1.16.2 returned "request changes." This release clears
the blocking and high-severity findings.

- **CRITICAL — restored `pyproj`.** Vendored pydcs imports pyproj at import time
  (`vendor/dcs/terrain/terrain.py`), but 1.16.2 had removed it from
  `requirements.txt`. A clean `pip install` produced an app that crashed on
  `import dcs`; the dev container only worked because pyproj happened to be
  pre-installed. Re-pinned `pyproj==3.7.2`. Added a CI **import smoke test**
  (`import server.app`) so a missing startup dependency fails the build.
- **HIGH — WWII coalition assignment.** pydcs' default mission pre-sorts Germany
  (and UK/USA) into the **blue** coalition. On WWII Normandy and The Channel,
  Germany is **red** — but `builder._get_country` accepted pydcs' default side,
  so red German airfields spawned their aircraft under a blue-coalition Germany.
  It now force-moves a country into the requested coalition. New regression test
  asserts Germany lands on red (and never leaks to blue) for both maps.
- **HIGH — temp-dir leak on failure.** `/api/generate`, `/api/dl` and `/api/brief`
  created a temp directory inside the `try` and only cleaned it up on success;
  any generation error leaked the directory. Cleanup now runs on every failure
  path.
- **HIGH — strict request validation.** `Recipe.from_dict` silently dropped
  unknown fields (a typo'd/renamed option vanished, so you got a *different*
  mission than you asked for) — it now rejects them. `map` and `era` are now
  validated against the data packs with a clear message. `KeyError` is no longer
  treated as a user error (400), so a genuine internal bug surfaces as a logged
  500 instead of a misleading "bad request."

### Changed

- **Data-pack validation extended.** `validate_data_packs` now also resolves
  `nation_rosters` (100+ refs + WWII anachronism guard + country check),
  `theater_identity` base owners, and carrier `hull_class` consistency — not
  just eras and ramp themes. `/api/health` returns **503** (not 200 + ok:false)
  when the packs are invalid, so a monitor/load-balancer treats it as unhealthy.
- **Versioned share links.** Share codes now carry a schema version in a small
  envelope. Legacy (pre-envelope) codes still decode; a code from a *newer*
  schema is refused with a clear "update to open it" message instead of silently
  mis-decoding into a different mission.
- **Test coverage.** Added a template-based recipe (`sead_range`) to the
  cross-process determinism suite, which previously claimed template coverage
  but had none.

---

## [1.16.2] — 2026-07-20

### Changed — make the seed's meaning explicit to the end user

The web UI already explained it ("Variation (seed)" + 🎲 re-roll), but the brief
and the in-game briefing printed a bare "SEED 7". Now, everywhere it reaches a
user, it says what it does:

- **Brief PDF**: data card field is "VARIATION (SEED)"; the GET FLYING strip
  gains the plain-language rule — *same settings + seed rebuild THIS exact
  mission (share it and a friend flies the identical flight); new seed = a fresh
  layout of the same setup*. Chart title block says "VARIATION 7".
- **Brief Markdown**: same explainer as a callout under the header.
- **In-game briefing footer**: "recipe seed 7" → the full plain-language line.

## [1.16.1] — 2026-07-20

### Changed — Brief theater chart: cartographic rework (Rob: "looks bad")

Review verdict: the v1.16.0 chart was symbols floating in tan void — no land/
water, unlabeled grid, label collisions, no symbology discrimination. Fixes:

- **Land/water base** (`data/coastlines.json`): hand-authored schematic
  coastlines in lat/lon — the Med + Cyprus for Syria (the carrier now sits in
  water, Cyprus fields sit on the island), provisional Persian Gulf. Data-only
  per map; maps without data render all-land as before.
- **Labeled graticule** at whole degrees (N36° / E38°), equal-scale panel
  letterboxed to the data aspect.
- **MIL-STD-2525 discrimination**: friendly fields = circles, hostile = diamonds.
- **Label declutter**: greedy placement against occupied boxes; threat sites are
  **numbered** on-chart with a THREAT ORDER OF BATTLE table below (the mil-chart
  answer to clustered SAM rings).
- **Bullseye range rings** at 20/40/60 nm — the bullseye is now usable for calls.
- **Chart title block** (mil-chart margin data): theater/era, DTG, seed,
  "SCHEMATIC · NOT FOR NAVIGATION", ticked scale bar.
- Still byte-deterministic; no-coastline maps verified unchanged-safe.

## [1.16.0] — 2026-07-20

### Added — Mission Starter Brief (pre-flight briefing pack: PDF + Markdown)

- **`missiongen/brief.py`** — a printable 4-page brief that rides alongside the
  .miz: **mission data card** (map/era/aircraft/start/weather/QNH/threat/seed +
  aligned coalition nations + a "get flying" strip) · **THEATER CHART** drawn to
  the tactical chart standard (chartstyle palette on terrain-tan: cyan fields
  and support orbits, scale-true red WEZ rings with the AD glyph, amber targets,
  carrier + BRC arrow, gold home star, dual-ring bullseye, graticule, scale bar,
  legend) · **comms/nav card** (full ladder with C/S, freq, cockpit CHAN, TACAN;
  QNH in 3 units; nav points) · **airfields & forces** (own/enemy fields with
  aligned owner nations and runway headings, threat level, support airborne).
- **Format decision (UX):** PIL-rendered pages → native multi-page PDF — the
  same machinery as the in-cockpit kneeboard, zero new runtime deps, and the
  paper chart matches the F10/kneeboard visual language. HTML→Chromium rejected
  for server runtime (container weight); reportlab unnecessary (chart is an
  image either way). Markdown emitted alongside for Discord/forum sharing.
- **Delivery decision (UX):** the .miz stays the untouched primary download;
  **`POST /api/brief`** returns a briefing-pack zip (PDF + MD) **statelessly** —
  the determinism contract regenerates the identical mission from the recipe, so
  nothing is stored server-side. Frontend gains a "BRIEFING PACK" button beside
  GENERATE.
- **Determinism extended to paper:** PDF metadata (title/dates) pinned to the
  recipe/mission date — same recipe ⇒ **byte-identical brief**. Also fixed a
  Pillow gotcha: its PDF writer needs `Image.init()` before save or RGB pages
  hit KeyError('JPEG') / bloat to 20 MB+ ASCIIHex (556 KB with JPEG pages).
- `generate(recipe, out, brief_dir=...)` renders the pack alongside the mission.

## [1.15.0] — 2026-07-19

### Added — Per-nation ramp rosters (International Alignment, second slice)

- Aligned bases now park **nation-correct TYPES**, not just skins. An Israeli
  base flies **F-15/F-16** (IDF), RAF Akrotiri the **Tornado**, Syria **MiGs**,
  GDR/USSR the right **MiG-21/MiG-29/Su-25/Su-27** mix, Germany/RAF the **Tornado**
  in Cold War, and **Iran parks the F-14A Tomcat**. Finland Hornet, Norway F-16,
  Georgia Su-25, Turkey F-16/F-5 also wired.
- **`data/nation_rosters.json`** — per-nation, era-gated fast-jet rosters. Only
  the `planes` list is nation-specific; transports/tankers and helos inherit from
  the side theme (a C-130 is a C-130). Every ref verified to exist as a DCS module
  and fit its era window (e.g. GDR's MiG-29G excluded from the ≤1985 Cold-War block).
- **`alignment.roster_theme(era, nation, side_theme)`** merges the roster over the
  side theme; wired into the builder's dress loop per base. **Additive**: a nation
  with no roster for the era falls back to the side theme (livery still nation-
  correct via the aligned country). Determinism preserved; same recipe reproducible.
- **Regression guard** `test_nation_rosters_place_correct_types`: Israel parks
  F-15/F-16, Syria parks MiGs, Iran parks the F-14A.

## [1.14.1] — 2026-07-19

### Added — International Alignment: more theaters (data-only)

- Alignment data for **Caucasus** (Georgia vs Russia), **Kola** (Norway/Finland/
  Sweden vs Russia), **Persian Gulf** (USA/Oman/UAE vs Iran), and **Normandy WWII**
  (USA/RAF vs Germany) — on top of Syria and Germany. Each is a pure
  `theater_identity.json` add, proving the pillar scales by data alone.

### Known issue (pre-existing, logged)

- On some maps whose enemy `preset` country is a pydcs default-blue nation (e.g.
  **Normandy**, red = Germany), enemy statics can land in the blue coalition.
  This predates alignment (it's the `enemy_country` path, not the alignment
  lookup) — queued as a NOW patch.

## [1.14.0] — 2026-07-19

### Added — International Alignment (Theater Identity pillar 1, first slice)

- **The spine of Theater Identity**: each airbase is now dressed with its **real
  owning nation's** DCS country instead of one country per side. On Syria modern
  the blue coalition dresses as **Turkey** (Incirlik/Hatay/Gaziantep/Adana),
  **Israel** (Ramat David), and **UK** (RAF Akrotiri); Germany Cold War dresses
  as **USA / UK / Germany** (USAFE + RAF + Luftwaffe) vs **USSR / GDR**. Statics
  carry the correct national identity and liveries — an Israeli base draws IDF/AF
  squadron skins, Syrian bases draw Syrian, RAF bases draw RAF.
- **`data/theater_identity.json`** — per-map/era base→nation ownership (Syria
  modern + coldwar, Germany coldwar shipped). Adding a theater is data-only.
- **`missiongen/alignment.py`** + `bb_alignment` recipe flag (default on).
  **Purely additive**: a base with no entry falls back to the side's preset
  country, and a map/era with no block is a full no-op — so unaligned maps are
  byte-identical and same-recipe output stays deterministic.
- Aircraft *types* still come from the side ramp theme; per-nation rosters are a
  later ramp-themes expansion — this slice sets COUNTRY + LIVERY (the visible win).
- **Regression guard** `test_alignment_dresses_bases_by_owning_nation`: Syria's
  blue side carries Israel/Turkey/UK; an unaligned map uses a single side country.

## [1.13.0] — 2026-07-18

### Added — Chart-style system + authenticity fixes (Theater Identity P3)

- **`missiongen/chartstyle.py`** — one shared tactical-chart style system (a
  DCS-drawing subset of MIL-STD-2525D / JP 3-52 / FAA conventions): semantic
  palette + category→(color, fill, weight, line_style) table + tactical-icon and
  corridor-geometry helpers. `graphics.py` and `airspace.py` now draw from it so
  the whole F10 chart reads as one system.
- **Corridors are now SQUARE-ended lanes**, nested into the Berlin Control Zone
  at the terminating end, with a **dot-dash centerline** — replaces the rounded
  `oblong` (which read as a racetrack orbit, not a lane; Rob flagged it). Locked
  by a regression assertion.
- **Threat WEZ rings now carry a MIL-STD-2525 Air-Defense glyph** at the shooter
  and use the chart-style threat spec — a ring + icon reads as a SAM site
  instantly instead of a plain red disc.
- **Syria Euphrates deconfliction line** (modern era) — first data-only Historical
  Airspace add beyond Berlin: an amber dashed coordination line with the US/Russia
  flight-safety MOU briefing. Proves the P3 pattern travels via `historical_airspace.json` alone.

## [1.12.0] — 2026-07-18

### Added — Scenery keep-out framework (Class-3 fix: statics on buildings)

- **The gap**: pydcs exposes runways and parking slots but **no building/hangar
  geometry**, so free-placed GSE/infra could land on top of a hangar (Rob's
  Nellis report). The occupancy registry only keeps our own objects off each
  other — it can't see map scenery. On Nellis the `shelter` flag is no help
  (sunshades/hangars report `shelter=False`), so the definitive fix is a survey.
- **`scripts/build_scenery_survey.py`** — builds a throwaway `.miz` that sweeps a
  sphere around each preset field with `world.searchObjects(SCENERY)` and logs one
  `SCNKEEP|field|type|x|z|radius` line per building to `dcs.log` (Su-25T player
  slot so it's flyable; same offline-tool pattern as the parking survey).
- **`scripts/import_scenery.py`** — bakes the big footprints into
  `data/scenery_keepout.json`, filtering out small props (< 12 m) and capping
  absurd boxes; falls back to a type-name size table when DCS reports no box.
- **`AirfieldKeepOut`** now loads building footprints for the map/field (when a
  survey is baked) and `clear()` rejects any free-placed object inside one —
  threaded through `dress_airfield(map_key=…)`. **Purely additive**: with no
  data file present it's a no-op, so generation is byte-identical until a survey
  is baked (determinism preserved). Scenery survey for **Nellis delivered to Rob**.

## [1.11.1] — 2026-07-17

### Changed — Berlin corridor briefing: historical accuracy

- Enriched the Berlin Air Corridors briefing block with researched dates and
  terminal detail: agreed ~30 Nov 1945; controlled by the four-power **Berlin
  Air Safety Centre** (est. 12 Dec 1945); in force until **BASC closed 31 Dec
  1990** at reunification (a Cold-War-only feature). Ceiling note now includes
  the occasional raise to 13,000 ft for Soviet exercises, and each corridor
  lists its principal West-German terminals (Northern=Hamburg, Central=Hanover/
  early "Bückeburg", Southern=Frankfurt). Confirms the overlay's `coldwar` gate
  is historically correct — corridors did not exist post-reunification.
- Reference note saved (`berlin-corridors-history.md`); wiki updated.

## [1.11.0] — 2026-07-17

### Added — Historical Airspace (Theater Identity pillar 3, first slice)

- **Berlin Air Corridors overlay** on the Cold War Germany map. The three
  20-statute-mile corridors (North/Hamburg, Center/Hannover, South/Frankfurt)
  and the 20 sm Berlin Control Zone are drawn on the **F10 Common** layer —
  corridors as stadium swaths, the zone as a circle — with a BASC airspace note
  appended to the briefing (lateral limits, 10,000 ft ceiling, interception
  risk). A circular trigger zone is laid at the Control Zone for a future
  scoring layer. **Information, not routing — no player waypoints.**
- **`berlin_corridor_transit` scenario template** (Germany · Cold War · F-4E):
  turns the overlay on, disables SAMs/threats, and carries an airspace-
  discipline tasking block ("fly the lanes, respect the ceiling, clean transit").
- **New data + module:** `data/historical_airspace.json` (geometry in lat/lon,
  widths in statute miles; projection-independent) and `missiongen/airspace.py`
  (reads the data, projects, draws, returns the briefing block). Adding Iraq
  Northern/Southern Watch or the Syria deconfliction line is now a data-only
  edit against the same machinery.
- **New recipe flag `bb_historical_airspace`** — default **off**, so existing
  share links stay byte-identical (determinism contract preserved).
- **Regression guard** `test_berlin_corridors_draw_and_brief`: asserts the
  corridors/zone draw + the BASC brief when on, and that the overlay stays off
  by default.

## [1.10.3] — 2026-07-16

### Fixed — statics spawning inside aircraft / on top of each other
Rob's report: GSE trucks inside parked aircraft, statics stacked on other objects.
Classified into three defect classes; two fixed here, one queued.

- **GSE inside heavies (fixed).** The GSE truck offset was scaled to the STAND
  (4–9 m) — but a B-52 half-span is 28 m, so the truck spawned inside any
  airframe bigger than a fighter. The offset is now derived from the AIRCRAFT
  footprint (pydcs exposes real width/length per type): wingtip + 3–6 m.
- **Occupancy registry (fixed).** Placement classes only checked the runway
  corridors, never each other. `dress_airfield` now keeps an (x, y, radius)
  registry: every aircraft static (0.6× circumscribing half-extent — tight
  ramp spacing allowed, gross overlap rejected), GSE truck, and infra object
  registers and must clear it first; stands claimed by the player/ambient AI
  are pre-registered from stand dimensions. Verified across seeds (pydcs-load
  audit incl. parked AI): 0 statics inside aircraft footprints, 0 gross
  aircraft overlaps. New regression test locks it.
- **Statics on map buildings (queued, engine gap).** pydcs has NO scenery
  database — terrain buildings are invisible at generation time (same class
  of gap as land/water and parking headings). Plan on the roadmap: extend the
  proven survey pattern (Lua `world.searchObjects` exporter → per-airfield
  `scenery_keepout.json`), one survey flight per map.

## [1.10.2] — 2026-07-16

### Fixed — carrier aircraft dropdown collapsed to the AV-8B
Selecting the carrier in **Cold War** defaulted the hull to the first era option —
the **V/STOL Invincible** — which restricts the jet roster to the AV-8B only.
`eraHull()` already preferred a CATOBAR deck but was only a fallback, never used
once the dropdown had picked Invincible.
- `refreshCarrierUI()` now defaults the hull to a **CATOBAR deck** (full fixed-wing
  air wing → Forrestal in Cold War, a CVN in modern), not the first list entry.
  The Invincible/Harrier stays selectable for a deliberate V/STOL mission (and
  still correctly shows only the AV-8B when chosen).
- `applyScenarioPreset()` forces a CATOBAR hull for a carrier scenario that
  doesn't pin one (Carrier Qualification), so it can't inherit a previously
  picked Invincible and collapse to the AV-8B.
- ACLS Practice and Carrier Qualification now default to the **F/A-18C** (the
  canonical boat trainer) instead of an arbitrary carrier-capable jet.

## [1.10.1] — 2026-07-16

### Fixed — v1.9.1 code review: reproducibility, placement, presets, validation, ops
An external review (executed, not inferred) found the core "a share link IS the
mission" promise was broken across processes, plus placement/preset correctness
bugs. All P0/P1/P2/P3 items fixed and locked with a test suite + CI.

- **P0 — share links now reproduce byte-for-byte across processes.** Two pydcs
  non-determinism sources, both independent of our seeded rng: an import-frozen
  `random` default in `add_runway_waypoint` (fixed at the ambient call site by
  passing `distance` from the rng), and `Country.next_onboard_num` popping a set
  of strings (PYTHONHASHSEED-dependent → patched to `min()` in
  `missiongen/_determinism.py`). Verified identical across 4 processes / varied
  hash seeds.
- **P0b — `slot_name` is not unique (Syria).** Six Ramat David stands are named
  "02"; keying on the name under-placed ramps (86→69), emitted duplicate DCS
  unit names (which DCS rejects), and applied one twin's facing to the others.
  Now keyed on the unique `crossroad_idx` (`placement.slot_key`) for dedup,
  unit/group names, and geometric headings. All 86 stands placeable; names
  unique; no backwards parking.
- **P0c — radio presets wrote UHF into VHF radios.** The premise "radio 1 is
  always UHF" was inverted for the A-10C (UHF is radio 2), Apache, and others,
  and VHF-only jets (Spitfire, MiG-21, Ka-50, Gazelle) got invalid UHF presets.
  `presets.py` now picks the module's actual UHF radio by band, skips airframes
  with no UHF radio, reserves Guard before agencies (no more CH8 clobber), and
  the card advertises only channels actually programmed.
- **P1 — tests + CI.** `tests/test_determinism.py` (cross-process byte-identity,
  round-trip, data packs) and `tests/test_regressions.py` (the P0b/P0c bugs).
  `.github/workflows/ci.yml` runs them on every push. `requirements.txt` pinned;
  dead `pyproj` dep removed.
- **P2 — recipe validation + error contract.** `Recipe.validate()` rejects bad
  enums/bounds with field-level messages — `coalition="purple"` no longer
  silently flies you from the RED side. `/api/generate` and `/api/dl` share one
  build path: user errors → 400 with a clean message, real bugs → 500 (logged,
  no leaked server paths). A hand-edited share link now 400s instead of 500.
- **P3 — ops.** Temp dirs cleaned up after each response (BackgroundTask; was
  leaking ~93 KB/request). Dockerfile no longer pip-installs an unpinned pydcs
  that the vendored copy shadowed (dead + non-reproducible); container runs as a
  non-root user.
- **P4 — clean guards** for unknown map/era and unresolved airbases (no more bare
  KeyError/IndexError); removed a dead `__import__` and unused import.

## [1.10.0] — 2026-07-16

### Added — Template Library (scenario presets) + Scenario-step UX rework
Requirements/UX in the roadmap; Rob greenlit the first batch + the contextual-filter model.

**Four scenario templates** (`missiongen/data/mission_templates.json`) — opinionated
presets that arrange the sandbox into a recognizable mission, with SUGGESTED tasking
in the briefing and NO forced waypoints (the Starter rule holds):
- **Carrier Qualification (CQ)** — boat into the wind, recovery deck, tanker overhead, calm threat picture. Case I/III currency.
- **ACLS Practice** — SuperCarrier (auto-gated to ACLS-capable hulls), Link4 + ACLS, night/weather, Mode I/IA coupled approaches.
- **CAP / Alert-5** — enemy air picture up (intensity 4, mixed), AWACS + tanker; hold the line.
- **SEAD / Wild Weasel Range** — heavy SAM belt (intensity 4), targets on, AWACS + tanker; roll back the defenses.

**Scenario-step UX rework** (contextual filter):
- The template picker moved from the LAST screen to a **"Scenario" step right after Theater** (map+era), and is **filtered to only scenarios valid for that theater** — carrier scenarios hide on landlocked maps, modern-only ones vanish in WWII. Fixes the late-override anti-pattern (a preset arriving after you'd already configured everything).
- Picking a scenario **pre-fills the downstream wizard** (carrier/home, blocks, threats, weather, suggested aircraft), all still editable — a fast-fill, not a separate track. "Build your own" is the default.
- Builder: scenario templates fall through to a NORMAL player flight (only crew-ops templates own their own), get their tasking briefing block, and are era-gated from data. Verified all four generate a player flight + tasking; filtering verified across Nevada (no carrier), caucasus/coldwar, and WWII.

## [1.9.3] — 2026-07-16

### Added — realistic altimeter setting (QNH) in the briefing
Every mission used to ship DCS's default `weather.qnh = 760 mmHg` — which is
exactly 29.92 inHg / 1013 hPa, the ISA standard — so the briefed altimeter was
always standard. Now (`missiongen/pressure.py`):

- A **seeded QNH** correlated to the weather preset: clear ~1018–1028 hPa,
  scattered ~1010–1018, overcast ~1000–1010, storm ~992–1002. Derived from the
  mission seed, so it's reproducible and matches the Variation number.
- Baked into the mission (`m.weather.qnh`, mmHg) and printed in **all three
  altimeter units** on the briefing and the kneeboard comms page:
  *"Altimeter (QNH): 29.77 inHg / 1008 hPa / 756 mmHg — set it before you taxi."*
  inHg for US jets, hPa for the metric jets, mmHg for the Russian/DCS-native side.
- Verified: QNH varies by weather and seed (never a flat 760), unit conversions
  round-trip, and the line renders in briefing + kneeboard.

## [1.9.2] — 2026-07-16

### Fixed — carrier F10 arrow rendered perpendicular to the ship's track
`graphics.draw_layers` passed the compass BRC straight into pydcs
`layer.add_arrow(angle=...)`. The DCS arrow's default point set points along
**+Y (due East / 090)** at angle 0 and the angle field is degrees-clockwise,
while BRC is a compass bearing from North — a clean 90° mismatch, so the arrow
drew across the track. Fix: `angle = (brc - 90) % 360` at the single call site.
Verified in the .miz (BRC 300 → arrow angle 210). The ops-box oblong was already
correct (built from geometry, not the angle field).

## [1.9.1] — 2026-07-16

### Added — carrier identity: real callsigns, hull-matched TACAN, 3-letter idents
Requirements doc: `docs/requirements-carrier-identity.md` (approved; Forrestal = "Fid").

- **Verified voice callsigns (ACP 113(AI))**: Rough Rider (CVN-71), Union
  (CVN-72), Warfighter (CVN-73), Courage (CVN-74 Stennis), Lone Warrior
  (CVN-75). Forrestal answers to **Fid** — her documented fleet nickname
  ("First In Defense"), marked as convention. Essex (WWII calls rotated per op)
  and Invincible (RN, undocumented) keep "Mother". The comm card shows
  "Warfighter (Mother)" — the identity AND the brevity word pilots actually say.
- **TACAN channel = hull number**: 71X–75X, Forrestal 59X, Invincible 5X
  (pennant R05). 3-letter Morse idents: TDR, ABE, GWN, STN, HST, FID, INV.
  No conflicts: boats live on the X band, tanker (39Y) and the fallback
  allocator (40Y+) on Y. pydcs derives the correct paired beacon frequency
  from the channel (73X → 1160 MHz, verified in the .miz).
- **Wiring**: identity lives per hull in `carrier_decks.json`
  (`voice_callsign`, `tacan_channel`, `tacan_ident`, `callsign_verified`);
  `comms_plan.json` is the fallback. Briefing YOUR FLIGHT line now names the
  boat ("Warfighter is on CH 2"); guide comm section lists all callsigns and
  the hull-number rule.
- **Verified in .miz** for all 8 hulls: beacon channel/ident exact per table;
  Essex radiates nothing; voice callsign present on the comm card.

## [1.9.0] — 2026-07-16

### Added — carrier systems per hull + cockpit radio presets ("the boat is up, and your jet already knows it")
Requirements doc: `docs/requirements-carrier-systems-alignment.md` (approved by Rob).

- **Hull capability gating (FR-1).** Carrier systems now activate per what each
  boat actually supports in DCS (`carrier_decks.json "systems"`): SuperCarrier
  hulls + Stennis radiate TACAN/ICLS/Link4/ACLS; **Forrestal has no ACLS**;
  **Invincible is TACAN-only**; **Essex (1944) radiates nothing** — era-true
  visual recovery, noted on the comm card. The card never again advertises a
  system the boat can't provide.
- **Cockpit radio presets (FR-2), new `missiongen/presets.py`.** Player and
  every client slot get COMM1 programmed from the mission's own comm ladder:
  CH1 Flight · CH2 Mother · CH3 AWACS (or AEW) · CH4 Tanker · CH5 Angel ·
  CH6 CAP · CH7 Tactical · last channel Guard 243.000. Only assets that exist
  in the mission are programmed; unused channels keep module defaults. Radio 1
  only, deliberately — it's the primary UHF on every supported module, while
  radio 2/3 are VHF-only on some airframes. Works for carrier AND land starts.
  Modules without ME-settable radios are skipped silently.
- **CHAN column + Boat Card (FR-3).** The briefing comm card and kneeboard
  comms page gain a CHAN column matching the cockpit; the carrier row lists
  only real systems plus "F-14: RIO enters Link4 336". The YOUR FLIGHT line
  now says "COMM1 presets are loaded — Mother is CH 2."
- **Verified (FR-4):** all four hull system sets asserted in the .miz; Hornet
  COMM1 CH1-CH20 exact to plan; 4-slot client group = 4 programmed radios;
  Viper land start gets AWACS/Tanker/Guard with no Mother; COMM2 untouched.
- **Known limit (engine, documented in guide):** aircraft-side TACAN/ICLS/
  Link4 are cockpit state — no mission file can preset them. Boat Card carries
  the values instead.

## [1.8.9] — 2026-07-15

### Fixed — three placement realism bugs (SAMs in the sea, carrier near land, Angel adrift)

- **Area SAM sites no longer spawn in the ocean.** The Threat Dial belt used to
  interpolate free coordinates on the own→enemy axis; pydcs has NO land/water
  query, so on water-heavy maps (Marianas, Sinai, Kola…) sites landed in the
  sea. New rule — doctrinally better AND terrain-safe: **sites anchor to enemy
  airfields**, 4–9 km out (SAM belts defend assets, not empty map squares).
  Offset direction is a land bet in priority order: toward the nearest other
  enemy field within 90 km → toward the enemy rear → along the runway axis.
  Never toward the player (that points out to sea on carrier maps). Front-line
  fields get sites first, so the belt still sits between you and their
  heartland. Verified: worst site-to-airfield distance 8.9 km across
  Marianas/Sinai/Kola at maximum intensity.
- **Carrier no longer steams toward land.** Two bugs: (1) the Persian Gulf
  anchor sat ~15 km off Dubai with heading 090 — the 40 km steaming leg ended
  literally INLAND in the UAE. Moved to the central Gulf (25.45N 54.95E, hdg
  285), 40+ km from every coast and clear of Abu Musa/Sirri. Marianas heading
  070 aimed the leg at Guam's NW coast — now 250 into the open Philippine Sea.
  (2) Systemic: wind >2 m/s replaced the curated heading with an unconstrained
  wind BRC, steering the leg wherever the weather pointed on ANY map. BRC is
  now **clamped to ±60° of the curated open-sea axis** — wind down the deck
  when possible, sea room always. Every map's full ±60° arc was validated
  against the coastline.
- **Angel is now LINKED to the boat.** The plane-guard helo used to fly a
  dead-reckoned route parallel to the ship's leg — the moment the boat
  maneuvered they drifted apart. It now carries a DCS **Follow task on the
  carrier group** (500 m starboard, 100 m astern of the bow, 300 ft): the AI
  station-keeps in Starboard Delta through the ship's turns and speed changes
  for the whole mission. Verified: Follow task bound to the CSG group id in
  the .miz.

## [1.8.8] — 2026-07-15

### Added — global "Livery style" control (Airfields screen)
A single dropdown, not a per-aircraft picker — a deliberate UX call. Liveries are
install-specific (paid/3rd-party skins vary per machine) and a web app can't know
what any user owns, so a dropdown of exact skin names per type would offer skins
some users don't have. One coarse, robust choice degrades gracefully instead:

- **Squadron mix** (default) — real nation-correct schemes (the v1.8.7 behavior).
- **Aggressors** — adversary paint where a type has one (F-5E/F-16/F-15 Aggressor,
  etc.), falling back to squadron for types with none.
- **Clean / stock** — no override; DCS default factory skin.
- **Random** — any scheme in the pack, for a busy, varied ramp.

Applies to parked statics on **both** sides. New recipe field
`dress_livery_style` (default `"squadron"`); wired through share links + autosave.
`dressing._pick_livery(..., style)` does the filtering; the true per-type picker
stays deferred until we can populate it from a user's own harvested liveries.

## [1.8.7] — 2026-07-15

### Fixed — nation-appropriate parked-aircraft liveries (curated pack)
Parked statics shipped no `livery_id`, so DCS chose the default skin — which for
some jets is the wrong service (a USAF F-4E at Nellis drawing a USMC scheme).

- **New `missiongen/data/liveries.json`** — a curated pack keyed
  `types.<type_id>.<COUNTRY>` with a `default` fallback. Placement now steers
  every parked aircraft (both ramp-theme fill AND the Ramp Composer mix) to a
  livery for the base's own nation. Nellis F-4E/F-5E now draw USAF/Aggressor
  paint; a Huey correctly keeps US Army/USMC. An explicit theme/mix livery still
  wins; the pack only fills the gap that was previously left to DCS.
- **Wiring** — `dressing._pick_livery(type_id, country_name, rng)`; applied in
  `_place` when no explicit livery is set. Hyphen/underscore-normalized so the
  pydcs `.id` ("F-4E") matches the catalog-style key ("F_4E"). Unknown ids are
  harmless — DCS falls back to the stock default — so a stale string is safe.
- **New `scripts/dump_liveries.py`** — dependency-free harvester. Point it at a
  DCS install (auto-detects common paths, or pass install root + Saved
  Games/DCS) and it reads the real livery folder names, tags each by nation from
  its `description.lua`, and overwrites `liveries.json` with **verified** strings
  — including any paid/3rd-party liveries you own. `--merge` / `--dry-run`
  supported. This is the authoritative source; the shipped pack is best-effort
  until harvested.

*Note: the seeded strings are best-effort (pydcs bundles no livery database).
Run the harvester against your install to lock in exact, verified ids.*

## [1.8.6] — 2026-07-14

### Fixed / Changed — user-feedback pass: clarity + support-flight correctness
Three issues from a first-time user's feedback:

- **"I expected a mission, got a sandbox."** Added a prominent, unmissable **banner** at
  the top of the page: *"This builds a mission STARTER — a ready-to-fly world, not a
  scripted mission… no objectives, tasking or waypoints."* Dismissible (remembered), but
  shown to every new user. The generated **briefing** now leads with **">> YOUR FLIGHT:
  <aircraft> at <base>, <start> start"** and states plainly that there are no objectives.
- **"I couldn't find my plane."** The briefing's YOUR FLIGHT line names the actual base —
  including when the flight falls back to another field because the chosen home had no free
  parking for that type.
- **Support flights were the wrong faction / wrong tanker.** Tanker and AWACS now fly under
  a nation that actually operates the airframe (US KC-135/E-3, Russian A-50), added to the
  coalition if the lead nation doesn't fly it — so an Israel- or UK-led blue force gets a
  valid, ME-editable KC-135/E-3 instead of an airframe its country can't operate. The
  **tanker also matches the player's receiver**: boom jets (F-16/F-15/A-10) get the boom
  **KC-135**, probe jets (Hornet/Tomcat/Mirage) get a drogue tanker — fixing an F-16 being
  handed a drogue-only KC135MPRS it can't use.

Verified on Sinai (Israel-led): F-16 → KC-135 under USA, Hornet → KC135MPRS under USA,
both with the E-3 under USA. (Mission *tasking* — A/A, A/G, SEAD objective packages — is a
larger future feature; noted on the roadmap.)

---

## [1.8.5] — 2026-07-14

### Changed — the "seed" is explained and gets a re-roll button
The bare "Seed" number field confused people. Reframed it around what users actually
want — a different version — while keeping the reproducibility that share links rely on:

- Relabelled **"Variation (seed)"** with an inline **🎲 re-roll** button that drops in a
  fresh random seed, plus a one-line helper: *same seed builds the exact same mission
  (that's how share links reproduce it); change it or hit 🎲 to re-roll a different spread
  of aircraft, threats and support.*
- Guide gains a **"Variations & the seed"** explainer under the Flight screen — you never
  have to think about the number; treat 🎲 as "give me another version."

No engine change; the seed still drives reproducible generation exactly as before.

---

## [1.8.4] — 2026-07-14

### Docs — Airfields guide section broken into readable steps
The single full-length Airfields screenshot was too tall to read in print. Split the
guide's Airfields section into three sub-steps, each with its own focused, cropped
image: **Two ways to fill** (the theme/compose toggle + theme dropdown + fill),
**Compose exact aircraft** (the Ramp Composer, cropped to the coalition headers and top
categories), and **Placement mode & object types** (static-vs-AI + the object toggles).
`capture_screenshots.py` now emits `airfields_mode/compose/place.png` via bounding-box
clips (stable element ids added in the UI); `shot()` takes a per-image height cap and
the guide adds an `h3` sub-heading style.

---

## [1.8.3] — 2026-07-14

### Docs — user guide + README refreshed to current functionality
The documentation still described the old single-scroll "Step 4a/4b/4c" wizard with
stale screenshots. Rewritten to match the shipped product:

- **PDF guide** — "Finding your way" now explains section navigation (rail switches
  screens, completion checkmarks, Next/Back + Step N of M, pinned Preview + Generate).
  "Step by step" is now **"Screen by screen"** across the nine screens (Theater, Flight,
  Airfields, Threats, Support & extras, Carrier, Map & graphics, Template, Review), with
  current coverage of the Ramp Composer, Threat Dial, and the static-vs-AI performance
  guidance. Six fresh screenshots captured against the new UI (`scripts/capture_screenshots.py`
  rewritten to drive the screen navigation); stale step-*.png removed. `shot()` now caps
  image height so tall single-screen captures fit the page.
- **Comm ladder table** updated to the 25 kHz raster frequencies (251.475, 253.625,
  264.425…; Guard 243.000).
- **README** rewritten — 11 theaters / 3 eras, Ramp Composer, exact parking-heading
  facing, Threat Dial, carriers, 25 kHz comms, section-nav UI, current architecture map,
  and survey tooling.

No engine change.

---

## [1.8.2] — 2026-07-14

### Fixed — the live preview summary got buried by the redesign
After the section-nav redesign the bottom bar (with the running "Preview" summary)
spanned the full width and **collided with the rail's own Generate button**, and
Generate ended up in three places (rail, bottom bar, Review). Cleaned up:

- The bottom bar now starts after the rail (no overlap); the running summary is
  labelled **"PREVIEW"** and is clearly visible again, with Copy Share + Generate
  on the right.
- Removed the redundant **Generate / Copy-share buttons from the rail footer**
  (the bottom bar covers those) — the rail keeps just "Reset wizard".

One pinned action bar, one always-visible preview. No engine change.

---

## [1.8.1] — 2026-07-14

### Added — forward momentum + completion cues on the new screens
Section navigation needed a clear "you're done here, move on" signal. Added:

- **"Next: <screen> →" button** at the bottom of every screen (with a **Back**
  button and a **"Step N of M"** progress readout), so there's always an obvious
  way forward — not just the rail. Next hides on the final Review screen, where
  Generate takes over. The step count adjusts live (8 vs 9) as the Carrier screen
  appears/disappears.
- **Completion checkmarks** — each rail section shows a green **✓** once it has a
  valid selection (number badge until then), so you can see at a glance what's
  done and what's left.

Pure UX; no engine/recipe change. Verified Next/Back flow, dynamic step count,
checkmarks, and Review-as-terminal; no JS errors.

---

## [1.8.0] — 2026-07-14

### Changed — section-navigation redesign (the app is no longer one long scroll)
The single-page wizard had grown crowded. The left rail is now real navigation: it
**switches which single screen is shown** instead of scrolling one endless page. Only
the screen you're working on is on-screen; Generate/Share stay pinned (rail + bottom
bar), so the fast tweak-and-regenerate loop is untouched — you jump to any screen and
build anytime, no forced Next/Back.

Nine focused screens: **Theater** (era + map) · **Flight** (side, jet, home, start/
weather) · **Airfields** (populate + Ramp Composer, finally its own room) · **Threats**
(air defenses + Threat Dial) · **Support & extras** · **Carrier** (only shown when the
carrier is home) · **Map & graphics** · **Template** · **Review & generate** (one-glance
summary).

The flat 13-checkbox "building blocks" list is **dissolved** — each toggle now lives on
the screen it belongs to (air-defenses with the Threat Dial, tanker/AWACS/FARPs under
Support, carrier on Flight). Same recipe/share format and engine — this is purely the
navigation and layout. Verified: screen switching, distributed toggles, carrier
dims/enables, recipe collection, share-link restore, and generation all work; no JS
errors. Implemented from the approved prototype.

---

## [1.7.3] — 2026-07-14

### Added — Cold War Red Flag theme (Red Flag 81-x)
Red Flag existed only as a Modern ramp theme; it started in 1975, so a Cold War
version was missing. Added **"Red Flag exercise (Cold War)"** under coldwar/blue:
F-4E Phantoms, F-5E Aggressors, F-15C/F-16A, A-10s, B-52 heavies + KC-135/E-3, and
NATO visitors (Tornado IDS, Mirage F1CE) — a ~1981 Nellis surge ramp. Also flagged
F-15C and E-3A as Cold War-valid in the composer catalog (both in service by 1977),
so they show and pre-populate in the Cold War composer.

Find Red Flag in **Populate airfields → theme dropdown** (or Compose → start from
template) for either era + Blue. Verified it places in-game and pre-populates the
composer to 21 aircraft incl. the Tornado and Aggressors.

---

## [1.7.2] — 2026-07-14

### Changed — placement mode relabeled to steer users to lightweight statics
The default has always been static objects (inert, low memory), but the old labels
called static "best-effort facing" and AI-parked "exact facing" — which nudged
users toward the heavy AI mode right when measured parking headings made **static
exact** on surveyed maps. Fixed the framing:

- **Static objects (recommended)** — inert, low memory/CPU, no map contacts, exact
  facing on all surveyed maps (everything but Falklands & The Channel).
- **AI aircraft (uncontrolled)** — now clearly flagged as heavier (memory/CPU, map
  contacts, streams in), with an inline **⚠ may hurt FPS on lower-end PCs** warning
  shown when selected. Only needed for exact facing on the two unsurveyed maps.

No engine change — statics were and remain the default; this removes the UX trap
that led people to pick the memory-hungry mode. Guide copy updated to match.

---

## [1.7.1] — 2026-07-14

### Improved — Ramp Composer is pre-populated, coalition-separated, and complete
Rob's feedback on v1.7.0: Tornados missing, composer unintuitive (blank), Red/Blue
mixed together, B-1 absent in Cold War.

- **Catalog completed (89 types)** — added the Tornado (IDS/GR4), Mirage F1CE/EE
  and 2000-5, AJS-37 Viggen, Hawk, C-101, MB-339, F-16A, F-14A, Su-17M4, L-39 and
  more. Confirmed every ramp-theme aircraft now has a catalog entry (Tornado was
  the missing link). **B-1B and B-52H now available in the Cold War era.**
- **Pre-populated, not blank** — a "Ramp theme / Compose" toggle. Compose mode
  seeds the composer from the selected theme's real composition (Red Flag →
  4×F-16, 2×F-15C, 2×F-15E, Tornado, Mirage, 2×B-1, B-52, 2×KC-135, E-3, C-17…),
  so you start from a realistic ramp and adjust. The theme dropdown stays visible
  as a "start from template" picker; "Reset to theme" re-seeds.
- **Red & Blue separated** — the composer lists "Your coalition" and "Red / OPFOR
  & Aggressors" in distinct, color-coded sections. `/api/options` now exposes each
  theme's composition (`_theme_mix`) for the pre-population.

Verified: engine places Tornado + international types; Red Flag pre-populates to 20
aircraft incl. Tornado; era switch filters correctly (Cold War shows B-1, hides
modern-only jets); mode toggle drops the mix cleanly; no JS errors.

---

## [1.7.0] — 2026-07-14

### Added — Ramp Composer: pick exact aircraft & counts for your ramps
The aircraft-selection feature. Inside Populate airfields, a new **Ramp Composer**
lets you compose your side's ramps by hand instead of relying on the random theme
draw — directly addressing the gaps Rob raised (too few helos; no B-1 / C-130 /
AWACS / tanker statics; random liveries).

- **Category composer** — era-valid types grouped by role (Fighters & Attack,
  Bombers & Heavies, Tankers, AWACS & ISR, Transport, Helicopters), each with a
  count. New `data/static_catalog.json` (74 types) is the roster; `/api/options`
  exposes it. Era-filtered live (WWII offers warbirds, never a B-1).
- **Stand-aware placement** — helicopters go on pads, heavies (B-1, C-130, KC-135,
  E-3…) on large/roomy stands, fighters on airplane stands; anything beyond a
  field's capacity is skipped. Counts are **per airfield**, applied round-robin so
  a small field truncates proportionally.
- New `dress_mix` recipe field (`{type: count}`) for the player's side; enemy
  fields keep their era/map theme. When set, it overrides the theme + fill%.
  Rides share links + autosave; old links (no mix) decode to the theme path.
- Liveries currently use the default squadron skin (removes the "random livery"
  problem); a per-type livery picker is the next fast-follow.

Verified: Nellis with `{F-16:8, Apache:4, C-130:2, E-3:1, KC-135:1, B-1:2}` places
exactly that, with measured per-spot headings intact; share roundtrips; headless UI
renders the composer, era-filters types, and collects the mix with no JS errors.

---

## [1.6.10] — 2026-07-14

### Added — parking-heading data for 7 more maps (9 of 11 now surveyed)
Imported whole-map surveys for **Caucasus, Kola, Marianas, Normandy, Persian Gulf,
Sinai, and Syria** — every airplane parking spot on all their preset airfields now
carries its exact measured painted-line heading. Static aircraft face the real
per-spot direction with no AI cost across:

- Caucasus (19 fields), Kola (18), Marianas (5), Normandy (18), Persian Gulf (18),
  Sinai (22), Syria (28) — ~5,300 spots this batch.
- Verified on the big fields: Vaziani 92/92, Incirlik 126/126, Hatzerim 174/174,
  Monchegorsk 96/96 statics match their surveyed spot.

**9 of 11 maps done** (Nevada, Germany + these 7). Only Falklands and The Channel
remain. Recipe/share/API unchanged; samples regenerated.

---

## [1.6.9] — 2026-07-14

### Added — full Germany parking-heading data (26 fields, exact per-spot)
Imported the whole-Germany survey: 2,220 spots across all 26 preset airfields now
carry exact measured painted-line headings. Static aircraft across the Cold War
German fields — Bitburg, Ramstein, Spangdahlem, Laage, Finow, and the rest — face
their real per-spot direction with no AI cost. Big bases show heavy variety (Bitburg
alone: 76 distinct headings). Verified 146/146 Bitburg statics match; other maps
untouched; samples regenerated. Nevada + Germany now surveyed; 9 maps to go.

---

## [1.6.8] — 2026-07-14

### Fixed — GSE trucks land on the pad; carrier no longer hijacks the aircraft list
Two issues from Rob's in-game Nellis screenshot:

- **GSE placement** — ground trucks used a fixed 12–16 m side offset regardless of
  stand size. On a ~14 m fighter stand that threw the truck clean off the pad into
  the taxilane or onto the sunshade canopies. Offset is now scaled to the stand's
  half-width, clamped to 4–9 m, so trucks sit beside the aircraft on its own pad.
  (Nellis GSE now averages ~5.5 m from the jet, all ≤ 9 m.)
- **Aircraft dropdown showed only the AV-8B** — on coastal maps the home list put
  "⚓ The carrier" *first*, so it became the default home. That silently filtered
  the jet list to carrier-capable, and since the Cold War default hull is HMS
  Invincible (a Harrier deck), the roster collapsed to the AV-8B. Fix: land bases
  are listed first and are the default home; the carrier is opt-in and listed last.
  `eraHull()` now prefers a CATOBAR deck, so even choosing the carrier keeps the
  full air wing. Verified: coastal Cold War / modern maps now default to a land
  base and show the full 41 / 53-aircraft list.

---

## [1.6.7] — 2026-07-14

### Fixed — survey builder no longer caps at ~989 spots on big maps
pydcs gives each country only ~989 unique onboard/tail numbers, so large-map
surveys hit `pop from an empty set` and silently dropped every field past the cap
(Germany placed 988 of 2,220). The survey builder now spreads aircraft across a
15-country pool, round-robined per spot. Verified full placement: Germany
2,220/2,220, Sinai 1,546/1,546, Syria 1,044/1,044, and all reload clean.

---

## [1.6.6] — 2026-07-14

### Added — full Nevada parking-heading data (all 16 airfields, exact per-spot)
Ran the survey mission over the whole Nevada map and imported the results: every
airplane parking spot on all 16 airfields (571 spots) now has its exact measured
painted-line heading in `parking_headings.json`. Static aircraft across Nevada —
Nellis, Creech, Groom Lake, Tonopah, Tonopah Test Range, and the rest — face the
real per-spot direction with no AI cost.

- Nellis alone carries 27 distinct measured headings (the 220° main ramp plus the
  310°, 130°, 40°, 180° rows), replacing the single 219° dominant value from 1.6.1.
- The survey's Nellis dominant came out at **220°**, confirming the hand-measured
  219° to within a degree.
- Verified 247/247 Nellis statics match their surveyed spot; other maps untouched;
  samples regenerated.

---

## [1.6.5] — 2026-07-14

### Changed — survey mission is now fly-and-send (no local Python for the user)
`build_survey_mission.py` now adds a player slot (free Su-25T) so the survey
`.miz` is directly flyable in single-player, and the on-screen message points at
`Saved Games/DCS/Logs/dcs.log` (the reliable output — DCS sanitizes `io`/`lfs`
by default, so the tidy .txt only appears on desanitized installs; `env.info` to
dcs.log always works). Workflow for the user is now zero-dependency: fly the
pre-built mission, send the log; the maintainer runs the import. Verified full
Nevada survey builds (571 spots + player) at 48 KB and reloads clean.

---

## [1.6.4] — 2026-07-13

### Fixed — friendly dependency error in the survey tool
`scripts/build_survey_mission.py` now catches a missing dependency (e.g. `pyproj`,
which pydcs needs to project the map) and prints how to fix it — reuse the
launcher's `.venv` or `pip3 install <pkg>` — instead of a raw `ModuleNotFoundError`
traceback. `pyproj` was already listed in `requirements.txt`; this only improves
the message when a script is run outside the app's environment.

---

## [1.6.3] — 2026-07-13

### Added — parking-heading survey tool (auto-populate exact per-spot facing)
Two offline developer scripts that turn a map's real painted-line headings into
`parking_headings.json` entries without hand-measuring each spot:

- `scripts/build_survey_mission.py <map> [Airfield ...]` builds a throwaway
  `survey_<map>.miz` that drops one uncontrolled aircraft on every airplane
  parking spot (DCS seats each at the painted-line heading on load) and embeds a
  Lua exporter. Run it once in DCS, wait ~20 s: it writes one line per spot
  (`PSURVEY_OUT|<airport>|<slot>|<heading>`) to `dcs.log` and to
  `Saved Games/DCS/parking_survey.txt`.
- `scripts/import_survey.py <map> <log-or-txt>` parses that output and merges
  exact per-spot headings into the data pack (`{default: <dominant>, slots: {…}}`
  per field). `--dry-run` previews.

This makes exact facing scalable to whole maps in static mode — no FPS cost, no
contacts, no pop-in. The exporter Lua lives ONLY in the throwaway survey mission
(a dev tool); nothing shipped in a user mission contains a script. Verified the
full round-trip on Nellis: 233 spots surveyed, imported, and re-applied with
247/247 statics matching their measured heading.

Also: `.gitignore` now excludes release zips, scratch `.miz`, and survey logs
(removed some that earlier `git add -A` runs had committed).

---

## [1.6.2] — 2026-07-13

### Added — per-spot parking headings; heading is aircraft-static-only
The parking-heading data pack now supports **exact per-spot facing**, not just one
heading per field. A field value in `parking_headings.json` can be either a bare
number (whole-field dominant heading, as before) or an object:

    "Nellis": { "default": 219, "slots": { "F164": 41, "F163": 41 } }

Per-spot headings are keyed by the parking spot's stable pydcs name (F164, …), so
a value measured once is permanent. Priority: per-spot measured → field default →
per-slot geometric guess → runway-axis fallback.

Clarified/enforced scope: the measured heading applies to **static aircraft only**.
Ground equipment and infrastructure keep their own placement and orientation
(GSE still scatters realistically around occupied stands). Verified: with a
per-spot override, the named spots face the override and every other Nellis static
faces the 219 default; GSE headings remain varied. Recipe/share/API unchanged.

---

## [1.6.1] — 2026-07-13

### Added — measured parking-heading data pack (exact static facing, no AI cost)
New `missiongen/data/parking_headings.json`: a map → airfield → heading (°true)
table of *measured* painted-line headings. Static aircraft at a listed field now
face the measured heading instead of the geometric guess — exact facing with none
of the AI-parked costs (no FPS hit, no map contacts, no pop-in). This is the
"data pack" path that resolves the long-standing static-vs-AI tradeoff for any
field we have a real heading for.

- First entry: **Nevada · Nellis = 219°** (Rob's measured majority-apron heading).
  Verified: all 148 Nellis statics face 216–222°; every other Nevada field keeps
  its geometric guess (nothing regresses).
- Fields not in the table are unchanged, so this is purely additive.
- Extending it is one line: park an aircraft on a ramp slot in the Mission Editor,
  read the heading, add `"<Airfield>": <heading>` under the map. A single number
  is the dominant apron heading; the odd row facing another way is accepted.
  (Per-apron precision can layer on later without changing the mechanism.)

Recipe/share/API formats unchanged.

---

## [1.6.0] — 2026-07-13

### Added — Threat Dial: control how many threats and what level
New wizard panel (Step 4d) with two knobs, both era-gated and seeded so a
recipe+seed always regenerates the same picture:

- **Intensity (1–5: Minimal → Maximum)** — on top of the SAM defending each
  enemy airfield, spawns a *randomized* count of extra area SAM sites (a belt
  between the lines) and airborne enemy **CAP** flights. The count is rolled off
  the seed, so re-rolls at the same setting differ. Engagement skill scales with
  intensity (Good → Excellent).
- **System level (`threat_tier`)** — `auto` (era's historical mix, keeps default
  missions in character) · `light` (SA-2/SA-3, MiG-21/23) · `heavy`
  (SA-10/SA-11, Su-27/MiG-31) · `mixed` (rolled per site/flight). Fully
  era-gated: a WWII "heavy" push still tops out at period fighters, a Cold War
  one at the MiG-23 — no anachronisms.

New **SA-10 Grumble (S-300PS)** kit (Big Bird SR + Clam Shell + Flap Lid TR +
54K6 CP + six 5P85 TELs, 75 km WEZ) backs the modern heavy tier. Enemy CAP spawns
airborne (inflight patrol) so there's no parking/pop-in interaction and it engages
inbound air within ~55 km. Area SAMs and CAP feed the F10 threat-ring layer.

Recipe gains `threat_intensity` (default 3) and `threat_tier` (default `auto`);
both ride share links and autosave. Old share links (no threat fields) decode to
the defaults — non-breaking. Verified end-to-end through the API and UI, samples
regenerated, `.miz` reloads clean.

*Roadmap note: this shipped as the next MINOR (1.6.0); the aircraft picker moves
to 1.7.0. The scripted live-behavior features (fox-calls, stats/leaderboard, auto
bandit picture) are aggregated into a future MAJOR — they need an embedded-Lua
runtime the product doesn't have yet.*

---

## [1.5.4] — 2026-07-13

### Changed — comm plan now sits on the real 25 kHz channel raster
The standard comm ladder used round whole-MHz values (251.0, 254.0, 305.0…),
which read like placeholders rather than assigned frequencies. All agency
frequencies now sit on the real-world **25 kHz raster** (multiples of 0.025 MHz),
so a card looks like a SPINS ladder pulled from an ATO:

- Flight 305.725, Tactical 254.325, AWACS 251.475, Tanker 253.625/39Y,
  Mother 264.425/71X, CAP 258.175, AEW 259.925, Angel (rescue) 262.050,
  FARP base 127.525.
- **Guard stays fixed at 243.000** — the international UHF emergency channel is
  set by regulation and must not move.
- The fallback allocator (extras beyond the ladder) and the FARP allocator now
  step on the raster too, so any auto-assigned frequency is a legal channel.

New `snap()` helper rounds any frequency onto the raster; ladder values are
snapped defensively on read. Comms card / kneeboard now print 3 decimals
(251.475 instead of a rounded 251.48) and the callsign column was widened one
space to keep long callsigns off the frequency. Verified in-`.miz`: emitted
radio frequencies are exact on-raster Hz (e.g. 251475000, 253625000) with no
float drift, and no player waypoints or other behavior changed.

---

## [1.5.3] — 2026-07-13

### Fixed / Changed — parked aircraft default back to STATIC (fixes spawn-in "pop-in"); AI facing is now an opt-in mode
v1.5.2 placed every parked aircraft as an uncontrolled AI unit to get exact
facing. That fixed orientation but introduced worse problems: the aircraft
**stream in over the first seconds** ("only the player jet shows, then the
rest load"), cost real FPS, and appear as map/radar contacts.

Root reality (no free lunch): the painted parking line on the ramp *is* the
slot's true heading, which lives in the DCS terrain binary and is applied
only when DCS itself parks an aircraft — it is **not exposed** to static
placement. So exact line-alignment is only possible via AI-parked aircraft,
which carry those costs; static clutter loads instantly but can only
approximate facing.

This is now a **user choice** in Populate Airfields — *Parked-aircraft
placement*:
- **Static (default)** — instant load, light, inert, no radar contacts, no
  pop-in. Facing is a best-effort per-slot guess (rows via geometry, nose
  toward the runway).
- **AI-parked** — uncontrolled flights at real slots; DCS aligns each
  aircraft **exactly to the painted parking line** and never clips a
  building, but they cost FPS, show as contacts, and stream in.

Auto/density caps are per mode (static 10/18/28, AI 5/8/14 per field);
explicit fill % still overrides. Recipe `dress_aircraft_mode` rides share
links + autosave. Default static resolves Rob's pop-in immediately; AI mode
is one dropdown away for exact facing.

---

## [1.5.2] — 2026-07-13

### Fixed — parked aircraft now placed by DCS (correct orientation, never on buildings)
Two in-game bugs (Rob's screenshots): some parked aircraft faced the wrong
way, and some sat on top of buildings. **Root cause**: parked aircraft were
STATIC objects placed at a raw position + a guessed heading. DCS stores each
parking slot's real facing inside its terrain binary and applies it only when
it spawns an *aircraft* there — that heading is not exposed to static
placement (pydcs `ParkingSlot` has no heading field), so a static must guess
(v1.5.0/1.5.1 geometric inference — right for some aprons, wrong for others),
and a static at a raw XY can also land on a building's collision mesh.

**Fix**: parked aircraft are now placed as **uncontrolled flights at the
terrain's real parking slots** — the same mechanism DCS uses for the AI
flights that already spawn correctly. DCS owns position *and* heading, so
every aircraft is nose-out, ready to taxi, seated on a designer-validated
slot, and can never point the wrong way or clip a building. Uncontrolled =
it spawns parked, engines off, and never moves (no route, no waypoints).
Ground equipment and infrastructure stay static.

### Changed
- Parked aircraft are real (uncontrolled) aircraft now, so they cost more FPS
  than static shapes. The **auto/density default is capped per field**
  (sparse 5 / normal 8 / busy 14) so a "just generate it" mission stays
  performant; an **explicit fill % still overrides the cap** (you own that
  tradeoff — the slider label and guide say so). Verified: auto Germany 200→
  ~160, Caucasus ~60, Nevada ~34; explicit 75% at Nellis still fills to the
  user's number.

---

## [1.5.1] — 2026-07-13

### Fixed
- **Static aircraft now face the right way at every spot.** v1.5.0 aligned
  all statics to ONE heading per field (runway axis + 90°) — correct for the
  main ramp, wrong for every apron that faces another way, which is why some
  aircraft looked right and others didn't. Orientation is now derived
  **per slot** from the field's own geometry (`slot_headings`):
  each aircraft finds its parking ROW (neighboring stands within 90 m,
  principal-axis fit), parks perpendicular to it, and of the two
  perpendicular choices the nose points **toward the runway — parked ready
  to taxi for takeoff**. Isolated pads (revetments, dispersals, shelters)
  face the runway directly. Jitter tightened to ±3°.
- Audited visually across Nellis, Groom Lake, and Ramstein: every apron
  orients as its own row block (Nellis resolves ~10 distinct apron
  orientations where there was one), rows are internally consistent, noses
  point at the movement area. Geometric inference — worth one in-game look
  at unusual shelter complexes.

---

## [1.5.0] — 2026-07-13

### Added — Visual Fidelity (roadmap "v1.6", pulled forward)
- **Aligned parking rows**: parked statics no longer scatter at random
  headings — every aircraft parks on the ramp alignment (perpendicular to
  the runway axis, nose-out) with a realistic ±6° jitter. Verified: 123
  statics at Nellis span exactly 12° of heading. Ramps now photograph like
  ramps.
- **Livery machinery**: ramp-theme entries can carry livery lists
  (`[ref, weight, [liveries]]`); picked liveries apply to the placed static.
  Unknown livery ids fall back to the default skin in DCS, so curated
  livery data can be added safely after in-game verification (aggressor
  schemes at Nellis, squadron tails per theme).
- **Real helipad FARPs on Cold War Germany**: the map ships 100+ surveyed
  'H FRG/H GDR' helipad sites as terrain airports — FARPs now use the real
  pads nearest the frontline (side-correct: FRG pads for blue, GDR for red)
  with the full support ring and comms, instead of synthetic pads dropped
  in a field. Maps without helipad sites keep the synthetic FARPs.

### Deferred (honest scope)
- Measured deck data for non-SC hulls (Forrestal/Invincible/Essex) stays in
  the patch train — it needs community template extraction or in-game
  measurement, not guesses.

---

## [1.4.0] — 2026-07-13

### Added — Per-base population overrides
The "Per-base overrides" expander inside Populate Airfields (per the UX
plan: progressive disclosure, not a wall of sliders):

- One row per base on the map — your side and the enemy's — each with a
  MIL/CIV badge, an enable checkbox, and a fill slider that defaults to
  **inherit** (the global fill).
- **0% empties any base**; an override on a CIVILIAN base deliberately
  populates it (the "populate anyway" escape hatch — F-16s at McCarran if
  that's your scenario).
- New recipe field `dress_overrides` ({airbase: 0–100}) — rides share links
  and the autosave. Verified: Nellis@90 → 221 statics, Creech@0 → empty,
  McCarran@30 force-populated, unset fields inherit; survives page reload.

---

## [1.3.2] — 2026-07-13

### Fixed
- **Only military installations are populated.** Civilian airports (McCarran,
  Henderson Executive, Dubai Intl, Murmansk International, the NTTR range-side
  town strips...) no longer receive military ramp dressing — no fighter rows
  on an airline apron. Classification is per map/era in maps.json
  (`civilian_airbases`) because it is era-dependent: Tinian 1944 is a B-29
  base, Tinian today is a civil field; WWII presets have no civilian fields.
  Civilian airports remain fully usable as home plate and for ambient
  traffic, and are marked "— civilian" in the Home selector. Verified on the
  NTTR: Nellis 148 / Creech 31 / Groom Lake 31 / Tonopah Test Range 41
  static aircraft; McCarran, Henderson, Tonopah town, Beatty, Lincoln
  County, Mesquite all zero.
- Per-base fill overrides (one row per base, MIL/CIV badge, inherit-global
  default) are planned for v1.4.0 — see the roadmap.

---

## [1.3.1] — 2026-07-13

### Fixed
- **The fill slider now means what it says.** 75% fill was producing ~10%
  at large fields: a hidden FPS guard capped every field at 24 static
  aircraft regardless of the slider (Nellis has 247 stands — 75% was
  clamped from ~185 to 24). An explicit user percentage now WINS with no
  cap (verified at Nellis: 75% → 184 aircraft, 25% → 25%, 100% → 100%);
  the 24-aircraft guard still applies only to the automatic/density default.
  Also, the percentage is now computed over FILLABLE stands only — helipads
  that can't take an aircraft in the era no longer dilute the math. UI and
  guide text updated (with an honest FPS note for big fields at high fill).

---

## [1.3.0] — 2026-07-12

### Added — Wizard navigation (UX Phase 1: the hybrid rail)
Per the approved design (hybrid over strict tabs, to protect the re-roll
loop — see docs/ROADMAP.md and the UX plan):

- **Progress rail** (left, sticky): every step with a live value summary
  (Era ✓ Cold War · Map ✓ Germany · Populate ✓ NATO allied wing · 80% ·
  Map graphics 8/9 layers…). Click scrolls to and expands the section;
  steps go green as they carry real choices; irrelevant steps (carrier on
  a landlocked map) hide.
- **Collapsible sections**: header click folds a section to its title —
  collapse is CSS-only, inputs stay mounted.
- **Generate + share link pinned in the rail** — always reachable, plus a
  "Reset wizard" that clears saved state.

### State architecture (why nothing is lost between steps)
1. Single source of truth: the DOM inputs themselves — sections are never
   unmounted, so navigation cannot destroy state by construction.
2. One serializer pair: `recipe()` / `applyRecipe()` powers share links,
   autosave, and restore — persistence and sharing can never drift apart.
3. **Autosave**: every change writes the full recipe to localStorage; a
   refresh or crash restores exactly where you were. Share-link URLs (?r=)
   take precedence over the autosave.

Verified in-browser (Playwright): collapse keeps values; full reload
restores era/map/seed/theme/fill/layer selections; reset returns to
defaults; zero console errors. Narrow screens (<900 px) fall back to the
classic single column with the bottom bar.

---

## [1.2.0] — 2026-07-12

### Added — Mission graphics: F10 map drawing layers (roadmap "v1.6" pulled forward)
The map briefs the mission. New wizard section 4c "Map graphics (F10)" — a
layer picker where each drawn zone is added individually:

- **Tanker track** — racetrack + TEXACO freq/TACAN/altitude label
- **AWACS orbit** — OVERLORD station behind friendly lines
- **Carrier CAP station** and **Hawkeye AEW orbit** — air-wing racetracks
- **Carrier ops box** — CSG operating area + BRC arrow
- **Target & range rings** — amber ring + name over strike packages and the
  practice range
- **FARP rings** — service radius + name
- **Bullseye** — shared reference marker
- **Threat rings (intel)** — known enemy area-SAM engagement rings with
  doctrinal WEZ radii (SA-2 40 km · SA-3 22 · SA-6 24 · SA-11 35 ·
  Hawk 40 · Patriot 90), drawn on YOUR side's layer only

Design rules: coalition-private picture on the Blue/Red drawing layers (DCS
renders them per side — multiplayer-safe by construction), shared references
on Common; one visual language (blue friendly orbits, red threat rings, amber
targets, green FARPs); zones inform, they never route — no player waypoints,
ever. Every zone draws from geometry the engine already computes. Recipe
carries the layer set (`map_layers`; null = auto), so share links reproduce
the exact map picture. Nav points remain the Common-layer companion (existing
block, same checklist family).

---

## [1.1.2] — 2026-07-12

### Changed
- License and attribution updated for **Authentic Media LLC**: strengthened
  no-liability disclaimer covering software defects, generated mission files,
  and third-party modified/tampered/redistributed copies (official source
  only); no support or updates promised. Footer, guide cover, and README
  now state "no warranty and no liability."

---

## [1.1.1] — 2026-07-12

### Added
- **Roadmap ships with the product**: `docs/ROADMAP.md` served at `/api/roadmap`,
  linked from the app header and footer — the release plan is a published manifest.
- **Attribution & license**: Developed by Authentic Media; MIT LICENSE added —
  the tool is free and provided **as-is with no warranty of any kind**. Stated in
  the app footer, the PDF guide cover, the README, and the LICENSE file.
  Not affiliated with Eagle Dynamics or Heatblur.

---

## [1.1.0] — 2026-07-12

### Added — "Populate airfields" control panel (new wizard section 4a)
Airfield dressing is no longer a random grab-bag. Users now control exactly
how their fields are populated:

- **Fill slider (0–100%)** — how much of each field's parking to fill,
  replacing the coarse sparse/normal/busy for statics (density still scales
  air defenses and ambient traffic). Capped at 24 aircraft/field for FPS.
- **Object-type toggles** — parked aircraft, ground equipment, and
  infrastructure can each be switched off independently.
- **Ramp themes** — WHO parks on your fields, with weighted realistic mixes
  (`ramp_themes.json`), strictly era-gated:
  - Modern blue: **US Air Force** (Vipers/Eagles/Hogs/heavies, no Navy
    paint), **Red Flag exercise** (Nellis surge ramp: B-1/B-52 heavies,
    aggressor Vipers, Navy and allied visitors — Hornets, Mirages,
    Tornados), **Navy/Marine Corps**, **Joint expeditionary**.
  - Modern red: **VKS frontal**, **Long-Range Aviation** (Backfire/Bear base).
  - Cold War: **USAFE**, **NATO allied wing**, **US Navy** vs **VVS
    frontal**, **PVO interceptors**.
  - WWII: **RAF**, **USAAF** vs **Luftwaffe**.
- **Map-aware defaults** — Nellis is an Air Force base: the NTTR now
  defaults to the USAF theme (no more random F/A-18s), Andersen/Marianas to
  USAF, Cold War Germany to USAFE, Normandy to USAAF. "Auto" always picks
  the right ramp for the map; enemy fields dress with their own era default.
- Heavy airframes (B-1B, B-52, KC-135, C-17) now park on physically roomy
  stands even on terrains whose data flags no stand as "large" (NTTR).
- Share links carry the full population config; the wwii anachronism guard
  extends to every theme; invalid theme keys warn and fall back safely.

---

## [1.0.1] — 2026-07-12

### Fixed
- **Statics no longer appear on runways or taxi routes.** Free-placed objects
  could land on the movement area: the airfield infrastructure cluster was
  pushed 350 m from the ramp centroid at a *random* bearing (the ramp sits
  beside the runway, so this regularly dropped fuel tanks and tents
  mid-runway), GSE trucks could drift off the stand into taxilanes, and
  SHORAD point defense was placed 900–1400 m from the field reference point
  at a random bearing — often on the runway itself. New `placement.py`
  models every runway as a keep-out corridor (built from pydcs runway
  headings through the field reference point, with generous width to absorb
  shoulders, parallel taxiways, and magnetic-variation error) and all
  free-placed objects are validated against it:
  - Infrastructure cluster now anchors on the ramp side *away* from the
    runway axis and its row runs *parallel* to the runway — geometrically
    unable to cross it — with per-object validation as backstop.
  - GSE stays within the parking stand's own footprint (12–16 m off the
    aircraft; stands are 40–80 m wide) — apron, never taxilane.
  - SHORAD and SAM sites sample bearings until clear (SAMs demand 550 m
    margin so no launcher of the kit crosses the corridor).
  - Aircraft statics were always safe: they only occupy surveyed parking
    stands from the terrain data.
  - Verified: 30 generated missions across 10 maps / 3 eras / 3 seeds —
    12,256 free-placed objects, zero inside a runway corridor.
- **Period dressing is now a hard invariant.** Dressing data was already
  era-keyed (WWII fields only draw warbirds, Bedfords, Kübelwagens), but the
  health check now carries an anachronism guard: any future data edit that
  puts a jet, helicopter, or modern vehicle into the WWII era block fails
  `/api/health` loudly. No F/A-18 on a 1944 field, guaranteed.

---

## [1.0.0] — 2026-07-12

First locked release. Everything below is the 1.0 baseline.

### Theaters (11, era-gated)
Caucasus, Syria, Sinai, Persian Gulf, Nevada NTTR, Normandy 2, The Channel,
Marianas (all three eras), Cold War Germany, Kola, South Atlantic. Every preset
carries both sides' major airfields, validated against pydcs terrain data.
Historian-checked scenarios: October 1973 Sinai (IAF from Refidim vs the canal
SAM belt), 1982 Falklands OOB (San Julián/Puerto Santa Cruz), Fulda Gap,
NATO Northern Flank with Cold War Finland/Sweden neutral, 1944 Marianas.

### Mission engine
Era hard-gating (service windows × era windows, UI + server), airfield dressing
with period statics, doctrinal SAM layouts, tanker/AWACS per era, ambient
traffic, FARPs, target areas + range, NTTR nav points on the F10 map,
3-page PIL kneeboards, standard comm ladder (Guard 243 · Mother 264/71X/ICLS 11/
Link4 336 · Angel 262 · full list in the guide), share links that regenerate the
mission from a recipe code, seeded determinism. No player waypoints, ever.

### Carrier strike groups
Real CSG compositions and ship names (CSG-9 TR, CSG-3, CSG-5, CSG-8, Forrestal
CarGru 6, Invincible TF 317, Essex TF 58.1), doctrinal screen stations,
editor-measured Supercarrier deck formations (recovery/launch/underway/packed)
with a hard min-separation validator, deck crew + yellow gear, real air-wing
squadrons for CAP/AEW launch options, plane-guard SH-60 in Starboard Delta
during flight ops, carrier-as-home-base flow with deck-class aircraft
filtering, all boat systems active (TACAN/ICLS/Link4/ACLS).

### Crew Ops (F-14 only)
`rio_fleet_defense` — works today on the F-14A/B: solo (air start or carrier
warm start) or MP crew, GCI Picture menu, player-paced triggers.
`backseat_izlid` (Pilot + Jester) and `backseat_intercept` (RIO + Iceman) —
built on the F-14B(U) PROXY flag API, pending-module warned until Heatblur
ships. The F-4E has no crew AI (the WSO flies the jet) — by design, not omission.

### Product
Era-first wizard, one-click Mac launcher, vendored pydcs, illustrated PDF user
guide with a screenshot pipeline, 21-mission sample suite, Dockerfile + fly.toml.

### Pre-1.0 development history
Internal build numbers v1–v17 (see `claude/build-status.md` in the project for
the archaeology): core engine → carrier realism arc (real CSGs, measured decks,
stacking fix) → Crew Ops (F-14 correction) → map buildout → plane guard →
Sinai/Groom Lake/major-airfield pass.
