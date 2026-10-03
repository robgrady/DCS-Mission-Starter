# Architecture 2.0 — implementation in progress

3 October 2026. The owner requested a complete architecture refactor targeting
2.0 after correcting the Library and deploying production. Development branch:
`codex/refactor-2.0`, based on production release `v1.108.0` / `7765421`.

## Decision

Keep production on the validated 1.108.0 release while extracting domain
responsibilities into explicit interfaces. Keep PyDCS, measured airport slots
and headings, Flightline visual tokens, recipe/share-link compatibility and
existing HTTP endpoints. Treat 2.0 as the requested product milestone; do not
invent an API break solely to justify the number. Set the final 2.0 version and
produce its release artifacts when the migration and release gates are complete.
The development tree therefore retains the current application version stamp.

## First implementation slice

- Extract carrier/deck/support placement from `StarterBuilder.build()` into
  `missiongen/phases/carrier.py`. Return a typed immutable result for the fleet,
  course, hull, strike flight, support names, deck count and graphics. The
  orchestrator applies those facts; the phase does not mutate `ctx.stats`.
- Extract effective scenario and lineup calculations into a browser module with
  explicit options/state inputs. Keep the existing DOM/navigation controllers
  and visual design while removing those calculations' dependency on globals.
- Exclude local audit outputs and generated packs from Docker build context.
  The 1.108 deployment uploaded 330 MB although the image never copies packs or
  outputs. Keep their separate publication workflow.
- Record the corrected six-pack production catalog, image and health checks in
  `deployment-1.108.0.md`. The second Fly volume had been empty; it now receives
  the same existing public catalog. Unrelated persisted stores are untouched.

Seeded mission baselines cover modern/WWII shore, Cold War carrier, carrier
escort, TIC, convoy, WK intercept and guns-only BFM. Compare emitted native
mission structure, translations/documents, stats and warnings before/after
placement extraction, preserving RNG call order. Browser regression checks
exercise the shared pure calculations and actual form restoration/downloads.

## Remaining milestone boundaries

| Order | Work | Completion evidence |
|---|---|---|
| 1 | Player/deck start placement, parking ownership and payload phase | Seeded carrier/shore/helo starts preserve unit IDs, surveyed stands/headings and actual stores; old share links work |
| 2 | Support/threats, ground/scenario actors and training phases | Typed results replace implicit shared dictionaries; actor/store/task contracts cover all authored promises |
| 3 | Routes, timing and shared document facts | One emitted factual model supplies F10, brief, kneeboard and Mission Kit; clock/fuel facts agree |
| 4 | Browser recipe state, Library and comm-plan controllers | Explicit module inputs/callbacks; actual desktop/mobile, keyboard, sharing, Back and independent result download checks |
| 5 | API routers and generation/artifact service | Preserve response headers/errors/cleanup and capacity limits; separate CPU work from transport |
| 6 | One ordered release registry and complete input/provenance hashes | No duplicated generator lists; all engine/data dependencies invalidate affected packs; failed producers cannot be stamped fresh |
| 7 | Durable published catalog/storage contract | Two Fly volumes are independent. Future admin uploads must not diverge; choose one storage owner or shared revision storage, atomic catalog publication, backups and cross-instance read tests before accounts/saved missions |
| 8 | Dated historical world contracts | Distinguish sovereignty, base operator and mission coalition; sourced validity dates and visibly approximate zones; resolve the remaining historical audit findings |
| 9 | Resource measurements and final 2.0 release | Measure production peak memory/latency before worker/hosting changes; run full source Library, browser, pack, release and DCS flight gates |

The first slice starts the full scope above. It does not claim all builder phases,
API services, browser controllers or historical data are already migrated.
Discord login, saving and sharing remain deferred product features.

## Storage constraint discovered in production

Catalog synchronization fixes the current published content, not future
replication. Each Fly machine owns a separate `/data` volume. Pack publication
currently uses an in-process lock and directory replacement; multiple service
instances do not share that lock or data. Define storage ownership before
introducing more writers. Do not silently copy private contact, sponsor, credits
or analytics stores as part of a public pack correction.
