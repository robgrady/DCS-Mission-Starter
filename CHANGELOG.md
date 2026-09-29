# Changelog — DCS Sortie Starter

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

> **Entries 1.104.0 – 1.105.0 were reconstructed on 2026-09-29.** The originals
> were written in a build environment that was reclaimed before the release
> tree reached git; the running Fly.io image kept the code but not this file.
> Each entry below was rebuilt from the code's own dated comments
> (`formation_hud.py`, `checkride.py`, `server/app.py`, `docs/AGENT_HANDBOOK.md`)
> and the session record. Where the code is silent the entry is short rather
> than invented.

## [1.105.0] — Packs, four kinds

### Added
- **Pack format 3** — `docs/PACK_FORMAT.md`. A pack declares a `kind`:
  `missions` (format 2, unchanged), `course`, `reference` or `theater`, each
  with a documented layout. Format 3 is the required minimum for any kind
  other than `missions`, so a format-2 reader refuses a format-3 pack rather
  than half-loading it. `theater` packs are **gated**: owner-installed only,
  schema-validated, and stamped with the recipe that produced them.
- **`/api/packformat`** — the pack format published as an in-app page with a
  shareable link, built from the Markdown by `scripts/build_packformat_html.py`.
  Squadron authors get the spec without a repo.
- `docs/PACK_AUTHORING_PROMPT.md` — the standard course-pack template.

### Removed
- **What's new.** The page, its builder, `docs/RELEASE_NOTES.md` and every
  guard that kept them fresh. This changelog is the one record. `/api/whatsnew`
  answers **410** with a pointer here, not 404 — it was in the footer for
  eighty releases and "this is gone" is more useful than "this never existed".
  The admin sidebar slot it held now opens the pack format page.

## [1.104.2] — Airplane

### Changed
- **American English throughout** — copy, code identifiers, kneeboards, PDFs,
  the guide. `aeroplane` → `airplane`, `colour` → `color`, `programme` →
  `program`, `manoeuvre` → `maneuver`, `defence` → `defense` and the rest,
  applied with word-boundary rules so `programmed` stays `programmed` and
  `analysis` stays `analysis`. Every URL was diffed against the previous
  release and is byte-identical; only link *text* changed.
- The `.sspack` packs were regenerated so their cards match.

## [1.104.1] — The ladder that would not draw

### Fixed
- **Formation position ladder never appeared in the cockpit** (1.104.0). The
  text half of the same trigger set arrived; the picture did not. Every other
  difference from the proven `aar_hud` surface was ruled out one at a time —
  build, packaging, resource map, group targeting, art format, condition
  logic — leaving two: `vertAlignment` Bottom vs Center and size 9 vs 10.
  Now Left / Center / 10 %, the one placement this product has ever had
  confirmed rendering. Placement is copied from `aar_hud`, not reasoned about.
- **F10 "Formation ladder: show it now"** — draws the current card on demand,
  so "is this rendering at all?" costs five seconds on the ramp instead of a
  sortie. Doubles as recall after another message clears the card.
- With the ladder fitted, the two continuous drift calls it replaced are gone.

## [1.104.0] — Read it, then fly it

### Changed
- **Formation training coaches by position, not by stream.** The old coaching
  was a continuous run of messages that scrolled off faster than anyone could
  read — Rob: *"a continuous display of information that happens quickly that
  is too difficult to watch and navigate."* Replaced with a **position ladder**:
  one card, one step at a time, edge-triggered so it never strobes. A patient
  lead holds each rung until the wingman is in it.
- **Checkride debrief is one card, not twelve messages.** Grade letters and
  critical items render as drawn cards (`missiongen/data/checkride/`) that stay
  on screen, instead of stacked `MessageToGroup` calls that shoved one another
  off.
- Cold War Germany missions with the F-4 now build on the Germany map's
  corridor set rather than the generic one.

### Internal
- Trigger sets are built into a local list and attached all at once; a
  half-attached set made the `.miz` unsaveable on a pydcs API drift.
- Flag-block registry documented in `docs/AGENT_HANDBOOK.md`; the ladder
  nearly shipped on timing_coach's block.

## [1.103.0] — The Central Region corridors

Rob: "Let's do the Germany map like the previous two."

### Added
- `missiongen/data/corridors/germany.json` (generated by
  `scripts/gen_germany_corridors.py`): 111 fixes, 51 corridors, 10
  clusters (7 NATO / 3 Warsaw Pact), 10 sectors (5 GDR / 5 FRG), 45 plans
  through 6 shared gates, 32 areas (the ADIZ, HAWK and Nike bands offset
  from a schematic border; the three Berlin corridors as strips; the LFAs
  and ED-Rs with printed vertices; the Soviet ranges as boxes on printed
  points), the 27-town GDR flight-restriction line, coast / border / Elbe
  / ATAF seam, autobahns, 8 terminal panels; page 2400x1250 in a 4x2 grid.
- `corridors.py`: a data file's `eras` — the structure belongs to one era
  (`plan_route()` returns None for the rest). `corridor_chart.py`:
  `panels[].clusters` (one panel for several clusters), `lines[].label_at`
  (a line label only on the panel holding its anchor, and never on a
  terminal panel without `area_labels`), unlabelled sub-areas.
- `tests/test_corridors_germany.py` (44 tests); `scripts/mutate_nttr.sh`
  runs three suites and 58 mutations (58/58). `docs/img/germany_corridors.*`;
  `GET /api/corridors/germany/chart.png|svg`; the *Automatic waypoints*
  hint links all three charts. SOURCES.md §3: the Central Region entry.
- `Recipe.corridors` (default True): thread the route through the map's
  corridors where it has them. The five timing rides (Fassberg, Cold War
  Germany) set it False in `mission_templates.json` - the card they teach
  has four points on it, and the rides stay under 25 minutes.

## [1.102.0] — The Levant corridors

Rob: "let's refer to this map detail as the authentic standard map detail.
Let's now do the research and create it for the Syria map."

### Added
- `missiongen/corridors.py` — the map-agnostic router (`plan_route(home_pos,
  target_pos, era, rng, terrain, map_key, home_name)`), reading
  `data/corridors/<map>.json`: `clusters` (a home's field family;
  `cluster_for_home`), `sectors` (rules + `labels`; `sector_label`),
  `plans[cluster][sector][mode]` with `low`/`any` fallback, `text` for every
  map-specific phrase (`brief_title`, `brief_intro`, `md_line`,
  `gate_in_label`/`gate_out_label`, `known_issues`). `md_line(plan)` replaces
  the Nevada-only sentence in `brief.py`; `stats["nttr"]["md_line"]`.
- `missiongen/corridor_chart.py` — the map-agnostic chart. New: `page_size(mk)`
  (`chart.page`), `_layout` as a grid (`chart.panel_cols`,
  `panel_col_frac`; overview height follows the bounds' aspect), `_sea()`
  (sea fill inside the bounds, `chart.land` polygons back on top), panel
  `declutter` (the overview hides non-gate fixes a panel draws), `minor`
  places, per-panel and overview label overrides (`labels: {id: {seg, off,
  nudge, hide}}`).
- `missiongen/data/corridors/syria.json` (generated by
  `scripts/gen_syria_corridors.py`): 89 fixes, 26 corridors, 6 sectors,
  4 clusters (israel / cyprus / turkey / jordan), 16 areas, coast, borders,
  the Euphrates line, 4 terminal panels, page 1800x1040 in a 2x2 grid.
- `scripts/build_corridor_charts.py` renders every map's chart
  (`docs/img/nttr_corridors.*`, `docs/img/syria_corridors.*`);
  `GET /api/corridors/{map}/chart.png|svg` (`/api/nttr/chart.*` kept).
- `tests/test_corridors_syria.py` (38 tests); `scripts/mutate_nttr.sh` now
  runs both suites and 48 mutations (48/48).
- SOURCES.md §3: the Levant entry (AIP Israel, CARC, DHMİ, UK Mil AIP LCRA,
  Syria GACA eAIP, Lebanon DGCA via IVAO, the press record of the IAF roads,
  Northern Watch, Al-Tanf and the Euphrates line).

### Changed
- `data/nttr_corridors.json` → `data/corridors/nevada.json` (adds `clusters`,
  `sectors.labels`, `text`, `chart.panels`). `nttr.py` / `nttr_chart.py`
  are shims onto the generic modules. Builder, kneeboard, brief and the
  server take the map from the recipe. The *Automatic waypoints* hint links
  both charts.

## [1.101.0] — Two panels, vector

Rob: "the corridors overlap each other and is difficult to see. They're
also pixelated."

### Changed
- `nttr_chart.py` rebuilt around a display list (`Canvas`: polygon / line /
  circle / text) with two backends — `Canvas.svg()` and `Canvas.pil(ss=3)`
  (3x supersample, LANCZOS down). Two panels: `overview()` (transits as
  lanes, departures/recoveries as dotted centrelines, the terminal footprint
  boxed) and `terminal()` (`TERMINAL_BOUNDS` 36.08–36.95N / 115.95–114.62W,
  `TERMINAL_IDS` as lanes). Role colours (`ROLE_COL`: transit blue,
  departure green, recovery amber), the flown plan red (`HOT`), the rest
  ghosted. Shared legs drawn once (`_draw_lanes` keeps a drawn-set).
  Sutherland–Hodgman clip of areas to the panel. `render_svg()`,
  `render_terminal()`, `render_page()` (overview left, terminal + legend
  right; the roads list dropped from the page). Data: `label_seg` /
  `label_off` retuned for DREAM and MINTT; R-4806E label moved.
- Kneeboard and brief chart pages carry both panels (overview over
  terminal) and fit above the footer.
- `GET /api/nttr/chart.svg`; `scripts/build_nttr_chart.py` also writes
  `docs/img/nttr_corridors.svg` (artifact `covers` both); the site link
  points at the SVG.
- Tests: SVG determinism, terminal render, an anti-aliasing check (colour
  count), the SVG endpoint, the docs SVG byte-identical. `mutate_nttr.sh`
  29/29 (new: render aliased at 1x).

## [1.100.0] — The NTTR corridor chart

Rob: "as an expert military map maker and user can you add visual
representations based on real world corridors."

### Added
- **`missiongen/nttr_chart.py`** — `render_panel(w, h, plan, bounds, scale)`
  (equirectangular projection, nm-true at mid-latitude; graticule; MOAs
  under, restricted on top with an inward sectional hatch, the Box
  cross-hatched; corridor lanes with block labels placed from the data's
  `label_seg` / `label_off`; direction arrows on departures/recoveries;
  gate rings; fix triangles; peaks; roads; places; the plan's own road in
  amber with WP1 / IP / TARGET / EXIT; scale bar; north arrow),
  `legend_lines(plan)`, `render_page(w, h, plan)` (band, banner, panel,
  legend column, the roads list, sources).
- `data/nttr_corridors.json` `chart`: `bounds`; `areas` — R-4807A (27
  vertices) and R-4808N (14) transcribed from 60 FR 20635; R-4806E/W,
  R-4808S, R-4807B, R-4809 (fitted to the R-4807A notch = Tonopah Test
  Range), Desert MOA, Reveille MOA, A-481 as curated outlines flagged
  `approx:true` with sources and `label_at`; `roads` (I-15, US-93, US-95,
  SR-375); `places`. Corridors gain `label_seg` / `label_off`.
- Kneeboard `page_nttr_chart(plan)` (7th page on a corridor plan; builder
  passes `nttr_plan` in `kb_ctx`); brief `page_nttr_chart` (page 4 when the
  plan flew the corridors).
- `GET /api/nttr/chart.png` (serves `docs/img/nttr_corridors.png`, renders
  on the fly if absent); `scripts/build_nttr_chart.py` registered in
  `scripts/artifacts.py` and `release.sh`; the `bb_route` hint links to it.
- Tests (`test_nttr.py` 37): legal polygon vertex counts and the curated
  flags, deterministic render, the amber lane only with a plan, the
  kneeboard page, the endpoint, the docs image byte-identical to the
  renderer. `mutate_nttr.sh` 28/28.

### Fixed
- `brief.build_brief` centred the page locator on the page, over the tail;
  it is now centred in the gap between the form number and the tail.

## [1.99.1] — Locked time, unlocked speed

Rob's screenshot: "Mission cannot be saved due to errors! Package: All
waypoints (2-2) have locked speed and surrounded by waypoints 1 and 2 with
locked time!"

### Fixed
- `timing.apply_to_group(locked=True)` now sets `speed_locked = False` on
  every point it time-locks. pydcs's `MovingPoint` defaults `speed_locked`
  to True and `add_waypoint` leaves it; the package's locked ETAs on top of
  that produced a route the Mission Editor validates as unsaveable. The
  player's points (ETA unlocked) keep their speed lock. Tests in
  `test_timing.py` (package: `speed_locked is False`; player: stays True);
  `mutate_timing.sh` gains the mutation (36/36).

## [1.99.0] — NTTR corridors

Rob: "For NTTR there is the Sally corridor and other ways that flights make
their way to the training. I want you to investigate the corridors and
include them in the starter. Any mission that includes waypoints should go
through the corridors and not just a couple waypoints."

### Added
- **`missiongen/nttr.py`** — `plan_route(home, target, era, rng, terrain, map)`
  returns corridor legs or None; `sector_for(lat, lon)` (north / farwest /
  west / east / local, rules in the data, `local_nm` 22); `mode_for(era)`
  (`high` when `routing.ERA_PROFILE` transit ≥ FL190); `summary`,
  `approx_fixes`, `brief_lines`, `known_issue_lines`, `draw(m, plan)`.
  Legs keep the WP1 / IP / TARGET names; corridor points carry the fix's
  `short` name; a repeated fix is numbered (`MERCURY2`) so
  `timing.apply_to_group` lands ETAs on the right points; `cap_ft` /
  `floor_ft` on a fix beat the corridor block (FLEX ≤ 4,000, STRYK ≥ 9,500).
  From a non-Nellis field the departures are dropped and the recovery is the
  exit gate; nothing to join → generic route.
- **`data/nttr_corridors.json`** — 32 fixes (opennav positions for FYTTR,
  STRYK, JAYSN, INS, LSV, LAS, MMM, BLD; derived FLEX = LSV 338/4; curated
  `approx:true` where the published figure is a chart), 14 corridors
  (flex, dream, sally, alamo, fyttr, westroad, northrange, mormon, stryk,
  jaysn, mintt, arcoe, alamo_rec, acton) with blocks, widths, notes and
  sources, 6 gates, the sector rules and the per-sector low/high plans.
- Tests `tests/test_nttr.py` (33): data whole, sector picker, plan shape,
  restrictions, Alamo block, the west road round R-4808N (segments sampled;
  and the proof the direct line crosses it), a built mission's waypoints /
  ETAs / brief / F10 lanes / kneeboard pages / PDF, the fallbacks.
  `scripts/mutate_nttr.sh` 23/23.

### Changed
- `builder.py` — the route block asks `nttr.plan_route()` first on Nevada;
  `stats["nttr"]` (sector, mode, corridors, gates, summary, brief, approx);
  corridor block in the in-game briefing; `nttr.known_issue_lines` on the
  known-issues page; `nttr.draw` on the F10 Common layer.
- `routing.leg_card` rows carry `fix` and `corridor`.
- `brief.py` — "## NTTR corridors" section in the PDF/MD brief.
- `kneeboard.py` — `page_route(..., timed_elsewhere=)`, new `page_timing()`
  and `_timing_block()`; a plan longer than seven legs gets the clock on its
  own page; the WHEELS UP line no longer runs off the right edge.
- Docs: SOURCES §3 (the NTTR corridor sources), AGENT_HANDBOOK §10h,
  USER_GUIDE, the `bb_route` hint on the site.

## [1.98.1] — History goes in Learn It

Rob: "History goes in the Learn It section."

### Changed
- `courses.json` — the `f4e_history` reading moves from its own FRS phase
  ("Chapter 0 — History") into School 1's `ground` phase as the third
  reading, labelled "Chapter 0 — The Phantom: where it came from, what it
  taught"; the FRS `history` phase is removed. UPT and FRS intros,
  `pipeline_howto.md`, `courses.py` docstring and the user guide reworded.
  Counts unchanged (30 units, 49 rides, 3 readings, 4 checks, 4 planned);
  the FRS has five phases.
- Tests: `test_the_frs_opens_with_history_and_ends_with_a_check_ride` split
  into `test_history_is_read_in_ground_school_not_the_frs` (history in
  `ground`; the FRS carries no readings and opens on a card) and
  `test_the_frs_ends_with_a_check_ride`. Mutation proven: moving the chapter
  back to the FRS fails the build.

## [1.98.0] — The tagline

Rob: "Maybe it should be learn it, fly it, fight it" — "Yes, use it as the
tagline."

### Changed
- "Learn it, fly it, fight it" on the entry chip and the Train door, as
  `.ptag` on the pipeline page header, as `courses.json` `tagline` and in
  the course premise (kit and course card inherit), in `pipeline_howto.md`,
  the user guide (md + PDF). `test_the_tagline_is_one_line_everywhere`.

## [1.97.0] — Authentic Style v2.1 for every generated document

Rob: "This is the style guide for pdf files generated. All documentation
such as mission briefs should be generated and displayed with this style."
— then "The PDFs don't use the updated design styles … That needs to be
fixed."

### Added
- **`missiongen/authentic.py`** — the page furniture: `register_fonts()`
  (Bangers, Barlow Condensed ExtraBold/Bold, Source Serif 4 + Bold, Source
  Sans 3 + Bold, IBM Plex Mono + Bold, with `registerFontFamily` so `<b>`
  resolves to a real bold; Helvetica/Times/Courier only as fallbacks),
  `styles()` (title/sub/h1/h2/p/small/cell/mono/ride/tag/note/bullet),
  `section_rule()`, `pill()` (INFO/PASS/CAUTION/FAIL), `make_doc()` (navy
  band: identity left, locator right, mono white, long text cut to fit;
  hairline footer with the non-affiliation line and page number), and PIL
  helpers `pil_band`, `pil_section`, `pil_pill`.
- **Static font instances** cut from the variable fonts with fontTools
  (`scripts/cut_static_fonts.py`, `updateFontNames=True`):
  SourceSerif4-Regular/Bold, SourceSans3-Regular/Semibold/Bold.
- `docs/brand/authentic-style-specimen.pdf` — the specimen.
- **Tests** `tests/test_authentic.py` (15); `scripts/mutate_authentic.sh`
  15/15.

### Changed
- **`data/brand/flightline.json`** document palette → Authentic v2.1: paper
  #FFFFFF, ink #101828, navy #00205B, slate (dim) #475467, warning (danger)
  #9F1239, caution (warn) #B45309, rule #D0D5DD; new `accent` #1D4E89,
  `panel` #F4F6F8, `ok` #067647. The site's `sys_*`/`role_*` keys are
  untouched. `test_flightline` contrast pairs updated (warn/danger are text
  colours, not fills).
- **`aar_guide.py`** — styles and `Doc` now come from `authentic`
  (names kept; `Doc` is a factory taking a locator); **`wk_guide.py`** and
  **`course_kit.py`** inherit; the kit's tables set in Source Sans with navy
  heads and `S_CELL`; inline code in IBM Plex Mono; section rules.
- **`brief.py`** — `_page()`: navy band (rail left, `SORTIE STARTER / <page>`
  right), Bangers banner, Source Sans subtitle, section heads in Barlow
  ExtraBold with a full-width rule, footer with the non-affiliation line.
- **`kneeboard.py`** — `_page()`: the same band and banner at kneeboard
  scale; `h2` (section heads) is Barlow ExtraBold; white paper.
- **`scripts/build_guide_pdf.py`** — styles, band header, cover and tables
  from `authentic`; emoji glyphs the faces cannot draw removed from copy.
- **`scripts/build_whatsnew_html.py`, `build_sources_html.py`,
  `build_roadmap_html.py`** — `@font-face` for the six faces from `/fonts/`,
  the v2.1 tokens, a navy `.aband` identity band, Bangers h1, Barlow
  sections, serif prose; version read from `missiongen/__init__.py`
  without importing pydcs.

## [1.96.0] — Check rides

Rob: "each training session should have a check ride … for the F-4
wingtip to wingtip, how would we create a scoring system?" — then "keep the
same framework but we need to abbreviate it as a game."

### Added
- **`missiongen/checkride.py`** — the check-ride engine, trigger-only.
  Items read off LEAD's state (`UnitBankWithin` / `UnitVerticalSpeedWithin`
  on the lead unit): level, turns (both ways), climbs/descents. Time in
  the `POSITION_M` (60 m) moving-zone band per item as paired counters —
  in ×10 vs total ×9 (E, 90 %), ×4 vs ×3 (G, 75 %), ×2 vs ×1 (F, 50 %) —
  compared with `FlagIsLessThanFlag`, because the Editor has no division.
  Join-settle arm (20 s in band), pitchout at `formation.profile_seconds()`,
  rejoin timed by a per-tick counter (E ≤ 90 s, G ≤ 150, F ≤ 240, critical
  at 300), critical items (collision band 12 m; lost > 400 m for 30 s;
  never rejoined) → `F_CRIT` with a reason. Card: U/F/G/E per item,
  Q / Q- / U overall. Flag block **8700–8729**. `brief_lines(practice)`.
- **Formation profiles `precheck` (stage 6) and `check` (stage 7)** — same
  legs (level, ±45° turns, +3,000 ft, +30/−50 kt, −3,000 ft, level; 18 min);
  the pre-check keeps `_coach` and runs the engine as practice, the check
  runs the engine alone. `RECIPE_ENUMS["formation"]` gains both.
  Cards `form_precheck`, `form_check` (`scripts/add_formation_checks.py`,
  idempotent; copies form_close's recipe and aircraft choices).
- **Recipe `check_ride`** — the timing coach goes silent (no per-point
  calls, no cues), adds an E window (`TIGHT_S` ±10 s, flags 8980–8983),
  and prints a U/F/G/E card with Q/Q-/U overall (flags 8984–8985); late at
  the anchor is a critical item. Card `timing_5_check` (TOT 06:00, track
  ride 5).
- **Course** — Formation phase: 5 stages + pre-check + check; Timing:
  track rides 1–4 + `timing_5_check` (check); AAR: rides 0–7, ride 8
  (qualification) as the check, rides 9–10 after it. Track units carry
  `check`; gradesheet rows inherit it.
- **Kit** — gradesheet columns `sim_grade_UFGE`, `ip_grade_UFGE`,
  `check_result_Q_Qminus_U`; the PDF prints the U/F/G/E and Q/Q-/U scales.
- **Tests** — `tests/test_checkride.py` (15); `scripts/mutate_checkride.sh`
  20/20. `test_formation` and `test_timing` updated for the new stages.
- `docs/brand/authentic-style-specimen.pdf` — the Authentic Style v2.1
  specimen Rob supplied; the PDF restyle is the next release.

## [1.95.0] — The Training Pipeline

Rob: "What if as part of Sortie starter we started having a set of training
sessions … a curriculum. Virtual Squadrons could take this curriculum … for
each aircraft … an initial course that helps them understand the flight
characteristics … then they learn to fight the aircraft. Including a chapter
on the history." Then: "Let's do the MVP. We also need to update the Site UX."

### Added
- **`missiongen/courses.py` + `data/courses.json`** — a COURSE is schools >
  phases > units laid over the shelf. Unit kinds: `reading` (a chapter under
  `data/courses/`), `track` (optionally `from`/`to` ride range and a preferred
  `aircraft`/`era` for the wizard), `card` (a Library template, optionally a
  preferred aircraft that must be in its `aircraft_choices`), `planned`
  (shown with `why`). `resolve()` raises on any reference the shelf cannot
  honour (unknown card/track, empty ride range, missing reading, aircraft the
  card does not offer, duplicate unit id); `summaries()`, `gradesheet_rows()`,
  `reading_path()` (bare names only — no `/`, `\`, `..`).
- **Course `f4e_pipeline`** — 3 schools, 12 phases, 25 units (46 rides, 3
  readings, 4 planned): UPT (readings, `form_*` in the F-4E, `timing_f4e`,
  `aar_boom` F-4E/coldwar), FRS (history, WK 1–3, Turning the Phantom, WK
  4–11, Proud Phantom 1–8 and 10–11, check ride `pp_8_bnai`), MQT (gun belt,
  timing package, Berlin corridor).
- **Readings** — `f4e_history.md` (original, sourced), `aviation_basics.md`,
  `pipeline_howto.md`. SOURCES.md §4 records the chapter's sources.
- **`missiongen/course_kit.py`** — `Programme.pdf` (cover, syllabus tables,
  gradesheet, readings verbatim via a small markdown walker),
  `Gradesheet.csv` (one row per ride/reading; grade, mission score, IP,
  date), `readings/*.md`, `README.txt`. No .miz on purpose (v1.78.1 lesson).
- **API** — `GET /api/courses`, `/api/course/{id}`,
  `/api/course/{id}/reading/{doc}` (only docs the course lists; rendered by
  `server.admin._md_to_html`, which now renders italics),
  `/api/course/{id}/kit.zip`; `/api/options` carries `courses`.
- **Site UX** — fourth door **Train**: topbar tab, entry card (doors now a
  2×2 grid), hero copy and a third "why" chip; `#pipeline` section with the
  course card, three school cards with progress bars, phases and unit rows
  (done checkbox → `localStorage['ss_course_<id>']`, kind chip, graded /
  IP-grades chip, Open / Open track / Read); readings open in the detail
  modal; `openDetail(k, pref)` / `openTrack(id, pref)` pre-select the
  course's jet and era only where the card or wizard offers them. GA events
  `pipeline_unit`, `pipeline_reading`, `pipeline_kit`.
- **User guide** — "The four doors" (md + PDF builder).
- **Tests** — `tests/test_courses.py` (23); `scripts/mutate_courses.sh`
  20/20.

### Fixed
- Track panel for a non-configurable track (`configurable: false`: White
  Knights, Case III, Timing) drew three empty wizard rows and "Your series:
  undefined behind a undefined"; the guide link carried
  `?era=undefined…`. Now a one-line "Flown in the F-4E, Cold War" note and a
  bare guide link.

## [1.94.0] — Waypoint timing: the clock on the card

Rob: "We need to add times to the waypoints. As a military mission planner
explore what functionality we need to add" — then "build as you suggest and
make a set of missions to help teach it. I fly the F-4E."

### Added
- **`missiongen/timing.py`** — `plan(rows, start, era, anchor, anchor_hhmm,
  mission_start, hold_s, winds)`: ground block by start type (cold 480 s,
  warm 180, runway 60, air 0), first leg on a climb schedule (`CLIMB` per
  era: fpm + climb GS), wind component from the mission's `wind_at_2000` /
  `wind_at_8000` (file `dir` read as blowing-to), per-row `leg_s`, `gs_kt`,
  `hold_s`, `cum_s` (sum of the rounded legs), `eta_s` (from mission start),
  `eta` (HH:MM:SS); anchors `takeoff | push (WP1) | tot (TARGET)`; with a
  push/TOT anchor the mission start is solved backwards
  (`start = anchor − cum − ground`) and returned as `mission_start` with
  `shift_s`; `windows()` (±30 s at the TOT / anchor, ±60 s push),
  `apply_to_group(group, tl, locked, offset_s)`, `brief_lines()`,
  `known_issue_lines()`, `parse_hhmm()`.
- **`missiongen/timing_coach.py`** — flag block **8860–8879** (`F_ARRIVE`
  8860+i, `F_GRADE` 8866+3i+k, `F_DEBRIEF` 8878, `F_ARM` 8879): hidden zones
  at WP1 (2 nm), IP and TARGET (1.5 nm); wheels-up by `UnitAltitudeHigherAGL`
  50 m; early / on-time / late by `TimeBefore` / `TimeAfter` around the
  card's ETA; "missed" five minutes after the window; hack message at arm,
  one-minute-to-wheels-up cue, hold reminder, package-at-the-IP call;
  scorecard 60 s after TARGET (base 50; +10 / −5 / −10, anchor ×2).
- **Recipe**: `timing_anchor` (enum), `timing_at` (HH:MM[:SS]; requires a
  push/TOT anchor), `timing_hold_min` (0–15), `timing_coach`,
  `timing_package`. `/api/options` carries the enum.
- **Builder**: `_time_the_route()` after `routing.leg_card` — moves
  `m.start_time` when the anchor needs it and records `stats["start_clock"]`;
  writes the player's ETAs unlocked; `_launch_timing_package()` — a
  late-activated two-ship of the player's type on the same points with ETAs
  locked `PACKAGE_LEAD_S` (120 s) ahead, activated by trigger; attaches the
  coach when asked. `stats["timing"]` (JSON-safe), `stats["timing_coach_triggers"]`,
  `stats["timing_package_label"]`; `X-Kit` carries `timing`.
- **Paperwork**: TIMING block (+ TIMING COACH) in the in-game brief; `## Timing`
  table in the PDF/markdown; TIMING rows on the kneeboard flight-plan page;
  `brief._dtg` prints the moved clock; Known Issues gains the advisory-ETA
  and locked-package lines.
- **`saydo.check_timing`** — card ETA vs waypoint ETA vs mission clock, a
  locked player point, a renamed/missing waypoint, and the anchor clock
  present in the in-game brief; `saydo.run(..., timing=, said_hhmm=)`.
- **Library track `timing_f4e`** — "Timing — The Clock on the Card (F-4E,
  1980)", four rides from Fassberg / Germany (`timing_1_flythecard`,
  `timing_2_hitthetot` TOT 05:45, `timing_3_thepackage` push 12:35 + package,
  `timing_4_absorbtheearly` TOT 05:50 + 3-min hold); `scripts/add_timing_track.py`
  (idempotent).
- **Builder UI**: Timing controls under Automatic waypoints (anchor, time,
  hold, coach, package); share-link defaults; `timing_at` sent only with a
  push/TOT anchor.
- **Tests**: `tests/test_timing.py` (39) — arithmetic, recipe validation,
  file, paperwork, coach flags, say/do plants, wiring, the four rides
  (briefs may quote only clocks the plan produces), UI wiring.
  `scripts/mutate_timing.sh`: 35 mutations, 35 caught.

## [1.93.0] — Roadmap and changelog are admin-only

Rob: "lets add the roadmap and log to the admin section, not for people to
read AI implementation thoughts."

### Changed
- `/admin/roadmap` (+ `/admin/roadmap/page`, the built document in a frame)
  and `/admin/changelog` (CHANGELOG.md rendered by a small in-house
  Markdown renderer, `server/admin._md_to_html`) behind the admin password;
  Roadmap and Changelog tabs in the admin bar.
- `/api/roadmap` now only redirects (303) to `/admin/roadmap`.
- Header, footer and the What's new page no longer link to the roadmap.
  What's new stays public.
- `tests/test_admin_docs.py` (11): closed without the password, open with it,
  no public link anywhere, renderer escapes HTML.

## [1.92.0] — The flight flies under a callsign DCS can say

Rob, on the v1.91.0 Known Issues line ("DCS will call you 'Enfield', not
'Gypsy'"): "Yes, we should always map that."

### Added
- **`missiongen/callsign.py`** — `pool()` (DCS's western fighter table, read
  from pydcs: Enfield, Springfield, Uzi, Colt, Dodge, Ford, Chevy, Pontiac),
  `dcs_name(wanted)` (a pool name is used as typed; anything else maps
  stably by `crc32(name)`, so VF-32's Gypsy is the same DCS name in every
  mission), `heritage_line()` (the brief sentence that keeps the real name),
  `apply(group, name)` (sets `callsign[1]` — the index DCS reads — plus
  [2]/[3]/name on every unit; bort numbers as integers on numeric nations).
- Brief: `Callsign: COLT 1.` + heritage line in the in-game text; `**Callsign
  Colt 1.**` + heritage in the PDF/markdown. `stats.callsign`,
  `stats.callsign_heritage` in the API result.
- Builder: the callsign field's hint names the eight and says the typed name
  will be mapped and kept as the squadron's own.
- 6 tests, 5 mutations (27/27 caught in `mutate_saydo.sh`).

### Fixed
- **The index DCS reads.** pydcs's `_assign_callsign` writes the derived name
  ("Springfield11") and leaves `callsign[1]` at 1, so the sim announced
  ENFIELD for every flight regardless of the name in the file. `apply()` sets
  the index. (Found because the say/do check compared the two.)
- A Russian-flagged player group was given a western callsign dict by pydcs
  (Russia's table lists the western pool even though the nation speaks
  numbers); it now carries the bort number as an integer.

### Changed
- White Knights: the flight flies under `wk.RADIO_CALLSIGN` (REX's stable
  DCS mapping); the comm card and wingman note say both ("REX in the
  Standards; on the radio you fly as ENFIELD 1").
- The v1.91.0 "DCS will call you X" Known Issues line no longer fires in the
  shipped library (file and paper agree); it remains in `saydo.known_issues`
  and a test proves it returns if they ever disagree.

## [1.91.0] — What the experts taught us

Rob: "I want you to become an expert Mission and Campaign maker" → dissected
Fulda 1979 M1/2/3/5/6, Sedlo Red Flag MP, Reflected Red Flag 81-2 M02, Rampagers
M05 in depth and scanned all 97 missions in the Sample Missions folder
(`docs/technique_dossier.html`, `scripts/scan_corpus.py`,
`docs/research/corpus_scan.json`). Then: "update Sortie Starter now with the
updated information and plan."

### Added
- **`missiongen/saydo.py` — the say/do check, on ourselves.** Runs last in
  `StarterBuilder.build()` and recomputes the paperwork from the world: every
  comms-card frequency must be held by a player preset, a group frequency or
  a field's ATC radio; the clock the brief prints must be the mission clock;
  the callsign the brief uses must be the one DCS will use, or the brief must
  admit the difference. Findings are `SAY/DO:` warnings in the build result.
  `tests/test_saydo.py` holds a library sample to zero and plants each defect
  class to prove it is caught. The full 142-build sweep (every template ×
  era) is clean.
  - **First-run finding, fixed:** VHF-only airframes (P-51D, MiG-21bis) were
    given the UHF flight/tactical ladder — a wingman they could not talk to
    and a card that said so. `saydo.in_band_flight_freqs` now yields to the
    airframe's band (the module's factory channels 1 and 2) and the card
    notes "this aircraft's band". Entries the jet truly cannot reach (Guard
    243.0 in a Mustang) are marked *not tunable in this aircraft* on the
    card rather than hidden (`saydo.mark_unreachable`).
  - **The in-game brief prints the mission clock** ("Mission clock: 12:00
    local, 21 JUN 1978"), read from the file at the moment the brief is
    written. The PDF's `brief.HOUR` is a twin of `builder.TIME_PRESETS`; a
    test now holds them equal.
- **"What DCS will get wrong"** — a Known Issues block in the in-game brief
  and the PDF/markdown brief, generated per mission: the stock DCS callsign
  vs the voiced one, untunable card entries, the AI limits every expert
  campaign warns about, and the readback-gate availability line on Case III
  rides. (`saydo.known_issues`; Reflected's mission notes and Rampagers'
  guide page 9 are the models.)
- **`missiongen/cockpit.py`** — cockpit parameters and draw arguments we
  have VERIFIED, with provenance, and nothing else: F-4E `COMM_FREQ` /
  `AUX_FREQ` and gear-handle argument 5 (Fulda's trigger tables), F-16C
  `COMM1_FREQ` / `COMM2_FREQ` (ED forum 273747). F-14 and F/A-18C are
  deliberately absent until someone runs `list_cockpit_params()` on them.
- **`missiongen/gates.py` — the readback gate.** Fulda's set / not-set /
  advance triplet: `c_cockpit_param_in_range` (±6 kHz, because the ladder
  sits on the 25 kHz raster and equal-to is reported to misbehave past one
  decimal) sets DONE and confirms; reminders at 30 s and 90 s while not set.
  Flags 8976–8978 in the cq_coach registry. Refuses to install on an
  unverified airframe and returns None; `gates.brief_line` prints the true
  sentence either way. Wired into the Case III pack: the check-in cue opens
  the gate, the builder installs it after presets are programmed so the
  reminder names the real channel.
- **Case III scorecard** (`cq_coach.SCORE`, `BASE_SCORE = 50`,
  `DEBRIEF_AFTER_S = 60`, `F_DEBRIEF = 8975`): a minute after the ride's last
  cue, "RIDE DEBRIEF — base 50", one line per fired grade with its points,
  and "No busts recorded" when no bust flag is set. Rides 4 and 5 stay
  silent by design. Rampagers' `Mission-Debrief.lua` is the model.
- **`scripts/scan_corpus.py`** — one record per mission for a whole corpus
  (.miz or extracted dirs), with the automatic say/do checks; the 97-mission
  scan is in `docs/research/corpus_scan.json`.
- **`scripts/mutate_saydo.sh`** — 22 mutations, 22 caught.

### Changed
- Case III card gains two lines: the readback-gate sentence (working, or
  honestly not available on this airframe, with Mother's freq and channel
  either way) and the scorecard sentence.
- `docs/ROADMAP.md` — "Now" and "Next" rewritten from the dossier: Doc folder,
  campaign export (`.cmp`, chained sorties with carried clock/fuel/stores,
  score-keyed alternates), chained rides as a syllabus, cockpit-parameter
  verification, and the Lua decision recorded as Rob's.
- `docs/AGENT_HANDBOOK.md` — new §10c on the expert techniques, the
  provenance rule for cockpit facts, and the self-check.

## [1.90.0] — Google Analytics 4, injected at serve time

Rob: add Google Analytics to the site to track behaviours in detail.

### Added
- **`server/ga.py`** — the gtag.js block, injected into every HTML response
  (front page, roadmap, what's new, sources, 404) from `GA_MEASUREMENT_ID` in
  the environment.
  - **Not in the page source, on purpose.** This app ships as a downloadable
    zip and `REPLIT.md` is a brief for re-hosting it. A hard-coded id would
    mean every self-hosted copy reports into our property: our traffic becomes
    "everyone who has ever run this", and their visitors are measured by a
    party they have never heard of. Unset, the page makes no Google request.
  - **The id is regex validated** (`^G-[A-Z0-9]{4,20}$`, anchored). It is
    interpolated into a `<script>` block; the value comes from an operator's
    environment rather than a user, so this is not the front line of anything,
    but a quote in it would be an injection in the most literal sense and a
    typo would put broken JavaScript in the head of every page.
  - **Injection is idempotent.** The sources page already passes through a
    second transform; a double injection would load gtag.js twice and double
    every page view — a reporting error that looks like growth.
- **Client events.** `ga(name, params)` in `index.html`, and eight real
  behaviours wired to it: `generate` (with `source`: builder / library / quick),
  `generate_error`, `view_change`, `library_open`, `track_open`,
  `contact_open`, `kneeboard_download`, `qf_reroll`. The existing `track()`
  helper now feeds both ledgers.
  - `view_change` exists because GA4's automatic page view fires once, on load,
    and this app never navigates again — the three doors are the same document,
    so without it Library and Fly Now do not appear in the reports at all.
  - **`ga()` no-ops when gtag is absent**, which it is on any deployment
    without an id and for every visitor running a content blocker. An analytics
    tag must never be able to break a button.
  - **The recipe is not sent to Google.** The server-side ledger already
    records map, aircraft and mission type against it; two systems recording
    the same fact is how two numbers start disagreeing, and it widens what a
    third party learns for no analytical gain.
- `GA_MEASUREMENT_ID` in `fly.toml` `[env]` — a measurement id is public in the
  page source of every site that uses one, so it is not a secret and does not
  belong in `fly secrets`.

### Changed — the privacy notice, because it had stopped being true
- The footer said **"No IP address, no account, no name — nothing that says who
  you are"** as a statement about the site. That remains true of our own
  counting and is false of a page running Google Analytics. It now describes
  the two separately: ours (no IP, off-switch, Do Not Track honoured) and
  Google's (cookies, IP, browser and device details, neither signal read).
  v1.57.0's release notes had specifically celebrated removing Google Fonts so
  the page "no longer tells Google your IP address just to draw letters" —
  reversing that quietly was not an option.
- The off-switch's own status line was **"Counting is on/off"**, unqualified.
  With GA running that is a switch that lies about what it did, which is worse
  than having no switch. It now says whose counting it governs.
- The Do Not Track line said **"we're counting nothing from this browser"** to
  the one visitor who has explicitly asked not to be tracked. It now says our
  counting is off and that Google does not read that signal.
- `REPLIT.md` tells re-hosters that they report to nobody by default, and that
  setting their own id obliges them to rewrite that footer paragraph for what
  *their* deployment collects.

### Guards
- **`tests/test_ga.py`** (33) — no id in the page source; an unconfigured
  deployment emits nothing; eight malformed ids refused including two injection
  attempts; the tag in the head, once, on every HTML response; and eight
  assertions on the footer and the switch copy. Plus a real-browser probe that
  loads the served page with **gtag.js blocked** — what an ad blocker does to
  most visitors — and checks both that the page asked Google for the script and
  that `ga()` still runs without throwing when it never arrives.
- **`scripts/mutate_ga.sh`** — 20 mutations, 0 weak. Half of them are edits to
  PROSE: restore the old no-IP wording, claim the off-switch stops Google, tell
  a Do Not Track browser it is not being counted. Those matter as much as the
  ones that break the script.
- One weak guard re-aimed: the switch-label test checked the on and off
  branches and let the Do Not Track branch revert to "we're counting nothing
  from this browser" — the most misleading of the three, aimed at exactly the
  reader who cares. Guarded separately now.

### Not done, and worth saying
- **No consent banner.** Running analytics cookies without prior consent is not
  compliant with UK/EU ePrivacy rules for visitors in those jurisdictions. Rob
  chose always-on with an honest notice over a consent gate; this line is here
  so the decision is on the record rather than overlooked.

---

## [1.89.0] — Case III night recovery: a second syllabus engine

Casmo: *"i have zero idea how to do a case 3 recovery so i was flying around
blind."* v1.88.0 fixed the radios. This is the procedure.

### Added
- **`missiongen/cq.py`** — Case III doctrine as data. CV NATOPS 00-80T-105
  §6.4 and glossary, read directly rather than through community summaries;
  every constant carries its citation, and the two places the summaries are
  wrong are called out at the constant. Also the ED radio sequence, the LSO's
  published deviation thresholds, the per-airframe cockpit setup, and the five
  rides.
- **`missiongen/cq_route.py`** — geometry hung off the SHIP rather than a map
  axis, because every fix in a recovery is a radial and a DME. The marshal fix
  and the final approach are on the same line, so one unit vector does all of
  it. Includes the left-hand six-minute racetrack laid as waypoints, so the F10
  map shows the pattern the card describes.
- **`missiongen/cq_coach.py`** — cues and grades, flag block **8940-8979**.
  Grades exactly what Supercarrier does not check: departure against the
  approach time, rate of descent below platform (via
  `UnitVerticalSpeedWithin`), altitude at ten miles, speed at six.
- **Ten templates and two tracks** — `cq_case3_f14` (VF-101 Grim Reapers) and
  `cq_case3_hornet` (VFA-106 Gladiators), the real Fleet Replacement Squadrons.
  Persian Gulf, modern, night; the check ride adds weather.
- **Recipe field `cq_ride`.** Set by a template, never the wizard — a Case III
  ride is an airborne start at a point computed from the ship's BRC, which is
  not a knob a picker can offer. Validation refuses a ride without
  `home_airbase="CARRIER"` and refuses an airframe the syllabus has no cockpit
  procedure for, rather than generating a recovery to nothing.
- **A carrier-relative airborne start** in `builder.py`. Every other carrier
  mission is a deck start because "air" has no meaning on the boat; a recovery
  is the opposite shape, and a ride that made you launch first would spend
  fifteen minutes getting to the part being taught. Single aircraft, per NATOPS
  §6.4 and because DCS AI cannot fly a Case III at all.

### Three decisions that would have been defects the obvious way
- **The marshal radial hangs off the FINAL BEARING, not the BRC** — the
  extension of the angled deck, ~9° to port. Deriving it from BRC looks perfect
  in code and is three and a half miles off the arc at 21 DME.
- **PLATFORM is an ALTITUDE (5,000 ft), not a range.** Community guides quote
  a DME beside it; a range gate is the natural implementation and it teaches
  the student to hunt for a number that is not the gate.
- **Range gates are `UnitInMovingZone`, never static zones.** The ship makes
  25 knots, so a static zone at 10 DME is four miles out of position ten
  minutes in. `UnitInMovingZone(unit, radius_m, zoneunit)` gives a DME annulus
  centred on the carrier that is correct at any point in the ride.

Plus two the tests exist for: **which cues a ride fires is declared**
(`RIDE_CUES`), never inferred from sequence — ride 4 starts at three miles,
already inside every range gate, and would otherwise fire three wrong cues in
its first second; and **the timing grade allows for the transit** from the fix
to the commence band, without which every pilot is graded LATE including the
one who crossed the fix on the second.

### Fixed
- **"Your jet starts clean" fired on armed jets.** The warning hung off
  `if wk_ride:` rather than off whether anything reached the pylons, so every
  mission that was not a White Knights ride was told its jet was empty — while
  the kneeboard listed the stores and the aeroplane wore them. Live on every
  carrier sortie anyone generated.
- **The briefing described an airborne jet as "parked and ready"**, and printed
  the free-flight sandbox paragraph ("there are NO objectives, tasking or
  waypoints") over a mission with a flight plan, cues and grades.
- `missiongen/tracks.py` publishes a track's `requires` to the browser; the
  Library's ownership check only knows maps and aircraft, and DCS: Supercarrier
  is neither.

### Changed
- The ride panel, the track panel and the in-mission briefing all name the
  module the pack depends on. Three surfaces because a ride that belongs to a
  track is never a grid card, so the grid chip alone would have been dead code
  for exactly these missions — which is what the browser guard caught.

### Guards
- **`tests/test_case3.py`** (46) — the marshal rule read back out of the .miz
  by bearing and range from the actual ship; the gates; the moving zones and
  which unit they hang off; per-ride cue sets; the flag block against
  wk_coach/wk_brief/aar/formation; the briefing telling the truth about an
  airborne start; the cockpit card matching the cockpit; and a real-browser
  probe of the two panels a pilot actually opens.
- **`scripts/mutate_case3.sh`** — 33 mutations, 0 weak. Every one is a
  defensible-looking implementation rather than a typo: derive the radial from
  BRC, make platform a range gate, use static zones, let the cues run in
  sequence, grade the push with no transit allowance.
- One weak guard re-aimed and recorded: the gate parametrisation read
  `cq.LEVEL_DME` for its own expected value, so moving the gate moved the test
  with it and a four-mile error passed. The published numbers are now written
  out as literals, with a separate test pinning the module's constants against
  the manual.
### Also fixed, found by the guards
- **A featured card briefed a Case III it had never built.** Carrier
  Qualification told the pilot " - CASE III (night/IMC): Marshal stack, push on
  time, CATCC/ACLS approach" over a recipe set to day, clear, warm start on the
  deck. It sets up a Case I and always did. The night Tomcat sandbox did the
  same thing more quietly — night and weather right, but it put you on the deck
  and then walked you through a stack it had not set up. Both now say what they
  are and point at the taught version.
- `test_no_card_tells_you_to_fly_a_case_three_it_has_not_built` generalises it:
  a card that names the procedure must either BE one of the taught rides or say,
  in the same paragraph, where the taught version is. Paragraph-scoped, because
  a first cut checked the whole brief as one string and a card could instruct a
  daylight Case III and still pass on the strength of a pointer further down.
- **24 stale NEW badges cleared.** Adding ten cards tripped
  `test_the_new_badge_still_means_something` at 34 of 101 — the guard's own
  reasoning is that NEW means shipped in THIS release, and the White Knights
  and Proud Phantom sets had had their moment several releases ago.

- **Every mutation harness now checks the baseline is GREEN before it starts**
  (`baseline_green`), and this one is a lesson rather than a feature. A brief
  was edited so that it failed one of the guards the Case III harness
  exercises; the harness was run without running the plain suite first; and
  every mutation on that guard reported "caught" — because the tests were
  already failing. Thirty-six caught, zero weak, and the entire run was noise.
  A mutation harness measures the delta between green and broken, and with no
  green there is no delta. Added to `mutate_case3`, `mutate_boat_card`,
  `mutate_preflight` and `mutate_theater`.
- The browser probe was wrong twice before it was right — first it called
  `libItems()`, which filters track members out and returned an empty list and
  a green test; then it called `libCard()` on a ride item, a path the page
  never uses, and crashed. Probing a path the product does not use is worse
  than not probing.

---

## [1.88.0] — The boat card, read back out of the cockpit

Casmo, after a Case III: *"i have zero idea how to do a case 3 recovery so i
was flying around blind. The radios didn't turn right tho. It says carrier on
channel 2 but I had to manually tune it to the freq."*

### Fixed
- **`presets.py` programmed ONE radio.** The F-14 has two full UHF sets — the
  pilot's AN/ARC-159 (radio 1, 20 presets) and the RIO's AN/ARC-182 (radio 2,
  30 presets, 225-400 MHz among other bands) — and the RIO's is the set crews
  normally use for boat comms. It kept pydcs's factory table, where channel 2
  is 258.000. The card advertised CH2 = Mother and was true only about a radio
  the pilot was not keyed to. Now every radio that is genuinely a UHF set
  carries the full ladder.
- **Which radios count, measured rather than assumed.** Across all 78 shipped
  airframes, the fraction of each radio's DEFAULT channels inside 225-400 MHz
  is bimodal: 100% (a real UHF set — F-14 r1+r2, Hornet r1+r2, F-4E r1+r2,
  A-10C r2, Mirage F1 r2, Apache r2, F-16C r1, F-15E r1), 0% (a VHF set), and
  three stragglers with no pure set at all (AV-8B r1 85%, AJS37 91%, MiG-29
  95%). Pure UHF is the rule; the three stragglers keep the older
  single-best-radio fallback so they do not lose the presets they have today.
  Below 50%, nothing is programmed and the card prints no CHAN column.
- **The brief dropped the comms notes column.** ICLS channel, Link 4 frequency,
  ACLS state and BRC were rendered only as grey sub-text on the kneeboard PNG
  inside the .miz. `brief.py` discarded the note (`_n`) when building the
  markdown table. The boat card now reaches the brief the pilot plans from.

### Added
- **`missiongen/pydcs_patches.py`** — a single, documented home for fields the
  DCS Mission Editor writes and vendored pydcs does not. First entry: **ship
  `modulation`**. ED's Supercarrier guide describes the boat's ATC radio as
  frequency *and* modulation; pydcs's `Ship.dict()` emits only the frequency
  and has no modulation key anywhere. Carrier ATC is AM, and the F-14 pilot's
  ARC-159 is AM-only across its whole band, so an FM carrier is unreachable no
  matter how the presets are programmed. Written as AM explicitly.
  **Stated honestly:** what is confirmed is that the editor writes the field
  and pydcs does not. What is NOT confirmed is what DCS does when the key is
  absent — it may default to AM, in which case this changes nothing observable.
  It is not the fix for the reported defect; the radio change is. Keeping the
  correction here rather than editing `vendor/dcs` keeps the vendored tree
  byte-identical to upstream so it can be re-pulled without hunting local edits.
- **`tests/test_boat_card.py`** (18 guards × 5 hulls). Reads the whole card
  back out of the mission: ship frequency in hertz, modulation, TACAN
  (channel, ident, band, **surface vs air-to-air**, bearing, and the derived
  frequency), ICLS channel, Link 4 frequency and ACLS — each in BOTH
  directions, so the card can neither under-promise nor over-promise. Plus the
  cockpit: which radios were loaded, decided from the file (channel 1 holding
  the flight frequency, a raster value no factory table carries) rather than by
  re-deriving `presets.py`'s own rule, because a test that restates the
  module's rule proves only that the module agrees with itself.
- **`tests/test_pydcs_patches.py`** (5 guards) including a delete-me alarm: it
  fails if upstream pydcs grows ship modulation, so the local patch cannot
  quietly outlive its reason and start fighting upstream's value.
- **`scripts/mutate_boat_card.sh`** — 18 mutations, 0 weak. Restores the
  one-radio bug exactly; puts the ladder in the A-10C's VHF sets; moves Mother
  off CH2; drops Guard; makes the carrier TACAN air-to-air; publishes DME with
  no radial; mis-tunes ICLS by one; activates ICLS without carding it;
  advertises ACLS on hulls without it; gives the 1944 Essex a landing system;
  sets the group frequency in megahertz; puts the boat on FM; removes the
  modulation patch; and three ways of losing the notes column again.
- Coverage that did not exist: `test_comms_truth.py`'s preset check was real
  but only ever built a **land** Hornet mission, so the carrier row's channel
  had never once been read out of a cockpit. That is why this shipped.

### Changed
- `tests/test_comms_truth.py` unpacks comms rows tolerantly (`*_notes`) now
  that the table carries a sixth column.
- `docs/AGENT_HANDBOOK.md` — five new unit traps: two UHF radios per jet and
  which ones to program; DCS clobbering channel 1; `ShipGroup.set_frequency`
  taking hertz; pydcs writing no ship modulation; and `aa=False` on a ship
  beacon.

### Known and deliberately not changed
- ACLS and the Case III marshal/approach comm sequence are **DCS: Supercarrier
  module** features. Whether the free CVN-74 Stennis exposes them when the
  module is owned could not be confirmed from any source, so no hull's declared
  systems were altered on an inference. This gets settled — with a plain
  statement on the card — in the Case III training release.

---

## [1.87.1] — Parallel preflight

Rob: *"Whats the wait? Do we need that much testing"* — the answer was yes to
the testing and no to the wait.

### Changed
- `scripts/preflight.sh` runs the suite under `pytest-xdist` when it is
  importable: `-n auto --dist loadfile`. **Measured: 20:34 -> 10:17 on the
  two-core build box, 3,528 passed / 43 skipped either way.** No test was
  removed, deselected, or sampled.
- `--dist loadfile` is required, not preferred. Several test modules share a
  module-scoped fixture that generates an entire mission (`built`,
  `built_green`, `built_drag`, `built_full_ramp`); xdist's default `--dist
  load` distributes individual tests, so a module split across N workers builds
  its mission N times. On two cores that can be slower than serial while
  presenting as a speed-up — a performance defect that produces a correct,
  green result and therefore leaves no artifact to read back.
- Parallelism is detected, never assumed. `preflight.sh` must work on a fresh
  unzip of the release zip before the launcher has built its venv, which is why
  the pytest step already skipped rather than failed when pytest was absent.
  A hardcoded `-n auto` would have turned the release's own recovery check into
  an install error.
- `requirements.txt` documents `pytest-xdist` as test-only and optional,
  alongside the existing `pypdf` note, with the exact command preflight uses.
- Release workflow: the suite is no longer run once by hand and then again by
  `release.sh`'s preflight. One run, at the gate.

### Added
- `tests/test_preflight_parallel.py` (6 guards). Unusually for this codebase
  these are text assertions on a shell script rather than measurements, and the
  file says why: every failure mode here yields a green suite, so there is no
  artifact to read. Guarded: the pytest step still exists; the flags come from
  a variable rather than being hardcoded; the variable is only set inside the
  xdist probe; the distribution is `loadfile`; `requirements.txt` documents a
  copyable command that actually parallelises, with its reason, and does not
  pin xdist into the deployed image.
- `test_the_module_scoped_mission_fixtures_this_protects_still_exist` is the
  counterweight to a text guard: it fails loudly if the premise disappears, so
  `--dist loadfile` gets re-decided rather than re-asserted.
- `scripts/mutate_preflight.sh` — 12 mutations, 0 weak. Includes the
  distribution swap, the hoisted assignment (a hardcoded flag wearing an
  if-block as a disguise), the deleted probe, gutting the pytest step, and four
  ways of degrading what the zip tells the reader.

### Fixed
- One weak guard, re-aimed and recorded: the first requirements.txt check
  searched the whole comment block for `--dist loadfile` and passed when the
  flag was cut from the *command* but survived in the *sentence explaining why
  it matters*. A reader copies the command. Now aimed at the command line.

### Docs
- `docs/AGENT_HANDBOOK.md` — corrected suite timing, added the full-suite
  invocation, and a paragraph on why `loadfile` is load-bearing. `pytest-xdist`
  removed from deferred work; it is done.

---

## [1.87.0] — The coastline, and which half the enemy starts in

Rob: *"When I download the map for a persian gulf mission thats been
generated, the map is reversed with blue being land and water being brown."*
and *"let's not add a single random red aircraft at the beginning of a mission
in the blue area."*

### Fixed
- **`coastlines.json`: the Persian Gulf water ring was not a coastline.** It
  traced the Arabian shore, then closed with three box corners — (22,64),
  (30,64), (30,48) — and the lat-30 edge from lon 64 to lon 48 swept the whole
  of Iran into the flood. Rendered base measured **67.9% sea before, 31.4%
  after**. Re-authored as one simple ring: Qatar's west coast and around the
  peninsula, east along the UAE to Ras Musandam, back down the Gulf of Oman
  side past Muscat, out into the Arabian Sea, home along the Makran/Iranian
  coasts to the head of the Gulf, down the Saudi shore to close (49 vertices).
- **Seven island airfields had no island polygon** (Kish, Lavan, Sirri, Abu
  Musa, Greater/Lesser Tunb, Sir Abu Nuayr) — all rendered in open water. Two
  coastal fields (Bandar Lengeh, Bandar-e-Jask) had the shore cut inland of
  them. Syria: Cyprus's outline missed the Akrotiri peninsula, and the
  Lebanese/Turkish shore cut inland of Wujah Al Hajar and Gazipasa; measured
  25.6% sea after vs 26.4% before, which is the number that says Syria was
  only ever marginally off.
- **`threats.add_enemy_cap` stationed on the friendly side.** `frac =
  rng.uniform(0.40, 0.65)` of the way from own_center to enemy_center; over
  2,000 seeds that lands on the blue side of the midpoint **42%** of the time.
  Now `(0.55, 0.80)`: past the midpoint by more than the racetrack and lateral
  jitter can undo (both are perpendicular to the axis, so neither moves the
  fraction), and short of the enemy fields where `defend_airbase` already
  sits. `max_engage_distance` unchanged at 55 km — they still come to you.
  NOTE: this changes generated content for a given seed, as the Sinai axis fix
  did in v1.83.0.

### Added
- `tests/test_theater_chart.py` (18) — every airfield the presets and lineups
  NAME must render on land (derived, exhaustive; scoped to preset fields
  deliberately, since DCS's own airport list includes genuinely offshore
  helipads on Syria); 13 named geography probes checked both ways; islands
  must sit in water and carry their airfields; and a rendered-page check on
  the TAN/WATER ratio that needs no copy of the projection (the base plate is
  only those two colours and only inside the panel).
- `tests/test_red_air_placement.py` (16) — airborne red flights must start
  nearer the enemy centroid; ground-started red aircraft must be parked on a
  red field (two definitions, because centroid distance is the wrong question
  for a parked transport on a long coast); the band asserted at its source,
  scoped to `add_enemy_cap` because `threats.py` has three `frac` rolls and an
  unscoped regex read the SAM belt's; and a guard that enemy air still exists
  at all.
- `scripts/mutate_theater.sh` — 11 mutations, 0 weak, including the original
  broken ring restored verbatim and a swap of the two base colours.

---

## [1.86.0] — Pattern traffic to eight

Rob: *"Pattern Traffic is too limited, it should have the ability to add more
aircraft numbers."*

### Changed
- `pattern.MAX_COUNT` 4 → **8**, with the ceiling reasoned in place: the
  landing conveyor spaces 7 km in trail from 11 km out, so aircraft eight
  starts 60 km (~32 NM) from the threshold — nine minutes out at approach
  speed. Departures stay bounded by free stands (best-effort loop + warning,
  unchanged). The Builder's picker offers 1–8; the recipe bound still reads
  `pattern.MAX_COUNT` (one number, owned by the module that flies them).

### Added
- `tests/test_pattern.py` — the building block's FIRST tests, six of them:
  eight aircraft read out of a built .miz (landing mode, no stand limit to
  hide behind, all AI); pairwise spacing > 1 NM (eight on one point is a
  mid-air, not a pattern); `both` puts three on approach and some on the
  ramp; the recipe rejects 0 and MAX+1 and accepts MAX; the UI select derived
  from `MAX_COUNT`; and the ceiling-keeps-the-tail-in-sight arithmetic.
- Five mutations in `scripts/mutate_library_shelf.sh` (which gains
  `pattern.py`/`recipe.py` in FILES and runs test_pattern.py): the old cap
  restored, the picker left at four, the trail spacing zeroed, `both` made
  all-landing, and a drifted private copy of the bound. 18 caught, 0 weak.

---

## [1.85.1] — The credit, and the third waypoint case

Rob: *"I need to add Tricker for his feedback and help. Also we don't provide
a tool to make waypoints but automagically adds them."*

### Added
- **Tricker credited** in the frontend footer ("Flight testing & feedback")
  and a Credits section in README.md.
- `test_the_footer_credits_the_flight_tester` and
  `test_every_document_tells_the_same_waypoint_story` in
  `tests/test_library_shelf.py`; two mutations in
  `scripts/mutate_library_shelf.sh` (13 caught, 0 weak). README.md joined the
  harness FILES/baseline.

### Fixed
- **The waypoint promise told two-thirds of the truth.** The north star named
  two ways a flight plan appears (strike templates, the Automatic waypoints
  tickbox) while the White Knights rides have carried the squadron's route
  automatically since v1.76.1. All five statements of the promise —
  README.md, docs/ROADMAP.md, docs/USER_GUIDE.md, REPLIT.md,
  scripts/build_guide_pdf.py — now name the three cases and state there is no
  waypoint editor. The guard requires each document to carry the tickbox, the
  training-syllabus case, and the not-user-authored statement.

---

## [1.85.0] — The wingman moves into the player's flight

Rob: *"The other Rex flight doesn't fly with me at all. When I fly it, the
navigation aids don't fly to the target either."*

### Changed
- **Two-ship rides are built as ONE group.** Third separate-flight failure in
  a row; DCS gives an independent flight no way to hold position on a human.
  `_wk_two_ship = has_counterpart(ride, map)` sizes the player's group
  (ground and air start), seat 1 `set_player()`, seats 2+ `Skill.Excellent`;
  `load_pylon` is group-wide so the wingman is armed identically for free.
  Deleted: `apply_counterpart` call sites, the late-activation hold, the
  release trigger. `counterpart_legs` survives as the two-ship PREDICATE and
  as the trail/abreast numbers the cards print.
- **`WINGMAN_NOTE` and the brief's wingman page rewritten** — "IN YOUR
  FLIGHT, on your wing", with the cost stated: he will not fly the geometry
  by himself; radio menu sends him.
- **The active helper gate is pinned.** `SetActiveHelperGateToPoint(me, 2)`
  when the brief ends, then eight phase-flag triggers advance it (lowlevel→3
  … egress→8). First pass only — TriggerOnce is spent by the re-attack, and
  the second run is flown on the cues, which is the point of a second run.
- `wk_proud_phantom` pack content 2.3.0 → **3.0.0**.

### Tests & harness
- Reworked across test_wk.py and test_wk_coach.py: one group with two armed
  units (skills read from the .miz), no REX 2 group, no hold trigger, no
  late activation on the player's flight, air-start two-ship, stand-clash
  guard iterates units. Retired guards whose mechanism no longer exists
  (climb-out point, hold/release). The line-abreast offset mutation retired
  (dead geometry); the trail mutation re-aimed at the card-vs-table guard;
  the hangar mutation re-aimed at dressing's `unit_id` filter — the only
  place that bug can now re-enter.

---

## [1.84.0] — Gates on the coached ride, and the shared shelter

Rob: *"On the coached mission, there should be training-mission gates and
there is a static plane in the same hanger as the second plane."*

### Fixed
- **A static F-4E in REX 2's shelter** — 0 m at the pack's seed, GSE at 16 m.
  `dressing` fills stands where `slot.unit_id is None`; the player's group
  exists before dressing so his stand is skipped, but the counterpart was
  created ~400 lines later. Creation moved above the dressing block
  (`self._wk_cp`, guarded on `not carrier_home`); the wk-route block now only
  references it and wires triggers. `test_no_static_shares_a_stand_with_
  either_aeroplane` reads the distances out of the built .miz (< 30 m fails).
- **The coached ride had no gates.** The teach/check split was drawn in the
  wrong place: pp_8_bnai (ride 9) is the no-aids check, so the coached ride
  gets every aid. `coach_gates: true` on `pp_8_bnai_coach`; the brief's
  coaching page now names the gates ("The cues" pronoun fix included); the
  guard re-aimed to assert gates ON the coached ride and coach_gates on
  exactly {pp_8_bnai_coach, bnai_coach_green}.

### Added
- Two mutations (one two-site: early creation disabled AND late re-creation
  restored — the old order exactly), plus a gates-off-the-template mutation.

### Changed
- `wk_proud_phantom` pack content 2.2.0 → **2.3.0**.

---

## [1.83.0] — The target, the axis, and the helper gates

Rob: *"The coached BNAI mission doesn't have a target to bomb. The mission
waypoints don't seemed aligned. And the green navigation boxes don't exist."*

### Fixed
- **The White Knights attacks bombed empty sand.** `bb_targets` anchors its
  packages to enemy airbases — 60+ NM north-west under the Proud Phantom
  lineup — while `wk_route` runs the TARGET leg from the home field down the
  route axis. The brief listed TGT1/TGT2 the flight plan never visited. Now,
  for any ride whose leg table has a TARGET, one deterministic depot package
  is placed AT `leg_positions(...)["TARGET"]` and the generic placement is
  skipped (`picks = []` keeps the guns-tier loop shape).
- **Sinai's route axis ran through Cairo.** `AXIS_DEG["sinai"]` was 120°,
  chosen when the rides silently launched from Hatzor; from Cairo West that
  bearing crosses Cairo city (Cairo International: 28 NM out, bearing 091) at
  300 ft AGL. Now 265° — the open Western Desert, toward Libya, and the Beni
  Suef checkout rides stay west of the Nile.

### Added
- **`coach_gates` recipe flag** → DCS's native helper gates
  (`ShowHelperGatesForUnit`, predicate `a_show_route_gates_for_unit`) drawn
  along the player's flight plan, fired by the brief's `F_DONE` (or `t>1` on a
  brief-less build). NOT Lua — I twice told Rob otherwise (first building
  card-ring cosmetics, then proposing a scripted variant) before checking the
  ED forums: the training-mission gates are a stock trigger action, and pydcs
  carries all three gate actions. The no-script guarantee holds.
- `bnai_coach_green` is now **"Green Rings & Gates"**: `coach_gates: true`,
  and `test_the_green_variant_is_the_same_ride_with_a_different_ring` now
  licences exactly {`coach_ring`, `coach_gates`} as its recipe delta.
- Six guards in `tests/test_wk_coach.py`: targets within 3 km of the TARGET
  leg; every en-route waypoint west of the home field; the gates trigger on
  the green variant aimed at the player's unit id and keyed on `F_DONE`; the
  track ride gate-free; and the air-start counterpart spawning above 250 kt —
  the one WEAK mutation from v1.82.1's harness run, now with a guard of its
  own (`built_drag` fixture).
- Nine mutations registered; the air-start stall mutation re-aimed from the
  suite-green pair to `flying_speed`.

### Changed
- `wk_proud_phantom` pack content 2.1.1 → **2.2.0**: the geometry moved; a
  pilot's notes about headings no longer match 2.1.x.

---

## [1.82.1] — The wingman takes off

Rob: *"The coached mission AI plane doesn't take off, it just goes slowly down
the runway."*

### Fixed
- **m/s where pydcs wants km/h.** `FlyingGroup.add_waypoint(speed=...)` and
  `flight_group_inflight(speed=...)` take km/h (pydcs divides by 3.6 before
  storing). `wk_route` passed `ias_to_tas_kt(...) * 0.514444` — metres per
  second — at three sites: the player's route, the counterpart's route, and
  the counterpart's air start. Every waypoint was commanded at TAS/3.6 ≈ 112
  kt for a 400-kt leg, below a loaded F-4E's rotation speed, so the AI rolled
  the length of the runway and never flew. Shipped in v1.76.1 with the flight
  plans; invisible until v1.82.0's brief hold meant Rob was on the ramp to
  watch him. Now `* 1.852` (kt → km/h). Audited every other
  `add_waypoint`/`flight_group_inflight` caller: `routing.py`, `formation.py`,
  `pattern.py`, `ambient.py` all already spoke km/h; `aar_hud`/`aar_grade`
  keep 0.514444 correctly (trigger-zone speed CONDITIONS are m/s).
- **No climb-out point.** `apply_counterpart` went straight from
  `flight_group_from_airport` to the first en-route leg 18 NM out. Every
  ground-started AI flight pydcs itself builds gets `add_runway_waypoint`
  between parking and the route; the counterpart now does too (fixed distance
  — the pack must stay byte-deterministic).

### Added
- Three guards in `tests/test_wk_coach.py`, all reading the built `.miz`:
  every named waypoint within 5 kt of what its leg sheet briefs (derived from
  `legs_for`, not a constant); nothing en route below 250 kt outside 12 km of
  the field (the blunt version, so a NEW leg with the old conversion still
  fails); REX 2's first point after parking within 12 km (measured spread of
  the climb-out point: 6.9–8.5 km, seed-dependent parking offset; the bug put
  it at 34 km).
- Four mutations in `scripts/mutate_white_knights.sh`: each conversion site
  reverted to 0.514444, the climb-out dropped, and a flat 500 km/h "reliability
  fix". All caught.

### Changed
- `wk_proud_phantom` pack content 2.1.0 → **2.1.1**.

---

## [1.82.0] — The held wingman, the green ring, and the authoring prompt

Rob: *"Let's do a version of the coached B'NAI with green rings. And there is
no wingman flying with me."* Then: *"I need downloadable instructions that I
can add to any AI that will tell it how to format a mission pack."*

### Fixed
- **The wingman flew the attack while the pilot read the brief.** REX 2 is a
  separate warm-started flight on a fixed schedule; the brief locks the PLAYER
  in his seat for as long as he reads. So the counterpart started, taxied and
  flew the whole B'NAI alone, and was on the ground again before SPACE. Now:
  `late_activation = True` on the counterpart whenever a brief attaches, plus a
  TriggerOnce (`WK wingman: released by the brief`) — `FlagIsTrue(F_DONE)` →
  `ActivateGroup` — so he is released by the exact action list that hands the
  aeroplane back. No brief, no hold. The brief's wingman page states the hold.

### Added
- **`coach_ring` recipe field** (`red` | `green`). A presentation choice, so it
  lives in the RECIPE rather than the ride — the green variant is the SAME
  `wk_ride` with a different palette. `wk_coach.card_path(key, ring)`,
  `RINGS`, and `scripts/build_wk_coach_cards.py` builds every palette
  (`wk_coach_green_<key>.png`); red keeps its original file names so every
  mission ever built still names the files it shipped with.
- **`bnai_coach_green`** — a loose Library card (deliberately NOT a 12th track
  ride): Proud Phantom ride 8 with green rings. A guard asserts its recipe
  differs from `pp_8_bnai_coach` in exactly `coach_ring`.
- **`docs/PACK_AUTHORING_PROMPT.md`** — AI-portable `.sspack` authoring
  instructions. `tests/test_pack_prompt.py` EXECUTES the doc's own
  `build_integrity` code block and requires byte-identical output from
  `packfmt.digest_of`, installs a pack built from the doc's example through the
  real installer, and pins the format number, role list, and digest formula to
  the code.
- Six guards in `tests/test_wk_coach.py` (wingman hold read out of the `.miz`,
  green cards shipped and pixel-verified, palette/enum/files agreement), five
  in `tests/test_pack_prompt.py`.
- Six mutations in `scripts/mutate_white_knights.sh` — 96 caught, 0 weak — and
  three hand-run against the prompt doc, all caught after two of my own guards
  were re-aimed (the role regex ate the digit in `a2a`; the format pin passed
  on an OR).

### Changed
- `wk_proud_phantom` pack content 2.0.0 → **2.1.0**: the coached ride's
  wingman now waits for the brief.

---

## [1.81.0] — Lineups: one map, one era, more than one order of battle

Rob, in one sitting: *"I haven't installed the pack yet but it is showing up in
the library"*, *"when I try to select a pack to upload, it doesn't recognize the
file extension"*, *"it threw an internal error when I uploaded the pack"*, and
*"Egypt is listed as a Red Force when it's supposed to be blue."*

### Added
- **`lineup` — a named order of battle, layered over the era preset.** An era
  says WHEN; a lineup says WHO. `maps.json` gains `<map>.lineups`, `Recipe`
  gains `lineup`, and `builder.py` merges the block over
  `map_cfg["presets"][era]` so a lineup states only what it changes.
  `Recipe.validate` refuses an unknown lineup by name and refuses one whose
  `eras` do not cover the era asked for.
- **`sinai.lineups.proud_phantom`** — June 1980. `blue_country: USA`,
  `red_country: Libya`, the eight Egyptian fields blue with **Cairo West**
  first, and the three western fields (Borg El Arab, Jiyanklis, Gebel El Basur)
  red. Israel is in neither list. The block's `note` records what DCS forced:
  Libya owns no field on this terrain, so the aggressor stands on real Egyptian
  ground in the direction Libya lies.
- `tests/test_proud_phantom_lineup.py` — 14 guards. Four read a built `.miz`:
  REX 1/2 depart Cairo West as **USA**, Israel has no groups on either side
  (NOT "Israel is absent from the coalition" — pydcs seeds 19 blue countries
  and 12 red by default, so a name in that list asserts nothing), the red air
  defence is Libyan and none of it rings Cairo West, and the generated brief
  never mentions Israel or an Israeli field.
- `tests/test_library_shelf.py` — 13 guards over the shelf and the upload,
  two of them driving a real Chromium.
- `scripts/mutate_library_shelf.sh` — 11 mutations, 0 weak.

### Fixed
- **Eleven rides took off from the wrong country.** `builder.py` resolved the
  home field with `next((a for a in own_fields if a.name == r.home_airbase),
  own_fields[0])`. Cairo West is red under the 1973 preset, so the fallback
  fired and every Proud Phantom ride launched from **Hatzor, Israel**, with the
  70th TFS registered as an Israeli unit against a Cairo West carrying an SA-6
  battery, two SHORAD rings and parked MiG-23MLDs. Now a hard `EraViolation`
  naming the field, why it is not yours, and what your side does hold.
- **`Nellis AFB` → `Nellis`** on `f100_sabre_dance_bfm`. Exposed by the same
  check; the DCS airfield has never been called that.
- **The Library shelved unpublished syllabi and duplicated published ones.**
  `libItems()` minted a card per track from `OPT.tracks`. Unpublished, it
  advertised a whole-track download that answers 409; published, it sat beside
  the pack card rendering the same syllabus from different missions — the pack
  pins `seed = 4400 + n`, the track card carries no seed and the server rolled
  one per request. `trackItems()` is gone. `openTrack` reads `OPT.tracks`
  directly, so every `track_<id>` link still opens the panel.
- **The pack file picker greyed out `.sspack`.** `accept='.zip,.miz'` while
  `packs.install` has taken `.sspack` since format 2 — the only extension
  `scripts/build_pack.py` writes.
- **Every successful upload ended in an internal error.** `_pack_edit_page`
  still called `_packs._bundled()`, deleted in v1.80.0 with bundled packs. The
  pack installed, the 303 fired, and the review page raised `AttributeError`.
  No test had ever followed the redirect.

### Changed
- `wk_proud_phantom` pack content version → **2.0.0**. The missions are not the
  same missions.

---

## [1.80.2] — The last brief page never left the screen

Rob: *"The B'NAI coached mission looks good except the last screen doesn't exit
when you press the space bar."*

### Fixed
- **A picture with no successor.** `wk_brief.attach` draws every page with
  `PictureToGroup(..., seconds=PAGE_S)` where `PAGE_S = 600`. Pages 1–5 are
  replaced by the next page's `clearview` picture long before that expires;
  page 6 has no next page, so it rendered over the canopy for ten minutes while
  the pilot flew. The SPACE branch was correct throughout —
  `StopWaitUserResponse`, `StopPlayerSeatLock`, `SetFlag(F_DONE)` and
  `SetFlag(arm_flag)` all fired. The mission was running; only the display said
  otherwise.
- **There is no action that removes a picture.** Confirmed against the pydcs
  action list: `PictureToGroup` with `clearview=True` is the whole mechanism —
  the only way to stop showing something is to show something else. The last
  page's continue branch now draws an 8×8 fully transparent
  `wk_brief_clear.png` for 1 second with `clearview=True`, followed by
  `MessageToGroup(m.string(" "), 1, True)` to clear the text window.

### Added
- `scripts/build_wk_brief_pages.py::build_clear()` — writes the transparent
  `missiongen/data/wk_brief/wk_brief_clear.png`; `main()` reports it.
- `wk_brief.clear_path()`, included in `pages_ready()` and in the `missing`
  check, so a build without the blank refuses to claim a brief it cannot end.
- Three guards in `tests/test_wk_coach.py`:
  `test_the_last_page_takes_the_brief_off_the_screen` (read out of a built
  `.miz`: exactly one clearing picture, ≤3 s, plus a clearing message),
  `test_the_pages_before_the_last_are_replaced_by_the_next_one` (the fix for
  the last page must not become a fix for all of them — every earlier page must
  still outlast any plausible read), and
  `test_the_blank_page_ships_inside_the_mission` (a clear that references a
  file the archive does not carry clears nothing).
- Five mutations in `scripts/mutate_white_knights.sh`, all caught: drop the
  clearing picture; hold the blank for `PAGE_S`; drop `clearview` from the
  clearing message; register the blank as a copy of page one; shorten `PAGE_S`
  so mid-brief pages time out.

---

## [1.80.1] — The Library drawer's Briefing pack button was never wired

Rob: *"The briefing pack pdf doesn't download."*

### Fixed
- **A race, not a broken endpoint.** `/api/brief` was answering 200 the whole
  time — verified against the live site. `generateFromLib` wired the drawer's
  `#kit_brief` button inside `setTimeout(..., 1600)`, and `showKit`'s `lib`
  branch drew the markup and returned without wiring anything. Any mission
  taking longer than 1.6 s to generate left the button in the DOM with no
  handler. A White Knights ride takes ~3.3 s, so it failed on every mission
  that carries coaching cards, brief pages and diagrams.
- **`wireKitButtons()`** — one helper, called in the same statement that draws
  the Kit, in all three branches (`lib`, `quick`, builder). The timer now only
  restores the button's label.

### How it was confirmed
Driven in a real browser against both builds. Shipped: `{'exists': True,
'wired': False}`, zero network calls, no download. Fixed: `wired: True`, a
`POST /api/brief` 200, and `..._briefing_pack.zip` on disk.

### Tests
- `tests/test_mission_kit_wiring.py`: five static guards on the SHAPE that was
  violated — one wiring helper, every drawing branch wires it, and no Kit
  button is ever wired inside a `setTimeout`. Both mutations that recreate the
  original bug were run and both are caught.
- The browser test that actually proved it is deliberately not in the suite: it
  needs a live server, a browser and fifteen seconds per case. The static
  guards check the property; the browser checked the behaviour.

## [1.80.0] — Thin architecture: packs uploaded, not bundled

Rob: *"I should be able to add the packs separately. A thin architecture and
then upload the pack through the admin."*

Reverses the "bundled" decision recorded in `docs/content-architecture.md`
after exactly one release, and completes Phase 3.

### Changed
- **No content in the image or the release zip.** The Dockerfile builds no
  packs and copies none; `packs` is out of `package.sh`'s MANIFEST. The
  release zip is back to ~15 MB from 59 MB. The deciding argument was the
  coupling rather than the size: content welded into an image can only change
  by deploying, and a corrected premise line is not a deploy.
- **One storage tier.** `packs.BUNDLED_DIR` and the bundled reader are gone;
  every pack lives on the volume and arrives through `/admin`.
- **`server/packref.py`** now resolves a track to its INSTALLED pack by id.

### Removed
- **`_track_zip_path`** — the in-request syllabus builder. Eleven missions,
  eleven brief PDFs and a guide, assembled while the browser waited. Caching it
  covered 4 of 60 combinations; deleting it covers all 60.
- `/api/track/<id>/all.zip` now serves a published pack or answers **409** with
  a sentence pointing at the per-ride Generate buttons. Old query parameters
  are accepted and ignored so every share link still resolves.

### Added
- `tracks` in `/api/options` carries **`published`** and
  **`superseded_by_pack`**, so the UI can gate the whole-syllabus button on a
  pack existing and show one card per syllabus instead of two.
- `packs.all_zip()` — ONE implementation of "zip up a pack", used by both the
  pack route and the track route.

### Fixed
- **The pack bundle cache was keyed on whole-second mtimes.** An author who
  corrected his titles on the review screen within a second of the last
  download kept serving the old manifest. Now nanoseconds plus the file count.
  Same trap as the `.pyc` staleness the mutation harness hit.

### Tests
- `tests/test_pack_delivery.py` replaces `test_bundled_packs.py`, which
  replaced `test_prebuilt_tracks.py`. Three answers to one question; this is
  the one that deletes the build instead of hiding it.
- `test_the_in_request_syllabus_builder_is_gone` asserts the function name is
  absent from `server/app.py`, so the convenience cannot quietly return.
- The five AAR tests that described the deleted builder were **rewritten to the
  new contract**, not deleted: the wizard's promise is now proved through the
  ride a pilot actually downloads, reading the tanker's real type id (`A-6E` —
  the KA-6D is an A-6E airframe, so neither the roster key nor the label
  appears in the file, which is the mistake that test's own docstring warns
  about and which it caught me making).

## [1.79.0] — The pack format, and the producer

Rob: *"we need to have a standard package format with a manifest that can be
uploaded and then downloaded directly rather than having them built like the
generators do"* and *"I want to be able to put together a set of missions that
are historically accurate and then upload it to the admin and have the system
create a manifest file and populate it in the library."*

Architecture exploration in `docs/content-architecture.md`; the decision was
all four phases, bundled, independent content versioning, public format.

### Added — the format (Phase 1)
- **`docs/PACK_FORMAT.md`** — NORMATIVE. The code implements it; where they
  disagree the document is right. Public format, so the §3 compatibility rules
  are promises to strangers: unknown fields survive a round trip, a higher
  `format` fails with an actionable sentence, missing is never invalid, `x_` is
  reserved for third parties.
- **`missiongen/packfmt.py`** — the implementation, split from storage.
  `requires` (terrains + modules a pilot must own), per-file `sha256`, a
  zip-order-independent `digest`, `version` (content, not app), `built_with`
  (provenance), optional `signature`. Format 1 upgrades on read, in memory
  only.
- **44 tests** in `tests/test_pack_format.py`, one per normative rule.

### Added — the producer (Phase 2)
- **`scripts/build_pack.py`** — spec in, artifact out. `tracks.json` and
  `mission_templates.json` do not move: they were always specs, and only this
  script reads them now. `--check` rebuilds and compares digests.
- The four built-in syllabi ship as bundled `.sspack` artifacts (~44 MB),
  built in the Docker image and in the release zip.
- **`server/packref.py`** — one naming rule, imported by producer and server.

### Added — the authoring workflow
- **Upload → derive → review → publish.** `/admin` lands an upload on a review
  screen: title, content version, author, premise, role, threat, era, maps,
  required modules, and per-mission order/title/premise. Save writes the
  manifest and the card is live.
- **Download the manifest** so the author's folder becomes self-describing.
- **Shadow warning** when an uploaded pack shares an id with a bundled one,
  naming both content versions and saying which the Library will show.

### Removed
- `scripts/prebuild_tracks.py`, `server/paths.py`, `prebuilt/` and their
  mutation suite. The pack replaces the cache: not version-keyed to the app,
  because content is not a computation.

### Fixed
- A bare `except Exception` in the bundled-pack reader hid a missing `zipfile`
  import and turned four packs into zero. It now logs.

### Tests
- `tests/test_pack_format.py` (29) + `tests/test_bundled_packs.py` (26).
- The load-bearing guard is unchanged in spirit: `generate` is replaced with
  something that raises, so "the download built nothing" is an assertion and
  not a stopwatch.

## [1.78.1] — Pre-built track downloads

Rob: *"The new version doesn't generate and download the Bnai or Proud
Phantom."*

### The diagnosis
Individual missions generated fine, live, including both B'NAI rides. What
failed was `/api/track/<id>/all.zip` for BOTH pinned tracks: Fly returned
**502**, and `/api/health` went unreachable at that instant and then recovered
— the machine was being restarted mid-request. The build is ~31 s of saturated
CPU on a dev container (peak RSS 184 MB, so memory was probably not the binding
constraint) against a `shared-cpu-1x` whose health check allows 5 s every 30 s.

### Fixed
- **`scripts/prebuild_tracks.py`** — builds every pinned track's zip plus each
  wizard track's DEFAULT combination, at image build time. Derived from
  `tracks.json`, so a new track is covered the day it lands.
- **`server/paths.py`** — ONE naming rule, imported by both the builder and the
  endpoint. Version-keyed, so a release cannot serve last release's missions.
- **`server/app.py`** — `_track_zip_path` returns the pre-built file before
  doing anything else. 30 s -> 0.18 s, and no build work in the request.
- **`Dockerfile`** — runs the pre-build before dropping privileges. ~46 MB and
  ~90 s of image build, once, instead of minutes of CPU per download forever.
- The lazy build stays as the fallback for wizard combinations nobody
  pre-built. Not-pre-built means built-now, never 404.

### Not shipped in the package
`prebuilt/` is gitignored and absent from `MANIFEST` in `package.sh`. 46 MB a
release of derived binaries in git is how a repository becomes a download, and
a local run has a real CPU.

### Tests
- `tests/test_prebuilt_tracks.py`: 12 tests. The load-bearing one replaces
  `generate` with something that raises, so "the request built nothing" is an
  assertion rather than a stopwatch.
- `test_two_tracks_can_never_share_a_filename` — both White Knights tracks are
  Cold War F-4E with no tanker, so every field but the id matches; dropping the
  id would make Proud Phantom serve the Checkout's missions in a download that
  opens perfectly and is the wrong syllabus.
- The Dockerfile guard reads LIVE LINES ONLY. A substring check passes on a
  commented-out build step, which is exactly how this gets disabled and
  forgotten.
- `scripts/mutate_prebuilt.sh`: 11 mutations, 0 weak. Every one of them is
  silent in production — this feature has no failure mode that raises.

## [1.78.0] — The spoken brief, and the hold

Rob: *"Lets have a voice over that gives a brief of the mission and the mission
is at active pause until they finish reading."*

### The constraint, stated first
**No Mission Editor action can press active pause.** It is a client keybind and
no Lua goes in our `.miz`. What DCS does give us is what ED's own training
missions are built from, and it delivers the actual requirement:
`START WAIT USER RESPONSE` (SPACE forward, BACKSPACE back) and
`START PLAYER SEAT LOCK`. The pilot is held; the world is not. The kneeboard
says which is which.

### Added
- **`missiongen/wk_brief.py`** — six pages, wired as a wait-response chain.
  One `StartPlayerSeatLock` before page one; one `StopPlayerSeatLock` on the
  last page, in the same trigger that sets `wk_coach.F_ARM`. Flag block
  8900-8939.
- **`scripts/build_wk_brief_pages.py`** — the page artwork. Wider crops of the
  squadron's drawing than the cue cards use, because a page read sitting still
  must not clip "TRACK POINT" to "OINT". Three illustrated pages, three type.
- **`wk_coach.attach(armed_externally=)`** — the coaching no longer arms on a
  timer when a brief owns the release.
- The recording sheet is now two parts, brief and cues, with different
  direction and a length rule that scopes itself to the cues.

### Fixed
- **A FLAG COLLISION THAT SHIPPED IN 1.77.0.** `wk_coach.F_ARM` was 8890 and
  the phase block is `F_PHASE + i`; with thirteen phases, phase 10
  (`twos_pass`) WAS the arm flag. The cover-two cue re-armed the sequence, and
  the re-attack's clear-everything loop disarmed the coaching — so the second
  run worked exactly once. `F_ARM` moved to 8899 with `F_PHASE_MAX = 16`, and
  `test_the_flag_blocks_do_not_overlap` asserts the arithmetic across both
  modules rather than trusting anyone to remember it.

### Design notes
- **The brief restates no number.** Page text formats live values out of
  `wk.DELIVERIES` and `wk.ATTACKS`, and a test asserts the formatted values
  appear — which is only true while it is reading them rather than reciting
  them.
- **Every branch closes the wait and clears BOTH flag blocks.** The forum
  thread on this action documents the footgun: taking the BACK branch leaves
  the CONTINUE flag live and one page later two branches fire at once.
- **BACKSPACE on page one re-shows page one** rather than doing nothing. A key
  that appears to be ignored reads as a broken mission.

### Also fixed — a hole under the freshness system
- **`scripts/build_wk_coach_cards.py` had been dead for a release.** It
  unpacked `PHASES` as a fixed-width 4-tuple; v1.77.0 gave the table a fifth
  field for the prerequisite and the generator started dying with a
  `ValueError`. The committed cards were still correct only because nothing
  had changed their words yet.
- **`release.sh` swallowed it.** Every regeneration line read
  `cmd >/dev/null && ok "label"`, and `set -e` does not fire for a command on
  the LEFT of `&&` — so the traceback printed, the tick was skipped, the
  release carried on, and `artifacts.restamp()` then recorded the current
  input hashes anyway. A stale file certified as fresh, permanently. Every
  generator now runs through a `gen` helper that calls `bad` on a non-zero
  exit.
- **`test_every_registered_generator_runs_and_is_deterministic`** executes each
  cheap registered generator for real, asserts exit 0, and asserts the output
  is byte-identical to what is committed — so a broken generator fails the
  suite rather than the next person's mission.

### Tests
- `tests/test_wk_coach.py`: 62 tests, 15 of them new for the brief — seat lock
  counted out of the built `.miz` (locked once, freed once, on the named
  trigger), the wait pairs, the clear-both-blocks rule, and the honesty
  paragraph about active pause.
- `test_no_action_in_the_product_claims_to_pause_the_simulation` fails if pydcs
  ever gains a real pause action, which is the right outcome either way.
- `scripts/mutate_white_knights.sh`: 77 mutations, 0 weak.

## [1.77.0] — The coached B'NAI

Rob: *"at each waypoint the pilot gets a visual cue and at the same time
jester tells them to turn a direction, pop or whatever they need... and repeat
this after egress."*

### Added
- **`missiongen/wk_coach.py`** — a 13-phase cue sequence for the B'NAI, wired
  as edge-triggered Mission Editor rules. Each phase draws a `PictureToGroup`
  card, prints its own directive and call, sets its flag and disarms itself.
  No Lua. Flag block 8880-8899.
- **`pp_8_bnai_coach`** at position 8, pushing the un-coached check ride to 9
  and the two splits to 10 and 11. Proud Phantom is 11 rides. The two B'NAI
  rides fly the same attack from the same document and differ in exactly one
  respect: whether anything talks to you.
- **`scripts/build_wk_coach_cards.py`** — composites 13 cards from the
  squadron's own B'NAI page: panel crop, one red "you are here" ring in
  SOURCE coordinates, directive burned large, call underneath. One card per
  PHASE rather than per ring position — four positions are shared by two
  phases, and sharing the card would print "TRACK" where the pilot must
  pickle.
- **`wk_route._bnai_coached()`** — the coached leg table approaches the IP 83
  degrees off the run-in axis, because the guide says "approach the IP at
  nearly 90 degrees angle off" and a cue saying *turn inbound* while the route
  runs dead straight through the IP is a cue arguing with its own flight plan.
  PULL-UP is a real waypoint at the sheet's 11,400 ft.
- **`wk_route.leg_positions()`** — one function for "where is that leg",
  called by both the waypoints and the cue zones, so they cannot drift.
- **`wk.ATTACKS["bnai"]`** gains the drawing's own annotations: `pop_stages`
  (PUP → ROLL-IN → APEX → TRACK POINT), `climb_deg_lead` 30,
  `climb_deg_two` 45, `tas_kt` 540.
- **The voice slot.** `SoundToGroup` — a cockpit sound, not a radio
  transmission — emitted per phase only when that phase's WAV exists.
  `docs/WK_BNAI_VOICEOVER.md` is GENERATED from `wk_coach.PHASES` by
  `scripts/build_wk_voiceover_sheet.py`, so the sheet cannot ask for a
  filename the mission does not look for.

### Design notes
- **`prereq` is not "the previous phase".** PULLOUT hangs off TRACK, not off
  RELEASE. A shallow pop never descends through the release altitude, so
  chaining the pullout behind the release would let one bad pass cost the
  pilot every remaining pass — and the second run is the ride.
- **The re-arm hands back the stages before `RESET_TO`**, so the second pass
  begins at the IP, which is where the re-attack cue just sent him.
- **The diagram's "4.5 NM" is not the pull-up distance.** The guide's
  split-attack section uses the same figure for where mutual support ends. The
  cue fires on the delivery sheet's 11,400 ft and the card prints both numbers
  and says which governs.

### Tests
- `tests/test_wk_coach.py`: 47 tests. Zones read back out of the built `.miz`
  and compared against the WAYPOINTS in the file — not against a second call
  to the function that placed them.
- **Three guards were WEAK on first write and were rewritten rather than
  kept.** The recording-sheet check used a bare substring, and renaming
  `wk_bnai_lowlevel.wav` to `lowlevel.wav` leaves the new name a substring of
  the old. The ring-position check asserted only "lands on ink", and the page
  has a paragraph of body text beside the geometry — so the four pop stages
  are now checked as a shape: up the page in the drawing's own order, in one
  narrow column. The third mutation was re-aimed: removing `attach`'s own
  ride guard is a no-op because the leg-table check catches it anyway, so it
  now aims at the route, where the check ride could genuinely acquire the
  coached approach.
- `scripts/mutate_white_knights.sh`: 65 mutations, 0 weak.

## [1.76.4] — The counterpart, and the stores

Two defects Rob found by flying Proud Phantom: *"no ai aircraft and no
air to ground munitions."* Both were worse than reported.

### Fixed
- **No ride had an AI counterpart.** Not Proud Phantom — all twenty-one. Every
  card printed `WINGMAN_NOTE` ("he is a SEPARATE FLIGHT flying a scripted
  route") and every built `.miz` contained one aeroplane. The note was written
  before the thing it described existed: the say/do gap, in our own product,
  in the feature whose whole point is that the brief and the file agree.
- **Every ride carried the air-to-air fit** — 4x AIM-7M, 3x AIM-9P5, tank —
  because `mission_kind` was never set on the White Knights recipes, so
  `loadouts.apply_fit` chose a sweep fit for a card that says pickle six
  Mk-82s.

### Added
- **`wk_route.counterpart_legs()` / `apply_counterpart()`** — REX 2 as a
  SEPARATE GROUP, not a flight member. Aircraft inside your group are wingmen
  under the F-key structure and DCS treats the group as player-led whichever
  slot you occupy; a separate group is the only shape in which the squadron's
  own two-ship procedures mean anything. He flies the player's legs, offset by
  the briefed number: the mid-point of `LINE_ABREAST_NM` on the low-level
  rides, half the B'NAI's own `trail_nm` in trail on the B'NAI, 7 nm lateral
  on the splits, 10 nm on the working-area rides.
- **`wk.loadout_for()` / `loadout_lines()`** — the sheet's ordnance on the
  pylons and a STORES block on the card, from one function. 6x MK-82LD on a
  MER for the low-drag sheets; 2x Snakeye on TERs at stations 3 and 11 for the
  high-drag sheet. Air-to-air is period-correct: AIM-7E-2 and AIM-9J, not the
  AIM-7M/9P5 the generic fit was applying. The counterpart inherits the
  player's pylons rather than deriving them a second time.
- **`wk.has_counterpart()`** — one predicate behind both the printed promise
  and the aeroplane, so a hand-kept list of "who has a wingman" cannot come
  back.

### Tests
- `test_the_counterpart_the_card_promises_is_actually_in_the_mission` reads the
  group count and waypoints back out of every built `.miz`.
- `test_the_stores_on_the_card_are_the_stores_on_the_pylons`,
  `test_the_high_drag_sheet_gets_snakeyes_and_the_rest_get_low_drag`,
  `test_a_ride_that_drops_something_carries_something_to_drop`,
  `test_the_air_to_air_fit_is_period_correct`.
- **A weak guard, rewritten rather than kept.**
  `test_the_promise_and_the_aeroplane_come_from_one_function` compared the
  card's promise against `wk.has_counterpart` — the same function
  `brief_lines` calls to decide whether to print it. Replacing the predicate
  with a hand-kept list moved BOTH sides and the suite stayed green. It now
  compares the printed promise against `wk_route.counterpart_legs`: the
  promise, the predicate and the flight plan are three independent things.
- `tests/test_wk.py`: 302 tests. `scripts/mutate_white_knights.sh`: 51
  mutations, 0 weak.

## [1.76.3] — The squadron's attack diagrams on the kneeboard

### Added
- **`missiongen/data/wk/*.png`** — the five attack diagrams from Conventional
  Tactics, extracted by `scripts/build_wk_diagrams.py` (committed, because the
  source PDF is a personal copy and is not in the repo).
- **`kneeboard.page_image()`** — a framed page carrying one picture, fitted
  inside the body and NEVER scaled up.
- **`wk.DIAGRAMS` / `diagram_path()` / `diagram_note()`** — path lookup that
  returns None rather than raising, so a missing asset costs a picture and not
  a mission; and the provenance line that rides with the picture.
- Diagrams in the printed guide (PDF and markdown) after each attack's card.

### Fixed
- **The punch-hole filter ate the type.** Removing binder holes by fill ratio
  alone destroyed bold sans capitals — "DOUBLE 90" rendered "OU LE O",
  "TRACK POINT" as "TR CK POINT". Recalibrated against measured blob sizes
  (holes 54-62 x 75-77 px, type 13-19 x 12-23 px at 200 dpi), with position
  required as well.

### Tests
- Two guards in this batch were WEAK on first write and were rewritten rather
  than kept: page count is now exact instead of sniffing ink density, and the
  no-enlarge rule is exercised with a small synthetic source, because the real
  scans are height-constrained and never trip it.
- `tests/test_wk.py`: 258 tests. `scripts/mutate_white_knights.sh`: 41
  mutations, 0 weak.

## [1.76.2] — Both halves of the split attack

### Added
- **`pp_9_splithigh`** — Split Attack, Low/High (Conventional Tactics II).
  Proud Phantom is now ten rides and all five `wk.ATTACKS` geometries are
  flown. Teaching order: echelon, double 90, B'NAI, split low/high, split
  low/low — easiest position to hold, hardest last, ranked by the guide's own
  disadvantage lists.
- `deliveries` on `pp_5_divetoss` — the ride flies BOTH dive-toss sheets, and
  `_b_divetoss` now reads the pair off the ride instead of naming it a second
  time inside the brief.
- **Coverage guards.** `test_every_attack_in_the_guide_has_a_ride` and
  `test_every_delivery_sheet_has_a_ride` assert the syllabus covers the
  source. Neither existed, which is why a reader found the gap before the
  suite did. Plus `test_both_halves_of_the_split_are_taught_and_in_the_right_order`.

### Note
- `pp_9_split` now sits at position **10** while keeping its key. It shipped in
  v1.76.0 as ride 9, so the key is in share links; renaming it to match its
  position would be tidier and would break them. Position comes from `n`.

### Tests
- `tests/test_wk.py`: 245 tests. `scripts/mutate_white_knights.sh`: 36
  mutations, 0 weak.

## [1.76.1] — White Knights: flight plans, kneeboard cards, callsign, livery

### Added
- **`missiongen/wk_route.py`** — per-ride flight plans. Low-level routes at
  `wk.floor_ft(map)` and `MIN_IAS_KT` with 90-degree turn points; range
  patterns whose IP sits at the delivery sheet's own `pup_ft`; attack routes
  splitting at `ATTACKS[k]["support_nm"]`; intercept working areas using the
  Standards outbound leg (2 min at 350 KIAS). `wk_3_cqt` returns no legs by
  design and the card explains the omission.
- **`kneeboard.pages_text()`** — paginates a generated card onto kneeboard
  pages. Headings, wrapped prose, and columnar lines drawn in mono unwrapped.
- **`wk.LIVERY` / `wk.livery_lines()`** — the SEA scheme with FS numbers, the
  tail band, serial presentation and stencil convention, the two 1980
  airframes, an explicit unverified list, and the admission that no 70 TFS
  livery exists for the DCS F-4E.
- `callsign: REX` on all twenty cards — per card, not in `callsigns.json`,
  because REX belongs to the 70th and not to every F-4E in the product.

### Fixed
- **Kneeboard text ran off the right edge.** Any indented line was drawn in
  mono unwrapped, so a numbered contract rule was clipped mid-sentence — which
  on a kneeboard means the pilot reads half a rule and believes it. Indented
  PROSE now wraps with a hanging indent; only lines with a real column gap
  (a run of 3+ spaces) stay unwrapped. The pad allowance is measured with
  `textlength` rather than guessed at 12 px, and a test asserts no ink in the
  right margin of any rendered page.
- `_wk_ride` was resolved below the routing block that needed it, and the
  kneeboard card was written into `self.kb_ctx` before that dict was built.
  Both hoisted/stashed.

### Tests
- `tests/test_wk.py`: 233 tests. `scripts/mutate_white_knights.sh`: 33
  mutations, 0 weak. Three mutations in this batch were no-ops on first aim
  and were re-aimed rather than discarded.

## [1.76.0] — The White Knights: two tracks from a 1980 squadron's documents

### Added
- **`missiongen/wk.py`** — the 70 TFS data module. Comm card, ground-ops
  timings, tactical split, overhead, landing, combat quick turn, tanker
  rendezvous, intercept setups, the twenty-rule low-level contract, comm-out
  turn geometry, ridge crossing, threat reactions, route abort, sixteen WIS
  No. 1 BFM calls plus seven inter-flight calls, five delivery planning sheets
  and four attack geometries. Every value transcribed, none rounded.
- **`wk.LOW_LEVEL_FLOOR_FT`** — per-theatre low-level floor with its basis
  (`squadron` | `host_nation`). Unlisted maps fail CLOSED to the most
  restrictive known floor: for a minimum altitude, failing closed is the
  higher number.
- **20 mission templates and 2 tracks** — `wk_checkout` (11 rides, Germany
  default + Sinai, Route Abort Germany-only) and `wk_proud_phantom` (9 rides,
  Sinai pinned). Generated idempotently by `scripts/add_white_knights.py`.
- **`by_map` in `mission_templates.json`** — the twin of `by_era`, applied
  after it. A `by_map` block cannot change `map`; honouring that would make
  the override a teleport.
- **`templates.maps_for()`** and **`tracks.summary()['configurable']`** — a
  track pinned to one airframe now says so instead of shipping an empty
  wizard the Library renders as a broken control.
- **`missiongen/wk_guide.py`** — printed syllabus (PDF + markdown) for tracks
  with no refuelling lane. `/api/track/<id>/guide.pdf` and `all.zip` route to
  it; previously a non-lane track would have 404'd on a committed default that
  does not exist and 400'd on a tanker it never had.
- `tests/test_wk.py` (181 tests) and `scripts/mutate_white_knights.sh`
  (22 mutations, 0 weak).

### Fixed
- **The BFM ride shipped the wrong card.** `wk_11_bfm` sets `bb_bfm`, and the
  generic BFM standards block ran before the White Knights branch — so a card
  advertising WIS No. 1's sixteen directive calls produced something else. The
  branch is now first in the chain.
- **Mutation harnesses could silently skip a same-size mutation.** CPython
  invalidates a `.pyc` on (mtime, size); a mutation changing `11400` to
  `11500` leaves the size identical, and rewriting within the same clock
  second as the cached `.pyc` served STALE bytecode — the harness reported
  WEAK for a guard that was never challenged. All three scripts now purge
  `__pycache__` before mutating and run with `PYTHONDONTWRITEBYTECODE=1`.
  `mutate_aar_academy.sh` re-verified at 45/0, `mutate_aar_hud.sh` at 14/0.
- **`tests/test_aar_academy.py` and `test_aar_wizard.py` assumed every track
  was a refuelling lane.** Scoped by `lane` rather than id prefix, with a
  guard that the filter is actually filtering something.

## [1.75.4] — Terrain floor for AAR tracks

### Fixed
- **AAR track altitude ignored terrain.** `aar.TANKERS[*]["alt_ft"]` was flown
  verbatim: 15,000 ft for the KC-130 and KA-6D, 12,000 for the S-3B, with the
  pre-contact air start a further 305 m below. Mount Elbrus (18,510 ft) is on
  Caucasus. Track altitude is now
  `min(max(book_alt, terrain_floor_ft(map)), max_alt_ft)`, where
  `terrain_floor_ft` is the map's highest ground + `TERRAIN_CLEARANCE_FT`
  (3,000) rounded up to the next 1,000 ft.
- **Printed guides quoted the book altitude, not the flown track.** Both the
  reportlab and the markdown builder — the near-identical twins that already
  produced one divergence this cycle. `test_the_printed_guide_prints_the_
  altitude_the_mission_flies` extracts the PDF text with `pypdf` and asserts
  the flown figure is present and the book figure is not used as the track.
- **`test_an_aar_card_puts_the_tanker_where_it_says` and
  `test_the_tanker_actually_flies_the_speed_the_card_prints` pinned stale
  values** — the tanker's own `alt_ft`, and a TAS computed at that altitude.
  Both now derive from `aar.track_alt_ft`/`track_speed_kmh` with the recipe's
  map, so a terrain-raised track is compared against what it actually flies.

### Added
- `aar.TERRAIN_MAX_FT` — highest ground per map, each row tagged `"cited"`
  (Elbrus 5,642 m, Noshaq 7,492 m) or `"ours"` (conservative estimate).
- `aar.TERRAIN_CLEARANCE_FT`, `TERRAIN_MAX_DEFAULT_FT`, `terrain_floor_ft()`,
  `track_alt_ft()`, `clears_terrain()`. Unknown maps fail closed to the worst
  known map.
- `max_alt_ft` on every tanker. `tankers_for()` and `choose()` take `map_key`
  and drop tankers that cannot reach the floor; `tankers_excluded_by_era()`
  takes `map_key` and returns a terrain reason for them, which the wizard and
  both guides render.
- `WHY THE TRACK IS HIGH` block on the kneeboard card and a matching paragraph
  in both guides, shown only when terrain actually raised the track.
- `docs/SOURCES.md` §2 entry for the terrain table.
- 10 further mutations in `scripts/mutate_aar_academy.sh` (45 total, 0 weak).

## [1.75.3] — 2026-08-17 — Cockpit round three: the store, the start, the speed

### Fixed
- **The KA-6D shipped with `["pylons"] = {}`.** The A-6E is the only tanker in
  `TANKERS` whose refuelling system is a pylon store; every other has one built
  in, and `refuel_flight` fits nothing. New `TANKERS[k]["store"]` declaration
  plus `support_air._fit_refuelling_store()`. **A tanker that cannot give fuel
  is the purest form of the say/do gap this product exists to avoid.**
- **The pre-contact air start was not behind the tanker.** Measured:
  relative bearing 311° from the tanker's route heading (astern is 180°), and
  the player's own heading 131° off the tanker's track. Two causes:
  `_air_start_astern_tanker` read `unit.heading` before pydcs assigned it
  (0.0), and **`psi` — the field DCS orients a spawned aircraft on — is only
  synced from `heading` when a group has more than one waypoint**
  (`unitgroup.py: if len(self.points) > 1`); an air start leaves exactly one.
  New `_tanker_track_heading()` derives from waypoint 0 → 1, and `psi` is set
  explicitly. `aar_hud.attach_gates()` had the same heading bug.
- **KA-6D 270 → 290 KIAS (max 310); F-14 band floor 250 → 270.** Reported
  twice as "still slow for the F-14 to line up with it". A floor below where
  the aeroplane is comfortable silences the shortfall warning exactly when it
  should speak; a Tomcat behind a Hercules is now flagged at 35 kt short.
- **The guide printed two speeds** — the tanker's nominal and the flown,
  receiver-clamped figure. Only the flown number now.

### Notes
- The first store guard was **vacuous**: it asserted the declaration and the
  pydcs pylon, both true while the mission still shipped empty pylons. The
  mutation caught it. Replaced with one that reads the generated `.miz`, plus
  its negative twin (a KC-135 must NOT carry an A-6 pod).
- New per-combination guard: the guide's `TRACK: n KIAS` must equal
  `aar.track_ias_kt()` for every combination the wizard offers, and must equal
  the tanker's route speed in the generated mission.
- 35 Academy mutations + 14 indicator mutations, all caught, zero weak.

---

## [1.75.2] — 2026-08-17 — Era rule, and the guide carries every card

### Fixed
- **Era availability was a hand-applied judgement, applied inconsistently.**
  The S-3B (service ends 2009) was offered in `modern` (2000-2030); the KA-6D
  (service ends 1997) was not, and nothing in the data explained the
  difference. Every tanker now carries a `service` window and
  `aar.period_note(tanker, era)` derives the caveat from it. A tanker whose
  service only partly covers an era is **offered with a label**, not hidden —
  hiding it costs a usable DCS asset for a bucket boundary. `ka6d` gains
  `modern`; the note explains the 1985-2000 gap between our era windows.
- **`aar.tankers_excluded_by_era()`** derives its reason from the service
  window too, so an absence cannot be explained in prose that disagrees with
  the rule beside it. The hand-written `retired` strings are gone.
- **The printed guide was missing the indicator card and every image.** Two
  new pages: the eleven indicator states at full size (rendered from the SAME
  PNGs the mission carries, via `aar_guide._hud_sheet()` — a separately drawn
  legend drifts within one release), and the indicator's kneeboard card. Plus
  a tanker page giving the receiver-clamped track speed, any shortfall, and
  the tankers not offered with reasons.
- **The wizard shows what it did not offer.** `tracks.excluded()` and
  `tracks.period_notes()` reach `/api/options`; the track card renders both
  under the tanker row.
- **`s3b` gains `gwot`** — the Vikings tanked until 2009, well inside a
  2003-2020 window.

- **A reportlab call landed inside the markdown builder**, so
  `/api/track/<id>/all.zip` returned 500 for every customised download. The
  PDF and markdown guide builders are near-identical twins and an edit meant
  for one has now landed in the other three times this session. Caught by the
  release suite. New guard renders EVERY wizard combination through both
  builders, and a mutation proves it.

### Notes
- `mutate_aar_academy.sh` gains `run_guide()`, which regenerates the printed
  guides either side of a mutation. Without it a guide mutation tests against
  stale documents and reports "caught" for the wrong reason. PDFs are now in
  the snapshot list and the content baseline.
- 29 Academy mutations + 14 indicator mutations, all caught, zero weak.

---

## [1.75.1] — 2026-08-17 — Cockpit fixes: tanker speed, indicator placement

All four from flying it.

### Fixed
- **Track speed was a property of the TANKER alone**, so a KC-130 flew one
  speed regardless of who joined. New `aar.RECEIVER_IAS` gives every receiver a
  comfortable band; `aar.track_ias_kt(tanker, receiver)` is the tanker's
  operating point clamped into that band and then by the tanker's own
  `max_ias_kt`. Consequences: drogue tankers raised (kc135mprs 250→280,
  kc130 210→230 and 12k→15k ft, ka6d 250→270, s3b 230→250, il78 250→280);
  a KC-135 **slows to 220** for an A-10; and `aar.shortfall_kt()` reports a
  pairing that cannot reach the receiver's floor, which the card prints as
  "THIS TANKER CANNOT FLY YOUR SPEED … That is the aeroplane, not you."
- **`choose()` now prefers a tanker that can fly the receiver's speed**, ahead
  of every other criterion, and deprioritises carrier-organic tankers ashore —
  a land-based Hornet was getting an S-3B because the sort ran on altitude.
- **`receiver_id` is threaded through** `add_tanker`, the pre-contact air
  start, `aar_grade` and `aar_hud`. Previously the tanker could fly one speed
  while the brief, the grader and the indicator quoted another.
- **Indicator placement**: bottom-centre → **left, vertically centred**. Under
  the nose it competes with the sight picture; the left edge at eye level is
  where the glance already goes.
- **Indicator size**: 22% → **10%** of window, and the art is redrawn for it
  (200×360 portrait: ball between datum bars, one chevron, one word). The old
  420×300 prose card is unreadable at that scale.
- **Indicator flicker**: firing only on a state change is not the same as
  firing rarely. New `MIN_REDRAW_S = 4` with an `F_DRAWN` clock gated by
  `TimeSinceFlag`; clear-then-set restarts it, and a test pins that order
  because set-only would lock the indicator out after its first draw.

### Notes
- `RECEIVER_IAS` is **ours**, like the tanker table — operating points chosen
  so the receiver is neither on the back of the drag curve nor out of control
  authority. The Hornet's floor is 230, not 250: it tanks off a Hercules
  routinely, and a warning on the most ordinary pairing in the Navy is how a
  real caveat gets ignored.
- A mutation anchor went stale twice while editing this release, and once a
  `str.replace` in a test edit silently did not apply. Both are the reason
  `mut` asserts before mutating; the same discipline now applies to test edits.

---

## [1.75.0] — 2026-08-17 — The AAR Academy is configurable

### Added (position indicator)
- **`missiongen/aar_hud.py`** — eleven-state graphic driven by `PictureToGroup`,
  a native ME action (PNG from mission resources, aligned + sized as a percent
  of the window). Bottom-centre at 22%. Two axes: fore/aft from the speed delta
  against the tanker's track speed, high/low from `UnitAltitudeHigher/Lower`.
  **No lateral axis** — the envelope check is a sphere and cannot tell abeam
  from astern; drawing one would be invented, and a test enforces the card
  saying so. Bands are TIGHTER than the grader's (5 kt vs 10) because guidance
  may lead where a verdict may not.
- **Edge-triggered refresh.** One ARM flag per state (8840–8850); entering a
  state draws, disarms itself and re-arms the others. No timer, no strobe.
- **F10 toggle** (`F_HUD_OFF` 8855) and **absent on the `quiet` profile** —
  the qualification and night rides are silent evaluation by design.
- **`aar_hud.attach_gates()`** — DCS helper gates on the Rendezvous ride only,
  three gates back along the tanker's track, stepped down.
- **`scripts/build_aar_hud.py`** builds the eleven PNGs deterministically
  (48 KB total, 8-bit palette). **`tests/test_aar_hud.py`** — 37 guards.
  **`scripts/mutate_aar_hud.sh`** — 9 mutations, all caught, zero weak.

### Changed (position indicator)
- **`aar_grade.attach(..., hud=True)` drops its two CONTINUOUS text cues** when
  the indicator attaches. The excursion COUNTER still runs — that is
  bookkeeping the debrief needs — but the corner stays quiet. The three
  discrete calls (opening, 15 s gate, 60 s standard) survive either way.

### Fixed (position indicator)
- **The mission built and would not have OPENED.** `PictureToGroup` was handed
  `HorzAlignment.Center` (the Enum member) rather than `.value`; pydcs writes
  whatever it is given straight into the Lua table, so the mission contained
  `a_out_picture_g(..., HorzAlignment.Center, ...)` — an undefined variable DCS
  refuses to compile. Every stat was correct and the art was in the zip.
  Two suites that re-read the generated `.miz` caught it; a suite that only
  generates never would. There is now an explicit `load_file()` guard, because
  **generating a file proves nothing about whether it loads.**

### Notes (position indicator)
- **Not otherwise verified in-sim.** The `.miz` demonstrably carries the art and the
  actions; how DCS renders a picture at that size and alignment, whether
  `clearview` replaces rather than stacks, and how it reads in VR all need the
  PC. Same for the helper gates' coordinate convention.
- A mutation block appended to `mutate_aar_academy.sh` silently never ran: a
  snippet containing triple-quoted Python cannot nest inside that script's
  heredocs, and the quoting collapsed. Split into its own file, whose `mut`
  helper **fails loudly if a substitution does not apply** — a mutation suite
  reporting "all caught" while skipping cases is worse than none.

### Added
- **Track wizard.** `tracks.picker(track_id)` returns the full decision tree
  `{era: {roster_key: [tanker_key, ...]}}`, filtered so only combinations that
  build appear: bounded by the track map's own era presets, then by lane
  (boom/probe), then by aircraft service window, then by tanker era. Computed
  in the engine, not the browser — a second copy of those rules in JavaScript
  would drift. `tracks.resolve_choice()` validates a selection and raises
  `ValueError` with a message written for the pilot.
- **`GET /api/track/{id}/all.zip?era=&aircraft=&tanker=`** and the same query
  on `guide.pdf`. Omitting the query keeps the previous behaviour, so old
  links still work. Cache key now includes the selection — keying it on the
  track alone would serve a Hornet syllabus to somebody who asked for a
  Tomcat.
- **`tankers` in `/api/options`** (label, boom, IAS, altitude, callsign) so
  the wizard can name what it offers instead of printing `kc135mprs`.
- **`aar.lane_of()`, `aar.receivers_for()`, `aar.tankers_for()`** — the three
  queries the wizard needs, in the module that owns the rules.
- **`tests/test_aar_wizard.py`** — 158 guards. Mutation script now runs 25
  mutations, all caught, zero weak.

### Changed
- **`NO_AAR` (deny-list) → `AAR_RECEIVERS` (allow-list), failing closed.**
  See Fixed. `BOOM_RECEIVERS` is now derived from it and kept for existing
  call sites.
- **`missiongen/aar_guide.py`** (was `scripts/build_aar_guides.py`) builds the
  guide for a chosen era/aircraft/tanker. **reportlab is a RUNTIME dependency
  now** — a committed guide cannot describe an aeroplane the pilot chose at
  download time. `scripts/build_aar_guides.py` remains as a thin wrapper that
  regenerates the committed defaults.
- **Every Academy ride advertises `coldwar` and `modern`** with per-era
  defaults (`F_4E_45MC`/`kc135` and `F_14A_135_GR`/`kc130` in the Cold War) and
  `aircraft_choices` per era, so an individual ride opened from the Library
  offers the same set the wizard does. `gwot` is deliberately absent: Caucasus
  has no War-on-Terror preset and the Academy's promise is that the only thing
  you must own is the receiver.
- Guide covers name the designation *and* the popular name — three Tomcat
  variants can fly the probe lane and they are not the same aeroplane.

### Fixed
- **`can_refuel()` failed open for most of the roster.** `NO_AAR` held DCS type
  ids that had drifted: `P-51D` vs `P-51D-30-NA`, `SpitfireLFMkIX` vs
  `SpitfireLFMkIXCW`, `MiG-15bis` vs `MiG-15bis_FC`, `F-86F Sabre` vs
  `F-86F_FC`, `L-39C` vs `L-39ZA`, `C-101EB` vs `C-101CC`. Warbirds were saved
  only by era gating (no tanker exists in their eras); **in Cold War and modern
  an F-5E, a Gazelle, a Hind, a Huey or a Ka-50 would get a KC-130 on station
  and the full AAR procedure card.**
- **The F-14B(U) resolved to three different strings** — roster key
  `F_14B_U`, display label `F-14B(U)`, DCS type id `F-14BU` — and only the type
  id reaches `can_refuel`. The allow-list was keyed on the label and
  `tracks._flyable_keyed()` mapped to the label, so the wizard offered the
  Tomcat and the engine built eleven tanker-less missions. Both now use
  `provisional_id`, and a test pins every pending module to it.
- **Widening the shipped cards' eras replaced `aar_boat`'s S-3B Viking with a
  KC-130** in the modern era. That card is the carrier-organic one — the air
  wing's own tanker is the point of it. The merge now widens only eras the
  card did not already advertise.

### Notes
- The allow-list is **ours**. No published table maps DCS modules to refuelling
  systems; ED's scripting docs define the two system types and stop. Additions
  are one line each and should be made on a pilot's report rather than argued
  with.

---

## [1.74.0] — 2026-08-16 — The AAR Academy: two graded lane tracks

### Added
- **`missiongen/aar_grade.py`** — in-mission AAR coaching and grading built
  entirely from Mission Editor triggers. No Lua, no script inside the `.miz`.
  Measures presence in a 150 m envelope around the tanker unit
  (`UnitInMovingZone`), speed within ±10 kt of the track speed, dwell via
  `TimeSinceFlag`, and excursions via a counter. Four profiles (`station`,
  `closure`, `contact`, `quiet`) change the opening call and whether the
  closure warning attaches; **tolerances never vary between rides**, because a
  standard that moves is not a standard. Edge-triggered through flags in block
  8810–8839 so a continuous trigger calls once per transition rather than once
  a second. Closure coaching fades after 3 calls. Three F10 menu items give
  self-requested feedback. Scoring is suppressed for the first 20 s as a VR
  recentre/seat-height window. Never raises: a pydcs drift degrades the card to
  an ungraded one via `warnings`, matching `formation._coach`'s contract.
- **`missiongen/tracks.py` + `missiongen/data/tracks.json`** — training tracks:
  ordered sets of generated cards that travel together. Distinct from
  `packs.py`, which serves curated static `.miz` uploads on the Fly volume;
  tracks ship with the code and need no volume, upload or `ADMIN_PASSWORD`.
  Ordering lives on the cards (`track: {id, n}`), so a card cannot be in a
  track without knowing it. Duplicate ride numbers raise rather than resolve
  quietly.
- **17 new Library cards** across two lanes, numbered to the Academy plan's own
  0–9 syllabus plus a ride-10 extra: Orientation and Control Check, Formation
  on the Tanker, Closure Control, First Contact, Sustained Contact, Disconnect
  Recovery and Reset, Refuelling Through the Turn, Rendezvous, Qualification
  Check Ride, Operational Transfer.
- **`GET /api/track/{id}/all.zip`** — builds every ride plus its brief PDF and
  the lane guide into one download, cached per version (7.8 s cold, then
  served from disk). Fixed per-ride seeds (`4400 + n`) so a printed syllabus
  stays true for the next person who downloads it.
- **`GET /api/track/{id}/guide.pdf`** — the printed lane guide, path-resolved
  inside `docs/` and refusing anything that escapes it.
- **`tracks` in `/api/options`**, and `track` on each template, so the Library
  can keep a track's rides out of the loose grid.
- **`scripts/build_aar_guides.py`** — generates the two printed lane guides
  (PDF + Markdown) from `aar.brief_lines`, `aar_grade.brief_lines` and each
  card's own brief, so a printed syllabus cannot drift from the missions.
  Build-time only; reportlab stays out of `requirements.txt`.
- **`--accent-on2`** design token: the accent at 5.44:1 (light) / 6.12:1 (dark)
  against `--panel2`. Plain `--accent` is 3.32:1 / 3.82:1 there — below the AA
  floor for 11 px text, latent in `.evrow` until the track modal exposed it.
- **`tests/test_aar_academy.py`** — 139 guards. **`scripts/mutate_aar_academy.sh`**
  — 18 mutations, all caught, zero weak.

### Changed
- **Closure is now printed as two phase-labelled numbers.** 1–3 kt approach
  (Stephenson) and ≈1 ft/sec in the last few feet (KC-46 programme). One knot
  is 1.688 ft/sec, so the card previously asked a pilot to arrive at the boom
  two to five times faster than the source it implicitly leant on.
- **The pre-contact hold is split into a 15 s gate and a 60 s standard**, with
  the 60 s explicitly labelled as ours — no document in the library states a
  duration, and it was borrowing ATP-56's authority by proximity.
- **Ride titles are descriptive**: `Air-to-Air Refuelling <n> (<Lane>) — <what
  it teaches>`. The lane is in the title because both tracks number 0–10 and
  the files land in one Missions folder.
- **The hardware page gains the throttle section** the research asked for:
  pulse/counter-pulse, baseline power, the close–stop–aft–stop drill, the five
  throttle errors, linear-first curve guidance, and friction setup. VR gains
  physical lens spacing, recentre binding, seat height, frame-timing priority,
  and the "check your eye height before your stick curves" note.
- **The five shipped AAR cards** are stamped into the tracks and renumbered.
  They were written as a set of four and said so in their briefs; inside an
  eleven-ride track that is a brief miscounting its own course. Recipes are
  untouched, so existing share links regenerate the same missions.
- **Track rides drop `featured` and `new`.** A badge on a card the grid never
  renders is not a signal, it is dilution of the badge everywhere it is.

### Fixed
- **`.evrow` colour contrast** — see `--accent-on2` above. Pre-existing;
  surfaced by putting an `.evrow` in front of axe for the first time.

### Notes
- **`aar.compatible()` takes DCS type ids** (`F-16C_50`), while `tracks.json`
  and every recipe use roster keys (`F_16C_50`). Passing a key where an id is
  expected returns `False` for every boom receiver, silently, in the function
  whose job is to stop a Viper being sent to a basket. Found by a test;
  guarded there. Worth collapsing the two namespaces one day.
- **No Lua ships in any `.miz`.** Contact, plug duration and fuel onload remain
  unmeasurable from triggers. Adding them means a resource file inside the zip
  (`DoScriptFile`; inline `DoScript` is known-broken in this stack) with
  consequences for byte-stable share links and for testability. Deferred as a
  deliberate decision, recorded in `docs/aar-academy-incorporation.md`.

---

## [1.73.1] — 2026-08-15 — AAR hardware page: FFB, VR, throttle

Second research pass covering force feedback and VR, which the first missed
entirely (0 hits for FFB, 3 passing mentions of VR). `aar.hardware_lines()`,
appended to the `aar_*` and `qf_tanker` briefs only — it is read once on the
ground, and stapling it to every mission with a tanker would bury the procedure.

**The negative finding, stated as one.** No first-hand evidence exists that FFB
helps AAR. The main ED FFB thread, the VPforce Rhino threads, the Mudspike and
Moza reviews and VPforce's own DCS settings page contain zero AAR or formation
content; the one thread asking directly concluded the problem was tanker speed.
The card says so and explicitly discourages buying FFB to fix refuelling.

**A correction to our own advice.** The procedure card says "add curve until
small corrections stop overshooting". VPforce's documentation: curves and
saturation are "incompatible with FFB" and must be disabled — structurally,
because DCS *writes* stick position on FFB to represent trim, and a curve
desynchronises commanded offset from interpreted deflection. Substitutes given:
spring gradient (force per degree) and damping (rate-dependent, so it suppresses
the panicky input and not the deliberate one); explicitly NOT friction (adds
breakout, recreating the step-input problem) or inertia (adds lag to reversals).
Flagged as reasoning from the effect definitions — nobody has published
AAR-specific FFB settings. Plus the trim gotcha: on FFB the stick physically
moves to the trim point, so trim before pre-contact.

**VR bounded by range rather than left as "VR is better".** Stereo depth
resolution falls as range squared; Navy SBIR N251-008 specifies accurate depth
judgement between 5 and 100 ft. At 1 nm astern stereo resolves kilometres, so VR
contributes nothing to the rejoin — angular size and closure rate do that work
on any display. Corroborated by the KC-46 Remote Vision System's decade-long
depth-judgement failure and a Wright State study finding stereo and hyper-stereo
improved RVS refuelling performance. VR-specific technique: hold head still at
contact, do not zoom at the boom (zoom corrupts the stereo cue), DCS VR "IPD" is
world scale, 45-degree approach, right basket harder.

**Known DCS defect named** so pilots stop blaming their hardware: the KC-135's
director lights are a pre-rendered texture, not lights — ED beta tester
confirmed, reported 2021, still open.

**Throttle and pedals**, both under-covered previously: throttle resolution is
usually the real bottleneck, a separate unit wins on travel, tune out the
Warthog afterburner detent near 90 %, speedbrake for a livelier RPM band, and
feet completely off the rudder pedals.

**7 new tests** in `tests/test_aar.py` (52 total). The two most important guard
claims that would quietly revert under an editing pass: the FFB negative
finding, and the fact that the hardware page contradicts the procedure card's
curve advice on purpose. Mutation-proved by softening the FFB heading and by
removing the VR range bound.

Suite: 2,358 passed, 18 skipped.

## [1.73.0] — 2026-08-15 — Air refuelling: the tanker was 80 knots too slow

**The bug.** Every tanker this product has ever generated used
`support_air.add_tanker(..., speed=550)` — pydcs takes km/h — at 6,096 m.
Measured out of a built mission: **152.8 m/s = 297 kt TAS ≈ 217 KIAS at
20,000 ft.** Boom AAR for fighters lives in the high 200s to low 300s KIAS; at
217 an F-16 is on the back of the drag curve, which to the pilot is
indistinguishable from being bad at refuelling. One speed, one altitude, every
tanker, every receiver, every era.

Root cause worth naming: **a pilot flies IAS and a mission file stores TAS**,
and at 20,000 ft they differ by 37 %.

**`missiongen/aar.py` (new).** Six tankers, each with its own indicated
airspeed and track altitude, converted to the file's true airspeed via the ISA
density ratio at that tanker's own altitude:

| key | type | track |
|---|---|---|
| `kc135` | boom | 300 KIAS / 20,000 ft |
| `kc135mprs` | drogue | 250 KIAS / 18,000 ft |
| `kc130` | drogue | 210 KIAS / 12,000 ft |
| `s3b` | drogue, carrier organic | 230 KIAS / 12,000 ft |
| `ka6d` (A-6E buddy) | drogue, carrier organic | 250 KIAS / 15,000 ft |
| `il78` | drogue, red | 250 KIAS / 18,000 ft |

Every entry carries **`basis`** — these are tuned operating points, not
quotations, because no document in our source library states AAR airspeed
bands. Labelled as the weaker claim it is.

**Matching.** Boom receivers get booms, probe receivers get drogues; a boom
tanker behind a probe jet is worse than no tanker (mission builds, tanker
flies, nothing happens). Off the boat the air wing's own tanker wins — S-3B
modern, KA-6D Cold War; an altitude tie-break previously handed both a KC-130.
`recipe.tanker_type` lets the pilot pick, and an incompatible pick **warns**
rather than silently swapping. An aircraft in `NO_AAR` gets no tanker at all —
the first cut warned "no tanker placed" and then placed one through the legacy
fallback.

**`air_start: "astern_tanker"`** — `builder._air_start_astern_tanker` puts the
flight in the pre-contact position: 1 nm astern, 1,000 ft BELOW (the escape
from a bad approach is down), at track speed, heading matched with
`manualHeading`. Refuelling is thirty seconds of skill wrapped in half an hour
of commuting.

**Six cards**: `qf_tanker` reworked, plus `aar_1_join` (explicitly *do not
plug*), `aar_2_contact`, `aar_3_probe`, `aar_4_night`, `aar_boat`.

**The procedure card** (`aar.brief_lines`) is generated for the tanker actually
placed and appended to the briefing. Research-grounded content, from
`docs/aar-training.md`:
- **Controller setup first** — the most-reported fix, and it lives outside the
  mission. Gives PRINCIPLES and refuses to give a curve number: published
  recommendations span 0-30 depending on gimbal type and stick length.
- **PIO, named and explained** — correcting for position instead of rate,
  phase lag, inputs landing 180° out of phase, the 0.5-1 Hz danger band. Turns
  "be better" into "reduce gain" with four levers. "Look at the tanker, not the
  basket" stops being a comfort tip and becomes removal of a second oscillator
  from the control loop. The F-16's FLCS does the same thing in hardware when
  the AR door opens.
- **Pass criteria**: zero closure at pre-contact for 60 s (ATP-56's gate),
  1-3 kt closure (Stephenson), a 3 ft box, 1-3 s connections progressing to a
  full transfer.
- **An honest expectation**: ~30 min/day for two weeks, and "you are not the
  exception."

**`tests/test_aar.py` (45, new).** Speeds asserted **in KIAS computed from the
mission file**, not against our own metres — the conversion is the fix, so it
is what is tested. Plus receiver/tanker compatibility, the carrier-organic
preference, no-tanker-for-non-refuellable, the warn-don't-swap path, the
pre-contact geometry, and the instructional content (no curve number, PIO
named, pass criteria present, expectation stated).

Mutation-proved: collapsing IAS→TAS to the identity (7 fail), allowing any
tanker for any receiver (3), and moving the astern start to 9,000 m (5).

**Badge hygiene.** `new` now means *shipped in this release* rather than
"recently" — the v1.71.0 B-Course flags cleared, 6 of 51 flagged (12 %).

Suite: 2,339 passed, 18 skipped.

## [1.72.0] — 2026-08-15 — Library audit: brief-vs-mission guard, five perch cards, badge hygiene

All 41 cards generated at seed 7 and their `.miz` contents compared against
their own briefs. Full findings: `docs/library-audit-2026-08-15.md`.

**`tests/test_library_promises.py` (51, new).** The systemic fix, and a sibling
to the existing "a number must be measured or cited" rule: **a brief may only
promise what the mission contains.** Seven detectable promises (controller,
moving target, airborne opponent, tanker, AWACS, something to shoot, a second
seat), each with a **disclaimer pattern** — a card is allowed to NAME a thing in
order to say it is absent. Plus: no empty-sky card contains enemy air; no brief
interrupts itself with a Builder config task; the NEW badge stays under a third
of the Library; every card declares a role; a brief that points at a sibling
card points at one that exists.

**`bc_cas1` was genuinely broken** — briefed a 9-line readback and a moving-target
attack, mission had neither. Rewritten to state both gaps and give the pilot a
self-briefed substitute.

**Two false positives in my own first pass, recorded because the lesson matters.**
`f100_fulda_cas` ("No JTAC datalink in this era") and `f100_victor_alert` ("GCI
only — no AWACS") were flagged by a matcher that saw the keyword and missed the
negation — the same error as flagging escaped HTML because the payload's
characters survive. Hence the disclaimer column. **The pre-existing cards were
more disciplined about this than the twelve added in v1.71.0.**

**Five new cards**: `bc_ahc_6k`, `bc_bfm1_6k`, `bc_bfm1_3k`, `bc_bfm4_6k`,
`bc_bfm4_3k`. The AETC ladder runs 9,000/6,000/3,000 ft inside each position;
those rungs were previously reachable only by editing the recipe in the Builder,
which three briefs instructed the pilot to do mid-brief.

**`bb_ambient: False`** on `bc_tr1` and `bc_sa1`, both of which briefed an empty
sky and contained an ambient enemy aircraft.

**Badge and metadata hygiene**: `new` cleared on 16 cards (28/41 → 12/46, 26 %);
`library.role` backfilled on `qf_tanker`, `qf_bfm`, `qf_guns`, `qf_sam`, which
had none and were being sorted by a frontend fallback.

**Recorded, not fixed — the largest say/do gap in the product:** zero moving
vehicle groups exist in any card, including `armed_recon_route` and
`af_convoy_overwatch`. ROADMAP has "Moving convoys" under *Later*; the audit
argues it up.

**Process note.** A `safe_mutate.sh save` was run with `|| true`, which swallowed
the helper's deliberate refusal to overwrite a stale snapshot, and a later
`restore` reverted the session's fixes. The helper worked; defeating its guard
with `|| true` did not. Fixes re-applied.

Suite: 2,277 passed, 16 skipped.

## [1.71.0] — 2026-08-14 — F-16 B-Course track; real BFM perches; Turning the Phantom

Two source documents, twelve cards, and a scripts/safe_mutate.sh so the next
mutation test stops eating uncommitted work.

**The B-Course track (11 cards, `bc_*`).** Follows AETC Syllabus F16C0B00PL /
F16C0TX0PL / F16C0SOCPL (56 FW, Luke AFB, April 2014) — 287 pages, 53 B-course
sorties. Cards: TR-1, AHC, BFM-1, BFM-4, BFM-7, ACM-1, TI-1, LASDT-1, SA-1,
SAT-2, CAS-1 — one per phase module, covering all four phases (TR / AH / A-A /
A-S). Each brief carries the asterisked task list and cites document + wing +
paragraph. Design rationale, and the 42 sorties deliberately NOT built with a
reason for each: `docs/f16-bcourse-track.md`.

**The BFM perches are now the syllabus's.** v1.66.0 shipped a three-perch ladder
with ranges we invented (2,200 m offensive and defensive). The syllabus flies
offensive BFM on BFM-1/2/3 and defensive on BFM-4/5/6, and every one of those
sorties runs the SAME three setups — *"a. 9,000 ft; b. 6,000 ft; c. 3,000 ft"*.
That is a range ladder INSIDE each position, structurally better than ours.

Six additive setups in `bfm.SETUPS` (`off_9k/6k/3k`, `def_9k/6k/3k`) plus the
`recipe.RECIPE_ENUMS` entries. **The original four are frozen** — a share link
minted against `offensive` must keep building the identical mission forever.
Measured out of a generated .miz: 8,999 / 6,001 / 2,999 ft.

**`f4_turning_phantom`.** Built from TAC ATTACK Vol 7 No 2, February 1967, p.4,
"Turning the Phantom — keep your speed up, Podner" (HQ TAC Chief of Safety).
TAC reviewed 22 F-4 accidents and lost control in 11; of those 11, ten were
manoeuvring, eight were at ≤300 kt, **all eleven carried external stores**,
seven had 12–14,000 lb of fuel, eight were low. Seven of the crews averaged 175
hours in type. The card teaches the three mechanisms: ~3G available at 250–300
KCAS against the 4.5–5G a pilot pulls off a weapons pass; Category II testing
finding external stores cut the stick-force gradient by ~50%; and buffet as
drag rather than turn. Full note incl. the aft-CG walk-through:
`docs/f4-turning-the-phantom.md`.

**What was deliberately NOT invented.** Chapter 5 of the syllabus is a set of
gradesheets: no dive angles, release altitudes, pop parameters, safe-escape
numbers, engagement counts — and **no BFM floor value**, though floor awareness
is a graded task. `HARD_DECK_FT = 5000` remains ours and is labelled as ours.
The 1967 article's own complaint was that the F-4 Dash One contained no V-G
diagram; we did not draw one. Both accountings are in the docs and summarised
in `docs/SOURCES.md`.

**`tests/test_bcourse.py` (46, new).** The perch ranges are asserted **in feet
against the document**, from a distance measured in a generated .miz — not
against the metres in our own table, which the implementation would satisfy by
construction. Plus: the two ladders must be the same three ranges; the original
four setups frozen; every new setup selectable in a recipe; all four phases
covered; every card cites its paragraph; every card builds; TR-1's G-profile
and LASDT-1's 500 ft floor and three rules stated exactly; and eight counted
findings from the 1967 article present verbatim.

Mutation-proved: reverting `off_9k` to the old 2,200 m (2 fail), drifting the
defensive ladder (2), dropping a syllabus citation from a card (1), and
softening "EIGHT were at 300 knots or below" to "Most were slow" (1).

**`scripts/safe_mutate.sh` (new).** Three times in one session a mutation test
was reverted with `git checkout <file>`, which restores to HEAD and therefore
discards every uncommitted change in that file — it cost `_fitting_slots` once
and eleven Library cards once. `save` snapshots to a temp dir and refuses to
overwrite an existing snapshot; `restore` puts it back and clears it. The
mutation runs in this release used it.

## [1.70.0] — 2026-08-14 — Admin-editable Thanks list

Rob asked for specific people to be thanked (Sedlo, Stewmanji) and then, better,
for the list to be editable from the admin section rather than hard-coded.

**The architectural point, which is why this is not a file.** `docs/SOURCES.md`
is a build artifact: `tests/test_sources.py` asserts it byte-for-byte against
its generated page and `scripts/release.sh` rebuilds it. A thanks list baked in
there fails twice over — the owner cannot add a name without a deploy, and the
next release silently wipes anything edited on the server. So: **cited facts are
versioned, gratitude is editable.**

- **`missiongen/credits.py` (new).** JSON manifest on the data volume, mirroring
  `sponsors.py`. `load/add/update/delete/restore_seed`. Seeds on first read so a
  fresh deploy is never a blank heading. URLs are https-only **at the storage
  layer**, so a bad value cannot reach the renderer even if a future renderer
  forgets to check.
- **`/admin` → Thanks tab** (`server/admin.py`): add, edit in place, reorder,
  delete, and restore the shipped list.
- **`/api/sources` injects the block at REQUEST time** via `_with_thanks()` —
  never into `docs/sources.html` on disk. Everything escaped at render.
- **`/api/credits`** returns the list as JSON. Read-only; there is no
  unauthenticated write path, and `/admin` is disabled outright without
  `ADMIN_PASSWORD`.
- **`fly.toml`**: `CREDITS_DATA_DIR = '/data/credits'` on the existing volume.
- **`docs/SOURCES.md`** gains §7 explaining the split, so the page documents why
  its own Thanks section is not in it.

**`tests/test_credits.py` (14, new).** Seed-on-first-read; add/edit/delete round
trip with ordering; a credit cannot be left nameless; six hostile URL schemes
rejected (`javascript:`, mixed-case, `data:`, `vbscript:`, `file:`,
protocol-relative); markup escaped when served; restore works; the endpoint is
read-only; editing requires the admin. And the architectural assertion **both
ways** — present in the response, absent from the artifact on disk.

Mutation-proved: dropping the URL scheme check (6 fail), dropping the render
escape (1), and baking the block into the artifact instead of injecting it (2).

**A repeat mistake, recorded.** The XSS assertion first searched for the
substring `onerror=alert(2)` and failed against *correct* output, because
escaping neutralises the angle brackets without deleting the text — it is still
there, inert, inside `&lt;img ...&gt;`. This is the second time this exact error
has been made in this codebase. The rule now written into the test: **assert
that no live element was emitted, not that a payload's characters are absent.**

## [1.69.0] — 2026-08-14 — GWOT era; Iraq corridors re-scoped to what ED shipped; infrastructure targets

Prompted by reading Eagle Dynamics' actual shipping state for DCS: Iraq rather
than assuming it. Research and sources in `docs/iraq-air-corridors.md`
(appendix) and `docs/dcs-iraq-map-state.md`.

**The finding.** What ships today is **Iraq North**, in Early Access since
11-13 Dec 2024, and ED states its focus is "the Global War on Terror and ISIS."
Desert Storm and Iraqi Freedom are the **South** region, which has no release
date (its Q2 2025 target was missed by over a year); Iran-Iraq is not a
supported era, only a stated intention to "evaluate expanding to the east."
Kharg Island arrived 22 Jul 2026 (build 2.9.28.26283) with airfield, oil
terminal, ATC, flares and pipelines — a South-region asset delivered early.
Our 20-airfield vendored list is confirmed complete and current.

So v1.68.0's seven corridors targeted two eras the terrain does not yet model
and skipped the one it does.

**New era: `gwot`, "War on Terror (2003-2020)".** Window [2003, 2025], which
overlaps `modern` deliberately — the era gate is not what distinguishes them.

- `data/eras.json`: blue is coalition with `sam_kits: []` (point defence only —
  a Patriot battery defends against an air force this enemy does not have); red
  is derelict Iraqi Air Force airframes, insurgent gun trucks, `sam_kits: []`.
- `threats.TIER_SAMS["gwot"]`: empty both sides, every tier.
- `threats.TIER_CAP["gwot"]`: **red empty**. The defining fact of the era.
- `threats.TIER_AAA["gwot"]`: pydcs's dedicated `_Insurgent` gun variants.
- `routing.ERA_PROFILE["gwot"]`: (7500, 6000, 4500, 800) — HIGHER than modern.
  With no radar SAM and a gun line topping out around 8-10,000 ft, descending
  to a modern medium-altitude transit is the one place this profile would be
  actively dangerous.
- `data/ramp_themes.json`: blue coalition/rotary_heavy/air_bridge, red
  abandoned/captured.
- `data/maps.json`: `iraq.presets.gwot` (Inherent Resolve — Al-Asad/Erbil vs
  Qayyarah West/Mosul/K1/Kirkuk) and `afghanistan.presets.gwot` (Enduring
  Freedom — Bagram/Kandahar/Bastion/Salerno vs Khost/Sharana/Gardez/Tarinkot).
- Plumbed: `support_air.AWACS_TYPES` (red None) and `tanker_type`,
  `naval.CARRIERS`, `builder` hull default, `carrier_decks.json` modern hulls.

**Two defects the era exposed, both fixed:**

1. **Enemy ambient traffic ignored whether the enemy has an air force.** It
   flies `era.parked_planes`, so GWOT's derelict MiG-21s would have taxied out
   and flown. `builder` now reads `threats.cap_types_for` — the single source
   of truth for "does this side fly" — and gates enemy ambience on it.
2. **The area threat belt is SAM-only unless the tier is "guns".** An era with
   no SAM inventory therefore placed *no area threat at all* on the default
   tier, at any intensity. This had been true of **WWII since the Threat Dial
   shipped** — the flak in a 1944 mission was entirely airfield SHORAD.
   `builder` now falls to the AAA belt whenever
   `sam_kits_for(...)` is empty, whatever tier is set. Measured effect on the
   semantic sweep: marianas/wwii 8 -> 24 and 30 AAA units, normandy/wwii
   18 -> 32/36, thechannel/wwii 10 -> 24/25.

**Iraq corridors re-scoped (10 total).** Three new `gwot` lanes (Tigris Valley
345 x 260 km, Haditha Dam Corridor 280 x 135 km, Kirkuk-Hawija Pocket 20 x 160
km) and three for Afghanistan (Helmand Green Zone 237 x 191 km, Khost Bowl
80 x 320 km, Kunar Valley 59 x 449 km).

New optional `terrain_note` field, briefed verbatim, on the three corridors
that cross ED's undetailed southern band (Kharg Island Strike Lane, Southern
Watch, Karbala Gap) — Rob's call was to keep them selectable and flag them
rather than pull them.

**Jafati Valley re-anchored** 64 x 320 km -> 51 x 300 km, onto the Dukan Dam,
which ED shipped as a unique 3D model on 22 Jul 2026 and which HRW's account of
the First Anfal places a few miles from the target area.

**Two new target packages** (`targets.TARGET_PACKAGES`): `infrastructure`
(dam/power) and `oil_terminal`, both era-filled including `gwot`. These exist
because ED built the buildings — the package garrisons a real modelled
structure rather than spawning a fake one.

**`tests/test_gwot_era.py` (12, new).** The era is one large negative claim, so
every assertion reads a generated .miz: no enemy aircraft anywhere (planes AND
helicopters, max intensity, ambience and BFM both on), the derelicts still
parked as statics, no SAM on either side at any tier, the threat dial still
scaling, the area belt using insurgent variants, the brief SAYING there is no
enemy air force, and — parameterised over every SAM-less era, so WWII is
covered — that an area belt exists at all.

Mutation-proved four ways: un-gating enemy ambience (2 fail), reverting the
AAA fallback (1), giving red a MiG-21 (3), and swapping the insurgent guns for
regular AAA (1).

**A fifth vacuous test caught before it shipped.** The insurgent-gun assertion
originally scanned every red vehicle and survived gutting `TIER_AAA["gwot"]`,
because airfield SHORAD comes from a different table (`eras.json`) that still
had the insurgent types. Two tables, one assertion, and the assertion was
satisfied by the table it was not testing. Now scoped to the `AAA - Area N`
groups.

**Era-literal cleanup.** `tests/test_formation.py` duplicated `eras.json`'s
windows verbatim and asserted formation cards cover exactly the three known
eras; both now derive from the data. `tests/test_pending_aircraft.py` asserted
`_eras_for("F_14B") == ["modern"]` — an assertion that fails on correct data
teaches people to edit assertions, so it now states the product decision
("not in the Cold War"). `frontend/index.html`'s Library era filter was static
markup and `qfEra`'s candidate list was a closed three-element array; both are
now built from `OPT.eras`.

**`docs/SOURCES.md` + `/api/sources` (new).** A permanent, served bibliography:
the vendored library and its pinned commits, what is measured in-sim by our own
instrumentation (9,550 parking headings, the BUSURVEY airframe boxes, the
Afghanistan projection probe), the era-gate tables and how they were compiled,
every historical source behind a corridor, the design/accessibility standards,
and a licensing summary. It also records what we could NOT source and therefore
did not ship. Rendered by `scripts/build_sources_html.py`, registered in
`scripts/artifacts.py` so the release check blocks on a stale page, linked in
the entry screen and the footer.

**`tests/test_sources.py` (18, new).** A bibliography that has gone stale is a
stronger lie than none, so: every pinned commit must match the provenance
header of the terrain package it claims (cross-checked, not trusted); every
externally-sourced data pack must be traceable from the page or a document it
links; every licence file on disk must be declared; no placeholder links; the
page must admit its gaps; the HTML must be byte-identical to what the builder
produces. Mutation-proved: a stale commit, an undeclared licence and a
hand-edited HTML each fail.

**Semantic differ: 46 differences across 48 missions plus 4 new, all
explained.** Baseline regenerated at `docs/mission-semantics-baseline.json`.

## [1.68.0] — 2026-08-14 — Iraq air corridors; official Afghanistan export; width-first player parking

Completes "take the data, leave the engine" (docs/pydcs-fork-feature-review.md
items 1 and 3), plus a historian's pass over the Iraq map that shipped in
v1.67.0 with no corridors.

**Iraq air corridors (7).** `missiongen/data/air_corridors.json` gains an
`iraq` key: 3 coldwar (Kharg Island Strike Lane 125°×875 km, Jafati Valley
64°×320 km, H-3 Raid Track 350°×250 km) and 4 modern (Northern Watch (36th
Parallel) 348°×250 km, Southern Watch (33rd Parallel) 134°×258 km, Karbala Gap
172°×167 km, Western Scud Box 252°×345 km). Bearings and reaches were computed
from each preset's blue-airbase centroid to the real historical objective, then
checked to land over the theatre. Research, sources, source disagreements and
the four candidates deliberately rejected (Package Q, Osirak, Ugly Baby/Happy
Valley, the post-2003 Baghdad ROZ) are in `docs/iraq-air-corridors.md`.
No code change — the Builder already renders whatever `/api/options` carries.

**`tests/test_air_corridors.py` (46 tests, new).** Corridor data had never been
guarded at all. Three properties:
- every corridor's map and era resolve (the orphan class of bug that killed 26
  parking headings in v1.67.0 — orphaned data does not throw, it just stops
  being data);
- the corridor's focus lands within 200 km of an airfield on that map, which is
  the same land-and-on-map proxy `threats.add_area_sams` uses, because pydcs
  exposes no land/water query. Worst shipped value is 151.6 km (Afghanistan,
  Hindu Kush Passes);
- for Iraq, the lane actually drawn on the F10 map runs down the bearing the
  JSON claims, within 1°, read back out of a generated .miz.

Mutation-proved: an orphaned era, a reach walked off the map, and disabling the
`enemy_center` re-anchor in `builder` each fail (5, and 7 of 7 respectively).

**Afghanistan replaced with the official export.** `missiongen/terrains/
afghanistan/` is now dcs-retribution/pydcs @ 3a79b8ed (2026-07-25), LGPL-3.0,
with the same ONE adaptation Iraq needed — our `Terrain.__init__` requires
`utc_offset`, the fork's does not, so Afghanistan supplies UTC+04:30. This
replaces 4,602 hand-built lines shipped since v1.31.0 whose projection our own
source marked *provisional*.

Measured airport-by-airport before committing:
- **Nothing lost.** All 25 airports and every slot name present. All 460
  measured Afghanistan parking headings still resolve
  (`tests/test_parking_headings.py`, 31 passed).
- **Zaranj** added — a 26th airfield in the south-west our export missed.
- **Khost** +3 stands (13, 14, 15).
- **Stands widened, never narrowed**: Ghazni Heliport 18→23 m, Khost 22→41 m,
  Shindand 24→41 m. Verified against a measurement of the pre-swap file, not
  against round numbers.
- **Positions moved metres, not kilometres**: 6 Bagram slots ≤6 m, 12 Shindand
  slots ≤21 m, Ghazni Heliport's ARP 122 m.
- **The projection is the same projection.** Ours agreed to 2.3e-5 m of false
  easting and 3.8e-5 m of false northing, identical central meridian and scale
  factor. "Provisional" was over-cautious, not wrong.
- `center` becomes the surveyed 33.9346N/66.24705E; `bounds` is corrected —
  ours had top and bottom transposed, which pydcs uses only for the default map
  view, so the bug was never visible.
- The `temperature` table is the export's verbatim, **including** June's
  minimum (23 °C) being warmer than July's (18 °C). Deliberately not
  hand-smoothed: a silent local "fix" is how a vendored file stops being
  vendored. It feeds only `random_season_temperature`.

**`tests/test_afghanistan_export.py` (40 tests, new).** Absolutes, not
differentials — a differential assertion is how three vacuous tests shipped this
year. Seven surveyed airfield positions to 0.5 km; Zaranj present and the count
26; per-field widest-stand floors and KC-135 stand counts measured off the
pre-swap file; the UTC+04:30 offset pinned by value. Mutation-proved: wrong
utc_offset, a shifted central meridian, and narrowed stands each fail.

**Width-first parking for the player (`builder._fitting_slots`).** pydcs sorts
free parking `(helicopter, slot_name)`, so a flight takes whichever adequate
stand sorts first BY NAME — and stand "01" is usually the field's widest. **22
of 144 airfields we ship hand the F-16 a heavy-capable stand**; Fujairah Intl
has exactly one and pydcs gives it to the fighter. Adding `width` as the second
key is the fix the fork made upstream; we make it in our own placement code
rather than in `vendor/dcs`, which is a byte-for-byte mirror. Same class of bug
v1.47.0 fixed for the ramp *dressing* — the player's own parking never got the
treatment because it goes through pydcs, not through our code.

Returns `None` (not a short list) when a field cannot seat the flight, so the
existing `NoParkingSlotError` path still tries the next field rather than
seating half a four-ship.

**`tests/test_player_parking.py` (8 tests, new).** Mutation-proved three ways.
The helicopter-pad test uses synthetic slots on purpose: across all twelve
shipped maps there is not one airfield where an aeroplane stand is narrower
than the narrowest pad, so a data-driven version passes for the wrong reason —
the first draft did exactly that and survived deleting the key. Recorded with
it: pydcs's `helicopter` key means the opposite of what it looks like. `False`
sorts first, so it keeps an AEROPLANE off a pad, not a helo on one.

**Semantic differ: 38 differences across 48 missions, all explained.**
`scripts/mission_semantics.py --compare` against the v1.67.0 baseline:
- 6 maps (iraq, marianas, nevada, sinai, thechannel) move `player.x/y` — the
  width-first sort choosing a different stand at the same field. Intended.
- `afghanistan/modern/42` gains 4 SAM units with the player position unchanged.
  Traced: same 6 red sites and 1 blue site before and after, but 4 of the red
  batteries drew SA-11 (6 units) instead of SA-6 (5). Cause is the 26th
  airfield shifting the seeded draw order, i.e. the ordinary consequence of
  adding map content. No site was lost or gained.

**Share-link note.** Determinism is intact — same recipe and seed still give a
byte-identical file — but the *data underneath* changed, so links minted before
v1.68.0 regenerate a slightly different mission on Afghanistan and on the six
maps whose player parking moved. Called out in the release notes.

## [1.67.0] — 2026-08-14 — Iraq terrain; parking-heading guard; semantic differ

Executes the revised sequence from docs/pydcs-plan-critique.md. Rob deployed
v1.66.0 to production first, so this lands on a clean base.

**Iraq, without swapping libraries.** `missiongen/terrains/iraq/` is vendored
from dcs-retribution/pydcs @ 3a79b8ed (2026-07-25), LGPL-3.0, with ONE
adaptation: our pydcs's `Terrain.__init__` requires `utc_offset` and the fork's
does not, so Iraq supplies UTC+3 (Arabia Standard Time). Airport data,
projection and everything else are byte-for-byte upstream. Verified: 20
airports, 1,397 parking slots, and the projection puts Baghdad, Mosul and
Al-Asad on their real coordinates to 2 dp.

The point of doing it this way (critique §2): the fork's value to us was a
terrain we lack, and **new terrain is risk-free precisely because it is new** —
it replaces nothing. Swapping the whole library would also have replaced the
airport data underneath 9,550 hand-measured parking headings. Presets: coldwar
(Iran-Iraq basing) and modern (2000s coalition basing), 15 named fields each,
every one verified present on the terrain.

**tests/test_parking_headings.py (31)** — the guard the critique called for.
Every field and every slot name in parking_headings.json must still exist on
its terrain; a corpus-size floor catches silent truncation; values must be
compass bearings. **It found 26 dead measurements on first run** — hyphenated
sub-slot names ('02-1', 'D09-1') that DCS uses for multi-aircraft stands and
pydcs flattens to the parent, so they never resolved and were dead from the day
they were measured. Every one was shadowed by a live parent measurement and
several disagreed with it by ~180 degrees (nose-in vs nose-out on the same
spot), so they were removed rather than kept. Three mutations proven.

**tests/test_every_map_builds.py (50)** — nothing built every map. Every
map-level test pinned one theatre (Nevada, Syria), so a new or broken map could
ship silently; Iraq itself was only verified by hand. Now: every map × era
builds a valid .miz with a briefing dictionary, every preset airbase exists on
its terrain, both sides have fields and countries. 18 s. Three mutations proven.

**scripts/mission_semantics.py** — the tool the critique replaced byte-diffing
with. Fingerprints ramp occupancy per field, player spawn/geometry/loadout,
threat and support counts, and document presence across every map/era/seed (48
missions), then compares two runs field by field, exiting 1 on any mission that
built before and does not now. Byte-diffing 2,218 changed lines of planes.py
would have produced noise a reviewer starts rationalising; this produces
sentences a human can adjudicate. Baseline committed at
docs/mission-semantics-baseline.json. Its own ramp-name parser was wrong first
(squadron tags contain spaces, producing phantom airfields) — caught by reading
the output, fixed with an anchored regex.

**Tests** — 1,675 passing.

## [1.66.0] — 2026-08-13 — BFM three-perch ladder + generated standards cards

Rob: "Let's do the BFM three-perch ladder and as an instructional designer,
create training scenarios to do it." Designed in docs/skillwork-syllabus.md;
the rung is a PARAMETER of the rep (`bfm_setup`), not four more cards on a
screen the UX review already found overlong.

**Geometry, not AI skill.** `missiongen/bfm.py` holds the four setups as
pilot-terms geometry (range, bearing off YOUR nose, bandit heading relative to
yours, altitude offset): neutral 2 nm abeam · offensive 1.2 nm ahead at 30 deg
angle off · defensive 1.2 nm astern, co-heading, +300 m · high_aspect 5 nm
nose-to-nose. `add_bfm_adversary(setup=, player_heading=)` lays them out; perch
rides fly a straight 40 km leg rather than a racetrack, because an orbit turns
as the mission starts and the briefed angle-off would be a lie by the time the
pilot looked.

**Two library defaults were silently overriding deliberate values.** Both found
by measuring the built .miz, neither catchable any other way:
1. `m.patrol_flight()` spawns an in-flight patrol at
   `Point(pos1.x - 10*1000, pos1.y)` — a fixed offset ignoring heading. The
   legacy "2 nm abeam" merge measured **5.9 nm at 149 deg off the nose**, so
   every BFM brief shipped before this release was fiction. Now built with
   `flight_group_inflight` at the exact point + `patrol_flight_to_group` for
   the same orbit/engage tasking.
2. `unit.heading` is stored in DEGREES and converted on save; the first fix
   wrote radians, giving a player heading of 5.6 deg where the geometry used
   318.9 (318.9 deg = 5.566 rad, written as 5.566 deg). Every "off your nose"
   figure was measured from a nose that did not exist. Fixed to degrees, plus
   `manualHeading = True` as belt-and-braces against pydcs recomputing heading
   from wp0->wp1 if an RTB waypoint is ever added.

**Standards cards** — `bfm.brief_lines(setup, aircraft_id, guns_only)` generates
the briefing per rung: OBJECTIVE · SETUP (what you should see at t=0, so the
pilot can verify the sim gave them the briefed picture) · STANDARDS · COMMON
ERRORS, each with the CUE that reveals it · DEBRIEF (3 questions) · MOVE ON
WHEN (the progression gate). Deliberate design decision recorded in the module:
numbers WE control (ranges, blocks, times, the 5,000 ft hard deck) are exact;
aircraft performance is a band plus a method, because corner velocity is
per-type/weight/fuel and a confidently wrong number in a training document is
worse than an honest range.

**Tests** — 1,644 passing. `tests/test_bfm_ladder.py` (26) measures the actual
.miz: each ride's range/bearing/aspect/altitude, holding across three airframes,
three theatres and two eras; the card's structure per rung; that the cards
differ; that the briefing carries the ride actually flown (read out of
l10n/DEFAULT/dictionary — reading descriptionText returns the DictKey, which is
how a "card is in the brief" test can pass while the pilot sees nothing); that
no corner speed is invented. Five mutations proven. **A sixth was vacuous on
first write**: the player-heading test compared offensive vs defensive
differentially, and a constant offset cancels — it passed with the fix removed.
Rewritten to assert the bandit lands on the nose across three theatres, where a
stuck or mis-scaled heading cannot survive.

## [1.65.0] — 2026-08-13 — Fly Now: instant action, measured and guarded

Rob: "Fly Now should probably provide the user with instant action. Maybe that
starts in the air." Measured first (docs/fly-now-instant-action.md), then built.

**Baseline** (Caucasus/modern/A-10A/seed 42): qf_bfm airborne, bandit 6.1 km
(~25 s); qf_tanker airborne FL200; **qf_guns ramp-start, target 133 km
(~18 min in an A-10)**; **qf_sam ramp-start, ring 104 km (~13 min)**. Two cards
kept ramp starts while two got air starts because nothing measured it.

**Two target-relative air-start modes** (`air_start` in mission_templates.json):
- `roll_in` (qf_guns) — 11 km from the target, run-in from the friendly side,
  floor 3,000 m. Inside visual pickup, outside gun range: the attack geometry
  is still the pilot's to fly.
- `outside_the_ring` (qf_sam) — standoff sized from the SAM's OWN `wez_m`
  + 4 km margin, **anchored on the ring, not the target**. First implementation
  measured from the target and put the spawn 16 km from a 22 km SA-3 — inside
  the envelope, an ambush rather than a drill; the site sits between target and
  home. Now: 25.8 km from an SA-3 (Caucasus), 27.9 km from an SA-6 (Syria).

Implemented as a **reposition after target placement**, not an earlier target
computation: the package anchor draws from `self.rng`, so hoisting it would
reorder RNG consumption and change missions for every template using target
packages. `_air_start_on_target()` moves units AND waypoint 0 together (moving
one alone spawns you correctly then routes you back to the old position).

**Airframe-correct spawn block.** The air start's fixed 4,500 m / 800 km/h was
a fast-jet constant; `formation.cruise_for()` (which exists because exactly
this kind of constant once made the product "an F-16 tool") now supplies both.
A-10 spawns at 8,000 ft / 174 kt, P-51 at 3,000 m / 185 kt, F-16 at 320 kt.

**Template recipe merged server-side.** `Recipe._with_template_defaults()`
applies a template's `recipe` block as DEFAULTS in `from_dict`, so
`POST /api/generate {"template": "qf_bfm"}` no longer silently produces a ramp
start. Explicit caller values always win (an old share link encoding
`start: "warm"` keeps it). The frontend's own merge is now redundant but
harmless.

**Tests** — 1,618 passing. `tests/test_time_to_first_action.py` (16): every
card airborne; ARRIVE cards (bfm, guns) ≤90 s to the nearest threat **at the
airframe's own cruise** — a distance-only ceiling would pass fast jets and fail
exactly the pilots who need a short ride; the SAM card measured as GEOMETRY
instead (outside the ring, within 1.5×) because that mission begins when the
RWR chirps, not on arrival — measuring travel time there would have measured
the wrong thing, and "fixing" the failure by moving closer would have deleted
the standoff that is the exercise. Also: cross-airframe/cross-map coverage,
airframe scaling, api-matches-ui, explicit-beats-default. Six mutations proven
(ramp start restored, reposition disabled, ring anchor removed, cruise constant
restored, merge removed, merge overriding explicit values).

## [1.64.0] — 2026-08-13 — Contact form + admin inbox (read/unread)

Rob: "We probably need some type of way for users to make recommendations or
comments." Spec written first (docs/contact-form-spec.md), phases 1+2 built
together — a form whose messages nobody can read is not a feature.

**Store** (`missiongen/contact.py`) — JSONL on the Fly volume under
CONTACT_DATA_DIR, one file per month, following the analytics module's proven
pattern; no database, no new infrastructure. **Append-only including
mutations**: marking read appends `{"id":…, "op":"read"}` and `load()` folds
ops over base records, so no code path rewrites a line in a file the user
cannot regenerate. Corrupt/truncated lines are skipped, not fatal. Ids are
`<utc>-<rand>`, sortable by arrival with no counter file. `prune()` exists but
is never called automatically — expiring a bug report on a timer is a
decision, not a default.

**API** — `GET /api/contact/token` issues a signed issue-time; `POST
/api/contact` validates and stores. Three anti-abuse layers, no CAPTCHA (an
accessibility tax we will not levy one release after shipping AA):
honeypot field, signed time-floor (3s), per-IP token bucket (5/hr, 20/day)
whose key lives in memory and is **never persisted** — that is what keeps the
no-PII stance true on an endpoint that accepts PII by design. Honeypot and
time-floor rejections return the same success shape as a real submit; telling
a bot why it failed is free tuning advice for the bot. The server stamps
`context.version` itself — a client-supplied version is the one field a stale
cached page would lie about.

**Frontend** — Contact link in the topbar link set and the footer; dialog
reuses the v1.63.0 `modalOpen`/`modalClose` focus trap (role=dialog,
aria-modal, Escape, focus restore). Labelled fields, per-field inline errors
via role=alert cleared on input, live-region status, character counter,
disclosed auto-context in a `<details>`, and a success state that never
destroys typed text on failure. **Client-side validation mirrors the server**
and — the bug this build caught — the client *waits out* the server's bot
time-floor rather than posting inside it: the server silently discards a
too-fast submission, so a quick human pasting a prepared message would have
been told "sent" and lost their words. Found by browser-testing the real flow,
now pinned by `test_the_client_never_trips_the_time_floor_itself`.

**Admin** — fourth tab with an unread-count badge (an inbox you must open to
discover is empty is an inbox nobody opens). List newest-first with unread
marked by weight + left rule + the word "new" (never colour alone), filters by
unread and topic, expandable context, `mailto:` reply link — the app never
sends email, which keeps us out of deliverability entirely. Every
user-controlled string HTML-escaped: this page renders strangers' text into an
authenticated session. Render failures degrade to a shell with the other tabs
intact, same as the analytics page.

**Tests** — 1,602 passing. `tests/test_contact.py` (36): round-trip, op
folding with last-op-wins, delete, append-only-on-mutation, corrupt-line
resilience, 11 validation bounds, version stamping, honeypot, forged token,
time floor, per-field 422s, rate limit, no-IP-in-store, admin auth on all
three routes, badge counting, read/unread round trip, XSS escaping, unread
filter, and analytics/contact store separation. Six guards mutation-proven
(honeypot, time floor, admin auth, escaping, append-only, rate limit).
`scripts/axe_check.js` gains a contact-dialog pass (8 total) — a form is the
densest accessibility surface we ship, and it is clean.
`test_no_wizard_block_starts_collapsed` scoped by an explicit
COLLAPSIBLE_BY_DESIGN exception list rather than loosened, and re-proven
against a real wizard regression.

## [1.63.0] — 2026-08-12 — WCAG 2.2 AA: keyboard, semantics, contrast + axe gate

Rob: "What do we need to do to get WCAG compliant?" Audited (axe-core 4.13
over 7 view/mode passes + manual review against the 2.2 AA checklist),
reported in docs/wcag-audit-2026-08-12.md, then executed all three phases.

**Baseline found**: 2 violation types — color-contrast (up to 41 nodes/page)
and select-name (critical, 6 nodes) — plus manual findings the scanner cannot
see: no keyboard access to any card, no focus ring, no dialog semantics, no
live regions.

**Phase 1 — names, contrast, live regions, dialogs.**
- 25 selects + inputs: sibling `<label>`s bound via for/id (24 auto-bound, 1
  input, 2 group labels via role+aria-labelledby); search inputs got aria-label.
- New tokens: `sys_blue_access` #0040DD (small accent text + solid surfaces,
  light), `sys_blue_access_dark` #409CFF (small accent text, night),
  `sys_blue_solid_dark` #0070E0 (night solid — Apple's #0A84FF is 3.65:1 with
  white and fails), `sys_green_access` #1F7835; `sys_dim` darkened
  #6E6E73→#69696E to hold 4.5 on sys_fill. Emitted as `--accent-small`,
  `--accent-solid`, `--green-small`. ~24 call-sites moved (.eyebrow, .qlabel,
  .kindb, .acbadge, .hdrval, .lmodtag, .lnew, .kitbtn, .qgo .fly, #gen2,
  .navbtn.primary, .step h2 .n, …). The v1.61 "3.0 large-text floor" deviation
  for sys_blue is RETIRED — #007AFF now carries no text, only borders/rings/
  icons at the 1.4.11 3:1 non-text floor.
- Alpha-dimming replaced with colour-dimming (.rsub.off, #railreset, .card.dis,
  .block.dis, .qcard.dis): opacity multiplies into effective contrast and
  silently voids the computed token guarantees. Disabled state now reads as a
  dashed border + var(--dim), both above their floors.
- `role="status" aria-live="polite"` on #status/#status2 (4.1.3).
- role=dialog + aria-modal on all three overlays; shared modalOpen/modalClose
  focus trap with Tab cycling, Escape, and focus restore (2.1.2, 2.4.3).

**Phase 2 — keyboard.** 13 clickable non-native elements given role+tabindex
(.epath ×3, .owntg as role=switch, .corrcard, .revrow, .qcard ×4, .lmodcard,
.fchip, .libcard, .ochk as role=checkbox, the collapsible corridors h2 as
role=button + aria-expanded). One delegated keydown handler activates
role=button/switch/checkbox on Enter/Space. Global
`:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px }`.
The half-built ARIA tabs pattern (role=tablist/tab, static aria-selected, no
arrow keys) replaced with plain nav buttons + aria-current — an honest
complete pattern instead of a broken sophisticated one.

**Phase 3 — motion, targets, gate.** prefers-reduced-motion media query;
.dclose to 28px and .osel/.oclr/.fchip to a 24px min-height (2.5.8);
scripts/axe_check.js (axe-core 4.13 vendored, MPL-2.0, at vendor/axe-core/)
fails on any serious/critical violation across 7 view/mode passes; wired into
the suite as tests/test_a11y.py (skips without node+chromium).

**Tests** — 1,566 passing. tests/test_a11y.py (9): keyboard-operability scan,
accessible-name scan, live-region, dialog semantics, no-alpha-dimming,
reduced-motion, global focus ring, accessible-blue pinning, axe gate.
test_flightline.py PAIRS extended to 14 new pairs. Mutation-proven: unbound
label, stripped aria-live, card without tabindex, deleted focus ring, restored
alpha dimming — each caught. **The focus-ring test was vacuous on first
write** (a pre-existing `.topbar h1 a:focus-visible` rule contains the same
substring, so it passed with the global rule deleted) — caught by mutation,
now an anchored regex. Same class of bug as the v1.58 data-mode test.
Live keyboard walkthrough via Playwright confirms: Enter opens the dialog,
focus enters it, Escape closes and restores focus, Space toggles cards.

## [1.62.0] — 2026-08-12 — Explicit ramp fill outranks the squadron variety cap

Rob: "When I select 100% fill for Nellis airfield, it doesn't populate
completely. It only has a few aircraft."

**Root cause: two rules both claimed precedence.** `dress_airfield` line one
of the explicit-fill branch says "EXPLICIT user percentage WINS — no cap";
the squadron block system (`SQUADRON_MAX = 6`, v1.5x) says when every
identity is full, STOP — "an emptier ramp is the correct outcome." The stop
rule won: the ramp's hard ceiling was (distinct squadron identities × 6).
Reproduced at Nellis, modern/red_flag, fill=100: 79 of 233 airplane stands
(deterministic across seeds). An unverified livery pack makes it worse —
`_pick_livery` returns None, so each TYPE collapses to one identity.

**Fix: wave escalation, explicit-fill only.** `squad_cap` starts at
SQUADRON_MAX; when `_next_block` returns None with an explicit `fill` and
`placed < target`, the cap escalates by another SQUADRON_MAX and redraws —
one escalation per slot at most. Block sizes stay 2–8 so rows keep the
squadron-block look. The auto/density path never escalates (guarded on
`fill is not None`); the variety rule remains absolute there.

Measured after: Nellis fill=100 → 245/247 stands (99%); fill=50 → 124 (50%);
auto/busy unchanged at 28.

**Tests** (test_squadron_cap.py, 24): direct-dressing harness at Nellis —
`test_an_explicit_100_percent_fill_fills_the_ramp` (≥95% floor; the collision
gate and heavy-fit checks legitimately skip a stand or two),
`test_an_explicit_half_fill_lands_on_half`, and
`test_the_auto_path_still_stops_at_the_variety_cap` (full generate, auto
path, six-per-squadron still absolute). Mutation-proven three ways: escalation
removed → 100% test fails; explicit-fill guard dropped → auto-path test
fails; target arithmetic halved → 50% test fails.

## [1.61.0] — 2026-08-12 — Library role palette onto Apple HIG accessible colors

Rob: "The library colors don't seem to match what would be supported by the
Apple HIG."

**Role tokens generated, fork closed.** The seven Library role colours
(`--a2a --strike --sead --cas --carrier --training --historic`) were a
hand-written `:root` block outside the generated markers — a palette fork the
anti-fork machinery couldn't see. They now live in `flightline.json` as
`role_*` / `role_*_dark` pairs, emitted by `scripts/gen_theme.py` into BOTH
mode blocks, covered by the artifact-registry rebuild rule and
`gen_theme --check`.

**Apple HIG accessible variants, not the defaults.** Role labels render as
11px text; default systemOrange on white is 2.2:1. Light values are Apple's
published accessible variants, darkened one further step where needed to hold
4.5:1 on sys_fill (a2a/strike/carrier/training); sead's dark variant
brightened one step for 4.5:1 on sys_dark_fill. Mapping: a2a→cyan #006FA1/
#70D7FF, strike→orange #C43300/#FFB340, sead→indigo #3634A3/#8987FF,
cas→brown #7F6545/#B59469, carrier→teal #007387/#5DE6FF, training→green
#1F7835/#30DB5B, historic→purple #8944AB/#DA8FFF. Red stays banned from
taxonomy (danger only). Recorded as `_surface_note_3` in the token file.

**Teal-as-accent retired.** `var(--carrier)` had become the Library's de facto
accent: `.osearch:focus`, `.ochk`, `.osel`, `.ocount`, `.incl .k`,
`.lmodcard:hover`, `.mgo`, `.epath.lib .go`, `.lmodtag`, `.lnew`, the
`.owntg` switch. All now `var(--accent)` (the switch and FREE tag →
`var(--green)`, Apple's own switch treatment). Chip text `#04211d` →
`var(--accent-text)`; button text `#0B0E11` on accent (`.kitbtn`, `.qgo .fly`,
`.dcta .prime`) → `var(--accent-text)` — white on systemBlue, the tested
pairing. Legacy `rgba(63,184,175,…)` / `rgba(45,212,191,…)` /
`rgba(88,166,255,…)` tints → `color-mix(in srgb, var(--accent) N%,
transparent)`.

**Tests** (60 in test_flightline.py, all mutation-proven): 14 new contrast
pairs (every `role_*` on sys_fill, every `role_*_dark` on sys_dark_fill, 4.5
floor); `test_the_role_palette_lives_only_in_the_generated_block` (each role
var defined exactly twice, both inside the markers);
`test_the_library_accent_is_the_accent_not_carrier_teal` (relic hardcodes
banned, `var(--carrier)` appears exactly once — the ROLES dict entry).
Verified by pixel-sampling live screenshots in both modes.

## [1.60.0] — 2026-08-12 — Lucide icon system; emoji retired from the UI

Rob: "The icons look a bit odd for this design... let's go with a different
icons that fit the new design."

**Inline SVG sprite** (32 Lucide glyphs, ISC; licence text vendored at
data/brand/LICENSE-lucide.txt) injected after <body>; `.icon` class inherits
currentColor at stroke-width 2 — both modes for free, no network fetch. SF
Symbols itself was ruled out: its licence restricts use to Apple platforms.

**Replacements**: entry cards (zap/library-big/sliders), Fly Now cards
(fuel/swords/flame/radio-tower), Library role badges via `roleIcon()`
(plane/flame/radio-tower/target/anchor/graduation-cap/clock), search, lock,
star, gear, pencil, dice, anchors, downloads, book, mode toggle (moon/sun via
innerHTML — was textContent), and the whole Mission Kit row set
(file-archive/file-text/clipboard-list/save/compass/medal/target/radio-tower/
triangle-alert). Renderers that printed `r.ic`/`t.ic` raw now wrap ids in the
sprite reference.

**Kept as text, deliberately**: ✓/✕, the semantic ●◆▲ shapes (kit redundancy
rule), the ⚓ inside a <select> option (options cannot render SVG), and one ⚠
inside caution prose.

**Chip contrast**: `.lchip #c7d2de`, `.acbadge #cfe8ff`, `.dprem #c3cfdb`,
`.incl #cdd8e3` — pale-on-dark hardcodes from the pre-token theme, invisible
on Apple white — moved to var(--dim)/var(--accent)/var(--text); the
dress-mode warning to var(--amber) (it is a genuine caution).

**Guards**: sprite present + ≥20 uses + licence file exists; emoji-range scan
over the frontend with a named allowlist. Mutation proven: an emoji smuggled
into a kit row fails the scan.

---

## [1.59.0] — 2026-08-12 — Apple HIG palette (iteration 4, settled); typography retained

Rob: "Let's go with the Apple design guide for their applications with the
exception of using the typography stack that we're currently using."

**sys_* tokens** in flightline.json — Apple's published system colours:
grouped backgrounds (#F2F2F7 light / #000-#1C1C1E-#2C2C2E dark), opaque
separators (#C6C6C8 / #38383A), systemBlue #007AFF / #0A84FF as THE accent,
semantic red/orange/green in both variants. day_* (blue-light) removed;
`_surface_note_2` records the full four-iteration history so it never gets
relitigated. **Deliberate deviation**: secondaryLabel darkened #8A8A8E →
#6E6E73 to hold WCAG AA on white; recorded in the note and in the contrast
test comments.

**Both mode blocks regenerated** by gen_theme.py; radius token 3px → 10px
(Apple's continuous-corner feel); the manual-idiom ink top-rules and 2px
footer rule reduced to hairlines (they fought HIG's cleanliness); topbar is a
light toolbar with the product name in accent blue.

**Documents untouched** — kneeboard/brief/guide keep Flightline paper+navy;
HIG governs applications, not print. Bangers banners stay (Rob's typography
exception) and now outline in systemBlue.

**Contrast pairs extended**: sys_dim on white/grouped at 4.5; white-on-
systemBlue tested at the 3.0 large-text floor with the deviation documented
inline (Apple's own button treatment is 4.0:1; our accent buttons are ≥15px
bold).

Verified by pixel-sampling both modes (topbar/banner/content/rail) — the
thumbnail misread happened AGAIN and the samples caught it again; eyes lose
to pixels 2-0.

---

## [1.58.0] — 2026-08-12 — Blue-light theme (third iteration); Bangers heritage banners

Rob, after v1.57.1's grey workbench: "I still think that the light color is
not good. I like the blue and the typography stack. I would also like to see
bangers font used." Then, mid-build: "I would like a light theme, just not the
creme and white combo."

**day_* surface ramp** in flightline.json: `day_bg #E3EAF1`, `day_well
#EDF2F7`, `day_line #8FA3B8`, `day_dim #44566A` — every light neutral
navy-tinted so the page reads as one blue system. `_surface_note_2` records
the three-iteration history (cream+white → grey workbench → blue light) so
the next person doesn't relitigate it. Unused navy-dark ramp from the aborted
navy-default direction removed in the same commit.

**Heritage banner component** `.slantb`: outlined parallelogram, skew(-12deg),
Bangers via `--font-banner`, counter-skewed inner span. Applied in TWO places
(hero "GET AIRBORNE", Library "MISSION LIBRARY") with the kit's constraint
documented at the CSS: 1-4 words, never controls/body/safety, two placements
total.

Mode names unchanged (`paper`/`night`) — the stored preference and tests keep
working; "paper" now means "day". Contrast: day_dim on white = 7.0:1, ink on
day_bg = 12+:1; the computed-AA test covers the token file's declared pairs.

---

## [1.57.1] — 2026-08-12 — Light mode rebuilt: white page on grey workbench

Rob: "The cream and white combo looks terrible." Correct, and the root cause is
worth recording: **a print surface was used as an app surface.** PAPER
(#F4F0E6) is a one-layer document ground; an app is layered (page/panels/
cards/wells), and cream+white+beige is three near-whites with no edges — the
same no-contrast failure the v3 elevation pass fixed in dark mode, recreated
in light. The kit's own specimen never does it: body #D7D8D4 grey, white page
on top.

**Tokens**: `workbench` (#D7D8D4) and `well` (#EFF0EC) added to
flightline.json with a `_surface_note` recording the paper-is-print rule.
Light mode: bg=workbench, panel=white, panel2=well, line #9BA0A4. Cream
remains the DOCUMENT ground (kneeboard/brief/guide untouched).

**Component pass**: `.step` gets a 3px ink top-rule; `.step h2` becomes
Barlow Condensed 19px (real manual headings); cards white with hover
border-navy + well fill; `.card.sel` inset 1.5px navy ring + well; `.card.dis`
opacity .3→.55 on well (ghosts → readable). whatbanner: navy band → note
block (white, 4px navy left rule). genbar: navy band → ruled page footer
(white, 2px ink top rule). Net: ONE navy band (the topbar).

**Bug**: `.card:hover` background was hard-coded #232E3A from the dark theme —
every card flashed near-black on hover in light mode.

Verified by pixel-sampling both modes' rendered screenshots (topbar/banner/
content/genbar) rather than eyeballing thumbnails — two earlier "wrong colour"
reads were text glyphs and an emoji.

---

## [1.57.0] — 2026-08-12 — Flightline Technical, Phase 2 (the site)

**`scripts/gen_theme.py`** writes the token CSS into `frontend/index.html`
between markers from `data/brand/flightline.json` — the same file the
kneeboard/brief/guide render from. Registered in `scripts/artifacts.py`
(rebuild rule); the registry's own meta-guard caught that release.sh didn't run
it and now it does. Hand-edits inside the markers fail preflight.

**Mode architecture.** One set of variable NAMES (`--bg/--panel/--accent/…`),
two `body[data-mode]` value blocks. That is what made a full re-theme surgical:
242 var() consumers untouched, the mode decides what the names mean. Paper is
the default (body tag); night persists via localStorage — a display preference
is device state, not recipe state, so share links stay byte-identical.

**Semantics applied**: Generate button navy with per-mode text colour
(`--accent-text`); `#status/#status2` slate not amber; BETA chip band-dim; the
topbar is the identity band (`--band/--band-text`); tabs re-anchored to band
colours. Radius sweep 6–20px → 3px token; hover-smoke shadows and the
body's amber/teal radial glows removed (kit: flat, rules not shadows). Rail
step dots are square mono procedure counters.

**Fonts self-hosted**: `/fonts/{name}` route validates against the directory
listing (no traversal), 7-day cache. Google Fonts link+preconnect removed —
opening the page no longer ships visitor IPs to a third party for typography.

**Tests**: 8 site guards added (43 total in test_flightline). One was born
vacuous and mutation caught it: `data-mode="paper"` also matches the CSS
SELECTOR, so the default-mode check passed with the default flipped to night —
now matches the body tag exactly. Token hand-edit mutation fails the
generated-block test; the flipped default fails the tightened test.

**Screenshot note**: docs/img/* regenerate on this release; the guide's
screenshots now show the paper site.

---

## [1.56.0] — 2026-08-12 — Flightline Technical, Phase 1 (documents)

Rob adopted the Flightline Technical kit (his uploaded design system, derived
from MIL-STD-38784B/MIL-STD-3001 research). Phase 1 of the plan in
`docs/flightline-implementation-plan.md`: tokens, fonts, and every generated
document. Phase 2 (the site) is next.

**One token source.** `data/brand/flightline.json` + `missiongen/brand.py`
(`COLOURS` attribute access, `font(role, size)` with DejaVu fallback,
`rail_text()`). `kneeboard.py` and `brief.py` local palettes deleted — they
import brand. Guide PDF and whatsnew/roadmap generators carry the same values.
`test_the_renderers_use_the_tokens_not_local_copies` is the anti-fork guard.

**Fonts vendored** under `data/brand/fonts/` (OFL texts alongside; licence
presence is a test): Barlow Condensed 700/800, Bangers, Source Sans 3 VF,
Source Serif 4 VF, IBM Plex Mono 400/500/600/700. VF weights set via
`set_variation_by_axes`. Every load degrades to DejaVu rather than failing.

**Identity rail replaces the classification banner** (kit DESIGN.md don'ts +
research §5D; Rob's call from the three plan questions).
`test_no_classification_markings_anywhere` scans the renderers so it cannot
creep back. Brief page footer's old "UNCLASSIFIED // TRAINING USE" line
retired; page locator centred in the footer rail.

**WCAG AA computed, not claimed**: `test_contrast_meets_wcag_aa` runs the
relative-luminance maths over all ten (text, surface) pairs the product
renders.

**Mutations proven**: slate lightened → contrast fails (1); kneeboard
re-hardcodes its background → anti-fork fails (1); banner text reintroduced →
scan fails (1); typo'd font filename → vendored-face test fails (1).

Kneeboard/brief pixels changed wholesale; all structural tests (export parity,
page ordering, footer truth) pass unmodified, which is the point of testing
structure rather than pixels.

---

## [1.55.0] — 2026-08-11 — Kneeboard export; military documentation register

Rob: "I'm tired of everything you making having a dark theme" and "All the
documentation should look like real military documentation."

**`POST /api/kneeboard`** — rebuilds the mission (determinism contract) and
lifts `KNEEBOARD/IMAGES/*` out as a ZIP of PNGs plus a README with the
`Saved Games\DCS\Kneeboard` install path. Stateless like `/api/brief`; 400
when `bb_kneeboard` is off. Wired as "Download PNGs" on the Mission Kit row.
`test_the_exported_pages_are_the_ones_in_the_mission` byte-compares the pack
against the .miz — the guard that matters, since a divergent export would put a
different card in the pilot's hand than in his cockpit.

**Military form register** (researched: DD Form 175, squadron MDCs, NATOPS
pubs). `kneeboard.py`: white paper, black ink, double-ruled outer border,
classification-style banner top and bottom ("UNCLASSIFIED // FOR SIMULATION USE
ONLY"), `DSS FORM 175-K` footer, all-caps masthead. `brief.py`: same banner,
black masthead band (the T.O. cover idiom), `DSS FORM 175-B` footer; NAVY/GOLD
palette retired. Chart plates keep doctrine colours — real aeronautical charts
are printed in colour; prose is photocopier-safe monochrome. Amber/gold chart
markers darkened for paper (the old values were tuned against a near-black page
and vanished on white).

**Footer truth**: `page_comms` said "no waypoints placed" unconditionally —
false once `bb_route` landed. Now takes `routed` and states whichever is true.
The two kneeboard-immutability tests were updated to EXEMPT page 01 and instead
assert it differs (a page that misdescribes its mission is the bug; pages 02/03
must still be byte-identical whatever optional cards are appended).

**Tests**: 6 export tests + 1 footer test. Mutations proven: export rebuilt
with a different seed (1 fail), README dropped (1), filename ordering prefix
dropped (2), stores-from-label (1), stores-for-clean-jet (4), stores-after-route
(1).

---

## [1.54.0] — 2026-08-11 — STORES kneeboard page; true-heading labelling

Prompted by a look at Digital Kneeboard Simulator, whose headline tab is
loadout. We compose the player's fit at build time and printed it in one place
the pilot cannot reach in flight.

**`loadouts.station_list(fit)`** returns `[(station, store name)]` from the SAME
`fit["pylons"]` dict `apply_fit()` hangs on the aircraft. Deriving the card from
`fit["label"]` would be a second source of truth and the label is lossy — it
collapses "2x AMRAAM" without saying which two stations.
`stats["player_pylons"]` carries it to the kneeboard.

**`kneeboard.page_stores()`** — station table, fit summary, JOKER/BINGO.
Rendered only when `pylons` is non-empty, so `player_arm=False` still produces
the three reference pages. Appended BEFORE the route card and after the three
reference pages, so 01/02/03 keep their meaning.

**Headings labelled TRUE** on the route card and in `routing.brief_lines`.
pydcs exposes no magnetic declination (`terrain.magnetic_declination` is absent
on every theater), and its runway `heading` is just the designator x10, so
declination cannot be derived empirically either. Authoring a per-theater table
without a verifiable source, or bundling a WMM/IGRF model that silently expires,
both fail the project's "never write an unverified value" rule. Labelled instead;
a verified variation source is now a roadmap item.

**Tests** — 6 added to `tests/test_routing.py` (shared file: both cards are
optional kneeboard pages and the ordering rule is common). Mutations proven:
card built from the label string instead of the pylon dict (1 fail), card
rendered for a clean jet (4), stores appended after route (1).

**Note for future page work**: adding an optional page shifts `kneeboard_pages`
for every armed mission, which broke two route tests that counted pages while
`player_arm` defaulted True. They now pin `player_arm=False` so each tests the
page it names.

---

## [1.53.0] — 2026-08-10 — bb_route: opt-in player flight plan

Rob: "What about now creating a set of core waypoints to the strike or target
area and then back? Maybe we have it as an option."

**The north star is unchanged, and this is the important part.** "Never place
player waypoints" was always shorthand for "we set the stage, you write the
play" — do not tell a pilot how to fly a mission he did not ask us to plan. A
route he opted into does not violate that. `bb_route` defaults `False`, and
`test_the_default_produces_identical_bytes_to_before_the_feature` plus a
98-recipe hash sweep confirm nothing else moved.

**`missiongen/routing.py`** — new module. `route_for()` is pure geometry (no
mission, no groups), so it is testable standalone and callable from the brief
and kneeboard: WP1 at 45% of the way out offset 90 deg, IP 9-16 km short offset
150 deg, TARGET at attack altitude, dogleg side from `rng.random()`. Returns
`None` under 8 km — a three-point route inside five miles puts the IP behind you
at rotation. `leg_card()` derives heading/nm/alt/kt/min ONCE and carries the
point along, so the cartridge and the kneeboard cannot disagree.

**Refactor, not a rewrite.** The `route: "strike"` template branch in
`builder.py` was 35 lines of inline geometry; it now calls `routing`, and the
same code serves `bb_route`. Verified byte-identical across all 98 advertised
(card, era, seed) combinations before and after.

**Kneeboard** — `page_route()`, appended as page 04 so the three reference pages
keep their numbers. Rendered only when a route exists.

**DTC** — `NAV[0]["waypoints"]` was hard-coded `[]` with the comment "never the
player's route"; it now carries the route when there is one and stays empty
otherwise, with `route_as_line` following. This was the one place the rule was
written into a data FORMAT rather than a code path.

**Warns when it cannot deliver**: `bb_route` with no target package appends a
warning rather than silently producing nothing, because a ticked box and an
empty F10 map reads as a bug.

**Tests** — `tests/test_routing.py`, 19 tests, weighted toward the DEFAULT
(no waypoints, no fourth kneeboard page, empty cartridge, identical bytes).
Mutations proven: default flipped on (5 fail), cartridge falling back to
reference points as waypoints (1), route card inserted first (1), dogleg removed
(2), landing point dropped (1).

**Two tests were too weak and were found by mutation, not review.** The cartridge
test asserted `waypoints == []` without checking the cartridge was populated at
all — vacuously true. The kneeboard test compared page FILENAMES, which are
positional (`01/02/03`), so inserting the route card at the front produced an
identical name list; it now compares page bytes.

---

## [1.52.0] — 2026-08-10 — Six statics per squadron per ramp

Rob: "The max number of statics displayed from a single squadron should be 6.
After that, a new squadron must be picked."

**The defect.** `_next_block()` drew a type + livery and parked 4-8 of them, but
kept no record, so the weighted draw could return the same identity for the next
block. Measured over 40 missions (8 map/era pairs x 5 seeds, `density=busy`,
`ramp_heavies=surge`): **440 runs over six, worst 22** (MiG-21Bis at Templin).

**`SQUADRON_MAX = 6`** in `dressing.py`, with `_squadron_id(type_id, livery,
tag)` defining identity — the `squadrons.json` name where there is one, else
`"<type>|<livery>"`, because that is what distinguishes two units on a ramp.

**Counted at PLACEMENT, not at block creation.** The first implementation capped
the block and cleared a "used" set when the pool ran dry, which still measured
440 over — blocks can also be abandoned mid-run (a heavy that will not fit the
next stand), so charging a squadron for aircraft it never parked would shrink
the ramp for no reason. `squad_count[sid]` increments inside the `_place()`
success branch; blocks carry their `sid` as a fifth element.

**`_draw()`** picks an identity with room left, giving each airframe three
attempts before dropping it from the pool — the livery is chosen *after* the
type, so a type whose primary scheme is full may still have room in another. One
full draw per type would collapse the ramp to one squadron per airframe even
where the livery pack offers several. Returns `None` when every identity is
full, and the field simply stops: an emptier ramp is the correct outcome, and it
is self-limiting at (distinct squadrons x 6).

**Data + validator.** Four `squadrons.json` entries asked for 8 (Akrotiri, Ramat
David, Incirlik, Kandahar) and are now 6. `validate_data_packs()` rejects any
count above `SQUADRON_MAX` — a file that says 12 and renders 6 is a file that
lies about the mission. Imported function-locally in `resolver.py`: `dressing`
imports `resolver`, so a module-scope import would be circular.

**Measured cost: 22.57 -> 19.22 parked aircraft per field (-15%).** Simulating a
merged livery pack recovered almost nothing (19.48), which disproved the
assumption that livery variety was the binding constraint — it is the number of
airframes in the theme. `test_a_theme_can_populate_a_busy_ramp` now records each
theme's ceiling and fails on any thin theme not listed in `THIN_THEMES` with a
reason.

**Tests** — `tests/test_squadron_cap.py`, 21 tests. Mutations proven: no cap
(15 fail), block capped but placements uncounted (15 fail), only one airframe
ever offered so nothing follows a full squadron (2 fail). A first attempt at
that third mutation passed against every test and was discarded as too weak —
the per-slot redraw recovers from it, so it was not a defect at all.

---

## [1.51.1] — 2026-08-10 — F-14B(U) on the formation offer lists

Rob: "It should have the F-14B(U) as well in the formation missions." It was
absent from `aircraft_choices` on all five cards. Added to `coldwar` and
`modern` (service window 1974-2006), next to the F-14A/F-14B on each list.

`F_14B_U` is the only offered airframe with no native pydcs class — registered
at runtime from `pending_aircraft.json`, inheriting `planes.F_14B`, real DCS
type id `F-14BU`. That is the failure mode worth guarding:
`test_the_tomcat_upgrade_flies_the_syllabus` builds all five stages in both
eras and asserts both groups carry `F-14BU`.

**A tautological assertion caught during mutation testing.** The first version
of that test compared `stats["lead_speed_kt"]` against `formation.cruise_for(cls)`
— the same function the build calls. Mutating `cruise_for` to look the airframe
up in `dcs.planes` by name (which loses every runtime-registered class and falls
back to the default 300 kt) left both sides agreeing, and 74 tests passed. Now
pinned to `cruise_for(P.F_14B)`, the class it inherits from: 10 tests fail under
that mutation.

---

## [1.51.0] — 2026-08-10 — Formation: a real lead, in-mission coaching, five stages

Rob: "The formation flying training has no planes that are generated to fly in
formation with." Diagnosed, and it was structural rather than cosmetic.

**The lead was in the player's group.** `formation.build()` made ONE
`flight_group_inflight(..., group_size=2)`, set `units[0]` to Excellent and
`units[1]` to the player. Aircraft in the player's group are WINGMEN — under his
F-key command structure, and treated as his flight whichever slot he occupies.
Now two groups: `Formation Lead` (single-ship, Excellent, own scripted route) and
`Dash 2` (the player), each with its own flight plan.

**Why the old tests passed.** `test_formation.py` looked up one group whose name
contained "Formation" and asserted its two units' skills. It never asked whether
the thing you fly on is an independent aircraft. Same lesson as Incirlik: the
suite tested the feature's internals and not the property the user cares about.
Rewritten to assert across two groups.

**In-mission coaching.** `_coach()` attaches three triggers via
`dcs.condition.UnitInMovingZone` / `UnitOutsideMovingZone` (moving zone locked to
lead's unit id) and `action.MessageToGroup`: a `TriggerOnce` opening brief at
`TimeAfter(20)`, and two `TriggerContinious` position calls. `MessageToGroup`
needs `m.string(...)`, not a raw `str` — a raw str reaches `action.dict()` as
`self.text.id` and `AttributeError`s at serialisation.

Both position triggers are guarded by flag `FORMATION_FLAG = 8801`: the drift
call requires `FlagIsFalse` and does `SetFlag`; the recovery call requires
`FlagIsTrue` and does `ClearFlag`. Without it a continuous trigger fires every
second the condition holds. Recovery uses `radius * 0.6` — a deadband, so sitting
on the boundary cannot ping-pong the calls. The whole function is wrapped in
try/except that appends to `warnings`: pydcs is vendored and moves, and losing
the coaching must never cost the mission.

**Syllabus restructured, 4 stages → 5.** `station`/`turns` retired;
`route` (1) → `close` (2) → `energy` (3) → `rejoin` (4) → `takeoff` (5).
Route-first is the instructional fix: fingertip-first starts a learner at the
highest-workload position they will hardly ever use. `takeoff` is a ground start
(`flight_group_from_airport`, `StartType.Warm`) for both aircraft, with a
fallback to air start if the field rejects it. `START_OFFSETS` gains `"route"`
(150 m out); `IN_POSITION_M` maps each start to a coaching radius.

**`RECIPE_ENUMS["formation"]`** updated to the new keys. Separately,
`Recipe.validate()` crashed with `TypeError: sequence item 0: expected str
instance, NoneType found` when rejecting a bad value for any enum containing
`None` — the error path itself was broken, turning a user error into a 500. Now
renders `None` safely.

**`cruise_for(aircraft_cls)`** — lead's block and speed derived from pydcs
`max_speed` (45%, clamped 120–320 kt; 5,000/8,000/12,000 ft by speed band). The
hard-coded 12,000/300 was the actual mechanism behind "it shouldn't just be an
F-16 tool": a Yak-52 cannot reach 300 kt. The leg loop's speed floor is now
`0.7 * spd` rather than an absolute 150 kt, which would have silently pushed a
piston trainer above its own briefed cruise every time the energy sortie asked
lead to slow down.

**Cards.** `form_station`/`form_turns` removed; `form_route`, `form_close`,
`form_energy`, `form_rejoin`, `form_takeoff` added, all three eras (WWII is new).
New template field `aircraft_choices: {era: [keys]}`, surfaced by `/api/options`
and rendered as a pill row in the Library drawer; `pickEra()` re-picks and
re-renders it, because leaving a Spitfire selected under Modern would hand the
engine a jet the era guard rejects. `setupFromLib()` applies the pick AFTER
`applyScenarioPreset()`, which calls `refreshAircraft()` and would overwrite it.

**Tests.** `tests/test_formation.py` rewritten (63 tests). Mutations proven to
fail the right test: lead moved back into the player's group (27 fail), flag
guards removed (`test_the_instructor_does_not_nag`,
`test_the_two_calls_use_opposite_flag_states`), equal radii
(`test_the_recovery_zone_is_tighter_than_the_drift_zone`), cruise hard-coded at
the call site (8 fail). `test_every_offered_aircraft_is_real_and_era_legal`
validates the new card data against pydcs and `aircraft_service.json`, because a
typo in a data list is invisible until somebody clicks it.

---

## [1.50.3] — 2026-08-10 — Symmetry applies to everything, not just weapons

Rob downloaded a mission and found the F-4 asymmetric. v1.50.1 only fixed half
of it: `_load` places the PRIMARY weapon on `_mirror_pairs`, but passes 1 and 3
did not pair at all.

**Pass 3 (fuel).** Walked `stations` in order and filled whatever was free, so an
F-4E a2a fit came out with a tank on station 1 and nothing opposite. Tanks now go
on in mirrored pairs, or a single centreline bag.

**Pass 1 (air-to-air rails).** Took "the outermost two stations" by
`-abs(s - mid)`, which picks two stations on the SAME wing whenever the outer
pair is not AAM-only. Now pairs rails with `_mirror_pairs` and fills outermost
first.

**The targeting pod stays single on purpose** — it has its own station, nobody
carries two, and the Phantom's Pave Spike is asymmetric on the real aeroplane.
`SINGLE_OK` in the tests names that exemption rather than leaving it implicit.

`test_each_weapon_class_sits_on_mirrored_stations` is the guard that was
missing: `test_stores_come_in_pairs` checks even COUNTS, and two bombs on
stations 3 and 4 are an even count on one wing. This checks STATIONS, per class.
Plus `test_fuel_is_never_hung_on_one_wing` for the specific case found.
Suite 1278 → 1358.

**Still open:** Rob's report did not name the exact mission, and the F-4E strike
fit as it stands (4x GBU-24 on 1/3/11/13, 2x AIM-9 on 2/12, pod on 6, tank on 7)
reads as symmetric about station 7. If he is seeing something else, the case
needs the specific card and seed.

## [1.50.2] — 2026-08-10 — Air start is offerable, not just settable

Rob opened Formation 1 in the Builder to change the aircraft to the F-14B(U)
and found the Start dropdown unpopulated.

The card sets `start: "air"`. `RECIPE_ENUMS["start"]` accepts it. But
`/api/options`'s `enums.start` hard-coded `["cold", "warm", "runway"]` — air
starts were template-only when that list was written — so the frontend ran
`select.value = "air"` against a `<select>` with no such `<option>`, which
silently does nothing. The control showed blank and the setting was lost on the
next `collect()`.

Affected every air-start card, not just the formation ones (the Fly Now tanking
and merge cards set `start: "air"` too). `enums.start` is now
`list(RECIPE_ENUMS["start"])` so the two cannot diverge again.

`test_every_value_a_shipped_card_sets_is_offerable_in_the_builder` checks the
WHOLE shipped Library against every published enum rather than the one field
that broke: a value the engine accepts, a card sets, and the UI cannot display
is the worst of the three states. Paired with the existing opposite check (the
UI must not offer what the engine rejects). Mutation-tested by restoring the
hard-coded list. Suite 1271 → 1278.

## [1.50.1] — 2026-08-10 — Loadouts are homogeneous, paired and symmetric

Rob: an F-4E strike fit came back as one LGB, one iron bomb, one tank and a
Sidewinder. Not random — structural. `derive_loadout` picked PER STATION,
independently: each station took the first class in the role's want-order that
it happened to support. Stations do not all support the same stores, so a jet
with varied stations produced a sampler. Measured before the fix:

    F-4E strike     3x GBU-24 + 1x Mk-84 + 2x AIM-9 + pod   3 weapon types
    F-4E cas        2x Maverick + 1x Mk-84 + 1x Walleye     3 weapon types
    Hornet strike   3x JDAM rack + 1x Mk-82 rack            mixed
    F-16 strike     2x JDAM + 2x GBU-24                     mixed
    A-10 cas        CBU-103 + CBU-87 + CBU-103              two variants of one

Real fits are HOMOGENEOUS (one primary store), PAIRED (even counts) and
SYMMETRIC. Selection now chooses one class, then the one store within it that
the most stations can carry — by definition the jet's standard fit for that job
— and hangs it on mirrored pairs.

**Broke it differently first, and the test caught that too.** A mirror axis
inferred from min/max of ALL stations found no pairs on the F-4E (bomb-capable
on 1, 3, 11, 13 out of stations 1-14, so `lo+hi-p` mirrored nothing) and the jet
came back carrying no bombs at all — worse than the mixed load. `_mirror_pairs`
now pairs the CARRIER LIST inward from both ends, which is symmetric by
construction and needs no geometry.

**A second weapon type**, also in pairs, when the primary runs out of stations
and budget remains: real CAS is mixed, but as pairs of each. The A-10 goes from
2 Mavericks + 3 tanks to 2 Mavericks + 2 rocket pods + LITENING + 1 tank.

**Two more found while fixing it:** `tanks_left` caps bags at 2 (3 on heavy) —
an unbounded loop had put a tank on every free station, giving the F-16 three
tanks and two bombs; and `needs_pod` was computed from the PRIMARY class only,
so an F-16 with JDAMs (no pod) plus a second pair of GBU-24s (very much pod)
flew with nothing to designate them.

**Position-specific armament needed a last resort.** A CH-47's door guns are a
different CLSID per door, so no single store reaches two stations and the
homogeneity rule left it completely unarmed. When no store reaches two carriers,
take the CLASS and let each station carry its own variant.

`tests/test_loadout_shape.py` (203) — across 10 airframes x 4 roles: the primary
weapon is actually carried (the no-bombs regression), at most two weapon types,
even counts, one store per class, not mostly fuel, plus the F-4E case by name
and pod-with-guided-weapon. Suite 1068 → 1271.

## [1.50.0] — 2026-08-10 — Formation flying: the player as Dash 2

Rob asked for standard formation-flying training missions for the Library,
designed as an instructional designer would.

**New engine capability, not a recipe preset.** Every other Library card is a set
of options the engine already had. Formation keeping needs the player to be the
WINGMAN on an AI lead, and nothing could express that: `slots > 1` makes every
seat a client, and a single-ship flight has nobody to fly on. `missiongen/
formation.py` builds a two-ship where `units[0]` is an Excellent-skill AI lead
and `units[1]` is the player. That inversion is the whole feature.

**The instructional design.** Formation keeping is a sight-picture and
closure-rate skill, not stick and rudder. The novice failure mode is invariant:
notice the error, make a large power correction, overshoot, oscillate. The
wingman controls three nearly-independent axes — fore/aft on throttle, lateral on
bank, vertical on tiny stick — and a learner fixing all three at once is
task-saturated. So `PROFILES` isolates them, one new variable per stage:

  station  straight and level, 15 min, nothing else   builds the picture
  turns    heading only, alternating, time to settle  the turn asymmetry
  energy   altitude and speed only                    anticipation
  rejoin   starts in spread, you close it             closure control

`test_each_stage_adds_exactly_one_variable` pins that spine — if the station
profile ever starts turning, the foundation sortie stops being a foundation.

The lead flies a fully scripted route (`legs` of heading/time/altitude/speed
deltas) at Excellent skill. Predictability is the point: a learner cannot build
a sight picture against a leader who improvises.

**`data/formation_refs.json`** — airframe-specific sight pictures, because
"line up the wingtip with the intake" is meaningless without naming which. Real
references for the F-16C (wingtip rail vs ventral fin), F/A-18C (LEX vs canopy
trailing edge), F-14A/B/B(U) (glove vane vs canopy, plus the warning that the
wings MOVE and the RIO can call closure) and F-4E (intake ramp vs wing leading
edge, anhedral stabilator as a V). `_generic` carries the principles for
everything else and says plainly that it is generic.

`brief_lines()` generates the instruction sheet per aircraft at build time
rather than storing it on the card — the sheet has to match the jet you chose.
It carries the three axes, the sight picture, how to fly it, a self-assessment
standard, and a symptom-first error table (symptom first because in the air you
notice the symptom, not the cause).

**Four cards**, both eras, F-16C modern / F-4E Cold War, all with `bb_sams` off,
threat dial 1, `player_arm` off and no BFM bandit — being shot at while
task-saturated teaches nothing.

**Found while testing:** `refs()` strips underscore-prefixed keys as comments,
which made `_generic` unreachable — an unlisted airframe got no instruction at
all instead of the principles. `sight_picture()` reads the raw pack for the
fallback.

`tests/test_formation.py` (25) — all 8 card/era combinations build and seat you
as Dash 2 (not lead), the sight picture follows the airframe across four jets,
unlisted airframes degrade honestly, each stage's brief states its own teaching
point and carries a standard and diagnostics, the syllabus spine holds, the
rejoin starts out of position, formation cards carry no threats, the lead flies
a scripted route, share links round-trip, and — the other direction — an
ordinary mission still seats you as element lead. Suite 1011 → 1068.

## [1.49.1] — 2026-08-10 — Aligned bases dress from their own nation; house logo opt-in

**Incirlik parked A-50s, Il-76s, Su-24s and MiG-29s.** Reported by Rob, blue
coalition, correctly aligned to Turkey, and dressed from the RED theme.

Mine, from v1.47.0 and live from v1.48.0. The per-field ramp theme added for
Nellis inferred a field's side like this:

    side = r.coalition if theme is own_theme else enemy_side

An identity check against a value the caller had already transformed:
`_atheme()` merges an aligned nation's roster over the side theme and returns a
NEW dict, so the check was False for **every internationally-aligned base on
every map** — Incirlik, Akrotiri, Ramat David — and each was re-resolved against
the enemy side.

`_dress()` now takes `side` as an explicit parameter. While fixing it, a second
instance of the same class: the replacement re-resolved the theme whenever the
user had picked one in the Builder, which would have thrown away the national
roster and put the map default on Akrotiri. The per-field table is now the only
thing that may override, and never for an aligned base.

**The house logo was the fallback.** `bb_branding` → `branding_enabled()` →
active sponsor, else **the shipped Authentic Media wordmark**. A fresh Fly deploy
has an empty sponsor store (it lives on a volume), so every mission got our own
logo on the launch splash. New `house_brand` flag, default `False`, `setdefault`
so existing manifests inherit off; `sponsors.house_brand_enabled()` /
`set_house_brand()`; admin toggle at `/admin/housebrand`. Nothing configured now
means no splash.

**BETA badge** beside the version in the top bar (`cursor: help`, explanatory
tooltip) plus a prose note on the landing page that names the Mission Editor as
the escape hatch. A bare badge says "this might be broken" without saying what
to do about it.

`tests/test_alignment_ramps.py` (8) checks aircraft TYPES rather than coalition
— the coalition was right the whole time — across Syria modern/coldwar and
Persian Gulf, plus Incirlik by name, the explicit-theme case, that red fields
still look red, that Nellis keeps its Red Flag ramp, and that `_dress` still
takes an explicit side. `tests/test_branding_and_beta.py` (9) covers the default,
manifest migration, end-to-end absence, that the switch still works when asked,
the admin route, and the BETA markup. Mutation-tested: restoring the identity
check fails 5 tests. Suite 994 → 1011.

## [1.49.0] — 2026-08-10 — A derived-artifact registry, and one release command

Rob asked how we stop things going stale. The honest answer was that we had
solved it exactly once: `test_release_notes.py` regenerates `docs/whatsnew.html`
and compares byte-for-byte, so that page cannot drift. Nothing else had any rule
at all. An audit at v1.48.0:

| artifact | said | behind |
|---|---|---|
| `docs/ROADMAP.md` / `roadmap.html` | v1.37 | 11 releases — and this page had **already** drifted 17 once |
| guide PDF cover | v1.46.1 | 2 |
| `REPLIT.md` | v1.16.2 | **32** |
| `docs/img/*.png` | — | pre-dated the entire Builder rework |
| `claude/build-status.md` | v1.21.1 | 27 (off-repo; fixed by hand) |

**`scripts/artifacts.py`** — the registry. One list of every derived file, its
generator, its inputs and ONE freshness rule, chosen by regeneration cost:

- `rebuild` — regenerate into a temp copy and byte-compare. Exact; also catches
  a hand-edit to a generated file, which would otherwise survive until the next
  build silently reverted it. Used for the two served HTML pages.
- `stamp` — record input hashes in `docs/.artifacts.json`, fail when inputs move
  on. For artifacts too slow to rebuild in a test (PDF, browser capture).
  Hash-based, not mtime-based, deliberately: git does not preserve mtimes, so an
  mtime rule passes on a fresh clone no matter how stale the file is.
- `version` — must mention `__version__`. For hand-written prose a script cannot
  generate. It cannot prove the prose is right; it forces someone to open the
  file, which is strictly more than the nothing that let REPLIT.md describe a
  build 32 releases old.

`EXCLUDED` records deliberate omissions with reasons (sample `.miz` files,
`USER_GUIDE.md`, the off-repo Claude project docs) so an omission is
distinguishable from an oversight six months later — the exact failure this
whole file exists to prevent.

**`scripts/release.sh <version>`** — bump, verify the notes and changelog exist
(before the slow steps, so you don't spend a minute on screenshots to fail on a
missing changelog entry), regenerate everything registered, re-stamp, run
preflight, package. Prints a reminder about `claude/build-status.md`, which no
test here can reach.

**preflight now BLOCKS on staleness** (Rob's call over warn-only): warn-only is
the honour system with extra steps, and the honour system produced the table
above.

**`scripts/capture_screenshots.py` rewritten — it had rotted itself.** It
hardcoded the wizard's screen keys and entry path; v1.19 put a landing page in
front of the Builder and v1.46 renamed the screens (`threats` → `opposition`,
carrier became a conditional block on Flight). It timed out on
`#maps .card` — which resolves but is not visible until you enter the Builder —
and because nothing ran it, nobody found out. Now it enters through the real
navigation, reads `SCREENS` out of the running page and **fails loudly** if a
documented screen has disappeared. Also: hides `position: fixed`/`sticky` chrome
before element capture (a full-height screenshot is stitched from several
viewports and fixed elements re-render in every slice, printing the nav bar
across the middle of tall screens), and drives a real coastal/carrier scenario
so `carrier.png` actually contains a carrier.

**Fixed by this release:** ROADMAP.md rewritten to v1.48.0 reality (six-screen
Builder, 12 theaters, both sides armed, ramp heavies, 971 tests in the zip) with
the AI-package loadout gap and the blocked-on-liveries item stated honestly;
REPLIT.md's "what's new since v1.16.2" section deleted rather than updated,
because a summary pinned to a hard-coded past version can only ever rot —
replaced with a pointer to RELEASE_NOTES/CHANGELOG, and its verification
checklist de-numbered ("8 templates at v1.19.1" → no count, since a number in a
checklist is a number that goes stale); guide PDF and all 11 screenshots
regenerated.

**`tests/test_docs_fresh.py` (23)** — walks the registry, enforces all three
rules, and pins the meta-properties: every artifact carries a rationale, every
generator and input exists, exclusions are justified, preflight blocks rather
than warns, and `release.sh` runs every registered generator (a registry entry
is worthless if the release command ignores it). Mutation-tested: editing the UI
stales the screenshots, hand-editing a generated page fails rebuild-and-compare,
and bumping the version stales both hand-written docs. Suite 971 → 994.

## [1.48.0] — 2026-08-10 — Arm the player's aircraft from the mission kind

Rob asked how hard it would be to give the player a default loadout per mission
type. Investigating turned up that the player's jet spawned with **empty pylons
on every mission kind** — the same `load_task_default_loadout()` no-op that left
the bandits clean until v1.44.0, but documented as intentional ("your loadout is
yours to set in the Mission Editor"). It was never a decision.

**Derived, not authored.** 75 flyable airframes x 7 mission kinds x 3 eras x 3
weights is thousands of entries and thousands of chances to hang a store on a
station DCS refuses. `derive_loadout()` composes a fit from pydcs's per-airframe
`PylonN` legal-store lists — the same source `test_loadouts.py` checks the AI
table against — so a derived fit *cannot* be illegal by construction. An
authored entry always wins, and remains the override for anything derivation
gets wrong. Fully deterministic: no rng, stable sort on (service year, name,
clsid), because a share link is a byte-for-byte contract.

Three passes: AAM-only stations first (so a strike fit never spends its
centreline on a Sidewinder and nobody flies with empty rails), then the primary
weapon from the middle of the wing outward, then a targeting pod if the fit
needs one and fuel on what's left. `KIND_ROLE` maps the Builder's mission kinds
to roles; `ROLE_WANTS` maps roles to store classes.

**`store_class()`** — a superset taxonomy over `weapon_class()`, kept separate on
purpose: `weapon_class` feeds `implication()`, whose `_CLASS_ORDER` is
deliberately air-to-air only, and folding the vocabularies together would make
the ENEMY AIR brief start reasoning about Mavericks. Descriptive patterns first,
then a designation fallback. **The designation layer is not optional**: some
CLSIDs carry only the bare designation ("AIM-7M") rather than the descriptive
name, and the miss that mattered was the **AIM-54 Phoenix** — the Tomcat's whole
reason for existing was classifying as `other` and could never be selected.
Unclassified stores: 336 -> 97 of 1472, and the tail is now smoke, decoys, empty
racks and camera pods.

**Five defects found and fixed during the build, each by measuring:**

1. `player_loadout` inherited `loadout_for`'s deliberate `cap` fallback, so the
   sixteen airframes in the AI table flew their authored air-to-air fit on every
   SEAD, CAS and strike mission — picking a mission type changed nothing.
   Only an EXACT authored role counts now.
2. The F-14B(U) is registered at runtime as a subclass of the F-14B, so it never
   appeared in the pylon index under its own id and derived an **empty** fit.
   `_pending_base()` asks the donor airframe.
3. No cap on air-to-air stations: a "strike" F-15E came back with eight AMRAAMs
   and two bombs. `_AAM_STATIONS` caps non-CAP roles at 2-4, outboard first.
4. Ranking by name picked the AIM-120B over the C (B sorts first) and the
   AIM-9P over the AIM-9M (P is the older missile). Ranking is by in-service
   year now.
5. A modern MiG-21Bis carried 1974 R-13Ms, out of service since 1995, because
   the AI table's wildcard `*` entry outranked era discipline — those fits were
   written for the era the threat pools field the jet in, and the pools are
   already era-gated, so nobody had checked them against another decade. A
   wildcard entry now has to pass `_era_ok` to win.

**105 air-to-air stores had no service window at all**, which meant a 1959
RS-2US beam-rider was era-legal forever and got selected for a modern MiG-21.
A single missile has many CLSIDs (bare store plus every rack variant), so
`weapon_service.json` gains a `_families` layer keyed by designation, matched
longest-first against the store name — 78 families covering the A2A inventory
plus the guided A2G weapons where the era is just as visible. Also:
"Semi-Act Laser" (Kh-25ML, Kh-29L) was classifying as a radar AAM.

**New:** `Recipe.player_arm` (bool) and `Recipe.player_load`
(light|standard|heavy), on the Flight screen, in share links, in the rail
summary when not the default. `loadouts.apply_fit()` split out of `arm()`.
Surfaced in `stats["player_loadout"]`, the `X-Kit` header, the Mission Kit panel
and a new "## Your loadout" section in the brief.

**Player liveries.** `dressing.player_livery()` — the player's aircraft had no
livery path at all; `_pick_livery` only ever ran on parked statics.
`types.<type>.player.<era>` in liveries.json keys a marking to a period, so
VF-11 Red Rippers (F-14B, 1996-2005) is the modern default for the F-14B and
F-14B(U) and a Cold War mission gets an F-14A+ era squadron instead. Nothing is
written while the pack is unverified — same v1.46.4 rule — so this is inert
until `dump_liveries.py` runs. `_pending_key()` maps `F-14BU` -> `F_14B_U`,
which hyphen-normalisation alone cannot do. The pack's `_note` no longer claims
unknown ids are harmless; that belief is what shipped v1.46.4.

**Coverage:** 672 of 763 (airframe, kind, era) combinations produce a fit. The
remaining 91 are 8 airframes pydcs offers no pylon stores for — trainers,
aerobatic types, and the Gazelle variants whose armament is part of the
airframe. `tests/test_player_loadout.py` lists them by name and separately
asserts each one really is unarmed, so the list can't become a place to hide
broken fits.

**`tests/test_player_loadout.py` (450)** — sweeps every flyable airframe, checks
every store in a representative slice against pylon legality and era windows,
pins that mission type changes the fit, that a strike jet isn't all AAMs, that
the Tomcat carries the Phoenix, that derivation is deterministic, that an
authored entry wins, the weight dial, share links, the classifier, and the
F-14B(U) livery against a simulated verified pack. Mutation-tested: disabling
`arm()`, removing the pending donor, and restoring the `cap` hijack each fail
the specific test written for it. Suite 521 -> 971.

## [1.47.0] — 2026-08-10 — Heavies can park: airframe-aware stands + a reservation

Reported by Rob: Nellis missions rarely have tankers or AWACS on the field.
Measured, it was worse than "rarely" — **zero** parked tankers or AWACS across
eight seeds of a default Nevada mission, and 0-1 heavy aircraft of any type on
the whole map. Cold War Germany: 0-2 across fifteen airfields. Normandy: 0.

Three independent causes, all fixed:

**1. The stand test was a hardcoded rectangle.** A stand counted as heavy-capable
if `slot.large or (length >= 60 and width >= 55)`. NTTR sets `large` on nothing —
Nellis has 247 stands and the flag is False on every one — so everything rode on
the fallback, which exactly **six** Nellis stands passed (Creech and Groom Lake:
zero). It was also airframe-blind: it refused a C-130 (29.8 x 40.4) a 42 x 34
stand it fits, and would have offered a B-52 (49 x 56.4) a 60 x 55 stand it does
not.

pydcs ships the real box on every type (`width` IS wingspan), so `stand_fits()`
now asks the aircraft. Tolerance is mode-dependent and documented:
`STAND_TOLERANCE` is 1.0 for `parked_ai` (a live uncontrolled flight DCS may
taxi must actually fit) and 1.25 for `static` (inert scenery on an apron that
continues past the painted box — how a real KC-135 sits on a 40 m spot with its
tail over the taxi lane). A terrain author's `large` flag is still a hard yes.
Nellis goes from 6 heavy-capable stands to 37, with the C-17/B-52 class still
restricted to the six real ones.

**2. Heavy stands were shared with the fighter pool** (`large_w + plane_w`), and
fighters won them twice over: pool weights run ~11 fighter to 8 heavy, and a
fighter block is 4-8 deep against 2-3, so one F-16 block could swallow the lot.
`RAMP_HEAVIES` now reserves (share, floor, ceiling) stands per field before the
fighters fill in.

Three iterations were needed and each was caught by measuring, not reasoning:
- A share alone gave 2 stands at Nellis (12% of an AUTO_CAP-flattened target of
  18) — one heavy block, hence a ramp with three B-1Bs and no tanker. Added a
  floor.
- The reservation was then not honoured: `free` is in adjacency order so blocks
  read as squadron rows, but the fill stops at `target` and the roomy stands are
  often late in that order — the loop ran out of budget before reaching them, so
  `surge` placed exactly as many heavies as `auto`. Reserved stands are now
  served first.
- With a floor and no ceiling, 60% fill reserved every capable stand and parked
  **30** heavies at Nellis including ten B-1Bs. Added a ceiling, plus
  `SHARE_CEILING = 0.55` so fighters can't vanish, plus floor scaling by the
  field's own capable-stand count so a 48-stand test site doesn't reserve the
  same line as Nellis's 247.

Also: heavy block types drain the pool before repeating (measured 1.8 B-1B vs
0.6 KC-135 from a pool where both carried weight 2), the reservation prefers the
roomiest stands, and a block that runs from a roomy stand onto a tighter one is
dropped rather than clipping a B-52 into a fighter spot.

**3. Nevada dressed Nellis with the generic `usaf` ramp.** The `red_flag` theme —
"Nellis surge ramp", the only blue theme carrying an E-3A — existed in *both*
eras and the map used neither.

First attempt set `blue_theme: red_flag` map-wide and put B-1Bs and a Sentry on
the Groom Lake apron, which is the opposite of the point. Replaced with
`<side>_field_themes`, a per-field override consulted by `resolve_theme()` ahead
of the map default (an explicit user choice still wins). Nevada: Nellis →
`red_flag`; the test sites keep `usaf`/`usafe`. The `red_flag` heavy pool was
reweighted to lead with the tanker — tankers deploy in and sit for two weeks,
the bombers and the Sentry are guests.

**New: `Recipe.ramp_heavies`** — `none | light | auto | surge`, on the Airfields
screen, in share links, in the outline rail (shown only when not the default).

Measured at Nellis, per mission, 6-8 seeds:

| setting | heavies | tanker/AWACS |
|---|---|---|
| before | 0-1 *(whole map)* | **0** |
| none | 0 | 0 |
| auto (default) | 4 | 1-4 (avg 2.4) |
| surge | 9 | 2-6 (avg 4.0) |

Map-wide totals rose (Germany coldwar 0-2 → 59 across ~15 fields; Normandy
0 → 36) while **total static count is unchanged** — heavies substitute for
fighters on stands the fighters were taking, so no mission got heavier and no
frame rate moved. `test_other_maps_gain_heavies_without_gaining_aircraft` pins
that.

**`tests/test_ramp_heavies.py` (27)** — pins the NTTR fact the bug rests on (no
stand flagged large), the pydcs dimensions every threshold is derived from, the
fit test against the three real Nellis stand sizes, the per-field theme
(including that Groom Lake gets no Sentry — with a non-vacuity guard that the
field is actually dressed), monotonicity across the four settings, that the
reservation substitutes rather than adds, the ceiling, pool-drain, floor
scaling, share-link round-trip, older-link default, and UI/enum agreement.
Mutation-tested: reverting the stand test, the reserved-first ordering, or the
per-field theme each fails the specific test written for it.

## [1.46.5] — 2026-08-10 — Rebuild the test suite; ship it in the zip

No product change. This restores and extends the regression suite lost when the
build environment was reclaimed, and closes the hole that made the loss
permanent.

**The hole.** `scripts/package.sh`'s MANIFEST shipped `missiongen`, `server`,
`frontend`, `scripts`, `docs`, `samples` and `vendor` — and not `tests`. The
release zip is this project's backup of record. When the workspace went, the
code came back from the 1.46.1 zip and a 188-test suite did not, and every
invariant it guarded went unprotected until it could be rewritten. `tests` is
now in the MANIFEST, `package.sh` re-opens the zip and fails the build if
`tests/conftest.py` isn't in it, and `tests/test_packaging.py` asserts the
MANIFEST contents so the entry can't be dropped again.

**18 tests → 492.** New modules:

- `tests/conftest.py` — puts the repo root and `vendor/` on `sys.path`, so the
  suite runs as a bare `pytest` from a fresh unzip. It previously required
  `PYTHONPATH=vendor`, which is the kind of undocumented incantation that stops
  people running tests at all.
- `test_loadouts.py` (216) — every airframe a threat pool can spawn resolves a
  fit in the era it flies; every authored CLSID is checked against pydcs's
  per-airframe `PylonN` legal-store lists (DCS silently drops an illegal store,
  so this is otherwise invisible); every store is checked against
  `weapon_service.json` and the era window; the BFM adversary carries no radar
  missile in any era; the Threat Dial's `light` variant actually resolves; and
  four real missions are built and their enemy pylons read back out of the
  `.miz`. WWII is included rather than skipped — guns-only is the one case where
  empty pylons are correct, and it needs coverage precisely because it looks
  like the bug.
- `test_templates.py` (135) — all 33 advertised (card, era) combinations, four
  ways: the pinned aircraft's service window against the era, the map's
  `presets` against the era, `Recipe.validate()`, and a full build with a
  `mission=` preamble check on the result.
- `test_builder_ux.py` (44) — the frontend is 3,000 lines of vanilla JS with no
  build step, and four defects this cycle were broken *relationships* a compiler
  would have caught: a screen naming a step that doesn't exist, a rendered block
  no screen lists (`sec_kind`, orphaned from v1.19 to v1.45), a duplicate
  top-level `const`, a `STEP_COND` entry dropped. Also cross-layer:
  `MISSION_KINDS` must equal `RECIPE_ENUMS["mission_kind"]`, every kind's
  `patch` may only set fields `Recipe` has, and every `<select>` whose id is an
  enum field may only offer values that enum accepts.
- `test_determinism.py` (18) — same-process byte-identity, plus the one that
  matters: builds in a **subprocess** under two different `PYTHONHASHSEED`s.
  Both pydcs nondeterminism sources are invisible to a same-process test, so a
  same-process comparison passed for the entire period the bug existed. Share
  links round-trip, rebuild identical missions, carry only a diff against
  defaults, and a pre-`mission_kind` link still decodes.
- `test_release_notes.py` (11) — current version has an entry, at the top, with
  a body; versions descend; no duplicates; CHANGELOG covers it too; the user
  page contains no `.py` filenames (the two-audience split); and
  `docs/whatsnew.html` is **byte-identical** to what `build_whatsnew_html.py`
  produces right now, so a hand-edit can't survive to be silently reverted.
- `test_regressions.py` (13) — the two production 500s through the real ASGI
  app. Both were invisible in a unit test of the thing that broke: `_header_safe`
  was never wrong (the *engine* emitted an em dash), and `people()` was never
  wrong (the *admin page* divided by a `max(..., default=1)` that returns 0 from
  a non-empty list of zeros). Plus: `X-Kit` must `json.loads`, the analytics
  ledger must contain no IP/UA/fingerprint field, `/api/health` must 503 on a
  data-pack error rather than 200-with-`ok:false`, and R-4808N must still have
  its 14 points and its citation.
- `test_packaging.py` (37) — the MANIFEST, above.

**Each new guard was mutation-tested**: the invariant was broken, the specific
test was watched to fail, and the code was restored. Notably the hash-seed test
caught the reverted tail-number patch while every same-process test stayed
green, which is the whole argument for it.

**`scripts/preflight.sh` now runs the suite** before it says "clear to deploy",
skipping (not failing) if `pytest` isn't installed, since preflight must work on
a fresh unzip before the launcher has built its venv.

**Found, not fixed** (dormant, recorded so it isn't rediscovered): the
`<span class="n">` step badges in `frontend/index.html` still carry numbers from
the original eight-step wizard — `sec_kind` says 3 while it sits on screen 1,
Review says 9 of 6, and two blocks both say 2. They are hidden by
`.step h2 .n { display: none }`, so nothing renders wrong today.
`test_the_step_number_badges_are_hidden_or_honest` returns early while that rule
is present and starts enforcing the numbers if it is ever removed.

## [1.46.4] — 2026-08-10 — Stop writing guessed livery names

**Parked statics stopped wearing default skins because we were writing livery
names we had guessed.** `data/liveries.json` is a hand-authored pack of DCS
livery folder names, and it has always carried `"_verified": false` — the flag
`scripts/dump_liveries.py --merge` flips to `true` after reading the real names
out of an install. **The engine never read that flag.** One busy Caucasus
mission was shipping ~390 static aircraft each stamped with an unverified
string.

The comment in `dressing.py` claimed an unknown id was harmless because DCS
falls back to the stock skin. Rob's report is direct evidence that it doesn't:
a name DCS doesn't recognise gives you a wrong or blank aircraft, not the
default one. Nothing server-side can validate these — pydcs's `liveries` package
is a *scanner* over a DCS install, not bundled data, so this is the loadouts
problem without a loadouts-style source of truth.

So the engine now honours the flag: while the pack is unverified it writes no
`livery_id` at all and DCS picks its own default, which is the correct-looking
result. Running `scripts/dump_liveries.py --merge` against a real install
verifies the pack and the nation-correct skins switch on — including any paid or
third-party liveries, which is the only way they could ever have worked.

It says so, too, rather than being silently different: a warning on every
affected mission, `"liveries_verified"` in `/api/health`, and honest copy on the
Airfields screen in place of the old claim that skins already match the nation.

## [1.46.3] — 2026-08-10 — The comms card now describes the mission

Rob asked whether the printed frequencies are the ones the mission actually
uses. Most were. **Three were not**, for two separate reasons, both verified by
reading the generated `.miz` rather than the code.

**Tanker and AWACS spawned on 251.0.** pydcs's `refuel_flight()` and
`awacs_flight()` attach a `SetFrequency` *task* at waypoint 2 but leave the
group's own radio at their 251.0 default. So Texaco and Overlord started
**co-channel on 251.0**, off the briefed frequency until they reached their
second waypoint, and the Mission Editor showed 251 beside a card saying 253.625.
The carrier air wing's Hawkeye had the same defect. All three now call
`set_frequency()` as well, so the group is on the briefed frequency from t=0 and
the waypoint task is belt-and-braces.

**The carrier was on 264.425 Hz.** `ShipGroup.set_frequency()` takes **hertz**
(pydcs's own default is `127500000`) while `FlyingGroup.set_frequency()` takes
**MHz** — two conventions in one library, and we passed MHz to both. The whole
battle group was therefore on 264.425 Hz and never on the frequency the card
printed. Converted at the call site, with the trap documented there.

**Confirmed correct and left alone:** the player's flight frequency (305.725 on
the group and on COMM1 CH1), every cockpit preset behind the CHAN column, the
air wing's CAP and plane guard, the tanker's TACAN 39Y beacon, the FARP pads
(which store theirs as `heliport_frequency` in MHz — a third unit convention in
the same library), and Guard/Tactical, which have no group by design.

`tests/test_comms_truth.py` walks the printed ladder and checks every row
against the mission — including that the tanker and AWACS are not co-channel.
Four of its six tests fail against the previous code.

## [1.46.2] — 2026-08-10 — F-14B(U): Cold War, and just its name

**The F-14B(U) is selectable in the Cold War.** Its service window was
[1994, 2006], which does not overlap the Cold War era window [1965, 1985], so
the era guard excluded it. The (U) is a community *uprated* Tomcat rather than a
historical airframe, so its window is a product decision rather than a fact:
it now runs from the type's fleet service in 1974. The stock F-14B keeps its
honest 1988 date and the F-14A remains the period-correct Cold War Tomcat —
only the community variant gets the wider window.

**And it's called F-14B(U).** Every native entry in the roster is a bare type
designation ("F-14B", "F-16C_50") with the popular name supplied separately, so
the UI composes "F-14B · Tomcat". The F-14B(U)'s label was
"F-14B(U) Tomcat (Heatblur)" — the only aircraft carrying a vendor name, and
because the string ended in "(Heatblur)" the "strip the trailing popular name"
rule never matched, so it rendered verbatim with "Tomcat" in it twice. The label
is now the bare designation, `aircraft_names.json` and the frontend `AC_NAME`
table both carry its popular name, and it renders "F-14B(U) · Tomcat" like its
siblings. The vendor is credited in the site footer, which is the right place
for it.

**Fixed while testing: a pending module warned four times.** `_resolve_aircraft`
runs several times per build — roster gating, the player group, the DTC check,
the brief — and each call appended the same "verified DCS type id" note. Four
copies of a 130-character warning spent 500+ characters of the 900-character
`X-Warnings` budget saying one thing. Warnings from that path de-duplicate now.

*Note: `tests/` is not part of the release zip, so the suite did not survive the
workspace being reclaimed. `tests/test_pending_aircraft.py` covers this change;
the rest of the suite needs rebuilding.*

## [1.46.1] — 2026-08-09 — Carrier Qualification, and real arrows

**Carrier Qualification was broken by its own data, not by the server.** The
header 500 in 1.45.1 was real but it was only half the story: the card declares
`eras: ["coldwar", "modern"]` while its recipe pins the F/A-18C, which entered
service in 1987. Pick it in the Cold War — the Builder's default era — and the
era guard correctly refused a jet that didn't exist yet, so the card failed with
a 400. A template's pinned aircraft is a DEFAULT, and a default that spans eras
has to vary by era.

Templates now carry `by_era` overrides, resolved by
`missiongen/templates.effective_recipe()` and applied by the Library through the
same merge, so the frontend and the engine cannot drift on what a card builds.
Carrier Qualification flies the F-14A in the Cold War and the Hornet in the
modern era. **Six other cards had the same defect** — CAP/Alert-5, SEAD Range
and four Quick Flight cards all pinned the F-16C while offering the Cold War —
and two Quick Flight cards offered WWII on a default map with no WWII preset.
Nine advertised (card, era) combinations in total did not build; all nine do
now. `tests/test_templates.py` sweeps every combination the UI offers and builds
it for real, plus a structural check against the service-window data, so a card
can no longer advertise an era it cannot fly.

*(The F-4E fix needed a second pass: `F_4E` is the AI-only Phantom, `F_4E_45MC`
is the flyable module. The sweep caught it.)*

**Air routes draw a real arrowhead.** The corridor axis built its head from two
more line segments angled back from the terminus at ±148°. At map scale that
reads as a bent whisker rather than an arrow — the segments stay hairline at
every zoom, so the head never looks solid. DCS has a proper Arrow primitive, a
filled polygon, and the carrier BRC marker was already using it. Both the
selected threat axis and the historical airspace corridors now use it, sized to
the lane (9–26 km) and filled solid rather than with the 7 %-alpha wash meant
for the lane body. The shaft stops short of the head so the line doesn't show
through it. Angle convention documented in one place: the shape runs along +Y
(due east) at angle 0, so a compass bearing is rebased by −90.

## [1.46.0] — 2026-08-08 — Use the width, stop folding things

Rob, on the v1.45.0 wizard: the theater screen is overloaded, everything is
collapsed, you have to click to open it and it goes down too far. He's right,
and it was my design. v1.45.0 "fixed" eight screens by making four — one of
which was **four collapsed screens stacked on top of each other**. You arrived
with 4 blocks shut, it was an accordion so opening one closed the last, and you
never saw two at once. That is compression, not simplification.

**The measurement that changed the answer.** The content column was hard-capped
at 980 px at every window size: 154 px wasted at 1366 wide, **708 px at 1920**,
**1348 px at 2560**. We were solving a vertical problem by hiding things while
discarding up to 1348 px horizontally. Column raised to 1280 px, dense screens
laid out in two newspaper columns, and the crowding goes away without hiding
anything: **Support & presentation went from 1266 px with four blocks collapsed
to 652 px with nothing collapsed.**

**Six screens, each about one question, nothing folded.** Mission (era · kind ·
map · corridors) → Flight → **Opposition** → **Airfields** → Support &
presentation → Review. Threats gets its own screen back because the Threat Dial
is the most consequential creative decision in the Builder after the mission
kind, and burying it as one accordion row undersold it. Airfields gets one
because what parks on your ramps is a real scenario decision. Six screens that
each fit beats four where one is a filing cabinet — the count was never the
problem.

**The rail is now a live outline.** Widened to 288 px and given a second level:
the current screen's blocks, each with its live value, each a jump link that
flashes its destination. The whole Builder is legible from the rail without
opening anything, which is a stronger promise than "nothing on THIS screen is
collapsed" — and it is what let the accordion go.

**Three things Rob called individually.** Air corridors no longer start folded
(they were folded exactly when nothing was selected — precisely when you need
to know lanes exist). Pattern traffic moved out of Support & extras to sit
beside your base on Flight, because it is about YOUR field as the mission
starts. And the per-base fill table — 87 controls, 46 number inputs and 16
sliders — left the wizard for its own panel behind a button that says what it
opens; it is the one thing still behind a click, and it is why the Airfields
block overflowed no matter what the layout did.

**Fixed: carrier deck configuration appeared on landlocked maps.** Folding the
Carrier screen into Flight in v1.45.0 dropped the condition it used to carry as
its own screen, so the deck panel rendered on Cold War Germany where the carrier
option is disabled and the base list has no carrier in it. Steps now carry their
own visibility condition. My regression from v1.45.0.

Guarded: `tests/test_builder_ux.py` now fails if a wizard block becomes
collapsible again, if the accordion machinery returns, if the content column
narrows below 1200 px, if a screen block has no rail entry, if pattern traffic
goes back into the support list, if the carrier deck loses its condition, or if
the per-base table returns to the wizard step.

## [1.45.1] — 2026-08-08 — One button builds a mission

**The footer's GENERATE .MIZ competed with everything else.** On Review there
were literally two buttons with the same label — a green one in the panel and an
amber one welded to the footer, 383 px apart. On the theater screen a filled
amber "Next: Review & generate →" sat 64 px above the footer's filled amber
GENERATE .MIZ. Three things asking to be pressed, two of them saying generate,
and the sticky wizard nav shipped in 1.45.0 made the collision permanent rather
than occasional.

The footer is now a **status strip**: the live recipe line and whatever the last
action reported, with nothing in it that can be pressed. Generating lives in
exactly one place — the Review screen — so every screen has a single filled
primary: Next on 1–3, GENERATE .MIZ at the end. It wears the brand amber rather
than green, because green is the rail's "done" state and the same action should
not have two colours. The final screen is now called **Review**, since
"Review & generate" made the Next button read like a third generate control.
Status messages mirror into the Review panel so the confirmation appears where
you clicked. The generate handler became a named function, so removing the
footer button did not strand the Library drawer's one-click build.

**Fixed: carrier missions returned a 500 instead of a mission.** Found while
testing the above. HTTP headers are latin-1 by spec and the engine writes prose
straight into `X-Warnings`, so one warning containing a typographic character
made Starlette raise and the whole download fail. The warning in question —
"Carrier tanker is the KA-6D (A-6E) — the air wing's own gas" — fires on every
Cold War carrier mission with a tanker, which means the Library's **Carrier
Qualification** card had been failing outright. Header values are now
transliterated (— to --, × to x) and hard-encoded as a safety net. Pinned by a
test that generates a real carrier mission and fails with a 500 against the old
code.

## [1.45.0] — 2026-08-08 — The Builder asks what the mission is

**The Builder had no way to say what the mission was.** The Scenario picker was
orphaned in v1.19 when scenarios moved to the Library: it stayed in the markup
with `display:none`, belonged to no wizard screen, and was unreachable for
twenty-six releases. Every Builder mission was open tasking whether you wanted
that or not.

**Mission is now the second question**, right after era, before the map — a row
of seven kinds (Open tasking, Air-to-air, Strike, Close air support, SEAD,
Carrier ops, Training) drawn from the roles the curated templates already carry,
so the Builder asks *what kind of sortie* while the Library stays the place for
named missions and the two doors don't compete. Picking one stamps defaults onto
the real building-block controls — visible on the screens that own them, never a
parallel hidden state — and prints one line saying exactly what it changed. It
locks nothing: every later screen stays editable and a hand-edited recipe still
wins. `mission_kind` is additive with a default of `"open"`, so every existing
share link decodes to the same mission it always did.

**The wizard nav was invisible on arrival.** It sat at the end of the content,
so on a 1366×768 laptop — the most common laptop resolution — Back / Next /
"Step 3 of 7" landed 95 px below the fold underneath the fixed generate bar,
which sliced the panel mid-sentence. The page scrolled by exactly 123 px with
nothing on screen to say so. Support & extras clipped by 69 px, Theater by 12;
at 1280×720 it was 143 / 117 / 60. The nav is now sticky above the generate bar
and verified visible in 24 states across three viewport sizes, including screen
3 scrolled to the bottom with every block open in turn.

**Eight screens became four.** The old set was organised by engine subsystem —
Airfields, Threats, Support, Map graphics — mirroring how the code is factored
rather than how anyone decides anything; six of eight were toggle panels for a
subsystem. Now: **Mission** (era, kind, map, corridors) → **Flight** (aircraft,
seats, base, start, carrier) → **The theater** → **Review**. Screen 3 opens as a
plain-language summary of every default the mission implied, with each block
openable in place — deferred, never concealed. Screens render in the order the
screen *declares*, not the order the blocks happen to sit in the markup.

**And the small dishonesties.** Building-block descriptions are no longer
clamped to two lines with the rest behind a hover (nothing at all on a touch
device). The Air corridors disclosure says "Show"/"Hide" instead of being a bare
chevron that reads as decoration. `S.advanced` was hardcoded `true` and never
toggled — two screens were gated on a flag that could not change; the flag is
gone. The Carrier screen no longer appears and disappears from the rail.

**Guarded structurally.** `tests/test_builder_ux.py` fails if any Builder
section exists in the markup that no screen shows (the exact defect that hid the
Scenario picker for twenty-six releases — keeping a non-screen section now
requires naming it and giving a reason), if the nav stops being pinned above the
generate bar, if the card copy gets clamped again, or if the frontend's mission
kinds drift from the recipe enum. Every kind is also generated end-to-end.

## [1.44.0] — 2026-08-08 — The bandits are armed

**Every AI aircraft this product has ever spawned flew clean.** Not the wrong
missile — *no* missile. Enemy CAP flights and BFM adversaries were built with
zero pylons, so they flew a competent intercept, arrived at the merge, and had
nothing to shoot with. The Threat Dial made it worse in the only way it could:
intensity 5 spawned *more* unarmed jets.

The cause was structural rather than a missed call. pydcs's
`load_task_default_loadout()` reads payload `.lua` files out of a DCS
*installation*; a server has none, so every airframe reported zero payloads and
the call was a silent no-op. It can never work server-side. So the engine now
brings its own data.

**`missiongen/data/loadouts.json`** — aircraft → role → era → `{label, pylons}`,
covering every airframe the threat pools can spawn across all three eras and
all five Threat Dial tiers. The human label is authored *next to* the pylons so
the brief and the engine can never disagree. Threat Dial intensity 1–2 takes a
trimmed "light" fit where one is authored: the dial now changes the character
of the fight, not just the count. The player's own loadout is still never
touched — that's theirs to set in the Mission Editor, and a test enforces it.

**Machine-verified, not asserted.** pydcs ships the game's own per-pylon
legal-store lists, so `tests/test_loadouts.py` proves every authored store is
one DCS actually permits on that station of that airframe, that no combination
the pools can produce resolves to nothing, and — against a new
`weapon_service.json` — that no fit is anachronistic. Two tests generate real
missions and assert the bandits carry stores, which is the guard that would
have caught this years ago. `/api/health` runs the same checks, so a data gap
shows up as an error instead of as a clean bandit at the merge.

**And it's briefed.** Correct-but-invisible is how the last three features
became discovery problems, so the fit is now intel rather than trivia. The
brief's SITUATION paragraph names what the enemy carries; the theater chart
gains an **ENEMY AIR** block under the order of battle; the in-jet kneeboard
carries the same block on the airfield page; the Markdown brief gains an
*Enemy air* section; and the Mission Kit panel shows the fit before you open a
document at all. Each entry carries a one-sentence tactical implication —
"short-range IR, boresight only — deny the rear quarter and he has nothing but
the gun" — derived from the guidance type of the stores actually loaded, with a
separate warning when a radar shooter also carries high-off-boresight IR.

**Also — the Groom Lake box now matches the map.** R-4808N had been authored as
a four-corner lat/lon rectangle, which is not what the airspace is: the real
area is a 14-point polygon that steps around the Nevada Test Site, so the box
never lined up with the boundary the NTTR terrain draws on the F10 map. It now
carries the published legal boundary (60 FR 20661, 1995 realignment), verified
by geography rather than by corner count — Groom Lake and Yucca Flat inside;
Tonopah Test Range, Nellis, Creech and Rachel outside. The stroke also dropped
from weight 3 to hairline: the hatched boundary style already reads as a band,
and stacking a heavy line under it made the box look like a wall painted over
the map instead of a boundary drawn on it. *Byte-affecting for Nevada missions
(the polygon changed) — existing Nevada share links regenerate with the correct
box.*

**Fixed: `/admin/analytics` returned a 500.** The "missions per person"
histogram is always four buckets, so `max(..., default=1)` never fired — it
returned `0` from a non-empty list of zeros and the next line divided by it.
Any window with no attributable visitor took the whole page down, which on the
live site meant a ledger written before v1.43.0, since those events carry no
anonymous id at all. The histogram now explains the empty state instead of
drawing four zero-length bars, and the route degrades to a readable message
inside the admin shell rather than a bare 500 — a reporting page must never be
able to lock the operator out of Sponsor ads and Mission packs, which are
reached through its own tab bar. Three tests cover the empty ledger, the
all-anonymous ledger and an arbitrary render failure; all three fail against
the old code.

**Release notes are now part of the release.** New `docs/RELEASE_NOTES.md`
written for the person flying rather than the person maintaining, published by
`scripts/build_whatsnew_html.py` and served at **`/api/whatsnew`** with a
"What's new" link in the topbar and footer. The link carries a dot when the
running version is one this browser hasn't seen; a first-ever visitor doesn't
get it, because to them nothing is new. Enforced rather than remembered:
`tests/test_release_notes.py` fails if the current version has no section or
the published page is behind it, and `scripts/preflight.sh` refuses to declare
a deploy clear without both. This changelog stays the engineering record.

## [1.43.0] — 2026-08-07 — How many people, and do they come back

Analytics can now distinguish individuals — anonymously. Each browser
generates a **random UUID about itself** (not derived from IP, user agent or
any fingerprint) and sends it with each build; the server stores only a
**salted hash**, so the ledger can't be searched for a known id. The admin
Analytics tab gains a **People** card: distinct browsers, how many returned
on another day, new this window, missions per person with a distribution, the
one-and-done rate, and how many events came from opted-out browsers.

**Opt-out and honesty.** Do Not Track is honoured without asking. The home
page footer states plainly what is counted and carries a one-click off switch
(which also forgets the id). The user guide's privacy answer was rewritten to
match. A "person" is a browser that kept its id — clearing site data looks
like someone new, two machines look like two people — and the admin says so,
so the number is read as a floor rather than a headcount.

**Navigation.** The wordmark is now a link home (it was the only dead-end in
the topbar once you'd picked a door). Tabs gained proper tablist semantics,
aria-selected state and visible focus rings, and the page title now names the
view — browser history and pinned tabs were previously unreadable.

Fixed in passing: the visitor id shipped **dead** — a variable rename meant a
find/replace silently missed both generate call sites, so nothing was sent.
Caught by an end-to-end browser test, and a new test now asserts every
analytics POST carries the id.

---

## [1.42.0] — 2026-08-07 — Mission packs become content, not code

**Packs move out of the repo and onto the volume.** The AWI syllabus proved
the point the hard way: 28 MB of missions baked into the image made the
release untransferable, bloated the container, and turned every content
update into a code deploy — which then failed twice for reasons invisible
from a working local checkout.

Now there is a **Mission packs** tab in /admin. Drop in a **.zip** of missions
(any folder layout, documents and card art welcome) or a single **.miz**, and
it appears in the Library immediately, persists across deploys, and needs no
rebuild. Remove or replace from the same screen.

**Manifests.** A pack may carry a `pack.json` describing its card (label,
Library tab, premise, era/map, module, card art, docs, and an ordered event
list with each mission's brief). If it doesn't, one is **derived by reading
the upload**: missions sorted, each paired with its brief by number, theater
detected from the mission file, any image adopted as card art, stray
guide/read-me PDFs recognised as pack documents. So a bare folder of .miz
files still produces a proper card. Id precedence is admin input > pack.json
> file name.

Uploads are path-traversal-safe, capped at 256 MB, and manifest entries
pointing at files that aren't in the upload are dropped rather than served as
404s. The release zip is back to ~10 MB — one file again.

---

## [1.41.4] — 2026-08-07 — Fix: preflight failed on a fresh unzip

`preflight.sh` read the version by importing missiongen — which runs a pyproj
preflight and dies on a freshly unzipped folder, before the launcher has built
its venv. Reported "cannot read app version (are you in the right folder?)"
when the folder was, in fact, right. Now parses `__version__` with sed: no
Python, no dependencies, works on a bare unzip (verified under `env -i`).
A wrong folder now says so specifically. Two tests guard it.

---

## [1.41.3] — 2026-08-07 — scripts/preflight.sh

One command to run before `fly deploy` that checks the whole chain the AWI
pack has to survive: the packs folder is beside the code with all twelve
missions, its card art and documents are there, the Dockerfile copies it,
and .dockerignore isn't stripping it. Green means clear to deploy; red names
the fix and exits non-zero. Also prints what /api/health should say
afterwards.

---

## [1.41.2] — 2026-08-07 — The user guide catches up (and can't fall behind again)

The guide PDF is a build artifact — it only changes when someone runs the
builder — so it quietly rotted three releases behind: no squadron callsigns,
no Groom box, no Training tab, no JOKER/BINGO, no privacy line. Rebuilt with
all of it, plus a screenshot of the AWI card.

The durable part: the builder now stamps the version into the PDF metadata
and a test asserts it matches `__version__`, so a stale guide fails the suite
instead of shipping (verified by faking an old stamp — the guard fires and
names the fix command).

Note: the AWI pack's own *In-Flight Guide* is unchanged by design — that is
the syllabus author's document, not ours to rewrite.

---

## [1.41.1] — 2026-08-07 — Fix: the AWI pack could never deploy

The Training card vanished from the live site, and the previous deploy served
twelve 404 buttons. Neither was a packaging mistake on the operator's side —
**the pack could not reach the server by construction**, for two independent
reasons, both invisible from a local checkout (where the app runs fine):

1. `Dockerfile` COPYs an explicit list of directories into the image, and
   `packs` was not among them.
2. `.dockerignore` carried a blanket `*.miz` rule, which stripped all twelve
   missions from the build context — so even adding the COPY would not have
   been enough.

Both fixed (`COPY packs ./packs`; `!packs/**` exception). Verified with
gitignore-semantics matching: 28/28 pack files now enter the build context
while release zips and tests stay excluded. A regression test now asserts
both, since this class of bug is undetectable outside a container build.

The v1.41.0 reconciliation logic worked exactly as intended throughout —
it hid the unusable card rather than showing dead links, and `/api/health`
named all twelve missing files, which is how the root cause was found.

---

## [1.41.0] — 2026-08-07 — The AWI syllabus travels together

The twelve AWI missions are now ONE Library card instead of twelve — a
syllabus, not a scatter. The card wears the Naval Air Training Command seal
from the source manual (USG insignia, public domain) as the Library's first
media header, with a 12 MISSIONS badge. Its drawer lists every event in
flying order — each with its .miz and printed brief — plus the in-flight
guide, the read-me, and one **Download complete syllabus (.zip)** button
(served from a per-deploy cache; counted in analytics as a pack download).
Pack reconciliation now checks every event's file.

## [1.40.1] — 2026-08-07 — Pack reconciliation

A deploy without packs/ used to show Training cards with 404 download
buttons. /api/options now hides any pack entry whose files are not on disk,
and /api/health lists them under missing_packs — a forgotten pack addon
shows up in ops, not as user-facing dead links.

---

## [1.40.0] — 2026-08-07 — The Training tab arrives: AWI Basics syllabus pack

**The Library's Training tab exists at last — populated with a real syllabus.**
Twelve F-14B(U) All Weather Intercept missions derived from CNATRA P-825
(the Navy's AWI flight training instruction), flown from a cold-and-dark
Nellis ramp through real NTTR range points (SHEEP · ALAMO · FLEX): the four
target-aspect game plans, a night displacement turn, the weapons-live
timeline, aware/unaware bandits, the banzai/skate decision, two section
events, and a graduating self-escort strike. Weather progresses with the
syllabus; every event ships with its printed brief PDF and the in-flight
guide.

These are curated FIXED missions (exact intercept presentations the recipe
engine couldn't reproduce), so the Library gains a pack mechanism: entries
with a `pack` block render Download mission / Printed brief / In-flight
guide buttons instead of Generate, served from `/api/pack/` (path-safe,
counted in analytics as `pack` downloads). Requires the F-14A/B + F-14B(U)
modules and the Nevada terrain.

Note: the release zip grows ~28 MB to carry the pack.

---

## [1.39.1] — 2026-08-07 — The Box: R-4808N on every Nevada mission

The airspace over Groom Lake is now drawn on EVERY Nevada mission — magenta
restricted-area boundary on the F10 map with the sectional's data panel
(R-4808N · SFC—UNLTD · CONTINUOUS · NOT JOINT-USE — NO ENTRY), an
`AIRSPACE R-4808N` trigger zone for designers, and a briefing block with the
real-world context: even Red Flag crews are briefed that entering the Box is
a career-ending event. Missions basing FROM Groom Lake get a nod that they
operate inside by design.

Mechanism: historical-airspace overlays gain an `"always"` flag — standing
real-world airspace that draws regardless of the Historical airspace toggle
(which still gates the optional overlays like the Berlin corridors). New
`"box"` feature kind renders corner-defined restricted areas in the existing
chart style system. Deterministic; other maps unchanged (regression-tested).

---

## [1.39.0] — 2026-08-07 — Authentic callsigns + fuel planning numbers

**"Viper 1" is dead.** Flights now default to real squadron radio callsigns
per airframe (callsigns.json, researched): the F-14A flies as **Gypsy**
(VF-32 — the 1989 Gulf of Sidra call), the F-14B as **Victory** (VF-103
Jolly Rogers), the early -A as **Fast Eagle** (VF-41, Sidra '81), the Hornet
as **Chippy** (VFA-195), the Harrier as **Blacksheep** (VMA-214), the F-16
as **Basher** (O'Grady, Bosnia '95), the F-4E as **Oyster** (555th TFS,
10 May 1972), the F-100D as **Misty** (the FACs), red-side types as proper
bort numbers. Entries are tiered documented/flavor. A **Flight callsign**
field on the Coalition & basing screen shows the default and its provenance
and takes any override (new recipe field `callsign`; None = auto — every
existing share link regenerates identically).

**JOKER/BINGO boxes now ship filled** with planning defaults computed from
the airframe's internal fuel (JOKER 50%, BINGO 33%, shown in lb and kg) on
both the kneeboard and the brief's ADMIN block — the box outline stays for
grease-pencil overrides, and a caveat line says to adjust for loadout.

## [1.38.2] — 2026-08-07 — Navigation: a way home from admin, and a 404 with a scope

**The admin was a navigational dead end** — tabs between its own sections but
no route back to the product. Every admin page (dashboard, analytics, login,
not-configured) now carries "↩ Back to Sortie Starter".

**404s stopped being a JSON shrug.** A human who mistypes a URL now gets a
radar scope: rotating sweep, friendly paints — and one dashed amber circle
marked LAST KNOWN POSITION where the page should be. "BOGEY DOPE: negative
contact, all quadrants. Recommend RTB." The three doors are right there
(deep links: /?v=quick|library|builder now open the matching view). API
clients keep the JSON 404 contract on /api/* paths.

---

## [1.38.1] — 2026-08-07 — Fix: the site served a stale roadmap and guide

The in-app roadmap (`/api/roadmap`) serves `docs/roadmap.html` — which was
hand-authored and 17 minor versions stale (it still said v1.19, with no
mention of anything since). The 1.38.0 roadmap rewrite only updated the
Markdown fallback that nothing serves. Likewise `/api/guide` serves a
pre-built PDF that hadn't been regenerated since mid-July.

- New `scripts/build_roadmap_html.py`: renders ROADMAP.md into the styled
  HTML page — one source of truth, one command, can't silently drift again.
- Guide PDF rebuilt with current content (the three doors, Fly Now with a
  real screenshot, the Mission Kit, the guns-only tier) and **all nine
  screenshots recaptured from the live v1.38 UI** — the old ones showed the
  pre-tab, pre-elevation design.

## [1.38.0] — 2026-08-07 — Quick Flight, air starts, BFM, and briefs worth reading

**Fly Now — the new front door.** One screen, three picks, one button:
what to practice (Tanker Time · BFM Merge · Kill the Guns · Beat the SAM),
in what, where. Era, base, weather and comms are derived; one spice notch
(calm/realistic/hostile); 🎲 re-rolls the layout. Entry page and topbar now
lead FLY NOW · LIBRARY · BUILDER. Quick missions are ordinary recipes —
share links and "open in Builder" work unchanged.

**Engine: air starts** (`start: "air"`, pydcs inflight groups — FL200 behind
the tanker for the join, 2nm abeam for the merge), **BFM adversary block**
(`bb_bfm`: one era-correct bandit relative to the player, skill one notch
below the dial), and **target package selection** (`target_packages`,
R7 — None keeps the legacy random two, share-link safe).

**The briefing pack got a redesign** (military-document + UX review):
page 1 now opens SITUATION / MISSION / EXECUTION with a military DTG and the
template tasking inline; the chart declutter keeps labels out of the threat
glyphs; the comms page gains ADMIN — diverts with bearing/range/runway and
JOKER/BINGO fill-in boxes; the duplicate page 4 is gone; every page carries
UNCLASSIFIED // TRAINING USE and a page number. Kneeboard: the theater page
finally shows the threat rings and targets (it had none — the one place you
want them), label declutter, a diverts + fuel block on the comms page, and
cleaned aircraft designations everywhere (aircraft_names.json now serves
both the UI and the documents).

**Byte-determinism is now literal:** kneeboard zip timestamps pinned — same
recipe + seed produces a byte-identical .miz, not just identical content.

Also: roadmap rewritten to describe the shipped product (was 17 versions
stale) with a keep-it-current rule; user guide refreshed for the three doors
and the Mission Kit; qf_open/qf_reroll analytics events.

## [1.37.0] — 2026-08-07 — Analytics: what people make, never who makes them

**Admin gets an Analytics tab** (the admin is now tabbed: Sponsor ads ·
Analytics). Headline tiles (generates, briefing packs + attach rate,
share-link downloads, multiplayer share), generates-per-day bars, and
top-templates / top-aircraft / top-maps / eras tables over a 7/30/90/180-day
range.

**How it's counted.** Every generate is logged server-side at the single
build path — one JSON line recording the MISSION's shape only: kind, source
door (builder / library / share / api), template, map, era, aircraft, slots,
threat tier, timestamp. The schema is closed by design; there is no field a
user identifier could go in. No IP, no user agent, no cookies. Ledger lives
on the Fly volume (`ANALYTICS_DATA_DIR=/data/analytics`), rotates monthly,
keeps 6 months. Telemetry is best-effort by contract — it can never fail a
generate (tested). The entry-page footer discloses the counting in one line.

Also: `/api/generate` and `/api/brief` accept a `source` field (allowlisted),
and the frontend sends builder/library accordingly.

## [1.36.0] — 2026-08-07 — UX v3: Mission Kit, header tabs, elevation pass, no-scroll screens

The four fixes from `claude/ux-review-v3-prd.md`, all frontend + 15 backend
lines, no recipe change — every share link regenerates identically.

**Mission Kit panel.** Generate no longer ends in a status string. A manifest
panel names every artifact the engine built: the .miz (with mode-aware install
path), the briefing pack (downloadable right there instead of via a buried
rail button), the kneeboard page count, the DTC card when the airframe carries
one, the loaded strike route, and what's on station. Backed by a new `X-Kit`
response header on `/api/generate`. The Library drawer renders the same
manifest after its Generate & Download.

**Header tab navigation.** The floating Build/Library pill (active state:
a 1.06:1 contrast difference) and the Library's duplicate copy are gone.
One fixed topbar — brand, BUILD/LIBRARY tabs with an amber underline, doc
links — visible on every view including the landing page.

**Surface elevation pass.** Panels were 1.10:1 against the background and
borders 1.31:1 against panels — the "too dark" complaint was surfaces, not
text. Neutrals re-stepped (panel #161D24, panel2 #1D2630, line #33404D),
card shadows and hover states added. Identity unchanged.

**Zero-scroll screens.** Every builder screen now fits 1440×900 exactly
(was 1126–1247px). The 145px explainer banner is one collapsible line; the
footer moved to the landing view; Air Corridors folds when unused; the rail
no longer forces a 100vh page; placement + livery share a row; long block
descriptions clamp to two lines (full copy on hover).

Also: Review rows and rail dots number by visible order — with Carrier off
the sequence read 01–05, 07.

**New threat tier: "Guns only".** The Threat Dial's system level gains a fifth
setting that fields ZERO radar SAMs anywhere in the theater — including the
player's own home-field battery. The area belt becomes AAA clusters instead
(S-60/KS-19/ZU-23/ZSU-57-2 red · Vulcan/M45/37mm blue, era-gated down to WWII
flak), denser than the SAM belt it replaces, and each strike target package
defends itself with two gun clusters at the aim point. Enemy CAP still comes
up, drawn from the light (gun-era) pool. No launch warnings, no smoke trails
— the Rolling Thunder picture.

**Three routed strike templates (Library › Strike).** `gun_belt_strike`
(F-4E), `armed_recon_route` (F-5E) and `mig_gun_belt_strike` (MiG-21, red
side) are the first templates to carry a player flight plan: WP1 > IP >
TARGET > home, aimed at a real target package, with an era-plausible
altitude/speed profile and a seeded dogleg. This is a deliberate, template-
gated exception to the no-player-waypoints rule — a template must declare
`"route": "strike"` to get one; everything the wizard builds unrouted stays
unrouted (regression-tested).

Also: sponsor logos can now be REPLACED in place from the admin (previously
delete + re-add re-derived the same id and the browser kept showing the old
cached image), and the admin thumbnail cache-busts on file mtime instead of
impression count.

10 new tests (guns tier per era, friendly-SAM disarm, route shape, template
determinism); baseline tiers verified byte-stable against 1.34.1.

## [1.34.1] — 2026-07-28 — Fix: local install would not boot

**The downloadable release could not start on a clean machine.** Both
double-click launchers installed a hand-typed package list instead of
`requirements.txt`, and that list had drifted — it never gained
`python-multipart`, which FastAPI requires for the admin login form. On any
computer without the package already present, the app died at import with
`RuntimeError: Form data requires "python-multipart" to be installed`. The dev
container had it pre-installed, so nothing caught it. Affects every release
that shipped the admin section (1.33.0 onward).

Both launchers now `pip install -r requirements.txt`, so there is one source of
truth for runtime dependencies and no list to drift. The preflight `import`
guard that decides whether to install at all was missing the same package, and
now covers every requirement.

Also new: **`run_windows.bat`**, a double-click launcher for Windows mirroring
the macOS one. `package.sh` fails the build if either launcher is missing.

`tests/test_launchers.py` pins all of this: both launchers ship, both install
from `requirements.txt`, the preflight guard names every requirement, and
`server.app` actually imports with only the declared dependencies.

## [1.34.0] — 2026-07-27 — Aircraft in the pattern

New building block, **Aircraft in the pattern** (Support section, off by
default): a few AI aircraft recovering into or departing from *your* home field
as the mission starts, so the base you walk out onto is visibly operational
instead of dead.

Three knobs: the leg (`landing`, `takeoff` or `both`), the traffic type
(`fighter`, `cargo`, `helicopter` or `mixed`) and how many aircraft (1-4,
default 2). Arriving aircraft spawn airborne on the extended centreline,
stacked in trail on a ~3 degree profile, and land at the field; departing
aircraft start hot on the ramp, roll, fly a closed circuit and recover. Types
come from the era packs, so a 1944 pattern is period aircraft - the helicopter
category is disabled in WWII rather than silently substituting something wrong.

Skipped when home plate is the boat. Placed before airfield dressing so
departing traffic claims its parking stand first; if the ramp is full the
generator tries the rest of the category and warns about anything it could not
fit. Adds a "Field activity" line to the mission briefing. The player's own
route is never touched, as always.

## [1.33.1] — 2026-07-23 — Rename: DCS Mission Starter → DCS Sortie Starter

Product rename across all user-facing surfaces (web header/title, in-mission
briefing text, in-jet kneeboard footer, briefing pack PDF/MD, user-guide PDF,
API title, docs). The generator, package (`missiongen`) and repo name are
unchanged; "mission" as a common noun is untouched. Historical changelog
entries keep their original wording.

## [1.33.0] — 2026-07-22 — Sponsor Ads MVP (admin-managed launch splash)

New capability: an admin-managed sponsor logo baked into every mission's launch
splash, so the ad can be swapped (Authentic ↔ Pimax ↔ …) with no code change.
See `claude/sponsor-ads-design.md`.

- `missiongen/sponsors.py` — sponsor library: a small `manifest.json` + a
  regenerable PNG cache. One sponsor is *active* at a time. Sourced from an
  image **URL** (pulled server-side, SSRF-guarded: https-only, image
  content-type, size cap, private/loopback/metadata addresses blocked) or an
  uploaded file. Reusable `render_splash()` (PIL-only — no numpy) does the
  white-knockout → crop → translucent panel → downscale, which also sanitises
  uploads. Per-sponsor `splash_size`/`panel_opacity` and an `impressions` counter.
- `server/admin.py` — `/admin`, gated by the `ADMIN_PASSWORD` env var (signed
  session cookie; the section is disabled entirely when unset, so a
  misconfigured deploy can't expose it). Add/activate/refresh/delete sponsors,
  a global on/off toggle, thumbnails, and impression counts.
- `missiongen/builder.py` — the launch splash now uses the active sponsor (with
  its size), falling back to the shipped Authentic asset when there's no store
  or branding is globally off. Impressions are counted at the server boundary
  (`/api/generate`, `/api/dl`) so the builder stays pure/deterministic.
- `requirements.txt` — add `python-multipart` (FastAPI form/file uploads).
- Store location is `SPONSOR_DATA_DIR` (default `instance/sponsors`); point it
  at a Fly volume for persistence across deploys.

## [1.32.8] — 2026-07-22 — Drop the Advanced-options toggle

There aren't enough options to warrant hiding any, so the "Advanced options"
toggle is gone and the two previously-gated steps (Airfields, Map & graphics)
are now always visible in the builder rail. Removed `#advtoggle`,
`toggleAdvanced()`, and the `.adv` dot styling; `S.advanced` defaults true so
`visScreens()` shows every step.

## [1.32.7] — 2026-07-22 — Brand splash is not a user option

The sponsor/brand splash is a business decision, not something users opt out of.
Removed the "Brand splash on launch" toggle from the builder (BLOCKS +
RECIPE_DEFAULTS). Server-side `recipe.bb_branding` still defaults on, so the
splash is now always applied; it will be governed globally by the admin/sponsor
setting rather than per-mission by the user.

## [1.32.6] — 2026-07-22 — Brand splash: lighter panel, smaller on screen

- `data/brand/authentic_media.png` — white panel opacity halved (alpha 180 → 90,
  ~70% → ~35%) so it reads as a light translucent backing rather than a solid card.
- `branding.py` — splash render size 60 → 30 (% of window), so the logo shows at
  half the previous size on mission launch.

## [1.32.5] — 2026-07-22 — Left-rail layout: secondary actions no longer buried

The left rail's `#railsteps` used `flex: 1`, stretching the (short) step list to
fill the full-height rail and pushing **Advanced options** and **Reset wizard**
below the fold — offset by the header/banner, the rail bottom sat ~226px off
screen. Fixed the stretch and grouped the secondary actions in the rail.

- `#railsteps` → `flex: 0 1 auto` so the step list takes its natural height;
  Advanced options + the rail foot now sit directly beneath it, on screen.
- Moved **Copy share link** and **Briefing pack** out of the bottom action bar
  into the rail foot (IDs unchanged, so all handlers — including the review
  screen's `share2` → `#share` — keep working). The bottom bar keeps the
  preview line and **GENERATE .MIZ** as the single primary CTA.

## [1.32.4] — 2026-07-22 — Brand splash: real Authentic Media logo

The mission-launch splash now uses the **actual Authentic Media logo art** (navy
"AUTHENTIC" + sage-green brush-script "media"), not a font recreation. The white
background is knocked out to transparent and the wordmark sits on a
semi-transparent white rounded panel so it stays legible over any F10 map
background.

- `data/brand/authentic_media.png` — regenerated from Rob's original
  `Authentic-Media-Logo600x300.png`: white→transparent, cropped to the wordmark,
  composited on a ~70% white rounded panel, downscaled to 1600px wide.

## [1.32.0] — 2026-07-22 — Brand splash: logo on mission launch

Generated missions now show an **Authentic Media logo for a few seconds when the
mission launches**, then it clears — the same "Picture to All" trigger
(`a_out_picture`) campaign creators use for intro logos. Cosmetic only: no units,
no waypoints, no gameplay effect.

- `missiongen/branding.py` — embeds the logo as a mission resource + a
  mission-start Picture-to-All trigger. Coerces pydcs's alignment/size enums to
  their string values (pydcs serialised them as bare identifiers like
  `HorzAlignment.Center`, which is invalid Lua — the .miz wouldn't even reload).
- `data/brand/authentic_media.png` — a clean placeholder splash (amber reticle +
  wordmark); drop-in replaceable with the real logo.
- `recipe.bb_branding` (default on) + a "Brand splash on launch" toggle in the
  Briefing aids block. Off = no logo, no trigger.

Byte-affecting (adds a resource + trigger); determinism preserved. New regression
covers embed + toggle.

## [1.31.2] — 2026-07-22 — Fix: target packages no longer spawn in the sea

On coastal maps (Syria with the player on Cyprus, Sinai, Marianas) the `bb_targets`
packages — including "Command & control site" — could land in open water, because
they were placed at `enemy_center ± 15 km` with no land check (pydcs exposes no
land/water query). Now each package **anchors to a real enemy airbase** (always on
land) and is pushed a few km deeper inland, matching the land-safe pattern already
used for SAM placement (threats.py). Verified: targets now sit ~5–9 km from the
nearest enemy airbase instead of floating offshore. Byte-affecting for bb_targets
missions (target positions move); determinism preserved.

## [1.31.1] — 2026-07-22 — Fix: Air Corridor axis actually draws on the F10 map

The corridor feature (v1.30.0) re-anchored the threat axis and briefed it, but
the axis **line never appeared on the F10 map**: the builder appended it to a
`gfx["routes"]` key that `graphics.draw_layers()` has no handler for, so it was
silently dropped. Added a real **`corridors` layer** — an amber, arrowed lane
drawn friendly→enemy on the player's layer and labelled at the enemy end — and
pointed the builder at it. A chosen corridor now always draws, even if the F10
layer toggles are customised to a subset that omits it. Regression hardened to
assert the layer renders (default and custom-subset). Determinism preserved.

## [1.31.0] — 2026-07-22 — Redesign Phase 4: Review screen jump-back rows

The Review & Generate screen becomes the redesign's scannable, editable summary:
one row per Builder section (numbered key + live value + ✎), and **clicking any
row jumps straight back to that section** to tweak it. Rows reuse each screen's
live value function, so the review always matches the mission, and respect the
Advanced toggle (expert rows appear only when advanced is on). Replaces the flat
text blob. Frontend only.

## [1.30.0] — 2026-07-22 — Redesign Phase 5: Air Corridors (threat-axis driver)

The redesign's standout feature — and the first that reaches the engine.
Selecting a curated **Air Corridor** in the Builder's Theater section now
*shapes the mission*, not just the F10 map: the enemy focus re-anchors down the
corridor's compass bearing, so the **threat axis and the CAP/SAM concentration
follow the lane** instead of the raw base-to-base centroid. The corridor's axis
+ enemy picture are briefed, and the axis is drawn on the F10 map.

- New `air_corridors.json` — curated lanes per map/era (Fulda Gap, Strait of
  Hormuz CAP, Damascus Approach, Helmand River, …), each a bearing + reach +
  axis/enemy text. Map-agnostic geometry (no fragile per-corridor lat/lon).
- New `recipe.corridors` (list of names); multi-select UI filtered to the
  current map+era, with the redesign's card styling. Applies from scenario
  presets and share links.
- **North-star safe:** shapes the *enemy* picture and the threat axis only —
  never places player waypoints. Unknown names are ignored gracefully.

Byte-affecting when corridors are selected (empty list = unchanged output, so
existing share links reproduce exactly). Determinism preserved; new regression
covers axis shift, briefing, determinism, and graceful unknown-name handling.

## [1.29.0] — 2026-07-22 — Redesign Phase 3: Advanced disclosure in the Builder

Addresses the audit's P1 density finding — essentials and expert controls no
longer share the same weight. The Builder rail now shows only the **four
essentials + Review** by default (Theater, Flight, Threats, Support); an
**Advanced options** toggle reveals the expert screens (Airfields ramp/themes,
Map & F10 graphics), which carry a cyan step number to mark them as advanced.
The "airborne in a minute" user isn't confronted with ramp-fill and layer
geometry; veterans flip one switch. Screen-nav, progress, and jump behavior all
respect the toggle; you're never stranded on a hidden screen.

Frontend only; the Builder's existing screen model and recipe are unchanged.

## [1.28.0] — 2026-07-22 — Redesign Phase 2: full "My Install" module catalog

The ownership picker grows from a flat maps+aircraft list into the redesign's
categorized catalog, driven by the backend's real supported content (so nobody
"owns" a module the engine can't build for):

- **Categories** — Terrains, Modern jets, Cold War jets, WWII warbirds,
  Helicopters (aircraft bucketed by service dates; helos split out).
- **Nickname search** — type "Warthog", "Hornet", "Fulda" and it matches via an
  alias map, not just the designation.
- **Select all / Clear per category** + a live "N owned" count per section and a
  running total in the footer.
- **Free content** (Caucasus/Marianas, Su-25T/TF-51D) is always checked and
  tagged, never counted against you.

Extends the existing on-device `ms_owned` store; the Library's lock badges,
status rows, and "Only what I own" all read from it. Frontend only.

## [1.27.0] — 2026-07-22 — Redesign Phase 0: instrument-panel visual language

Visual foundation of the v2 redesign — all in vanilla CSS/HTML, no framework.
Because the app themes off CSS custom properties, the whole UI re-tints by
remapping the root variables:

- **Palette** → instrument-panel: tarmac base `#0B0E11`, signal-amber primary
  `#FFB020` (was blue), HUD-cyan secondary `#3FB8AF`, with a fixed radial-gradient
  field. Threat/coalition/ownership colors aligned to the redesign tokens. Every
  component (Library, Builder, modals) picks this up automatically.
- **Typography** → Archivo (display), Barlow (body), IBM Plex Mono (data/labels)
  via Google Fonts.
- **Landing refresh** → new hero "Get airborne fast. / Fly it your way.", a
  pure-value "why us" strip (no competitor names, per Rob's call), and a "Two
  flavors of mission" callout that teaches FULL MISSION vs OPEN STARTER.
- **Primary CTAs** (Generate) → amber with a soft glow; success/tick states stay
  green.

Frontend only; no engine/recipe/determinism change. Next: Phase 2 (full My
Install catalog) and Phase 3 (single-page Builder + live brief).

## [1.26.0] — 2026-07-22 — Redesign Phase 1: Full/Open kind badges + Type filter

First slice of the v2 UX redesign (implemented in vanilla JS in the existing
single-file frontend — no framework adopted, per the plan in
`claude/ux-redesign-v2-review.md`). Resolves the audit's P0 "starter vs mission"
confusion:

- **Kind badge on every Library card** — FULL MISSION (cyan) when the `.miz`
  places a flown route/waypoints (crew-ops), OPEN STARTER (amber) for a dressed
  theater with no waypoints placed (all scenario templates + the Builder). Honest
  to how the engine actually works and the never-place-player-waypoints north star.
- **"Tasking brief" chip** on open starters that ship a suggested-tasking brief,
  so a curated scenario isn't undersold as "just a sandbox."
- **Type filter** (All / Full mission / Open starter) with a removable chip.
- **Ownership status row** on cards once you've set My Content: green "✓ You own
  the terrain & aircraft" or amber "🔒 Needs: {module}".

Backend: `/api/options` now sends a per-template `kind` (full|open) + `tasked`
flag; crew-ops are full, scenario templates are open. No engine/recipe/
determinism change.

## [1.25.0] — 2026-07-22 — A-6E Intruder joins the carrier air wing

Heatblur's A-6E is an **AI-only** DCS release (the flyable module is still in
development), so it's integrated as an air-wing asset, not a player jet. Home is
CV-59 Forrestal (CVW-6, 1980s Med), whose deck was historically missing its
Intruder squadron — now **VA-176 "Thunderbolts"**. Three roles:

- **Deck dressing** — A6E added to the Forrestal deckable roster; parks on deck
  alongside the F-14As (checked by default when you pick the hull).
- **KA-6D organic tanker** — in the Cold War, a carrier-home mission's Texaco is
  now the A-6's tanker variant (the air wing's own gas) instead of a land KC-130.
  Carries an in-sim note to confirm the buddy-refueling store (A-6 is AI-only).
- **AI strike package** — new "Launch strike package" carrier toggle
  (`carrier_strike`) sends a 2-ship A-6 medium-attack flight outbound on the
  threat axis; the player flies escort. `naval.add_carrier_strike()`.

Plus a Library mission: **"Alpha Strike Escort — TARCAP for the Intruders"**
(F-14A off the Forrestal, escort the A-6 package). Non-Forrestal air wings with
no medium-attack squadron skip the strike/tanker gracefully. A-6E stays out of
the player-flyable roster. New regression locks all three roles in.

## [1.24.0] — 2026-07-22 — Library: "what I own" filtering + instant-missions copy

**Ownership filtering.** DCS locks content behind paid modules and map terrains,
so a mission you can't fly is noise. There's no purchase API, so the user now
**declares what they own** once (a "⚙ My content" editor in the Library — check
your maps and aircraft modules; stored on this device only; free content like
Caucasus/Marianas and Su-25T/TF-51D is always included). Then:
- Every mission that needs an unowned map or module shows a 🔒 badge naming it
  (e.g. "🔒 F-100D" or "🔒 Persian Gulf").
- "Only what I own" hides locked missions; when unset, the toggle opens the
  editor first.
- Owned missions always sort ahead of locked ones.
The old toggle was a heuristic (free maps = owned, aircraft ignored); it now
checks both the required map AND the required aircraft against what you own.

**Copy reframe.** Front-end no longer promises "no objectives, tasking or
waypoints, ever" globally (only true of the Builder starter). Header/entry now
lead with "instant, period-accurate DCS missions — pick one ready to fly, or
build your own"; Builder banner reframed positively; "scenarios" → "missions".

Frontend only; no engine/recipe/determinism changes.

## [1.23.0] — 2026-07-22 — Library: promote F-100D + F-14B(U), redesign for search & scan

**New modules promoted.** The F-100D Super Sabre (released for DCS June 2026;
native pydcs type, Cold War) and the F-14B(U) both get a Library push.

F-100D — 4 Cold War missions: Victor Alert nuclear QRA (Bitburg), Fulda Gap CAS
(Hahn), Iron Hand flak suppression (Spangdahlem), Sabre Dance gunfighter BFM
(Nellis). F-14B(U) — the 3 crew-ops missions (IZLID / GCI intercept / fleet
defense) are now featured, plus 3 new scenario missions: TARPS recon, Bombcat
precision strike, Case III night recovery. All carry a `library.module` tag.

**Library UX redesign** (frontend):
- **"New in DCS" spotlight rail** — a hero card per new module (F-100D,
  F-14B(U)) with a pitch and mission count; click to filter to that module.
- **Aircraft is now first-class** — shown as a badge on every card and a filter
  facet, alongside a new Map facet (plus the existing Role / Era / Difficulty).
- **Search box** over title / premise / aircraft / role / module.
- **Active-filter chips** with per-filter removal and Clear-all.
- **Sort** control (Featured / Newest / Difficulty / A–Z).

Pure additive: no recipe or engine changes, determinism untouched. Backend just
passes `library.module` and `recipe.aircraft` through `/api/options` (already did).

## [1.22.4] — 2026-07-22 — No GSE trucks on Kandahar shelters (covered-ramp gate)

**Fix.** At Kandahar the parking stands sit under arched sun-shelters. The
per-aircraft GSE truck is offset to the SIDE of the jet, which lands on the
shelter's curved roof — DCS clamps the truck to that sloped mesh, so it spawns
tilted on top of the shelter (Rob's screenshots, 2026-07-22). The occupancy /
keep-out checks validate against aircraft and runway corridors but have no
knowledge of map scenery like shelters.

New per-map `covered_ramp` list in `maps.json` (Afghanistan → `["Kandahar"]`).
`builder` suppresses per-aircraft GSE at listed bases while still placing the
aircraft (which sit AT the stand, fitting under the arch). Open bases —
Shindand, Bagram, Camp Bastion, etc. — keep their GSE. New regression asserts
Kandahar gets no GSE while other bases do. Easy to extend the list if other
sheltered bases show the same clipping.

## [1.22.3] — 2026-07-22 — Crew Ops jets get radio presets (cockpit matches kneeboard)

**Fix.** On Crew Ops missions the cockpit radio channels did not match the
kneeboard: dialing a channel showed a different frequency than the card
advertised (Rob, 2026-07-22). Cause: crew-ops templates own the player jet, so
`player_group` is `None` and the BB-19 preset step (`presets.apply`) was gated on
`player_group is not None` — it never ran for crew flights. The F-14B(U) kept
factory Tomcat defaults (CH1=225, CH3=260…) while the comm plan / kneeboard
showed the mission frequencies (CH1 Flight 305.725, CH3 AWACS 251.475…).

`builder` now captures the returned crew flight and programs it through the same
`presets.apply` path, so cockpit and card agree by construction. Standard
(non-crew-ops) missions were already correct and are unchanged. New regression
asserts every planned channel matches the in-jet value on a crew-ops F-14B(U).

Byte-affecting for Crew Ops recipes (player jet radio channels change).
Determinism preserved.

## [1.22.2] — 2026-07-22 — DTC now actually loads (unit-level cartridge link)

**Fix.** The F-14B(U) DTM page loaded EMPTY in-sim even though the `DTC/*.dtc`
sidecar was present and populated. Root cause: the sidecar was an orphan — the
mission tree had no reference to it. Re-diffing an ME-made cartridge `.miz`
against its plain twin (which the original reverse-engineering got wrong) showed
DCS pairs the sidecar to the jet through a **unit-level** field on the player
aircraft, not by type alone:

```
["DTC"] = { ["Cartridges"] = { [1] = { ["name"]="F-14B(U) DTC_1", ["default"]=true } } }
```

New `dtc.install_unit_dtc()` runtime-patches pydcs (vendor stays pristine) so a
unit carrying a `_dtc_cartridge` attribute serialises that block, and
`dtc.tag_player_cartridge()` (called in `generate()` before save) tags every
player/client F-14B(U) unit with the cartridge name that matches the sidecar
member. The sidecar content, name fields, and determinism are unchanged; only
the mission tree gains the link. New regression test locks the linkage in.

Byte-affecting for F-14B(U) recipes (mission tree gains the unit DTC block).
Determinism preserved (per-entry content identical across processes).

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
