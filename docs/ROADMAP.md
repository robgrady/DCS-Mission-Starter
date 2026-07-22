# DCS Mission Starter — Roadmap

*July 2026 · lives in the app at `/api/roadmap` · versions in CHANGELOG.md*

**North star:** "Select, don't search." A DCS pilot gets a living, period-accurate
mission in under a minute — no editor, no Lua. We set the stage, you write the
play. **Never player waypoints.**

## ✅ Shipped (highlights through v1.19.x)

- **Mission Library + two paths** — pick a curated scenario (role-coded cards,
  era/threat filters, preview → generate or open-in-builder) or build from
  scratch in the full wizard. All scenarios live in the Library.
- **F-14B(U) day-one support** — verified type id, real airframe footprint,
  radio presets, carrier ops, **DTM cartridge auto-loaded** into generated
  missions (bullseye, fix points, threat plot lines — never your route), DTC
  setup card in the briefing pack, Jester/Iceman crew-ops scenarios.
- **Theater Identity** — each airbase dresses as its real owning nation
  (country, aircraft types, liveries); per-nation ramp rosters.
- **Historical Airspace (first slices)** — Berlin Air Corridors, Syria Euphrates
  deconfliction line, drawn to a MIL-STD-2525-based chart standard.
- **Mission Starter Brief** — pre-flight pack: cartographic theater chart,
  comms/nav, forces (PDF + Markdown), plus in-jet kneeboards.
- **The foundation** — 11 era-gated theaters, airfield dressing on real stands
  with measured parking headings, doctrinal SAMs + Threat Dial, carrier strike
  groups with measured decks, tanker/AWACS with a real comms plan, deterministic
  share links (a link *is* the mission), open source (MIT).

## ▶ Now

- **In-game validation pass** — corridors, nation ramps, Tomcat spacing, DTM
  cartridge in the sim.
- **Scenery keep-out + final parking surveys** (Falklands, The Channel) so
  statics never touch buildings and always face the painted lines.
- **DTC v3** — historical-airspace corridors as PTID plot lines; kneeboard
  "cartridge contents" page.

## ⏭ Next

- **More Library missions** — theater-specific scenarios (Syria SA-10 hunt,
  Channel sweep '44, Kola QRA, Normandy rail strike…).
- **Owned-modules profile** — tell the Library what maps/jets you own once; it
  filters honestly everywhere.
- **Mission-pattern scenarios** from the chart plates: DCA/CAP, strike COMAO,
  CAS kill box, carrier recovery.
- More nation alignment theaters · nation support-air callsigns · CSG ship paint
  · livery picker · saveable ramp mixes.

## ★ Pillars

**Theater Identity** — every map gets its real geopolitical + historical
character without configuration. Next slice: **Theater IADS** — nation- and
era-correct integrated air-defense laydowns at real sites.

**v2.0 Live Mission Scripting** — BRAA calls, in-mission scoring, corridor
discipline; opt-in, never intrusive.

**v3.0 Community** — accounts via Patreon: save missions to a private library
(recipes, tiny and permanent — never stale files), stable share permalinks,
upload-a-mission → dissect → reusable recipe, owned-modules profile stored on
your account. The generator itself stays free.

## 🗺 New maps

**Afghanistan, then Iraq** — authored from real install data and contributed
upstream to pydcs. Iraq unlocks the Northern/Southern Watch no-fly-zone
scenarios.
