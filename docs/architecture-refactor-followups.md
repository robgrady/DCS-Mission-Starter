# Architecture decision: finish the refactor incrementally

3 October 2026 · application v1.107.0 · accepted direction, follow-up work
not implemented by this document. Updated after 1.108.0: effective presets are
unified; the owner requested a 2.0 refactor milestone on a separate branch.

## Context and decision

The reliability release extracts world preparation, artifact serialization,
recipe schema, generation admission and Mission Kit ownership. It integrates
the recovered generators and airfield guide from main. It is a substantial
incremental refactor, not a complete rewrite: `StarterBuilder.build()` still
coordinates most placement, the browser remains predominantly one HTML file,
and API handlers remain predominantly in `server/app.py`.

Keep PyDCS as the mission model and serializer, public generation entry points,
legacy share-code support, visual tokens and existing surveyed airport data.
Continue extracting responsibilities around explicit domain contracts. A major
version is unnecessary while those contracts remain compatible; v1.107.0 is
the next minor release. Version bundled pack content separately when generated
mission bytes change.

## Priorities

| Order | Boundary | Evidence and proposed change | Completion evidence |
|---|---|---|---|
| 1 | Effective recipe and presets | `templates.effective_recipe()` merges base, era and map overrides. `Recipe._with_template_defaults()` merges only base defaults; `/api/options` exposes era overrides but omits map overrides; `applyScenarioPreset()` has a handwritten control mapping that omits mission kind and slots. The browser can submit explicit defaults that override the intended scenario. Make one effective preset contract available to every entry point; distinguish deliberate user edits from omitted fields. | Submit recipes through actual Library, Fly Now, Builder and direct API paths for multi-era, map-specific, multiplayer and carrier presets. Assert resulting mission kind, slots, field, support and documents; preserve intentional overrides and old share links. |
| 2 | Builder placement phases | `missiongen/builder.py` remains about 2,000 lines. Move player/deck setup, support/threat placement, training/targets, routes and document context behind the existing `WorldContext`, one phase at a time. Return explicit phase results rather than adding a shared dictionary of hidden state. | Compare seeded mission structure, stats, warnings and briefing facts across modern, Cold War, WWII, carrier, BFM and curated training examples. Preserve RNG call order; byte comparisons require identical dependencies and exclude intended content corrections. |
| 3 | Browser recipe state | `frontend/index.html` combines navigation, local saves, preset application, recipe serialization, Library and comm-plan rendering. `mission-results.js` is extracted but still uses globals. Extract a recipe-state module first, then Library and comm-plan controllers; give modules explicit inputs and callbacks. | Real-browser checks for sharing/reloading, carrier restoration, era/map changes, Back navigation, keyboard use and mobile layouts; independent result downloads after selections change. Retain the Flightline design and existing navigation. |
| 4 | API services and document model | `server/app.py` mixes metadata, input parsing, generation, temporary-file cleanup, downloads, analytics and admin routes. Extract routers and a generation/artifact service while retaining HTTP contracts. Brief and kneeboard rendering also need a shared factual context; `fieldguide.py` already provides one useful source. | Keep response headers, error status and cleanup behavior; test capacity release on failures and document facts against the generated mission. Separate CPU work from HTTP responsibilities without introducing a queue until load measurements justify it. |
| 5 | Release registry | Generators are listed independently in `release.sh` and `artifacts.py`. Recovering three lost generators demonstrates the maintenance risk. Use one ordered registry for regeneration and freshness, with explicit dependencies and failure propagation. | Changing any registered input rebuilds its output; a generator failure cannot be stamped fresh; packaged files contain all source generators, and app/content versions appear in the intended manifests. |
| 6 | Historical data contracts | The Library audit found behavior mismatches and approximate boundary dates. Separate dated sovereignty, airbase operator and mission coalition; encode validity dates and source provenance, then resolve one historical snapshot used by engine and documents. | Verify map/era edge dates and named fields against cited historical sources, independently of build success. Keep approximate zones visibly identified until precise boundaries are sourced. |

The first boundary is also a product correctness issue and belongs with the
Library audit fixes. Splitting its code without correcting the inconsistent
preset semantics would leave the underlying defect intact.

## Conditional work

Pack publication currently serializes access inside one process and rolls back
ordinary publication failures. Two directory renames are not a crash-durable
transaction, and a returned file path is not an immutable revision snapshot.
Before multiple writer processes or concurrent pack replacement/downloads become
a requirement, use immutable revision directories and an atomic catalog pointer.
Do not introduce distributed storage solely to shorten a file.

Generation admission is per process. Measure peak memory and latency for carrier,
large ramp and training builds before choosing worker counts or comparing hosting
platforms. Neither this refactor nor a move from Fly.io to Render resolves
unmeasured memory limits or the audited mission semantics.

No wholesale PyDCS upgrade is required for these extractions. Preserve measured
stand IDs, coordinates and headings, and evaluate upstream changes separately
using `pydcs-current-audit.md` and the terrain-data checks.

## Alternatives and consequences

A full rewrite or immediate framework migration would change many contracts at
once and make mission regressions harder to locate. Pure file splitting would
reduce line counts without removing duplicated rules. Incremental extraction
keeps a working release at each step, at the cost of temporarily retaining some
globals and a large orchestrator. Each phase must own a clear responsibility and
earn its boundary through observable behavior checks.

The Library audit's 17 behavioral entries are corrected in 1.108.0; see
`library-validation-1.108.0.md`. Historical boundary/date findings remain open.
Automated release checks validate the code and artifacts; DCS cockpit and flight
validation remains a separate requirement. Discord login, sharing and saved
missions can follow these stable contracts after existing content works as promised.

## Action items

1. Completed in 1.108.0: effective presets with archive and real-browser regression examples.
2. Correct and re-audit the affected mission descriptions, behavior and historical data.
3. Extract builder phases, browser state and API services in separate reviewable changes.
4. Consolidate release regeneration and freshness registration.
5. Measure production resource use before choosing concurrency or hosting changes.

References: `reliability-handoff.md`, `library-validation-2026-10-02.md`,
`ROADMAP.md`, `pydcs-current-audit.md`, `parking-direction-survey.md`.

## Completion — v1.108.2

The ordered placement, controller, router/service, document facts, release
registry and catalog revision/ownership migration is implemented. The source
migration preserves public contracts and therefore ships as a patch. See
[completion and qualification limits](architecture-2.0.md). Historical content
research and DCS flight qualification are distinct follow-ups, not claims made
by splitting or validating source code.
