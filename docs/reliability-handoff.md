# Reliability and architecture implementation

Date: 2026-10-02. Base: v1.106.0 / `9360a0b`.
Branch: `codex/reliability-fixes` in the isolated workspace clone.

## Delivered behavior

Recipe field types are checked before template expansion and generation.
Malformed user input returns a field-specific 400. Browser and server share a
versioned UTF-8 envelope, preserve legacy codes, show invalid-link recovery,
and retain engine-only recipe settings through share-link round trips.

Builder, Fly Now, and Library use one generation lifecycle. Each successful
Mission Kit owns a frozen copy of the recipe submitted for that mission;
briefing and kneeboard buttons use that copy even after another mission has
been selected. Success follows the completed response and download initiation.
A failed request keeps the previous successful result. Duplicate mission builds
are blocked while a build is pending. API/proxy errors appear in the relevant
view. Kits show the generated support assets and the actual BFM setup geometry.

Fly Now filters template/map/era compatibility, service windows, upcoming
modules, aerial-refueling capability, and BFM helicopter eligibility before
submission. Builder cards and rail items are native buttons with selection and
disabled states. Contact closes with Escape and restores focus. All view and
utility navigation remains available at 390 pixels. Browser history restores
views and Builder steps; an options-loading failure offers a visible retry.
The existing design tokens, typography, and palette remain in place.

Reopening a saved/shared carrier recipe now populates the hull before restoring
deck aircraft, layout, equipment and launched support. Changes to those controls
save immediately, including dynamically rebuilt deck checkboxes. Browser reload
was checked with Stennis, launch layout, a selected Tomcat, equipment off and CAP
on; all choices were retained.

## Architecture boundaries

`missiongen/build_context.py` resolves and validates world setup, ownership,
home base, weather, corridors, and comms into an explicit `WorldContext`.
`StarterBuilder.build()` still orchestrates placement in its existing order.
`missiongen/artifacts.py` owns serialization and deterministic ZIP packaging.
The public `missiongen.generate` and old builder imports remain compatible.

`server/recipe_contract.py` derives the public recipe JSON schema from the
engine dataclass and enums (`/api/recipe-schema` and OpenAPI). It preserves
omitted-field/template semantics. `server/mission_manifest.py` projects engine
stats into the existing compact Mission Kit response header.

`server/generation.py` limits API builds to one active generation per server
process by default. Mission, briefing, and kneeboard generation share that
limit. Excess builds get 503 with Retry-After: 3; slots release on failure.
Duration/success and admission rejections are logged. `GENERATION_CONCURRENCY`
configures the process-local limit. More workers multiply capacity; this is not
a distributed queue or a production memory-budget measurement.

`frontend/assets/mission-results.js` owns result state, downloads, and Kit
rendering, served by a narrow `/assets` mount. Other UI behavior remains in the
existing page for an incremental refactor.

Pack replacement writes a complete hidden staging directory before publishing,
restores the old directory on a publication exception, serializes in-process
catalog/bundle access, publishes manifest edits with a temporary file/rename,
and uses unique temporary archive names with a storage-specific cache namespace.
This protects ordinary runtime failures and concurrent bundle creation. It is
not a crash-durable transaction across the two directory renames or a
cross-process lock. Individual FileResponse paths also are not immutable
revision snapshots. Revisioned storage is the next step if multiworker writers
or uninterrupted concurrent replacement/downloads become a requirement.

## Dependency and airport data

PyDCS remains the mission model and serializer. Its Python source is unchanged.
The exact vendored upstream commit is now recorded in its provenance document.
See `pydcs-current-audit.md` for current upstream capabilities, the actual 9,524
measured parking headings, and the three maps lacking those measurements.
Airport exports are unchanged. The subsequent direction fix deliberately removes
static-aircraft heading jitter on measured stands and adds id/coordinate-bound
survey imports; see `parking-direction-survey.md`. No new headings were
fabricated for the three unmeasured maps.

## Validation

Eight before/after recipes produced identical .miz bytes, briefing Markdown,
stats, and warnings: modern, Cold War, carrier, defensive BFM, F-14B(U)/DTC,
storm weather, WWII Channel, and the Proud Phantom Sinai lineup. This isolates
the phase extraction using the same dependency environment on both sides,
before the separately requested exact-direction behavior change. Regenerated
coaching/brief PNGs use the pinned production Pillow version; earlier checked-in
images were not byte-identical under that renderer.

New behavior tests exercise real JavaScript functions in Node: pending states,
immutable recipes, duplicate builds, failure paths, independent Kit downloads,
Quick Flight compatibility, schema boundaries, navigation, generation capacity,
and pack replacement failure/concurrent bundle creation.

Manual browser checks covered generation and Kit documents through all three
entry points, keyboard selections/rail navigation, Contact Escape, Back
navigation, shared Unicode and BFM recipes, invalid-link recovery, and mobile
navigation at 390 pixels. Guide screenshots/PDF and corridor charts were
regenerated; the freshness registry includes the extracted JavaScript asset.

The final frozen full run passed **4,277 tests, with 61 skips, in 160.92 seconds**
on four workers. Earlier timing measurements on this machine were 524.67 seconds
serially and 268.69 seconds with two workers; regression checks were added while
fixing the issues those runs exposed. The final quick check passes **200 tests in
12.58 seconds**, including carrier-restoration checks both with and without a
scenario preset. The refreshed artifact checks pass 42 tests in 5.98 seconds.
Direction tests
inspect generated .miz headings, duplicate stand identities, partial imports,
invalid data, atomic-write failure, and survey-unit coverage. Tests use temporary
storage and Python 3.12 with pinned Pillow 12.2.0/reportlab 4.4.10 and bundled
Node.js. Production Docker uses Python 3.11. A local Proud Phantom pack was
built to satisfy the existing release-artifact checks; the ignored binary pack
is not part of this patch. No DCS cockpit/flight validation, production load
test, deployment, hosting migration, or Discord integration was performed.

## Faster test workflow

`python3 scripts/test.py` runs focused development checks in temporary storage.
`python3 scripts/test.py --full` retains the entire release suite, with up to
four workers when optional pytest-xdist is installed; otherwise it runs serially.
`--workers` or `TEST_WORKERS` overrides the count. `--dist loadfile` keeps each
module's expensive mission fixture on one worker. `--profile` reports durations.
The preflight script uses the same bounded parallel policy and still checks all
tests. Most slow checks generate and compare multiple ramp missions; no such
coverage was removed or replaced with a permissive assertion.

## Integration and subsequent work

This isolated branch does not alter the original application checkout. Review
and apply it against the latest source, resolving any intervening frontend
changes from the other agent. Their promised Comm plan/generator recovery
commit is not included unless it was already in base `9360a0b`.

Further extraction should move placement subsystems behind `WorldContext` one
at a time with semantic output checks. The remaining builder is about 2,000
lines; renaming or splitting every method at once would not improve the tested
boundaries. Measure CPU, peak memory, and generation latency before choosing
worker counts, artifact reuse, or another hosting platform. Saved missions and
Discord can build on the stable recipe/result contracts afterwards.
