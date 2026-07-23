# DCS Sortie Starter

**Select, don't search.** A web-based mission *starter* for DCS World: pick a theater,
era, coalition and aircraft, and get a downloadable `.miz` with airfields dressed in
period-correct static aircraft and equipment, functional SAM sites, support flights
(tanker/AWACS) on station with a real comms/TACAN plan, optional carrier strike group,
threat tuning, and F10 map graphics.

**We set the stage — you write the play.** The starter never places player waypoints.
Open it in the DCS Mission Editor and build your mission on top.

Developed by **Authentic Media LLC** — free community tool, provided as-is with no
warranty. Not affiliated with Eagle Dynamics or Heatblur.

## Features

- **11 theaters:** Caucasus, The Channel, Persian Gulf, Nevada (NTTR), Normandy, Syria,
  Sinai, Marianas, Germany, Kola, Falklands — each with historian-checked airbase presets.
- **3 eras:** WWII (1944), Cold War (1965–1985), Modern (2000s+). Era is the master filter
  for maps, aircraft, statics, SAMs and support — no anachronisms.
- **Full aircraft roster:** every flyable DCS module (period-filtered), straight from the
  pydcs unit database.
- **Airfield dressing:** static aircraft on real parking stands, ground equipment and
  infrastructure — runways/taxiways always kept clear.
  - **Ramp themes** — curated, era- and base-correct mixes (USAF, Red Flag exercise for
    both Modern and Cold War, Navy/Marine, VVS, RAF/Luftwaffe…).
  - **Ramp Composer** — pick exact aircraft and counts by role (89-type catalog, coalition
    separated), pre-populated from the chosen theme; stand-aware placement.
  - **Exact facing** — a measured parking-heading data pack (9 of 11 maps surveyed) makes
    lightweight **static** aircraft face their real painted lines; an optional AI-parked mode
    exists for the two unsurveyed maps.
- **Threats:** doctrinal SAM sites (SA-2/3/6/10/11, Hawk, Patriot) + SHORAD, plus a
  **Threat Dial** — intensity (extra area SAM belt + airborne enemy CAP, seeded) and
  era-gated system tiers (Light → Heavy).
- **Carrier strike groups:** real CSG compositions, measured deck formations, deck states,
  CAP/AEW, Angel plane-guard, carrier-as-home-base (coastal maps).
- **Support & briefing:** tanker + AWACS with TACAN/freq, ambient traffic, FARPs, strike
  targets, practice range, comms card on the **25 kHz radio raster**, in-jet kneeboards,
  nav reference points, F10 map-graphics layers.
- **Crew Ops (F-14) template packs** using the Heatblur Jester/Iceman PROXY flag API.
- **Mission Library:** two paths at entry — *Pick from the Library* (curated,
  role-colour-coded scenario cards with era/threat/difficulty filters,
  pick → preview → generate or open-in-builder) or *Build a Mission* (the full
  wizard). **All scenario templates live in the Library**; the builder has no
  scenario step.
- **Section-navigation UI:** one focused screen at a time with a progress rail, completion
  checkmarks, a live preview, and share links (recipe+seed → same starter, always
  regenerable; a share link *is* the mission).

## Deploying / hosting (IMPORTANT — read before re-generating anything)

This package is a **complete, runnable application** — do NOT rebuild it from
scratch. Run it as-is: `pip install -r requirements.txt`, then
`PYTHONPATH=vendor uvicorn server.app:app` (the included `.replit` already does
this). The frontend is served by the server at `/` from `frontend/index.html`.

If a hosting agent re-skins or regenerates the UI anyway, these product
requirements are **non-negotiable** and must be preserved exactly:

1. **Two paths at entry:** "Pick from the Library" and "Build a Mission".
2. **ALL scenario templates live in the Mission Library** (card gallery with
   role/era/difficulty filters, pick → preview → Generate or Open-in-Builder).
   **There is NO Scenario/Template step inside the builder wizard** — do not add
   one back. Template data comes from `/api/options` → `templates` (each entry's
   `library` block carries role/premise/threat card metadata).
3. The **builder keeps every existing step and option** (era, map, basing,
   airfields/ramp composer, threats, support, carrier, F10 graphics, review) —
   nothing simplified or removed.
4. Generation is **on-demand** via `POST /api/generate` (recipe JSON); missions
   are never pre-baked. Share links regenerate via `/api/dl?r=<code>`.
5. Display the backend version from `/api/options` (`version`) in the UI so
   deployments are verifiable against the CHANGELOG.

## Quick start (macOS)

Double-click **`run_mac.command`** in Finder. First run sets up the environment
(needs internet, ~1 minute); the wizard opens at http://127.0.0.1:8000.
If macOS blocks the script the first time, right-click it → **Open** → **Open**.
pydcs ships vendored in `vendor/dcs`, so no special installs are needed.

## Quick start (any OS, manual)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=vendor uvicorn server.app:app
# open http://127.0.0.1:8000
```

Generate samples from the CLI without the server:

```bash
python scripts/generate_sample.py   # writes to samples/
```

Drop the generated `.miz` into `Saved Games/DCS/Missions/` and fly, or open it in the
Mission Editor and keep building.

## Parking-heading survey tooling (optional, advanced)

`static` aircraft face their exact painted lines wherever a map has been surveyed. To
survey a new map you don't have Python for: request a pre-built survey `.miz`, fly it once
in DCS (it logs every spot's heading to `dcs.log`), and the maintainer bakes it in via
`scripts/import_survey.py`. See CHANGELOG for the workflow.

## Architecture

```
missiongen/            generation engine (pure python, no web deps)
  recipe.py            wizard inputs; recipe+seed = reproducible starter
  builder.py           orchestrator
  dressing.py          static aircraft / GSE / infrastructure + Ramp Composer (dress_mix)
  airdefense.py        SAM sites + SHORAD (functional groups)
  threats.py           Threat Dial (intensity + era-gated tiers), enemy CAP
  kits.py              doctrinal SAM site layouts (incl. SA-10 S-300)
  support_air.py       tanker / AWACS
  naval.py / deck.py   carrier strike group + measured deck formations
  comms.py             freq (25 kHz raster) & TACAN allocator
  graphics.py          F10 map-drawing layers
  backseat.py/crewops  F-14 Crew Ops template packs (Heatblur PROXY flags)
  data/*.json          era/map/theme/catalog/parking-heading data packs (the product)
server/app.py          FastAPI: /api/options, /api/generate, /api/health, /api/guide, /api/roadmap
frontend/index.html    single-file section-navigation wizard
scripts/               CLI generation, PDF guide, screenshots, parking survey tools
```

Design principles: unknown unit types **fail loudly** (`/api/health` validates the data
packs), recipes are saved instead of artifacts, and the **data packs are the product** —
the code is plumbing. Semantic versioning from v1.0.0 (`missiongen.__version__`,
[CHANGELOG.md](CHANGELOG.md)).

## Roadmap

Ships with the app: [docs/ROADMAP.md](docs/ROADMAP.md), served at `/api/roadmap` and
linked from the web UI. Next: livery picker, mission-import → template, Crew Ops II, and a
v2.0 Live Mission Scripting pillar.

## Contributing

The **data packs are the product**, and most of them are community-extendable
without touching engine code: parking-heading & scenery surveys, coastline
outlines, per-map/era **theater alignment** (who owns which base) and **nation
rosters**, historical-airspace overlays, ramp themes, and scenario templates.
The survey tooling under `scripts/` lets you export exact data from your own DCS
install for a map that isn't fully covered yet. See
**[CONTRIBUTING.md](CONTRIBUTING.md)** for the workflow, the determinism/testing
expectations, and where each data pack lives. In-game validation reports (with a
screenshot and the recipe/seed) are just as valuable as code.

## License

- **This project's own code** (everything outside `vendor/`) — **MIT**, see
  [LICENSE](LICENSE). © Authentic Media LLC.
- **`vendor/dcs/` is [pydcs](https://github.com/pydcs/dcs)** — vendored
  **unmodified** under **LGPL-3.0** (`vendor/dcs/COPYING.LESSER` + `COPYING`;
  provenance in `vendor/dcs/PYDCS_PROVENANCE.md`). Runtime behaviour tweaks are
  monkey-patched in `missiongen/_determinism.py`, never edited into pydcs source,
  so the library stays separable and replaceable per LGPL.
- Full attribution for pydcs, Redkite's deck templates, fonts and DCS data
  references is in **[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)**.

## About

Developed by **Authentic Media LLC**. Free community tool — provided **as-is, with
no warranty and no liability of any kind**, including for third-party modified or
redistributed copies. **Unofficial** — not affiliated with or endorsed by Eagle
Dynamics or Heatblur; DCS World and its modules are their respective owners'
property.
