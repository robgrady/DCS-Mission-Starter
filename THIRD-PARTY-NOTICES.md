# Third-Party Notices

DCS Sortie Starter's own source code (everything outside `vendor/`) is licensed
**MIT** — see `LICENSE`. It also includes and depends on third-party components,
listed here with their licenses and attribution.

---

## pydcs (`vendor/dcs/`)

- **What:** the Digital Combat Simulator Python mission framework, which builds
  and serializes `.miz` mission files.
- **Upstream:** https://github.com/pydcs/dcs
- **License:** GNU Lesser General Public License v3.0 (LGPL-3.0). Full text in
  `vendor/dcs/COPYING.LESSER` and `vendor/dcs/COPYING`.
- **Modifications:** none. This is an unmodified vendored copy; behavioural
  adjustments are applied at runtime via monkey-patching in
  `missiongen/_determinism.py`. See `vendor/dcs/PYDCS_PROVENANCE.md`.
- pydcs itself bundles terrain/airport/beacon data derived from DCS World
  (© Eagle Dynamics); that data is redistributed here as part of pydcs, under
  pydcs's own LGPL-3.0 distribution.

## Supercarrier deck geometry (`missiongen/data/deck_formations.json`)

- Editor-measured carrier deck offsets are derived from **Redkite's "Supercarrier
  Lua Templates v2a"** (community resource). Used with thanks. The values are
  factual measurements; if the author requests different attribution or removal,
  please open an issue.

## Fonts (runtime only — not bundled)

- The kneeboard and Mission Brief renderers draw text with **DejaVu Sans / Mono**
  fonts loaded from the host system at runtime (e.g. `/usr/share/fonts/...`).
  These fonts are **not distributed** with this project; no font files are
  included in the repository.

## DCS World data references

- Aircraft type ids, livery id strings, airbase names, TACAN channels, radio
  frequencies and similar identifiers reference **DCS World** (© Eagle Dynamics).
  These are factual identifiers used for interoperability, not redistributed
  assets. DCS World and its modules are the property of Eagle Dynamics and the
  respective third-party developers (Heatblur, etc.). This project is an
  unofficial community tool and is not affiliated with or endorsed by Eagle
  Dynamics.
