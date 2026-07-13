# DCS Mission Starter — Product Roadmap

*v1.0 · July 2026 · Owner: Rob Grady*

**North star:** "Select, don't search." A DCS pilot gets a living, period-accurate mission in under a minute — no editor, no Lua, no digging through User Files. The heavy lifting (statics, defenses, comms, carrier ops) is done; the player writes the play. Never place player waypoints.

**Versioning:** semver (CHANGELOG.md). PATCH = fixes/data, MINOR = new capability, MAJOR = breaking recipes/share links. Current: **v1.3.0**.

---

## Shipped (v1.0.0 → v1.3.0) — the foundation

11 era-gated theaters with historian-checked presets · full mission engine (dressing, doctrinal SAMs, support air, ambient, FARPs, targets/range, nav points, kneeboards, comm ladder, share links) · real carrier strike groups with measured deck formations, CAP/AEW, Angel plane guard, carrier-as-home · Crew Ops (F-14) · runway/taxiway keep-out discipline · Populate Airfields panel (fill %, object types, era-gated ramp themes, map-aware defaults) · PDF guide with screenshots · Mac launcher · Replit/Fly.io/Docker deploy configs.

---

## NOW — v1.1.x patches (continuous)

**Theme: trust the output.** Fold in Rob's in-game findings as PATCH releases.

- Carrier anchor verification (PG, Marianas, Kola, Sinai) — coordinate fixes
- Angel station-keeping behavior at matched 25 kts (fallback: short racetrack)
- Non-SC hull deck offsets (Forrestal/Invincible/Essex) — extract measured community templates
- Small-field parking density (Sinai/Germany), approx NTTR nav coords
- Iceman flag value units once IronMike answers (kts/ft assumed)

## ✅ SHIPPED v1.3.0: Wizard navigation (UX Phase 1)

**Theme: the page grew past its design.** Per ux-redesign-plan.md (hybrid chosen over strict tabs to protect the re-roll loop).

- Left progress rail: every step with ✓ + current value; click scrolls
- Completed sections collapse to one-line summaries
- Generate + share link pinned in the rail — always visible
- Populate-airfields and carrier as expanded panels (drawer pattern)
- Pure frontend; recipe format untouched. Shipped 2026-07-12 with localStorage autosave (state survives refresh; sections never unmount).

## v1.4.0: Aircraft picker (UX Phase 2)

**Theme: your ramp, exactly.** The feature the new layout makes room for.

- Per-type selection inside Populate Airfields: theme cards become starting points, +/− weight counts per era-valid type, grouped fighters/heavies/support/helos
- Live mix bar: resulting proportions + estimated aircraft count at current fill
- New `dress_mix` recipe field — share links carry custom mixes; server-side era validation (anachronism guard applies)
- Decision open: nameable/saveable mixes (bridge to the personal library)
- **Per-base population overrides** (Rob, 2026-07-13): an expandable "Per-base
  overrides" table inside Populate Airfields — one row per base on the map,
  MIL/CIV badge, include-toggle, and a compact fill override that defaults to
  "inherit global". UX call: NOT a wall of always-visible sliders (6–10 sliders
  of clutter for a control most users touch rarely) — progressive disclosure
  behind one "Per-base…" expander. Civilian rows appear greyed ("not
  populated") with a deliberate "populate anyway" escape hatch for sandbox
  builders. Recipe: `dress_overrides` map; share links carry it.
  (The military-only default itself shipped early as v1.3.2.)

## v1.5.0: Crew Ops II

**Theme: the back seat is the product's moat.**

- AWG-9 sort drill (pure sensor gym, solo-friendly) · TARPS recce · LANTIRN FAC(A)
- Instructor difficulty tier (injected failures: lase windows, notching bandits, EMCON)
- F-14B(U) release day: swap provisional type id for the real one, verify Jester/Iceman flags in-game, drop pending-module warnings — the izlid/intercept templates go "works today"

## v1.6.0: Visual fidelity

**Theme: ramps that photograph well.**

- Liveries for airfield statics (aggressor schemes at Nellis, squadron tails per theme — livery_id already proven on deck statics)
- Measured deck data for non-SC hulls
- Germany map's 100+ FRG/GDR helipads as FARP spawns

## ✅ SHIPPED as v1.2.0: Mission graphics — F10 drawing layers (pulled forward)

**Theme: the map briefs the mission.** Extend the proven drawings mechanism (NTTR nav points, range rings already ship) to every mission element that has geometry, so the F10 map reads like a planned ATO instead of empty terrain. Pulled forward at Rob's call; shipped 2026-07-12.

Drawn zones (each from geometry the engine already computes):
- **Tanker tracks** — racetrack outline + label block (callsign · freq · TACAN · altitude), drawn from the refuel_flight anchor/orbit points
- **AWACS & AEW orbits** — same treatment
- **CAP stations** — racetrack + station label on the threat axis
- **Carrier ops box** — CSG operating area + BRC arrow (blue, coastal maps)
- **Target area rings** — circle + name over each strike package (mirrors the trigger zones)
- **FARP service rings** — the rearm/refuel radius players actually care about
- **Bullseye marker** — labeled on both sides' maps
- **SAM threat rings (design decision)** — planned red WEZ circles drawn on the BLUE layer only, framed as "intel picture": realistic (you brief known threats), and red MP players don't get their own SAMs highlighted

Design rules:
- **Layer discipline**: coalition-private info on Blue/Red layers (DCS renders them per side), shared references (bullseye, nav points, range) on Common — MP-safe by construction
- **One visual language**: consistent colors/line weights across all zones (racetracks dashed, threats red rings, references neutral) — documented in the guide
- **Kneeboard parity**: the same geometry already feeds the kneeboard theater page; graphics and kneeboard stay in sync automatically because both draw from the same data
- **User-selectable layers (refined requirement)**: not one master toggle — a "Map graphics" checklist in the wizard where each layer is added/removed individually: Nav points · Tanker tracks · AWACS/AEW orbits · CAP stations · Carrier ops box · Target rings · FARP rings · Bullseye · Threat rings (intel). Sensible defaults per mission shape (e.g. tanker track auto-on when the tanker block is on); the existing nav-points block folds in as the first layer of this system. Recipe carries the layer set (`map_layers`), so share links reproduce the exact map picture.
- No player waypoints, ever — zones inform, they don't route

## LATER — v2.0: Community (the original vision)

**Theme: fix "I can't find what I want on User Files" at the catalog level, not just the generator level.** MAJOR because accounts change the product shape.

- P1 personal library: accounts, saved recipes, named custom mixes, mission history
- P2 public catalog: browse/search shared recipes by map/era/aircraft/template — a share link IS the mission, so the catalog is metadata, not file hosting (cheap to run, nothing goes stale)
- Quick-start mode (3 clicks: era → map → jet → fly) once real traffic shows the funnel

---

## Operational track (parallel, not versioned)

1. **GitHub push** — blocked on repo URL/token from Rob; tags v1.0.0–v1.3.0 ready
2. **Deploy** — Replit Autoscale (verified) or Fly.io; then a domain
3. **Community feedback loop** — post to DCS forums/Reddit after deploy; in-game validation reports drive the v1.1.x patch train
4. **New maps as pydcs ships them** — proven pure-data, near-zero cost (Afghanistan/Iraq candidates when terrain data lands)

## Decision points for Rob

| When | Decision |
|---|---|
| ✅ Decided | Hybrid rail shipped in v1.3.0 (strict tabs rejected — protects the re-roll loop) |
| Before v1.4 | Weights vs exact counts; nameable mixes now or at v2.0 |
| ✅ Decided | SAM threat rings shipped as blue-layer intel picture, on by default (uncheck to hide) |
| Before v2.0 | Hosting/auth approach for accounts (cost vs free-tool ethos) |
| Anytime | Deploy target: Replit (fastest) vs Fly.io (custom domain story) |
