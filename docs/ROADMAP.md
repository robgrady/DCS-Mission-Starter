# DCS Sortie Starter — Roadmap

*October 2026 · owner-only, in the app at `/admin/roadmap` · the past lives in
CHANGELOG.md — this page is only ever about what's next, and why.*

**North star:** *Select, don't search.* A DCS pilot gets a living,
period-accurate mission in under a minute — no editor, no Lua. We set the
stage, you write the play. **You are never given a flight plan you did not ask
for**: there is no waypoint editor and none is planned. Waypoints appear only
where a routed strike *is* the mission, where a curated training ride's
printed syllabus *is* the flight plan (the route is the lesson, so the
mission carries it), or where the pilot switched on **Automatic waypoints**
(off by default).

**The engineering ethic, in one line:** the mission is generated and so is the
paperwork, so the paperwork is recomputed from the mission and a disagreement
is refused — *cockpit and paper agree by construction*. Every expert gap in
the commercial corpus was a hand-copied number. We do not copy numbers.

**The boundary on Training:** *Training teaches only what the mission can
MEASURE, and only what unlocks a sortie you could not otherwise fly.
Everything else is reference, not coaching.* Two tests, in order: can Mission
Editor conditions observe it without Lua, and does it unlock a sortie
(formation → flying with a lead, AAR → range, BFM → the fight, Case III → the
boat)? Failing routes an idea to the cheap channel — a kneeboard page, a guide
section, a chart — not to the bin. A course is *done* when a real pilot flies
it end to end and the check ride grades, not when it stops being extensible.
**The F-4E pipeline is done at v1.104.1.** No second pipeline starts until
somebody finishes the first one.

## Where the product is today

**v1.107.0**: four doors (Fly now · Library · Train · Builder), thirteen
maps, the existing Flightline visual design, the published pack format and
F-4E training pipeline. The release adds the airfield guide and reliability
boundaries for recipe validation, Mission Kits, generation capacity, artifact
serialization and pack publication. The comm-plan layout and three recovered
generators are included. The Library audit still has 17 entries with confirmed
behavior mismatches; generation success is not a content-validation pass.

## The bets

Four themes carry the next two quarters. Everything in Now/Next hangs off one
of them; an item that hangs off none is a candidate for *Later* or for no.

1. **Truth.** The thing no commercial campaign has: a file that cannot
   disagree with its brief. Comm plan shipped. Remaining gaps are in the
   cockpit, where only a sortie can look.
2. **The pipeline, finished before it is widened.** One aircraft flown to
   graduation beats three shipped. Growth is by reuse (BFM cards, AAR lanes,
   Case III are airframe-agnostic), not by new syllabi.
3. **The squadron's desk is someone else's product.** Digital Kneeboard
   Simulator shipped, in Aug–Oct 2026, a roster, courses with gradesheets,
   a currency board, ATO posting, LSO grading and Tacview debriefs — most
   of what the Dash-One PRD described. **Dash-One is paused** (October
   2026) pending a decision on what, if anything, it does that DKS does
   not. Sortie Starter's job is unchanged: be the mission engine whose file
   cannot disagree with its brief, and hand that file to whichever desk
   the squadron uses. Progress currently stays browser-local; optional personal
   mission storage is reopened for consideration in F13/F15 below.
4. **The Doc folder and the campaign.** What every commercial campaign ships
   and we do not yet: a printed brief, a kneeboard PDF, an in-flight guide
   per map, and chained sorties with the clock and fuel carried — all derived
   from the recipe so they cannot drift.

## ▶ Now

- **Deploy 1.107.0** (`fly deploy` from the unzipped release) and check
  `/api/health` says so. *Bet 1.*
- **Close the F-14B(U) front-seat question in the cockpit.** The file, the
  card and both radios agree; Heatblur's own missions program the jet the
  same way. Discriminator: fly the same mission in the plain F-14B. The ME
  now shows channel names, which is the second way to check. Rob's sortie,
  not code. *Bet 1.*
- **Library truth before expansion.** Resolve the 17 behavior mismatches
  and historical boundary issues in the [Library audit](library-validation-2026-10-02.md).
  Check the recipe submitted from the actual Library and Builder as well as
  generated groups, routes, objectives and printed claims. *Bet 1.*
- **Architecture follow-ups.** First unify recipe/preset resolution, then
  extract builder placement phases, browser recipe state and API services.
  See the [refactor decision](architecture-refactor-followups.md) for scope,
  compatibility limits and verification. GitHub pushes work; verify remote
  commit IDs when reporting release status.
- **Formation departures (AI runway line-up).** DCS 2.9.24 added the
  advanced waypoint action, 2.9.30 the group option; pydcs has neither and
  does not need to. The feature is built end to end — a *Formation
  departures* knob beside Pattern traffic, two-ship sections that carry
  the action, the brief sentence, 17/17 mutations — behind one gate: the
  Lua encoding has to come from a Mission-Editor-saved `.miz`, not a
  guess. **Rob: save the same 2-ship AI group twice, option on and off,
  and send both files.** One dict later the knob appears. Note ED's own
  campaign authors removed the feature in the same patch that shipped the
  option; it stays off by default. *Bet 1.*

## ◇ Next

- **A squadron's ladder inside its pack.** The comm table is per mission and
  per browser; a `comms` block in a course pack makes it per squadron, so
  every mission in the pack is on the SOP without anyone typing. *Bet 3.*
- **DKS integration — waiting on his MCP.** Pull, not push: a Sortie Starter
  MCP server over the JSON API we already have (`generate_mission(recipe)
  → .miz + manifest`), so a squadron in DKS or in Claude asks for a Case
  III and the file lands in their ATO with brief, kneeboard pages, DTC and
  comm plan as a sidecar. Until then: import one of ours into DKS and
  write down what survives (our `channelsNames` is what his comm-plan
  import would read); ask him for the tool list, the comm import's source
  fields and his kneeboard page size. *Bet 3.*
- **Cockpit-parameter verification.** The readback gate is built and off on
  the F-14 and Hornet until `list_cockpit_params()` output arrives for each;
  then `cockpit.py` gains two lines and the channel-2 problem is caught by
  the mission itself. *Bet 1.*
- **Bet 1 needs eyes.** The say/do reader must read kneeboard images, not
  only text — 60 of 97 corpus missions brief "refer to the PDF". *Bet 1.*
- **The Doc folder**, then **campaign export** (`.cmp`, chained sorties,
  score-keyed alternates — no Lua, the platform does it). *Bet 4.*
- **F-4E FRS units** — instrument recovery (TACAN penetration, ILS to
  minimums) and radar work with Jester — then a **UPT school on a free
  trainer** so the pipeline is universal (TF-51D is in every install). *Bet 2.*
- **Keep the gate fast.** Focused development checks and bounded parallel
  release tests now ship. Track runtime and peak memory as coverage grows;
  preserve semantic mission checks and the full release gate.
- **Fuel on the card** — a per-airframe burn table turns each ETA into a
  planned fuel state; JOKER and BINGO become computed numbers. Data before
  code. **Timing on the other routed cards** (White Knights, Case III).
- **AI loadouts, phase 3** — Iron Hand strikers and escorted bombers still
  carry the air-to-air table. **Verified liveries** — blocked on one
  command against a real DCS install. **Verified magnetic variation** —
  until a per-theater table exists, TRUE and labelled is the honest answer.

## ◈ Later (demand-gated — the analytics tab decides)

- Quick Flight completion (Pattern Work, The Boat) · callsign polish ·
  "bandit fit" toggle · mixed-type flights · the heritage layer of Flightline.
  Library curation, moving convoys, multiplayer, helicopters/CSAR and maritime
  strike have more specific candidate scopes in F01, F07, F14, F19 and F20.

## Feature candidates — for consideration, 2 October 2026

These are **proposals for owner review**, not delivery commitments or additions
to the active Now queue. They combine the product, DCS and architecture views.
The [Library validation audit](library-validation-2026-10-02.md) found behavior
mismatches in 17 entries despite 334 successful builds. The first investment
should make the existing missions work as described; new missions and social
features follow that foundation. Existing roadmap items are refined below,
rather than counted as newly invented capabilities.

**Priority and sizing:** P1 = consider first; P2 = consider after the mission
foundation passes; P3 = discovery or demand-gated. S/M/L are relative scope
estimates, not calendar promises. Reach and development capacity are not yet
measured, so a numerical RICE ranking would imply precision we do not have.
Evidence is identified as an audit finding, an owner request or a hypothesis.
Assign an owner and estimate delivery only when a candidate is selected.

**Foundation before expansion:** repair the shared effective recipe/browser
state behavior, task-specific payloads and missing actors identified by the
audit. Add explicit generated-artifact contracts for each card and a small DCS
flight-validation matrix. Successful generation, structural validation and
flight testing are separate statuses. Content revisions and their test evidence
must remain identifiable after generator updates.

**Consider first — confidence and preparation**

- **F01 · A Library that explains what each entry supplies.** P1 / M.
  Separate missions, coached lessons, self-directed exercises, reference setups
  and multi-ride tracks. Add historical classification and expose what is
  scripted, what requires another human, and what is measured. Build on existing
  filters and tracks. **Evidence:** audit and owner request. **Depends on:**
  content contracts. **Accept when:** each card and its generated brief agree
  about mode, actors and assessment; users can distinguish a lesson from a
  reference setup before downloading.
- **F02 · Mission readiness and compatibility card.** P1 / M.
  Show required terrain, aircraft/mods and ship modules, player/crew seats,
  essential equipment and validation status before Generate. Extend the existing
  owned-module selection into a check of the complete mission, including AI and
  carrier dependencies. **Evidence:** audit. **Depends on:** versioned manifests
  and effective recipes. **Accept when:** known incompatible combinations give
  an actionable explanation, and every validation badge names its content and
  DCS/module revision rather than asserting an unrestricted pass.
- **F03 · Preview the generated mission before downloading.** P1 / M.
  Provide a compact theater preview with home/deck, targets, support aircraft,
  threat rings, applicable historical airspace and any authored route. Let the
  pilot verify the intended setup. **Evidence:** audit; usability hypothesis.
  **Depends on:** a read-only summary derived from the emitted artifact.
  **Accept when:** the preview and download use the same build ID, with no
  independently recomputed targets or invented route.
- **F04 · Historical date and authenticity controls.** P1 / L.
  Select a supported scenario date and distinguish reconstruction, historical
  adaptation and fictional exercise. Apply date ranges to overlays, factions,
  airbase host/operators, deployments, aircraft and stores. Show sources and
  approximate geometry clearly. **Evidence:** historian audit and owner request.
  **Depends on:** curated temporal data and DCS substitutions. **Accept when:**
  the 1973/1980/1982 scenarios emit matching dates and later boundaries/weapons
  cannot silently enter historically strict configurations.
- **F05 · Parking and departure readiness.** P1 / M.
  Show stand capacity, aircraft-size compatibility, reserved player/AI parking
  and parked-aircraft orientation. Identify which values are surveyed and which
  are fallbacks. Add a reusable survey/import workflow for missing map data.
  **Evidence:** owner requests and existing parking work. **Depends on:**
  versioned airport surveys and allocation checks. **Accept when:** supported
  stands have evidence for location and heading, oversized or conflicting
  assignments are detected, and sampled populated ramps depart successfully
  in DCS. This extends existing heading support.
- **F06 · Task-specific weapons and delivery presets.** P1 / M.
  Offer a small set of usable fits for the selected job: SEAD, precision strike,
  unguided delivery, recon or clean training. Add fuze/delivery settings where
  their encoding is verified, and print the same settings on the stores card.
  **Evidence:** audit and prior weapon-settings investigation. **Depends on:**
  aircraft capability data and Mission-Editor-saved reference files.
  **Accept when:** each preset contains the required weapon/pod and supported
  settings; the aircraft, preview and kneeboard agree. Keep choices focused
  instead of adding a full pylon editor.

**Consider after the foundation — better sorties and return use**

- **F07 · Complete, replayable scenario objectives.** P2 / L.
  Start with controlled intercept, moving convoy overwatch, troops in contact
  and escorted strike. Supply the actual actors, routes and events; state
  completion criteria and intentional limits on reset/replay. **Evidence:**
  audit. **Depends on:** repaired payloads and actor/task contracts. **Accept
  when:** one representative mission in each family is flown through its
  advertised objective and recovery in DCS. This expands the existing moving
  convoy idea after repairing the current cards.
- **F08 · Duration, fuel and recovery planning.** P2 / L.
  Extend the existing Fuel on the card/Timing items with estimated sortie length,
  tanker plan, computed JOKER/BINGO and suitable divert/recovery options.
  **Evidence:** existing roadmap; product hypothesis. **Depends on:** measured
  per-airframe burn assumptions, route/time data and compatible landing fields.
  **Accept when:** the briefing exposes assumptions and fuel reserves, and
  representative profiles validate the estimates. Do not imply that an estimate
  is a live aircraft fuel measurement.
- **F09 · Missions that fit the pilot's available session.** P2 / M.
  Offer short, standard and extended sessions with suitable ramp/air/deck starts,
  transit distances and preparation requirements. Pair these with a small set
  of supported skill presets. **Evidence:** usability hypothesis. **Depends on:**
  F01/F08. **Accept when:** sampled sorties fit the advertised time band and
  difficulty changes observable settings, without changing the central lesson.
- **F10 · Save and compare mission remixes.** P2 / M.
  Extend existing seeds and recipe sharing with named variants: change weather,
  time, threats or start position and see what changed. Offer repeatable training
  setups and fresh combat variants. **Evidence:** replay-value hypothesis.
  **Depends on:** normalized, versioned recipes and F03. **Accept when:** a
  same-seed comparison preserves unchanged settings and identifies content/engine
  updates that prevent an exact rebuild.
- **F11 · One complete flight pack.** P2 / M.
  Refine the existing Doc folder item into one download containing the mission,
  brief, readable kneeboard, communications, stores, map and a short installation
  note. Include accessibility/VR legibility review of the pages. **Evidence:**
  existing roadmap and product hypothesis. **Depends on:** one artifact manifest.
  **Accept when:** filenames/build IDs agree, every required document is included,
  and the pack can be installed from its instructions without using the Builder.
- **F12 · Honest debrief and training progress.** P2 / M.
  Extend existing gradesheets and local progress with a sortie review showing
  measured results, manual instructor items and next practice suggestions.
  Support explicit self-report and export; prototype result import only for a
  verified DCS output format. **Evidence:** existing training mechanics; return-use
  hypothesis. **Depends on:** assessment contracts and F13. **Accept when:**
  an unobserved action never becomes a scored pass, manual completion is labeled,
  and exported progress round-trips correctly.
- **F13 · My Missions on this device.** P2 / M.
  Extend the existing last-recipe restore into named saved missions, favorites,
  collections, notes and revision history, with JSON import/export. Separate
  saved recipes from downloaded mission files and identify when regeneration
  would change the content. **Evidence:** owner request to save missions.
  **Depends on:** recipe versioning and storage migration. **Accept when:** users
  can save multiple missions, reload and export them, with clear behavior if
  browser storage is unavailable. Later cloud storage can use the same model.
- **F14 · A cooperative flight package for friends.** P2 / L.
  Offer validated two/four-aircraft packages and supported multicrew roles, with
  task allocation, a common comm plan and per-flight briefing. Distinguish crew
  seats in one aircraft from separate client aircraft. **Evidence:** DCS/product
  hypothesis and seat-count audit. **Depends on:** F02/F06/F11 and a multiplayer
  smoke test. **Accept when:** advertised roles can join the same mission and
  fly the objective; module/crew restrictions are explicit before Generate.

**Explore later — social use and broader mission families**

- **F15 · Optional Discord sign-in and cloud My Missions.** P3 / L.
  Use Discord identity to save private recipes, collections and progress across
  devices. Retain account-free generation and local saves. Decide explicitly
  whether to retain mission bytes as well as recipes, including content revisions
  and retention. **Evidence:** owner's explicit request, reopening the prior
  no-accounts decision. **Depends on:** F13, account/session design, access
  controls and storage costs. **Accept when:** sign-in, cross-device access,
  export and account/data deletion work. Proposal only; Discord work remains
  deferred until the mission foundation is ready.
- **F16 · Share a mission on Discord.** P3 / M.
  Extend existing recipe links with a share card showing map, aircraft, era,
  player roles, prerequisites and a preview. Provide a stable landing page from
  which others can inspect and regenerate/download the referenced revision.
  **Evidence:** owner request. **Depends on:** F02/F03/F10 and stable sharing
  identifiers; private cloud sharing also depends on F15. **Accept when:** the
  recipient gets the described setup and private drafts stay private. Begin
  with a user-copied link/card; any bot posting would be a separately scoped,
  explicitly authorized integration.
- **F17 · Pack authoring and content review tools.** P3 / L.
  Extend existing admin pack uploads with a manifest editor, lint report,
  description-versus-actor checks, review status and revision comparison. Include
  author, license, historical sources and requirements. **Evidence:** Library
  audit and existing pack architecture. **Depends on:** F01/F02 contracts and
  content versioning. **Accept when:** a pack can be staged, reviewed and rolled
  back without a code deploy; source generation and installed bytes receive
  separate validation evidence.
- **F18 · Short linked operations.** P3 / L.
  Refine existing campaign export into a small, authored sequence: suppression,
  strike and recovery, with documented success/failure branches and briefing
  continuity. Validate the selected campaign format and carried state before
  promising persistence. **Evidence:** existing roadmap; retention hypothesis.
  **Depends on:** F07/F08/F11 and a DCS campaign-format spike. **Accept when:**
  a complete sequence is flown and transitions obey its stated conditions.
- **F19 · Helicopter transport and rescue starters.** P3 / L.
  Expand existing helicopter/FARP and CSAR ideas with an initial transport or
  pickup/return mission. Add surveyed helicopter-compatible starts, usable
  landing areas and role-specific briefs. **Evidence:** existing backlog;
  demand hypothesis. **Depends on:** helicopter placement and a verified pickup
  completion condition. **Accept when:** the chosen module can complete the
  stated task; any cargo interaction, external script or mod is explicitly
  declared and tested before inclusion.
- **F20 · Maritime interdiction and naval strike.** P3 / L.
  Expand the existing anti-ship idea into one validated moving ship/convoy
  scenario, suitable weapons, target identification/ROE and a recovery plan.
  **Evidence:** existing backlog and owner interest in carriers. **Depends on:**
  F06/F07, ship routing and verified attack behavior. **Accept when:** targets
  follow the authored route and the supported aircraft can complete the attack
  under the briefed conditions. Evaluate map water and terrain constraints
  explicitly, including Germany, before advertising carrier-based variants.

## Candidate architecture and decision gates

**Incremental architecture:** keep recipe resolution, content contracts,
historical data, mission composition, artifact inspection and delivery as
separate responsibilities. Introduce versioned schemas at their boundaries.
Refactor `builder.py` around selected features rather than doing a broad rewrite
before a user-visible improvement. Add DCS/PyDCS behavior through focused
adapters supported by Mission-Editor-saved fixtures and cockpit tests.

**Dependency order:** shared effective recipe and artifact contracts →
F01/F02/F06 → F03/F04/F05 → complete scenario families. Saved-recipe versioning
supports F10/F13, then F15/F16. Fuel data supports F08, which supports session
planning and linked operations. This is a sequence of prerequisites, not a
calendar or a requirement to finish every candidate.

**Delivery and hosting:** keep job execution and artifact storage behind
interfaces so local storage and future cloud saves can evolve independently.
Before selecting Render or Fly.io, benchmark peak generation memory, queue time,
download reliability and persistence/recovery. A provider change requires that
evidence; this feature list does not assume migration is necessary.

**Select a first slice:** fix the audited missions and preset flow, then choose
F01/F02 plus one of F03 or F13 based on pilot feedback. Collect a baseline for
generation/download success, incompatible downloads, time to a usable sortie,
repeat generation and mission-related reports. Treat download success as a
delivery measure; it cannot establish that a DCS sortie worked. Review expansion
only after representative pilots complete the repaired missions.

**DCS reference:** use the [official DCS User Manual](https://www.digitalcombatsimulator.com/en/downloads/documentation/dcs-user_manual_en/)
for mission/campaign concepts, then verify exact file encodings and behavior
against the supported DCS build. Documentation and a successful PyDCS build do
not substitute for flight validation.

## Decided — and not re-opening without a reason

- **No waypoint editor.** Where a mission needs a plan, the mission brings it.
- **No Lua in the library.** Trigger-only, so every mission is inspectable
  and portable. Revisit only as an opt-in for the campaign engine.
- **No guessed encodings.** A Mission Editor feature enters the generator
  only after a file the Editor saved has been read; until then the knob
  does not exist (see `lineup.py`).
- **Accounts decision reopened for consideration.** Generation and local
  progress remain account-free today. The owner's request for Discord sign-in
  and saved missions is the reason to evaluate F13/F15; cloud storage is not
  approved or implemented by adding it to this roadmap. Squadron rosters and
  operational administration remain the squadron desk's responsibility.
- **Channels are fixed.** Frequencies are what SOPs differ on; the ladder's
  shape is what makes it learnable.
- **This page is the owner's.** The public reads the changelog.

---

*Rule of the page: this roadmap is updated in the same commit as any release
that ships one of its items, and the version line above is checked by the
release script. A stale roadmap is a bug — file it.*
