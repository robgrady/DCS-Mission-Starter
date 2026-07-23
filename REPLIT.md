# DCS Sortie Starter — Replit Implementation Brief

*For the Replit agent (and any hosting/re-skinning agent). Read this fully before
touching anything. Package version: see `missiongen/__init__.py` (`__version__`),
also served at `/api/options` → `version`.*

---

## 1. What this application is

**DCS Sortie Starter** generates ready-to-fly missions for DCS World. A user
either picks a curated scenario from the **Mission Library** or configures one in
the **Builder** wizard; the server generates a downloadable `.miz` on demand from
a small "recipe" (map, era, coalition, aircraft, threats, seed…). Same recipe +
seed always produces a byte-identical mission — that determinism powers share
links, so **missions are never pre-baked or stored; only recipes matter.**

Architecture (all included, nothing to scaffold):

- `server/app.py` — FastAPI backend. Serves the frontend at `/` and the API:
  `GET /api/options` (all wizard/Library data incl. templates + version),
  `POST /api/generate` (recipe JSON → `.miz` download),
  `GET /api/dl?r=<code>` (share link → regenerated download),
  `POST /api/brief` (briefing pack), `GET /api/health` (readiness; 503 on bad data).
- `frontend/index.html` — the complete single-file UI (entry, Library, Builder).
- `missiongen/` — the generation engine (pure Python).
- `vendor/dcs` — vendored pydcs library (LGPL-3.0, unmodified — do not edit).
- `requirements.txt`, `.replit` — install + run config.

## 2. THE PREFERRED IMPLEMENTATION: run it, don't rebuild it

This is a **complete, tested, runnable application.** The correct deployment is:

```
pip install -r requirements.txt
PYTHONPATH=vendor uvicorn server.app:app --host 0.0.0.0 --port <PORT>
```

(the included `.replit` already encodes this). Do **not** regenerate, rewrite, or
re-scaffold the app. Every regeneration in the past has dropped features and
frozen old versions. Serving `frontend/index.html` as shipped gives the exact,
QA-verified product.

## 3. If you re-skin the UI anyway — the non-negotiable contract

A branded wrapper (site nav, theme, login) around the app is welcome, but the
following must be preserved **exactly**:

1. **Two paths at entry:** "Pick from the Library" and "Build a Mission", with a
   persistent toggle between them.
2. **ALL scenario templates live in the Mission Library — there is NO
   Scenario/Template step inside the Builder wizard. Do not add one back.**
   The Library is a card gallery: each template from `/api/options` → `templates`
   renders as a card using its `library` block (`role`, `premise`, `threat` 1–5,
   `players`, `featured`, `new`) plus `eras`, `needs_carrier`, `default_map`.
   Cards are colour-coded by role (air-to-air, strike, SEAD, CAS, carrier,
   training, historic) and filterable by role, era, and difficulty. A template
   with no `library` block still gets a card (synthesize sensible defaults).
3. **Card → detail → two actions:** a detail view shows the premise, era
   selector (for multi-era templates), crew-difficulty for crew-ops templates,
   and "what's set up for you"; its two actions are **Generate & Download** and
   **Open in Builder to tweak** (pre-fills the wizard from the template's
   `recipe`, then the user lands in the Builder with everything editable).
4. **The Builder keeps every existing step and option** — Era, Map, Coalition &
   basing, Airfields (ramp themes + per-base overrides + Ramp Composer), Threats
   (intensity + tier), Support & extras, Carrier deck, F10 Map graphics, Review.
   Nothing simplified, renamed, or removed. Era is a first-class step here AND a
   filter in the Library.
5. **Generation is on-demand** via `POST /api/generate` with
   `{"recipe": {...}}`. Never pre-generate or cache `.miz` files server-side as
   a substitute. The seed ("Variation") stays visible and re-rollable — same
   seed = same mission; new seed = fresh variation.
6. **Share links** use the code from the recipe (`/api/dl?r=<code>`) so a link
   fully regenerates the mission.
7. **Display the backend version** from `/api/options.version` in the UI (e.g.
   next to a BETA badge) so deployments are verifiable against `CHANGELOG.md`.
8. **Never place player routing waypoints** in any UI copy or feature — the
   product's north star is "we set the stage, you write the play."

## 4. What's new since the previously deployed build (v1.16.2)

If the live site was last generated from v1.16.2, this package adds:

- **Mission Library + two-path entry** (v1.19.x) — the headline UI change; the
  old in-wizard "Template" step is gone.
- **F-14B(U) full support** (v1.17–v1.18): verified DCS type id `F-14BU`, real
  airframe footprint, radio presets, carrier ops, **DTC/DTM cartridge
  auto-injection** into generated `.miz` files, DTC setup card in the brief pack.
- **Correctness fixes** (v1.16.3+): pinned `pyproj` (required by vendored pydcs),
  WWII coalition fix (Germany correctly red on Normandy/The Channel), strict
  request validation, temp-file cleanup, `/api/health` returns 503 on bad data
  packs, versioned share links.

## 5. Verification checklist (run after deploy)

1. `GET /api/health` → 200, `"ok": true`.
2. `GET /api/options` → `version` matches this package's `CHANGELOG.md` top entry.
3. UI shows that version; entry screen offers **both paths**.
4. Library shows **all** templates from `/api/options.templates` as cards
   (8 at v1.19.1); filters work; a card's **Generate & Download** returns a
   `.miz`; **Open in Builder** lands in a fully-populated wizard.
5. The Builder has **no Scenario/Template step**, and all its original steps
   are present and functional.
6. Generate the same recipe+seed twice → identical file (determinism intact).

## 6. Licensing note

Project code is MIT (© Authentic Media LLC). `vendor/dcs` is pydcs under
LGPL-3.0 and must remain unmodified and included. Keep `THIRD-PARTY-NOTICES.md`,
`LICENSE`, and the license section of `README.md` intact in any deployment.
