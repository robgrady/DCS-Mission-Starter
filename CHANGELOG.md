# Changelog — DCS Mission Starter

All notable changes are documented here. This project follows
[Semantic Versioning](https://semver.org/) as of 1.0.0.

**Versioning policy**
- **MAJOR (X.0.0)** — breaking changes: recipe/share-link format changes that
  invalidate existing links, removed templates or building blocks, API breaks.
- **MINOR (1.X.0)** — new capability, backwards compatible: new maps, templates,
  building blocks, carriers, crew scenarios, aircraft.
- **PATCH (1.0.X)** — fixes and data corrections: airfield/preset fixes, deck
  offset tuning, warning text, doc updates.

The version lives in one place — `missiongen/__init__.py` (`__version__`) — and
is surfaced in the web UI header, `/api/options`, `/api/health`, and the PDF
guide cover.

---

## [1.1.2] — 2026-07-12

### Changed
- License and attribution updated for **Authentic Media LLC**: strengthened
  no-liability disclaimer covering software defects, generated mission files,
  and third-party modified/tampered/redistributed copies (official source
  only); no support or updates promised. Footer, guide cover, and README
  now state "no warranty and no liability."

---

## [1.1.1] — 2026-07-12

### Added
- **Roadmap ships with the product**: `docs/ROADMAP.md` served at `/api/roadmap`,
  linked from the app header and footer — the release plan is a published manifest.
- **Attribution & license**: Developed by Authentic Media; MIT LICENSE added —
  the tool is free and provided **as-is with no warranty of any kind**. Stated in
  the app footer, the PDF guide cover, the README, and the LICENSE file.
  Not affiliated with Eagle Dynamics or Heatblur.

---

## [1.1.0] — 2026-07-12

### Added — "Populate airfields" control panel (new wizard section 4a)
Airfield dressing is no longer a random grab-bag. Users now control exactly
how their fields are populated:

- **Fill slider (0–100%)** — how much of each field's parking to fill,
  replacing the coarse sparse/normal/busy for statics (density still scales
  air defenses and ambient traffic). Capped at 24 aircraft/field for FPS.
- **Object-type toggles** — parked aircraft, ground equipment, and
  infrastructure can each be switched off independently.
- **Ramp themes** — WHO parks on your fields, with weighted realistic mixes
  (`ramp_themes.json`), strictly era-gated:
  - Modern blue: **US Air Force** (Vipers/Eagles/Hogs/heavies, no Navy
    paint), **Red Flag exercise** (Nellis surge ramp: B-1/B-52 heavies,
    aggressor Vipers, Navy and allied visitors — Hornets, Mirages,
    Tornados), **Navy/Marine Corps**, **Joint expeditionary**.
  - Modern red: **VKS frontal**, **Long-Range Aviation** (Backfire/Bear base).
  - Cold War: **USAFE**, **NATO allied wing**, **US Navy** vs **VVS
    frontal**, **PVO interceptors**.
  - WWII: **RAF**, **USAAF** vs **Luftwaffe**.
- **Map-aware defaults** — Nellis is an Air Force base: the NTTR now
  defaults to the USAF theme (no more random F/A-18s), Andersen/Marianas to
  USAF, Cold War Germany to USAFE, Normandy to USAAF. "Auto" always picks
  the right ramp for the map; enemy fields dress with their own era default.
- Heavy airframes (B-1B, B-52, KC-135, C-17) now park on physically roomy
  stands even on terrains whose data flags no stand as "large" (NTTR).
- Share links carry the full population config; the wwii anachronism guard
  extends to every theme; invalid theme keys warn and fall back safely.

---

## [1.0.1] — 2026-07-12

### Fixed
- **Statics no longer appear on runways or taxi routes.** Free-placed objects
  could land on the movement area: the airfield infrastructure cluster was
  pushed 350 m from the ramp centroid at a *random* bearing (the ramp sits
  beside the runway, so this regularly dropped fuel tanks and tents
  mid-runway), GSE trucks could drift off the stand into taxilanes, and
  SHORAD point defense was placed 900–1400 m from the field reference point
  at a random bearing — often on the runway itself. New `placement.py`
  models every runway as a keep-out corridor (built from pydcs runway
  headings through the field reference point, with generous width to absorb
  shoulders, parallel taxiways, and magnetic-variation error) and all
  free-placed objects are validated against it:
  - Infrastructure cluster now anchors on the ramp side *away* from the
    runway axis and its row runs *parallel* to the runway — geometrically
    unable to cross it — with per-object validation as backstop.
  - GSE stays within the parking stand's own footprint (12–16 m off the
    aircraft; stands are 40–80 m wide) — apron, never taxilane.
  - SHORAD and SAM sites sample bearings until clear (SAMs demand 550 m
    margin so no launcher of the kit crosses the corridor).
  - Aircraft statics were always safe: they only occupy surveyed parking
    stands from the terrain data.
  - Verified: 30 generated missions across 10 maps / 3 eras / 3 seeds —
    12,256 free-placed objects, zero inside a runway corridor.
- **Period dressing is now a hard invariant.** Dressing data was already
  era-keyed (WWII fields only draw warbirds, Bedfords, Kübelwagens), but the
  health check now carries an anachronism guard: any future data edit that
  puts a jet, helicopter, or modern vehicle into the WWII era block fails
  `/api/health` loudly. No F/A-18 on a 1944 field, guaranteed.

---

## [1.0.0] — 2026-07-12

First locked release. Everything below is the 1.0 baseline.

### Theaters (11, era-gated)
Caucasus, Syria, Sinai, Persian Gulf, Nevada NTTR, Normandy 2, The Channel,
Marianas (all three eras), Cold War Germany, Kola, South Atlantic. Every preset
carries both sides' major airfields, validated against pydcs terrain data.
Historian-checked scenarios: October 1973 Sinai (IAF from Refidim vs the canal
SAM belt), 1982 Falklands OOB (San Julián/Puerto Santa Cruz), Fulda Gap,
NATO Northern Flank with Cold War Finland/Sweden neutral, 1944 Marianas.

### Mission engine
Era hard-gating (service windows × era windows, UI + server), airfield dressing
with period statics, doctrinal SAM layouts, tanker/AWACS per era, ambient
traffic, FARPs, target areas + range, NTTR nav points on the F10 map,
3-page PIL kneeboards, standard comm ladder (Guard 243 · Mother 264/71X/ICLS 11/
Link4 336 · Angel 262 · full list in the guide), share links that regenerate the
mission from a recipe code, seeded determinism. No player waypoints, ever.

### Carrier strike groups
Real CSG compositions and ship names (CSG-9 TR, CSG-3, CSG-5, CSG-8, Forrestal
CarGru 6, Invincible TF 317, Essex TF 58.1), doctrinal screen stations,
editor-measured Supercarrier deck formations (recovery/launch/underway/packed)
with a hard min-separation validator, deck crew + yellow gear, real air-wing
squadrons for CAP/AEW launch options, plane-guard SH-60 in Starboard Delta
during flight ops, carrier-as-home-base flow with deck-class aircraft
filtering, all boat systems active (TACAN/ICLS/Link4/ACLS).

### Crew Ops (F-14 only)
`rio_fleet_defense` — works today on the F-14A/B: solo (air start or carrier
warm start) or MP crew, GCI Picture menu, player-paced triggers.
`backseat_izlid` (Pilot + Jester) and `backseat_intercept` (RIO + Iceman) —
built on the F-14B(U) PROXY flag API, pending-module warned until Heatblur
ships. The F-4E has no crew AI (the WSO flies the jet) — by design, not omission.

### Product
Era-first wizard, one-click Mac launcher, vendored pydcs, illustrated PDF user
guide with a screenshot pipeline, 21-mission sample suite, Dockerfile + fly.toml.

### Pre-1.0 development history
Internal build numbers v1–v17 (see `claude/build-status.md` in the project for
the archaeology): core engine → carrier realism arc (real CSGs, measured decks,
stacking fix) → Crew Ops (F-14 correction) → map buildout → plane guard →
Sinai/Groom Lake/major-airfield pass.
