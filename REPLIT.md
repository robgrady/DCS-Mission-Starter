# DCS Sortie Starter — Replit Implementation Brief

*For the Replit agent (and any hosting/re-skinning agent). Read this fully before
touching anything. Package version: see `missiongen/__init__.py` (`__version__`),
also served at `/api/options` → `version`.*

---

> **This package is v1.113.0.** Verify a deploy with `GET /api/health` — it
> returns the running `version`, plus `data_pack_errors` (the endpoint returns
> 503 when non-empty) and `liveries_verified`.

Increment the semantic application version for every delivered change batch,
including refactors and documentation corrections on development branches.
Never deploy changed code under an earlier release's version; see `AGENTS.md`.

## 1. What this application is

**DCS Sortie Starter** generates ready-to-fly missions for DCS World from a
recipe (map, era, aircraft, threats and seed). Fly now, Library, Train and
Builder share the same engine. A recipe and seed reproduce the mission within
the same generator release; preserve a downloaded `.miz` for an exact archive.
Published collections are fixed authored downloads stored separately from the
application image.

Architecture (all included, nothing to scaffold):

- `server/app.py` — FastAPI backend. Serves the frontend at `/` and the API:
  `GET /api/options` (all wizard/Library data incl. templates + version),
  `POST /api/generate` (recipe JSON → `.miz` download),
  `POST /api/readiness` (bounded selection checks and declared requirements),
  `GET /api/dl?r=<code>` (share link → regenerated download),
  `/mcp/` (Streamable HTTP integration; see `docs/MCP.md`),
  `GET /api/mission-kit?r=<code>&version=<release>&sha256=<native-checksum>` (complete mission kit),
  `GET /api/mcp-guide` and `/llms.txt` (public agent guide and discovery index),
  `POST /api/brief` (briefing pack), `GET /api/health` (readiness; 503 on bad data),
  `GET /api/sources` (the product's bibliography, with the admin-curated
  Thanks list injected at request time), `GET /api/credits` (that list as JSON).
- `frontend/index.html` and `frontend/assets/*.js` — the assembled UI and explicit controller adapters.
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

**Analytics: your deployment reports to nobody by default.** The official site
runs Google Analytics, but the measurement id is read from the environment
(`GA_MEASUREMENT_ID`, see `server/ga.py`) and is deliberately NOT in the page
source. Unset — which is what you get out of the box — the page makes no
request to Google at all. Set your own id if you want analytics on your
deployment, and if you do, **update the privacy paragraph in the footer of
`frontend/index.html` to describe what YOUR deployment collects.** That
paragraph is a statement to your visitors, not decoration; shipping it
unchanged while running a different tag is the one thing here that would be
worse than having no analytics.

## 3. If you re-skin the UI anyway — the non-negotiable contract

A branded wrapper (site nav, theme, login) around the app is welcome, but the
following must be preserved **exactly**:

1. **Two paths at entry:** "Pick from the Library" and "Build a Mission", with a
   persistent toggle between them.
2. **Scenario templates live in the Library; there is no Scenario step in
   Builder.** Keep one catalog with **All content / Missions / Collections**.
   `frontend/assets/library-catalog.js` projects declared variants and fixed
   requirements for cards, search, filters, ownership and detail configuration.
   Quick-flight items and individual track members stay off the shelf; only
   installed packs appear as collection cards. Preserve full distinguishing
   titles, collection count, actual aircraft/maps and textual **Threat**. Do not
   restore static NEW promotions, NEW badges or the unsupported Newest sort.
   Show at most three featured picks without duplicating them in the remaining
   catalog. Keep secondary filters collapsible and preserve active filters.
3. **Card → detail → action.** Configurable missions honor matching aircraft,
   era and map selections and offer **Generate & Download** and
   **Customize in Builder**. Summaries and historical context update with the
   selection. Fixed collections display their complete requirements and flying
   sequence, offer an authored collection ZIP and individual Mission/Briefing
   links, and have no misleading configuration controls. **My DCS content**
   declares maps, aircraft and additional modules in this browser. Compatibility
   checks every fixed requirement or a matching configurable variant; unknown
   requirements remain unconfirmed. Preserve the existing fonts and palette.
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
8. **Never place player routing waypoints unless the mission calls for them** —
   the north star is "we set the stage, you write the play." Three things
   count as the mission calling: a routed strike template, the curated
   training rides whose printed syllabus IS the route (White Knights carry
   the squadron's own plan — the route is the lesson), and the pilot's own
   `bb_route` tick ("Automatic waypoints" in the UI). `bb_route` is the
   sanctioned opt-in (off by default) and the strike templates are the format
   exception. Anything that routes a player without a request is a bug.

## 4. What changed — where to look

**This section used to list "what's new since v1.16.2" inline.** It was still
saying that thirty-two releases later, which is worse than saying nothing: a
hosting agent reading it would have configured for a build from months ago.

A "since version X" summary pinned to a hard-coded X can only ever rot, so
there isn't one any more. Two files are kept current by the build and are the
only place to look:

- **`docs/RELEASE_NOTES.md`** — written for the person flying. Also served at
  `/api/whatsnew`.
- **`CHANGELOG.md`** — the engineering record, every change, newest first.

`tests/test_release_notes.py` fails the build if the current version is missing
from either, so they cannot be behind the code.

## 5. Verification checklist (run after deploy)

1. `GET /api/health` → 200, `"ok": true`.
2. `GET /api/options` → `version` matches this package's `CHANGELOG.md` top entry.
3. UI shows that version; entry screen offers **both paths**.
4. Library shows **all** templates from `/api/options.templates` as cards;
   filters work; a card's **Generate & Download** returns a `.miz`;
   **Open in Builder** lands in a fully-populated wizard. (Count deliberately
   not stated here — it changes every time a mission is added, and a number in
   a checklist is a number that goes stale.)
5. The Builder runs its six screens — Mission, Flight, Opposition, Airfields,
   Support & presentation, Review — with nothing collapsed and exactly one
   GENERATE button, on the Review screen.
6. Generate the same recipe+seed twice → identical file (determinism intact).

## 6. Licensing note

Project code is MIT (© Authentic Media LLC). `vendor/dcs` is pydcs under
LGPL-3.0 and must remain unmodified and included. Keep `THIRD-PARTY-NOTICES.md`,
`LICENSE`, and the license section of `README.md` intact in any deployment.


### Catalog ownership and release identity (v1.108.2)

`PACKS_OWNER_MACHINE` names the Fly machine holding the public catalog. Keep this
setting aligned with its volume when replacing that machine. Catalog metadata,
pack downloads and admin pack operations route to it; large uploads send the
`Fly-Force-Instance-Id` header before transfer. Do not add replicas as independent
writers. Private contact, sponsor, credits and analytics stores remain local.

Back up the public catalog including `.catalog/`, `.revisions/` and legacy pack
directories. A pointer change selects a revision; existing downloads retain their
old files. Retained revisions consume disk space: archive/prune only revisions
that are not current and are past the chosen retention window. Windows uses file
pointers too, with no symlink permission requirement.

Every release records a manual impact review in `docs/manual-release-review.json`.
The title, API and PDF cover all derive their version from the application.
