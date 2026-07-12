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
