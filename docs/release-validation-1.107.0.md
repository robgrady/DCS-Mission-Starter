# v1.107.0 release validation

3 October 2026. Release tree integrates reliability/audit commit `4e53019`
with main commit `5785fc7` (airfield guide, pattern elevation, Comm plan layout
and recovered generators). Application/API/share-link compatibility retained.

## Completed gate

`bash scripts/release.sh 1.107.0` completed successfully:

- Full suite: **4,302 passed, 55 skipped, 9 deprecation warnings in 163.28 seconds**,
  four pytest-xdist workers, `--dist loadfile`.
- Every registered derived artifact is current.
- Real Chromium capture regenerated the integrated UI screenshots; the header
  shows v1.107.0. Guide PDF, HTML pages, corridor charts, coaching/grade/HUD
  cards and all bundled packs were regenerated.
- Release archive includes both platform launchers, tests, application code,
  vendored PyDCS, documentation and all source generators.
- All seven pack ZIPs and their nested mission ZIPs pass CRC checks. Every
  pack manifest records `built_with.app: 1.107.0`.

Environment: Python 3.12, pinned Pillow 12.2.0/reportlab 4.4.10, Node.js,
optional pytest-xdist and Playwright/Chromium. Production Docker uses Python
3.11; this local gate does not represent a production deployment/load test.
The nine warnings concern TestClient and Pillow test API deprecations.

## Bundled content

Packs are delivered separately for upload at `/admin`; they are not committed
or included in the core application ZIP. Extract the mission-pack bundle before
uploading individual `.sspack` files.

| Pack | Content version | Mission files |
|---|---|---:|
| `aar_boom_modern_F_16C_50_kc135.sspack` | 1.0.1 | 11 |
| `aar_probe_modern_FA_18C_hornet_kc135mprs.sspack` | 1.0.1 | 11 |
| `cq_case3_f14.sspack` | 1.0.1 | 5 |
| `cq_case3_hornet.sspack` | 1.0.1 | 5 |
| `timing_f4e.sspack` | 1.0.1 | 5 |
| `wk_checkout.sspack` | 1.0.1 | 11 |
| `wk_proud_phantom.sspack` | 3.0.1 | 11 |

Total: 59 generated mission files in seven packs. Content patch versions
record corrected documents/placement independently of the application version.

## Limits and remaining work

The [Library audit](library-validation-2026-10-02.md) still records 17 entries
with behavior mismatches and historical boundary issues. This release integrates
the audit and priorities; it does not claim those findings have been corrected.
DCS cockpit/flight validation, formation-departure encoding verification,
production deployment, load measurement, hosting migration and Discord features
were not performed by this release gate.

See [architecture follow-ups](architecture-refactor-followups.md) for the
remaining extraction priorities and the [Roadmap](ROADMAP.md) for product work.
