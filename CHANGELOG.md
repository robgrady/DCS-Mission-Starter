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
