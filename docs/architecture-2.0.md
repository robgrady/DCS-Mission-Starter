# Architecture refactor — source migration completed in v1.108.2

3 October 2026. The owner's requested 2.0 architecture milestone was implemented
on `codex/refactor-2.0`. Public contracts remain compatible, so this delivered
migration is v1.108.2 under the owner's semantic version policy. No API break
was invented to obtain a major number. PyDCS, measured airport stands/headings,
Flightline tokens, recipe/share links and HTTP endpoints remain in place.

## Completed code boundaries

| Boundary | Owner and completion evidence |
|---|---|
| World and historical context | `build_context.py` resolves one world. `historical_world.py` carries dated identity facts separately from game coalition and display nationality; missing territorial/operator evidence remains unknown. Validity intervals are inclusive and reject reversed dates. Existing historical content remains unchanged by this structural migration. |
| Placement | `builder.py` orders carrier, player/payload, environment, threats/support, targets, routes/timing, training and presentation. Frozen result dataclasses name cross-phase facts; the public stats dictionary remains a compatibility report. Flight operations and mission prose have separate owners. Eight pre-migration seeded missions preserve native structures, documents, stats and warnings. |
| Document facts | `document_facts.py` resolves `MissionFacts` once from the completed world. Brief, kneeboard and Mission Kit adapters share clock, route, comms, fuel and historical context. Existing renderers retain their input contracts. |
| Browser | HTML holds presentation; `app.js` wires DOM/navigation. Recipe state, Library/training, comm-plan and Mission Kit controllers receive explicit state, option getters, environment and callbacks. Stable window entry points retain existing HTML event handlers. Real-browser guards exercise mobile/desktop, carrier share restoration, Back, Escape, retry and version identity. |
| HTTP | `server/app.py` composes site, metadata, document, Library, mission, comm, contact and health routers. `artifact_service.py` owns admitted generation and download cleanup; CPU work stays in `missiongen/artifacts.py`. Existing response/error/header contracts and failure-capacity tests remain. |
| Releases | One ordered registry in `scripts/artifacts.py` drives producers and freshness. Pack hashes include all engine code/data/resources and vendored engine code. Removed inputs invalidate stamps. A failed producer stops before stamping. A documentation-impact record is mandatory for every release, and the PDF reads the Markdown manual directly. |
| Catalog durability | Atomic `.catalog/<id>.json` pointers select immutable `.revisions/<id>/<revision>/` directories. Local writer processes share a file lock. Already resolved downloads survive replacement/deletion. Legacy directories remain readable. No symlink privilege is required on Windows. Retained revisions need deliberate backup/retention management. |
| Fly ownership | `PACKS_OWNER_MACHINE` selects one existing volume for public catalog reads and writes. Large admin uploads pin that instance before sending their body because Fly replay is limited to 1 MB. Other private stores are unchanged. Cross-instance checks must prove the catalog resolves through its owner. |
| Resource evidence | `scripts/benchmark_generation.py` measures carrier, training and large-ramp builds in separate processes, reporting latency and process peak RSS. Production observations are retained with release evidence; they are not a throughput guarantee or a reason to increase workers without load testing. |

## Verification and remaining product qualification

The release gate rebuilds all official packs, native missions, browser screenshots
and the PDF, then runs the full suite. Evidence and deployment measurements live
in `outputs/releases/1.108.2/`, outside versioned source. The source is frozen
while the gate runs. A failed check is repaired before any commit/deployment.

This completes the code migration, not every content research task. The historical
Library audit still identifies scenario dates, alliance labels, base operators,
weapon dates and approximate overlays needing separately sourced corrections.
The new contracts support that work without claiming unknown facts are verified.
DCS cockpit rendering and flight qualification require DCS on Windows and cannot
be certified by Python/browser/archive checks on macOS. Discord accounts, saved
missions and sharing remain deferred product features.

## Operations

Back up the owner's public catalog including pointers, revisions and legacy
folders. Change `PACKS_OWNER_MACHINE` when replacing its machine/volume. Route
all public writers through the owner; never synchronize private contact, sponsor,
credits or analytics data as a pack publication step. Keep non-current revisions
until active downloads and the chosen rollback/retention window have expired.
Monitor disk capacity before pruning, and preserve an off-volume backup first.

References: `../AGENTS.md`, `architecture-refactor-followups.md`,
`library-validation-1.108.0.md`, `library-validation-2026-10-02.md`,
`pydcs-current-audit.md`, `parking-direction-survey.md`.

Fly routing source: [Dynamic request routing](https://docs.fly.io/networking/dynamic-request-routing).
