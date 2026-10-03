# Production deployment — 1.108.0

3 October 2026. Completed `fly deploy --remote-only --app dcs-mission-starter`
from validated release commit `77654216efe658e72f7826af282b72ab46e7cd6f`.
GitHub main and annotated v1.108.0 resolve to that commit. Release assets'
server-reported SHA-256 digests match local `SHA256SUMS.txt`.

New image:
`registry.fly.io/dcs-mission-starter:deployment-01M40MW7GBESBDZMQ3AYXQZJHC`
(106 MB). Both existing dfw machines updated; no volumes removed/replaced.

| Machine | Persistent volume | Checks |
|---|---|---|
| `2869d64a914208` | `vol_re1oyn8lggdw6g34` | Public health/options 1.108.0; six packs; corrected published WK-10 download; live TIC, A-6 escort strike and TARPS generation |
| `784546dc427948` | `vol_v8el5jqnjxkw17lv` | Public health/options 1.108.0; six packs; corrected published WK-10 download; live convoy, WK-10 and clean CQ generation |

Live desktop/mobile Library loads on both machines show six packs and no
JavaScript errors. Authored AWI/campaign file hashes match across volumes.

All eight downloaded mission archives (two published plus six live-generated)
passed their emitted actor/store/task contracts. Requests were pinned to each
machine using Fly's documented routing header. Native production generation
runs Python 3.11, complementing the local Python 3.12 release gate.

## Published catalog

Both machines now serve the existing six IDs: `aar_boom`, `aar_probe`,
`awi_basics`, `pp_campaign`, `wk_checkout`, `wk_proud_phantom`.
The four official generated packs are rebuilt with app 1.108.0: three content
versions 1.0.2 and Proud Phantom 3.0.2. AWI and the campaign were copied unchanged
from the previously populated volume to the previously empty volume.
Additional generated CQ/timing syllabi were not newly published by this fix.
No private application stores were copied or replaced by catalog synchronization.

The old official pack archive is retained on **both** volumes at
`/data/release-backups/library-1.108.0.tar.gz`, plus a local copy. Previous image:
`registry.fly.io/dcs-mission-starter:deployment-01M3ZPSKZX225KENYZHSE1H63G`.
Rollback application and official content together on both volumes, preserving
authored AWI/campaign files. No rollback was required.

Local evidence: `outputs/releases/1.108.0/production/` contains health responses,
actual downloaded archives and check summaries. Build/deploy logs and manifest
hash checks are recorded alongside release evidence. DCS flight validation and
historical findings remain open; current catalog synchronization does not
provide future cross-machine write replication (see architecture-2.0.md).
