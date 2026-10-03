# v1.108.0 release validation

3 October 2026. Corrects the 17 behavioral Library findings C1–C6 and preset
resolution issue C7. See [correction evidence](library-validation-1.108.0.md)
for entry-specific capabilities and disclosures.

## Release gate

`bash scripts/release.sh 1.108.0` completed successfully after preserving the
single-player AI wingman on WK-9/10:

- **4,339 passed, 57 skipped, 9 deprecation warnings in 164.97 seconds**;
  four pytest-xdist workers with `--dist loadfile`.
- All derived artifacts current; real Chromium screenshots, PDF guide, HTML
  documentation, corridor/coaching/grade cards and seven packs regenerated.
- All seven `.sspack` archives and their 59 nested missions pass ZIP CRC checks.
  Every manifest records `built_with.app: 1.108.0`.
- Content versions: `wk_proud_phantom` 3.0.2; other six packs 1.0.2.
- Full Library matrix: 334 builds, zero failures; all 44 affected variants/seeds
  pass emitted actor/store/task contracts. Actual browser checks cover 23 preset
  submissions and 17 successful Library Generate downloads, whose mission
  archives pass the same structural contracts.

Local environment: Python 3.12, pinned Pillow/reportlab, Node.js, optional
pytest-xdist and Playwright/Chromium. Fly Docker uses Python 3.11; live checks
are recorded separately in deployment evidence. The warnings are TestClient
and Pillow API deprecations. Skips concern optional capabilities/absent fixtures.

## Production content and rollback

The pre-deploy inspection found six published packs on machine `2869d64a914208`
and none on `784546dc427948`, each with an independent volume. Update the four
already-published official generated packs (`wk_checkout`, `wk_proud_phantom`,
`aar_boom`, `aar_probe`) using the validated 1.108.0 producer outputs. Preserve
`awi_basics` and `pp_campaign` unchanged and synchronize that existing six-pack
public catalog to the empty volume. Do not modify other persisted application
stores or publish additional syllabi as part of this correction.

Before replacement, retain old official pack directories at
`/data/release-backups/library-1.108.0.tar.gz` on the source volume. Previous
application image:
`registry.fly.io/dcs-mission-starter:deployment-01M3ZPSKZX225KENYZHSE1H63G`.
A rollback must restore application and content together, on both volumes.

Final deployment/image/health/catalog checks are saved in local release evidence
and the deployment follow-up document. Independent per-machine pack writes need
a durable shared publication contract in the 2.0 architecture work.

## Limits

Three C6 exercises are truthful self-directed/instructor-led syllabi, not newly
automated coaching. Historical boundary/date findings remain open. DCS flight
validation of road movement, JTAC, strike/recovery and TARPS remains necessary.
No surveyed airport coordinates/headings or vendored PyDCS files changed.
