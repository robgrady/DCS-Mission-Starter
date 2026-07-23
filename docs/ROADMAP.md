# DCS Sortie Starter — Roadmap

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
- **Sortie Starter Brief** — pre-flight pack: cartographic theater chart,
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

## 💡 Idea board — unprioritized brainstorm (DCS-player wishlist)

*Not commitments. Anything here can be promoted into Next when it earns it.
Everything respects the north star: reference and stage-setting, never player
waypoints.*

**Mission & scenario depth**
- **COIN / Afghanistan-era ops** — convoy overwatch, FOB resupply, ridge-line CAS,
  CSAR with a survivor radio; the map is begging for them.
- **COMAO packages** — the player as one element of a timed strike package (AI
  SEAD sweep ahead, escort flank, stand-off jamming) without routing the player.
- **Naval strike scenarios** — ASuW: shadow, ID, and strike a surface group;
  era-correct (Styx-era boats vs modern SAG).
- **Campaign-lite chains** — the outcome seed of one mission feeds the next
  recipe: lose a SAM site today, it's gone tomorrow. Recipes make this cheap.
- **Seeded wildcards** — optional "something may happen" toggle: SAM ambush,
  zombie contact, diverted tanker, engine-start abort drill.
- **Helicopter-first templates** — Petrovich/George crew-ops, sling-load
  logistics chains, dustoff medevac under SHORAD.
- **Training syllabus track** — a progressive qual ladder (nav → BFM → BVR →
  SEAD → package lead) with each rung a Library card.

**Realism & environment**
- **Historical-date weather** — pick a real date: archived METAR-style weather,
  correct moon phase and sun times for the theater.
- **Weather fronts & winds aloft** — multi-layer wind profiles and moving cells
  instead of one static preset; icing bands in the right eras.
- **Era-correct night ops** — airfield lighting states, NVG-era gating, dark-ramp
  cold starts with follow-me truck.
- **Doctrine-true red air** — Soviet GCI-grid CAP behavior vs Western sweep
  patterns per era, not just skill sliders.
- **Period callsign packs** — nation- and era-correct callsigns end to end
  (no "Texaco" over the GDR in 1975).
- **Tail-code & BuNo sequencing** — squadron blocks numbered like a real flight
  line (already half-built via onboard numbers).

**Briefing, nav & comms**
- **Auto approach plates** — TACAN/ILS approach plates for home + divert fields,
  drawn to our chart standard, in the kneeboard.
- **Divert card** — nearest suitable fields with headings, distances, and fuel
  estimates from home/AO.
- **SRS export** — the comms plan as a SimpleRadio channel preset file next to
  the .miz.
- **QR brief handoff** — QR code on the PDF brief that opens the mission data
  card on your phone/tablet kneeboard.
- **TacView debrief pack** — auto-enable the right flags and ship a debrief
  checklist keyed to the mission's objectives.

**Carrier & fleet**
- **Cyclic ops schedule** — event-driven deck: launch cycle, recovery window,
  Case III stack times printed on the kneeboard.
- **Recovery tanker + LSO picture** — hawking tanker overhead, era-correct
  CV NATOPS numbers on the brief.
- **Escort stations that react** — plane-guard helo and shotgun destroyer
  repositioning with deck state.

**Product & platform**
- **Loadout presets (opt-in)** — era-authentic stores presets for the player
  flight; never forced, never a route.
- **MP server pack** — one click: mission set + rotation manifest ready for a
  dedicated server.
- **Mission date picker** — full date (not just era) driving weather, daylight,
  moon, and roster gating.
- **Range scoring lite** — strafe/bomb scoring triggers on the practice range
  (a v2.0 appetizer that works today).
- **In-app "what changed"** — release-notes card in the UI fed from CHANGELOG.

## 🗺 New maps

**Afghanistan — SHIPPED** (v1.21): 25 airports authored from a real install
export, projection probe-calibrated to 0 m error. **Iraq next** — same runbook;
unlocks the Northern/Southern Watch no-fly-zone scenarios. Both headed upstream
to pydcs.
