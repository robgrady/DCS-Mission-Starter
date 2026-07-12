# DCS Mission Starter

**Select, don't search.** A web-based mission *starter* for DCS World: pick a map, era,
coalition, and aircraft, and get a downloadable `.miz` with airfields dressed with
era-accurate static aircraft and equipment, functional SAM sites, and support flights
(tanker/AWACS) on station with a non-conflicting comms/TACAN plan.

**We set the stage — you write the play.** The starter never places player waypoints.
Open it in the DCS Mission Editor and build your mission on top.

## Features (P0)

- **Maps:** Caucasus, Syria (data-pack driven; more coming)
- **Eras:** Cold War (1965–1985), Modern (2000s+) — filters statics, parked aircraft, SAMs
- **Full aircraft roster:** every flyable DCS module, straight from the pydcs unit database
- **Building blocks:** airfield dressing (static aircraft on real parking stands, ground
  support equipment, infrastructure), complete SAM sites (SA-2/3/6/11, Hawk, Patriot)
  with doctrinal layouts, SHORAD, tanker + AWACS with auto-assigned freqs/TACAN,
  comms card, starter briefing
- **Template pack — Backseat Ops:** RIO/WSO-driven F-4E scenario using the Heatblur
  Jester/Iceman PROXY flag API (IZLID designation run; Iceman flies, you work the pit)
- **Seeded:** same recipe + seed = same starter, always regenerable

## Quick start (macOS)

Double-click **`run_mac.command`** in Finder. First run sets up the environment
(needs internet, ~1 minute); the wizard then opens at http://127.0.0.1:8000.
If macOS blocks the script the first time, right-click it → **Open** → **Open**.
pydcs ships vendored in `vendor/dcs`, so no special installs are needed.

## Quick start (any OS, manual)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi "uvicorn[standard]" pillow pyproj
PYTHONPATH=vendor uvicorn server.app:app
# open http://127.0.0.1:8000
```

Generate samples from the CLI without the server:

```bash
python scripts/generate_sample.py   # writes to samples/
```

Drop the generated `.miz` into `Saved Games/DCS/Missions/` and fly, or open it in the
Mission Editor and keep building.

## Architecture

```
missiongen/            generation engine (pure python, no web deps)
  recipe.py            wizard inputs; recipe+seed = reproducible starter
  builder.py           orchestrator
  dressing.py          BB-1..3  static aircraft / GSE / infrastructure
  airdefense.py        BB-5..6  SAM sites + SHORAD (functional groups)
  kits.py              doctrinal SAM site layouts
  support_air.py       BB-11..12 tanker / AWACS
  comms.py             BB-18 freq & TACAN allocator
  backseat.py          Backseat Ops template pack (Heatblur PROXY flags)
  data/eras.json       era whitelists per faction (versioned data pack)
  data/maps.json       per-map coalition presets (versioned data pack)
server/app.py          FastAPI: /api/options, /api/generate, /api/health
frontend/index.html    single-file wizard
scripts/               CLI generation + smoke test
```

Design principles: unknown unit types **fail loudly** (`/api/health` validates the data
packs), recipes are saved instead of artifacts, and the era/placement **data packs are
the product** — the code is just plumbing.

## Roadmap

See the project requirements doc (v0.3): P1 accounts + personal recipe library,
P2 public catalog with faceted selection, more maps/eras, more Backseat Ops scenarios.

## Roadmap

The product roadmap ships with the app: [docs/ROADMAP.md](docs/ROADMAP.md), also served
at `/api/roadmap` and linked from the web UI.

## About

Developed by **Authentic Media**. Free community tool — provided **as-is, with no
warranty of any kind** (see [LICENSE](LICENSE), MIT). Not affiliated with or endorsed
by Eagle Dynamics or Heatblur Defense.
