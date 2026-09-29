# The Agent Handbook — how missions get made here

*Written by the agent that built v1.50 through v1.86, for the agent that
builds what comes next. Everything below was learned by shipping, and most of
it was learned by shipping it wrong first. Read this before touching
`missiongen/`.*

---

## 1. The product in one paragraph

**DCS Sortie Starter** generates ready-to-fly `.miz` missions for DCS World
from a small **recipe** (map, era, aircraft, threats, seed…). Same recipe +
seed = byte-identical mission, forever — that determinism powers share links
and mission packs, and it is the first invariant you must never break. A user
reaches missions through three doors: **Fly Now** (one-screen picker),
**Library** (curated cards + uploaded packs), **Builder** (six-screen wizard).
The north star: *"we set the stage, you write the play"* — no Lua in any
`.miz`, no flight plan the mission didn't call for, and **no card may promise
what the file does not contain** (the "say/do gap" — the defect class this
whole codebase is organized around hunting).

## 2. The stack

| Layer | What | Notes |
|---|---|---|
| Mission engine | **pydcs, VENDORED at `vendor/dcs`** | Not pip's 0.15.0 — that lacks the F-4E-45MC and current units. `PYTHONPATH=.:vendor` for everything. |
| Runtime deps | `fastapi`, `uvicorn`, `python-multipart`, `pillow`, `pyproj`, `reportlab` | pinned in `requirements.txt`. `pyproj` is load-bearing: vendored pydcs imports it at import time. `reportlab` is runtime because guides are generated per pilot choice. |
| Server | `server/app.py` (API + static frontend), `server/admin.py` (pack admin, `ADMIN_PASSWORD`-gated) | FastAPI. Deployed on Fly.io; packs live on a volume at `/data/packs` (`PACKS_DATA_DIR`). |
| Frontend | `frontend/index.html` — ONE file, vanilla JS | No build step, no framework. |
| Cards/pages | Pillow (`scripts/build_wk_coach_cards.py`, `build_wk_brief_pages.py`) | Committed PNGs; regenerate via the scripts, never hand-edit. |
| PDFs | reportlab (`wk_guide.py`, `aar_guide.py`, `scripts/build_guide_pdf.py`) | |
| Tests | pytest (~3,500 tests; ~20 min serial, ~10 min with two workers), Playwright/Chromium for real-browser guards | `pip install pypdf` for the PDF-readback tests. `pip install pytest-xdist` and run `-n auto --dist loadfile` — `loadfile` is required, not a preference (see below). `PYTHONDONTWRITEBYTECODE=1` in harnesses. |

Run anything like this:

```bash
PYTHONPATH=.:vendor python3 -m pytest tests/test_wk_coach.py -q
PYTHONPATH=.:vendor python3 scripts/build_pack.py wk_proud_phantom

# the whole suite, the way scripts/preflight.sh runs it
PYTHONPATH=.:vendor python3 -m pytest tests -q -n auto --dist loadfile
```

**`--dist loadfile` is load-bearing.** Several test modules share a
module-scoped fixture that generates an entire mission (`built`, `built_green`,
`built_drag`, `built_full_ramp`). xdist's default `--dist load` hands out
individual tests, so a module split across N workers builds its mission N
times — on a two-core box that can be *slower* than serial while looking like a
speed-up. Whole files to whole workers keeps one build per fixture.
`scripts/preflight.sh` probes for xdist and falls back to serial if it is
missing, because preflight has to work on a fresh unzip of the release zip
before anything is installed. Guards: `tests/test_preflight_parallel.py`,
`scripts/mutate_preflight.sh`.

## 3. The map of the code

```
missiongen/
  recipe.py        THE contract. Recipe dataclass + RECIPE_ENUMS + validate().
                   Every knob is a field; enums validated by name; bounds read
                   from the module that owns them (e.g. pattern.MAX_COUNT).
  builder.py       THE engine. One giant build: coalition/preset/lineup merge,
                   player group, arming, building blocks (tankers, AWACS, SAMs,
                   targets, pattern traffic, dressing), White Knights wiring,
                   kneeboards, briefs. Order MATTERS — see §6.
  templates.py     effective_recipe(key, era, map): template recipe block +
                   by_era/by_map overrides merged under the caller's values.
  data/*.json      maps (presets per era + lineups), eras, mission_templates,
                   tracks, aircraft_service, air_corridors, theater_identity,
                   parking_headings, ramp themes…
  wk*.py           The White Knights: wk.py (the 1980 squadron's transcribed
                   documents — every number is the paper's, not yours),
                   wk_route.py (leg tables + geometry), wk_coach.py (cue
                   triggers), wk_brief.py (page hold), wk_guide.py (PDF).
  packfmt.py/packs.py  .sspack format (docs/PACK_FORMAT.md is normative) /
                   volume storage. Composition ≠ curation ≠ distribution.
  pattern.py, dressing.py, targets.py, threats.py, loadouts.py, aar*.py …
server/            app.py (API), admin.py (pack upload/review), packref.py
frontend/index.html
scripts/           build_pack.py, release.sh, mutate_*.sh, card/page builders
tests/             one file per subsystem; guards named as sentences
docs/              PACK_FORMAT.md, PACK_AUTHORING_PROMPT.md, ROADMAP,
                   USER_GUIDE, this file
```

## 4. pydcs: the API you will actually use

```python
import sys; sys.path[:0] = [".", "vendor"]
import dcs
from dcs.mission import Mission, StartType
from dcs import action as A, condition as C, triggers as Tr
from dcs.unit import Skill

m = dcs.Mission(terrain_instance)          # builder does this for you
g  = m.flight_group_from_airport(country, "REX 1", actype, airport,
                                 start_type=StartType.Warm, group_size=2,
                                 parking_slots=[...])
g2 = m.flight_group_inflight(country, name, actype, pos, alt_m, speed=KMH)
g.add_runway_waypoint(airport)             # EVERY ground-start AI needs this
g.add_waypoint(pos, altitude=meters, speed=KMH, name="IP")
g.load_pylon((station, {"clsid": CLSID}), station)   # applies to ALL units
g.units[0].set_player();  g.units[1].skill = Skill.Excellent
m.triggers.add_triggerzone(point, radius=m_, hidden=True, name="WKC IP")
m.map_resource.add_resource_file(path)     # returns a ResourceKey for actions
m.save("out.miz")                          # and Mission().load_file() to read
```

### The unit traps — each one shipped a bug here

* **Waypoint and inflight speeds are KM/H.** `add_waypoint(speed=...)` and
  `flight_group_inflight(speed=...)` divide by 3.6 internally. We passed m/s
  for four releases; every route was commanded at 112 kt and the AI drove the
  length of the runway without rotating. Convert: `kt * 1.852`.
* **Trigger-zone speed CONDITIONS are m/s.** `aar_hud`/`aar_grade` correctly
  use `kt * 0.514444`. Two units in one API — check which side you're on.
* **Altitudes are metres** everywhere in pydcs. Feet live only in our data.
* **Coordinates: `x` is north, `y` is east**, metres. Heading 0° = north,
  90° = east. `pos.distance_to_point(other)` for ranges.
* **Ground-start AI without `add_runway_waypoint` doesn't fly** — its first
  instruction after brake release is a turning point 20 NM out, and it taxis
  down the runway instead of rotating. pydcs's own tankers/AWACS all add it.
* **Parking:** `flight_group_from_airport` claims `slot.unit_id` on terrain
  slot objects. Anything placed BEFORE a group is created doesn't know the
  group is coming — create every aircraft group before ramp dressing runs.
* **A jet can have TWO UHF radios, and the card does not say which one.**
  `presets.py` programmed exactly one for a long time. The F-14 has the pilot's
  ARC-159 (radio 1) *and* the RIO's ARC-182 (radio 2, 225-400 MHz among other
  bands) — and the RIO's is the set most crews use for boat comms. Casmo flew a
  Case III, keyed the radio he was on, and got 258.000 on "channel 2" while the
  card said 264.425. Rule: program every radio whose default channels are
  ENTIRELY in 225-400. That test, measured across all 78 airframes we ship, is
  what separates the A-10C's VHF ARC-186 (radio 1, 0% in band) from its UHF
  ARC-164 (radio 2, 100%). Three airframes have no pure set (AV-8B 85%,
  AJS37 91%, MiG-29 95%) and keep the older best-radio fallback.
* **DCS clobbers channel 1** of the first compatible radio with the group's
  assigned frequency, whatever a preset says. We put Flight on CH1 deliberately
  — plan with the engine, not against it.
* **`ShipGroup.set_frequency` takes HERTZ**; `FlyingGroup.set_frequency` takes
  MHz. Passing MHz put a whole battle group on 264.425 Hz.
* **pydcs writes no `modulation` for ships.** The editor writes frequency AND
  modulation; pydcs's `Ship.dict()` emits only the first. Carrier ATC is AM and
  the ARC-159 is AM-only, so FM would be unreachable. Corrected in
  `missiongen/pydcs_patches.py`, which is where any future
  editor-writes-it-and-pydcs-doesn't gap belongs — the vendored tree stays
  byte-identical to upstream so it can be re-pulled without hunting local edits.
* **A ship TACAN must be `aa=False`.** `ActivateBeaconCommand(aa=True)` leaves
  the channel number on the card looking perfect and moves the transmitter to
  the air-to-air band, where an aircraft in T/R receives nothing. This is the
  single most common cause of "my carrier TACAN doesn't work".
* **pydcs default missions pre-seed coalitions** (19 countries blue, 12 red).
  "Israel is in the blue coalition" asserts nothing — countries having UNITS
  is the measurable fact. `builder._get_country` MOVES countries between
  coalitions when history disagrees with pydcs defaults.

## 5. The Mission Editor's trigger system — what exists and what does not

Everything a mission can "do" at runtime is `TriggerOnce` / `TriggerContinious`
rules + actions. **Conditions can read position, altitude, speed, time, flags,
and whether something died. That is the entire list.** No dive angle, no mil
setting, no weapon events. Cards must never claim otherwise.

What we use, and the sharp edges:

* `A.PictureToGroup(group, reskey, seconds, clearview, start_delay, horz,
  vert, size, size_units)` — **THERE IS NO ACTION THAT REMOVES A PICTURE.**
  `clearview=True` replaces the previous one; the only way to stop showing
  something is to show something else (we ship an 8×8 transparent PNG to
  blank the screen). A continuous trigger redrawing a picture every second is
  a strobe — every phase must disarm itself the moment it fires
  (edge-triggered discipline; see `wk_coach.py`).
* **PLACEMENT IS NOT A FREE CHOICE — copy `aar_hud`'s.** Left / Center / 10 %
  is the only combination this product has ever had confirmed rendering in a
  cockpit (CHANGELOG 1.75.1, "All four from flying it"). v1.104.0 shipped the
  formation ladder at Bottom / 9 % on a sound human-factors argument and Rob
  saw **no card at all** while the same trigger set's text still arrived — one
  whole sortie spent to learn that. A new picture surface starts at those three
  values and only moves on cockpit evidence, never on reasoning. Ship every one
  with an F10 "show it now" item as well: it turns "is this rendering?" into a
  five-second check on the ramp instead of a lost release.
* **One message, one channel.** If a picture says it, the text must not say it
  too. `aar_grade.attach(hud=...)`, the check-ride debrief and
  `formation._coach(ladder=...)` all silence their text when the card is
  fitted, and all restore it when the art is missing — losing the picture must
  never also lose the coaching.
* `A.MessageToGroup(group_id, m.string(txt), seconds, clearview)`.
* `A.SoundToGroup` — a cockpit sound, not a radio call. **Jester/AI crew
  cannot be scripted to speak**; recorded WAVs on the intercom are the honest
  substitute, and they're optional per-phase (missing WAV = no sound action,
  never a broken build).
* `A.StartWaitUserResponse(flag_fwd, flag_back)` / `StopWaitUserResponse` —
  SPACE/BACKSPACE paging (the brief hold). **Documented footgun:** taking the
  BACK branch leaves the CONTINUE flag set; every branch must Stop, then
  clear BOTH flag blocks, then draw.
* `A.StartPlayerSeatLock(seat)` / `StopPlayerSeatLock` — takes the controls
  during the brief. **Active pause cannot be pressed by a mission** — it's a
  client keybind; never promise it.
* `A.ShowHelperGatesForUnit(unit_id, 1)` — the training missions' green
  fly-through boxes. **NATIVE, not Lua** (I wrongly said Lua twice; the ED
  forum thread on "SHOW HELPER GATES FOR UNIT" settled it). Gates render
  along the unit's route **from its ACTIVE point** — pin it with
  `A.SetActiveHelperGateToPoint(unit_id, n)` and advance it from your own
  triggers, or after a long ramp hold the boxes trace the wrong leg.
* `A.ActivateGroup(gid)` + `group.late_activation = True` — the hold/release
  pattern (now retired for wingmen; see §7).
* Flags: `A.SetFlag/ClearFlag`, `C.FlagIsTrue`, `C.TimeAfter`. **Flag block
  registry — collisions ship silently:** checkride 8700–8749, wk_coach
  8880–8899 (F_ARM=8899, room for 16 phases), wk_brief 8900–8939
  (F_DONE=8939), timing_coach 8860–8879 (F_ARM=8879) + check mode 8980–8985,
  aar_hud 8840–8859, aar_grade 8810–8839, cq_coach 8940–8979
  (gates 8976–8978), formation_hud 8760–8779, formation 8801–8809,
  crewops 200/300. **v1.104.0 nearly shipped the ladder on 8860** because that
  looked free next to aar_hud — it is timing_coach's. Read this list before
  taking a block, not after. A new subsystem
  claims a fresh block and adds itself to `test_the_flag_blocks_do_not_overlap`.
* **A trigger set reaches the mission ALL AT ONCE or not at all.** Build into
  a local list and `extend()` at the end. pydcs reads `TriggerOnce.predicate`
  at SAVE time, so a set that is half attached when the API drifts does not
  merely lose its coaching — it makes the `.miz` unsaveable, and every
  `attach()` in this codebase advertises "never fails a build". Before
  v1.104.0 three of them were only accidentally safe: their first trigger
  happened to be the one that raised. `formation_hud`, `formation._coach`,
  `formation._patient_lead` and `checkride` all do it properly now.
* Sequencing: every coached phase requires the PREVIOUS phase's flag
  (`prereq`), and `prereq` is a named key, not "the entry above" — PULLOUT
  hangs off TRACK, not RELEASE, so a shallow pop can't wedge the sortie.

## 6. builder.py order of operations (violate it and you ship the hangar bug)

1. Recipe validated (`recipe.validate()` — enums, ranges, lineup/era pairing).
2. Map preset for the era, **merged with the recipe's `lineup`** (a named
   order of battle: era says WHEN, lineup says WHO — `sinai.lineups.
   proud_phantom` is the worked example). A `home_airbase` not on the
   player's side is a **hard EraViolation** naming what your side holds —
   never a silent relocation (that fallback once launched eleven "Cairo West"
   missions from Israel).
3. Player group created — **two-ship if `wk.has_counterpart(ride, map)`**
   (see §7). Arming (`loadouts`, then the ride's own sheet fit — the card's
   stores go on the jet, group-wide).
4. Building blocks that CLAIM STANDS OR PLACE AIRCRAFT: pattern traffic, then
   ramp **dressing last** among them — dressing fills stands whose
   `unit_id is None`, keeps clear of claimed stands via three independent
   layers (two filters + `_occ_register` keep-out). Any aircraft created
   after dressing can be assigned an occupied shelter.
5. Targets: `bb_targets` anchors packages to enemy airbases — EXCEPT rides
   with a route TARGET leg, which get one deterministic depot placed ON
   `wk_route.leg_positions(...)["TARGET"]` (a brief must never list targets
   the flight plan doesn't visit).
6. White Knights wiring: player route (`wk_route.apply`), brief
   (`wk_brief.attach` — owns the coaching's arm flag), coaching
   (`wk_coach.attach`), gates triggers. The brief attaches FIRST because the
   cues must stay dark until the pilot has the jet.

## 7. The wingman lesson (three failures, then the answer)

**A separate AI flight cannot fly with a human.** It flies its own plan on
its own clock; no schedule, hold, or release changes that — DCS offers no
mechanism. We tried three designs and every one produced "the other REX
flight doesn't fly with me at all." The ONLY native mechanism is a unit
**inside the player's group**: he taxis behind you, forms on your wing,
rejoins on call, attacks via the radio menu. Costs: he will not fly scripted
two-ship geometry by himself — and the card says so plainly. Do not resurrect
`apply_counterpart` (deleted in v1.85.0; `counterpart_legs` survives only as
the two-ship predicate and the source of the numbers cards print).

## 8. Content doctrine

* **THE BOUNDARY ON TRAINING — apply this BEFORE writing any coached feature.**
  *Training teaches only what the mission can MEASURE, and only what unlocks a
  sortie the pilot could not otherwise fly. Everything else is reference, not
  coaching.* Full reasoning in `docs/ROADMAP.md` under the north star; the
  operational form is two questions and a routing rule:
  1. **Can Mission Editor conditions observe it without Lua?** If no, it is not
     a coached feature — no exceptions bought with cleverness. This is the
     honest-cue discipline (`formation_hud`, `aar_hud` both refuse a lateral cue
     on a sphere) promoted from an engineering ethic to a scope rule.
  2. **Does it unlock a sortie?** Formation → flying with a lead. AAR → range.
     BFM → the fight. Case III → the boat. A history chapter unlocks nothing: it
     is good, and it is content.
  * **Fails either test → route it to the cheap channel**, do not kill it: a
    kneeboard page, a guide section, a brief paragraph, a chart. Reference costs
    a doc build. Coaching costs art, a flag block, a trigger set, a mutation
    harness and **a sortie of Rob's time — the only cockpit this project has**.
    Most scope creep is a good idea arriving through the expensive door.
  * **Why it is written down:** the generator scales on enumerable axes (maps,
    eras, aircraft) and can reach "done"; training has no such list, so it
    absorbs anything offered to it while every individual addition looks
    correct. It is also the half that cannot be proven at a desk — v1.104.0 had
    a green suite, 29/29 mutations and a card that never drew. The unbounded
    category is the expensive one. Do not propose a coached feature to Rob
    without stating which test it passes.
  * **Definition of done for a course:** its syllabus flies end to end and its
    check ride grades. **The F-4E pipeline is done as of v1.104.1** — no second
    aircraft's pipeline begins until a real pilot completes the first.
* **Determinism**: fixed seeds in packs (`4400 + n`); builders use
  `self.rng` seeded from the recipe; no wall-clock, no unseeded random.
  `build_pack.py --check` rebuilds and diffs digests.
* **Historical honesty**: the White Knights numbers are TRANSCRIBED from a
  real squadron's 1980 documents (`wk.DOCS`); a wrong digit looks exactly
  like a right one, so arithmetic guards + single-digit mutations protect
  them. Where DCS forces a departure from history (Libya owns no Sinai
  airfield), the data file says so in a `note` rather than letting a pilot
  infer nonsense.
* **Say/do**: every claim on a card/brief/guide must be checkable in the
  `.miz`, and the guard reads the built file, not the source. When a promise
  and the file disagree, fixing the promise is as legitimate as fixing the
  file — but one of them changes.
* **Packs**: `docs/PACK_FORMAT.md` (normative), `docs/PACK_AUTHORING_PROMPT.md`
  (drop-in instructions for any AI; its code block is EXECUTED by
  `tests/test_pack_prompt.py` against the real installer). The image and the
  release zip carry no content; packs are built by `scripts/build_pack.py`
  and uploaded at `/admin`. A syllabus reaches the Library shelf as a
  published pack or not at all.

## 9. The verification ritual (non-negotiable)

1. **Build and read back.** Never trust that an action was appended — load
   the `.miz` (`Mission().load_file`) and assert on triggers, groups, points,
   zip namelist, pixel colors. `zipfile.ZipFile(miz).namelist()` for shipped
   resources.
2. **Prove every guard by breaking it.** Apply the mutation by hand, watch
   the named test fail, restore. A guard that was never seen red is a hope.
3. **Register the mutation** in the harness that owns the file:
   `scripts/mutate_white_knights.sh` (WK content + coached ride),
   `scripts/mutate_library_shelf.sh` (frontend/server/packs/pattern),
   `scripts/mutate_aar_academy.sh`, `mutate_aar_hud.sh`,
   `mutate_formation_hud.sh` (the ladder, the patient lead, the gradesheet
   cards). Harness rules:
   anchors must be UNIQUE in the file (the `mut` helper asserts count==1);
   `-k` selectors must match collected test names (a selector matching
   nothing exits 5 and reads as a false "caught"); every mutated file must
   be in `FILES` and the baseline; **never edit anything under the baseline
   (`missiongen/`, `tests/`) while a harness runs** — the drift check aborts.
   A WEAK result is re-aimed or the guard strengthened, never deleted to go
   green; when a defect is defended in depth, MEASURE it (remove the layers,
   watch it still hold) and retire the mutation with the measurement written
   down.
4. **Second-resolution staleness**: purge `__pycache__` between mutations
   (CPython's .pyc check is mtime+size); cache keys use `st_mtime_ns`.
5. Real-browser guards (Playwright against a live uvicorn) for anything the
   pilot only meets through the UI — timers, wiring, the shelf.

## 10. The release ritual

```bash
# docs first: CHANGELOG.md (the record — release.sh refuses a version with no
# entry), ROADMAP.md + REPLIT.md version stamps, bump
# missiongen/__init__.py __version__, bump pack CONTENT_VERSION in
# scripts/build_pack.py when mission bytes changed (semver of the CONTENT).
setsid nohup bash scripts/release.sh X.Y.Z > /tmp/rel.log 2>&1 < /dev/null & disown
# release.sh: regenerates every registered artifact (packformat/roadmap html,
# cards, brief pages, voiceover sheet, packs, guide PDF), full preflight,
# packages dcs-mission-starter-X.Y.Z.zip (repo root). ~25 min.
git add -A && git commit   # Rob does not use git — you do it
# deliver the zip (and any changed .sspack) to Rob
# Rob then: fly deploy; re-upload packs at /admin (volume survives deploys)
```

**Never edit a running shell script** (bash re-reads at a byte offset), and
never touch versioned files while `release.sh` or a harness is mid-run.

## 10b. The Case III pack (`cq*.py`) — a second syllabus engine

Built for Casmo's *"i have zero idea how to do a case 3 recovery so i was
flying around blind."* Same shape as the White Knights family, different
geometry:

| Module | Holds |
|---|---|
| `cq.py` | The doctrine as data — CV NATOPS §6.4 numbers, the radio sequence, the LSO thresholds, the per-airframe cockpit setup, and the five rides. Every constant carries its citation. |
| `cq_route.py` | Geometry hung off the SHIP, not a map axis. One unit vector does all of it: the marshal fix and the final approach are on the same line. |
| `cq_coach.py` | The cues and the grades — flag block **8940-8979**. |

## 10e. The Training Pipeline (`courses.py`, `course_kit.py`, `data/courses.json`)

A course is DATA over the shelf: schools > phases > units, where a unit is a
`reading`, a `track` (with optional ride range and preferred aircraft/era),
a `card`, or a `planned` unit with a `why`. `courses.resolve()` raises on any
reference the Library cannot honor — that is the contract that keeps the
page from ever linking to a ride that does not exist, and `test_courses`
runs it on every course. Readings live in `data/courses/<doc>.md` and are
served only when a course lists them (`reading_path` takes bare names). The
kit (`course_kit.build_kit`) is docs only — program PDF, gradesheet CSV,
readings — never missions (see v1.78.1). Progress is `localStorage` in the
browser; nothing server-side, by design. The frontend door is `#pipeline`
(`renderPipeline`, `unitRow`, `openReading`); it opens cards through
`openDetail(k, pref)` / `openTrack(id, pref)`, which honor a preferred
aircraft only where the card or wizard offers it. `scripts/mutate_courses.sh`
is the proof (20/20). To add a course: write the JSON, write the readings,
run the tests — nothing else to register.

## 10g. Authentic Style (`authentic.py`) — one page furniture

Every generated document draws the specimen (`docs/brand/
authentic-style-specimen.pdf`). ReportLab documents (`aar_guide`,
`wk_guide`, `course_kit`, `scripts/build_guide_pdf.py`) take styles and the
page template from `authentic.styles()` / `authentic.make_doc()`; PIL
documents (`brief`, `kneeboard`) call `pil_band` and take faces from
`brand.font()` with `banner` = Bangers, `display` = Barlow ExtraBold. The
palette is `data/brand/flightline.json` (document keys only; the site keeps
`sys_*`). Never name a built-in face in a renderer — `test_authentic`
scans for it. Static bold faces are cut from the variable fonts by
`scripts/cut_static_fonts.py`; re-run only if the VFs change.

## 10f. Check rides (`checkride.py`) — the instructor's framework in triggers

Per item, U/F/G/E; overall Q/Q-/U; critical items. Items are read off LEAD
(bank, vertical speed), time-in-band is a per-tick `IncreaseFlag` counter,
and a ratio is two counters growing at different rates compared with
`FlagIsLessThanFlag` (in×10 vs total×9 is 90 %). Flag block **8700–8749**.
The formation check is a PROFILE (`formation.PROFILES["check"]`, with
`precheck` flying the same legs with the coach on); the timing check is the
timing coach with `recipe.check_ride` (silent, E window, letters). A check
never talks except the brief, the pitchout and the card. `scripts/
mutate_checkride.sh` is the proof (20/20).

## 10d. Waypoint timing (`timing.py`, `timing_coach.py`) — the clock on the card

Every routed card (`bb_route`, or a `"route": "strike"` template) is timed
by `timing.plan()` from the same `routing.leg_card` rows the kneeboard and
the brief print, so the three cannot disagree. Anchored, not accumulated:
`takeoff` (ground block 8/3/1/0 min by start type), `push` (WP1 at
`timing_at`) or `tot` (TARGET at `timing_at`); with a push/TOT anchor the
builder MOVES `m.start_time` and records `stats["start_clock"]`, which
`brief._dtg` and `saydo.run(said_hhmm=)` read. The player's points carry the
ETAs unlocked; `timing_package` launches a late-activated two-ship on the
same points with ETAs LOCKED `PACKAGE_LEAD_S` ahead. `timing_coach` grades
wheels-up / WP1 / IP / TARGET by `TimeBefore`/`TimeAfter` around the ETA in a
zone — flag block **8860–8879** — and scores the anchor double.
`saydo.check_timing` refuses card-vs-file-vs-clock drift after every build.
`scripts/mutate_timing.sh` is the proof (35/35). The four F-4E rides are
`scripts/add_timing_track.py` (idempotent; edit there, not in the JSON).

**The three things that are counter-intuitive and cost a defect if you get
them wrong:**

1. **The marshal radial hangs off the FINAL BEARING, not the BRC.** Final
   bearing is the extension of the angled deck, ~9° to port. Deriving it from
   BRC is a nine-degree error that looks perfect in code and puts the student
   three and a half miles off the arc at 21 DME.
2. **PLATFORM is an ALTITUDE (5,000 ft), not a range.** Every community guide
   quotes a DME beside it. A range gate is the obvious implementation and it
   is wrong; the student hunting for a DME flies through the rate change.
3. **Range gates must be `UnitInMovingZone`, never a static zone.** The ship
   makes 25 knots — a static zone at 10 DME is four miles out of position ten
   minutes into the recovery.

**Which cues a ride fires is DECLARED (`cq_coach.RIDE_CUES`), never inferred
from sequence.** Ride 4 starts at three miles, already inside every range gate
on the profile; sequential phases would fire "ten miles", "dirty up" and "on
speed" in its first second.

**Grade only what DCS ignores.** Supercarrier already does Marshal, the
approach time, radar contact, ACLS lock, the ball call and Paddles. It does
NOT enforce the approach time, and AI cannot fly a Case III at all (it reverts
to Case I in the pattern) — so no stack is populated with AI. The triggers
grade the push time, the descent rate below platform, altitude at ten and
speed at six, and leave the last mile to Paddles.

**The timing grade needs a transit allowance.** "Commenced" is measured two
miles inside the fix, which takes about half a minute at holding speed. Without
`cq_coach.commence_transit_s` every pilot is graded LATE, including the one who
crossed the fix on the second.

**Requires DCS: Supercarrier, and says so on three surfaces** — the ride panel,
the track panel and the in-mission briefing. It is NOT covered by the Library's
ownership check, which only knows maps and aircraft.

Guards: `tests/test_case3.py` (46), `scripts/mutate_case3.sh` (33 caught, 0
weak).

**Harness discipline, one more rule.** Every `scripts/mutate_*.sh` calls
`baseline_green` before its first mutation. A harness run against a RED
baseline reports every mutation as "caught" and means nothing — it measures the
delta between green and broken, and with no green there is no delta. This cost
a full harness run: 36 caught, 0 weak, entirely noise, because a brief had been
edited into failing one of the guards the harness exercises.

**Google Analytics (v1.90.0).** `server/ga.py` injects the gtag block into
every HTML response, from `GA_MEASUREMENT_ID` in the environment — never from
the page source, because this app ships as a zip people re-host and a
hard-coded id would report their visitors into our property. The id is regex
validated (it is interpolated into a `<script>`), and injection is idempotent
(the sources page passes through two transforms). Client events go through
`ga(name, params)` in index.html, which no-ops when gtag is absent — it is
absent for every visitor with a content blocker, and an analytics tag must
never be able to break a button. The recipe is NOT sent to Google: the
server-side ledger already records it, and two systems recording the same fact
is how two numbers start disagreeing.

**The footer is load-bearing.** It used to say "No IP address, no account, no
name" about the whole page. It now scopes that to our own counting and states
plainly what Google receives, that the off-switch does not stop Google, and
that a Do Not Track browser is still counted by Google. `tests/test_ga.py`
holds it there — half that file guards prose, and those guards matter as much
as the technical ones.

## 10h. Corridors — NTTR and the Levant (`corridors.py`, `corridor_chart.py`, `data/corridors/<map>.json`) — v1.99.0 / v1.102.0

v1.102.0 generalised the NTTR work into **one data file per map**
(`data/corridors/nevada.json`, `data/corridors/syria.json`) read by
`corridors.py` (router) and `corridor_chart.py` (chart). `nttr.py` and
`nttr_chart.py` are shims onto them with `map_key="nevada"` — keep the old
names working, add nothing to them. The schema every map shares: `fixes`
(`kind`, `approx`, `cap_ft`/`floor_ft`, `minor`), `corridors` (`role`
departure/transit/recovery, `points`, `block_ft`, `width_nm`, `notes`,
`src`, `label_seg`/`label_off`), `gates`, **`clusters`** (a home's family
of fields with a `center` and `local_nm`; `join_from_outside` lets a
non-member field — Creech — join the nearest cluster's transits),
`sectors` (`rules` of `lat/lon` clauses parsed without eval, `default`,
`labels`), `plans[cluster][sector][low|high|any]` and `text` (every
map-specific phrase: chart/brief titles, the intro, `md_line`,
`gate_in_label`, the legend, `known_issues`). `chart` holds `bounds`,
`page` (the standalone page size), `sea` + `land` polygons, `areas`,
`lines` (coast/border/deconfliction), `roads`, `places` (`minor` = terminal
panels only), `hide_fixes`, `overview_landmarks`, `labels` (overview
overrides) and `panels` — each a terminal-area panel with `bounds`,
`lanes`, `declutter` (the overview hides the non-gate fixes inside it) and
`labels` (per-corridor `{seg, off, nudge, hide}`). `panel_cols` lays the
panels out as a grid (Syria: 2x2 at 1800x1040; Germany: 4x2 at 2400x1250);
the overview height follows the bounds' aspect. v1.103.0 added `eras` (a
data file that belongs to one era — Germany's Cold War — makes
`plan_route()` return None for the rest), `panels[].clusters` (one panel
serving several clusters), `lines[].label_at` (a line label only on the
panel that holds its anchor) and unlabelled sub-areas (an `""` label rides
on its neighbor). Germany is a two-sided front: seven NATO clusters plan to
five GDR sectors, three Warsaw Pact clusters plan to five FRG sectors, all
through six shared gates; every out-chain must end on its gate
(`scripts/gen_germany_corridors.py` trims the chain; the test
`test_every_out_chain_ends_on_its_gate_and_joins_up` proves it). Add a map by writing its JSON (Syria's is generated by
`scripts/gen_syria_corridors.py` — edit the script, not the JSON), adding
the key to `MAPS`, and a stem to `server.app.CORRIDOR_CHARTS`;
`scripts/build_corridor_charts.py` renders every map's chart into
`docs/img/`. Nevada below is still the worked example of how the router
thinks.


On the Nevada map the builder asks `nttr.plan_route()` before
`routing.route_for()`. The target's lat/lon picks a **sector** (north / far
west / west / east; inside 22 nm of Nellis is `local` = generic route), the
era's transit altitude picks the **road** (`high` at FL190+ takes the Alamo
Corridor; `low` the Sally Corridor), and `plans[sector][mode]` names the
outbound corridors, the entry gate, the exit gate and the recovery. The legs
are `departure > corridor points > WP1 (= the gate) > IP > TARGET > EXIT (=
the exit gate) > recovery points`, then `land_at(home)`. **The names WP1 / IP /
TARGET are kept** so timing, the coach, the DTC and say/do work unchanged; a
fix flown twice gets a numbered name (`MERCURY2`) because
`timing.apply_to_group` writes ETAs by name. Fix-level `cap_ft` / `floor_ft`
are published crossing restrictions and beat the corridor block. From a
non-Nellis field the departure corridors are dropped and the recovery is the
exit gate then home; with nothing left to join it is the generic route.
`nttr.draw()` puts every corridor on the F10 Common layer (hairline; the ones
flown as solid lanes) and the gates as rings (`~` = curated). The kneeboard
splits a long plan onto a FLIGHT PLAN page and a TIMING page.
`nttr_chart.py` (v1.101.0: a display list with SVG and 3x-supersampled PIL
backends; an overview panel and a Nellis terminal panel; role colors,
flown road red) draws the chart from the same data (`chart.areas` — two
legal polygons from 60 FR 20635, the rest curated `approx:true`; `roads`;
`places`; per-corridor `label_seg`/`label_off`): a kneeboard page and a brief
page on a corridor plan, `docs/img/nttr_corridors.png` for the site
(`scripts/build_nttr_chart.py`, registered artifact, `/api/nttr/chart.png`).
`Recipe.published_corridors=False` keeps the generic plan (nothing shipped
uses it; `Recipe.corridors` is the older Air Corridors threat-axis list — do
not confuse the two, v1.103.0 did).
`scripts/mutate_nttr.sh` is the proof (59/59 across three maps; `tests/test_nttr.py` + `tests/test_corridors_syria.py` + `tests/test_corridors_germany.py`). Sources: SOURCES.md §3.

## 10c. What the expert missions taught us (v1.91.0)

Read `docs/technique_dossier.html` before touching coaching, briefs or the
campaign engine. It is the teardown of Fulda 1979 M1–M6 (the only
trigger-readable expert work we have), Sedlo's Red Flag MP, Reflected's Red
Flag 81-2 and MIG Killers, Baltic Dragon's Raven One and Rampagers, plus a
scan of all 97 commercial missions (`scripts/scan_corpus.py`,
`docs/research/corpus_scan.json`). The rules that came out of it:

- **Provenance or nothing for cockpit facts.** `missiongen/cockpit.py` holds
  only parameter names and draw arguments a shipping mission or a first-hand
  source showed working, with the source written down. A guessed name makes a
  trigger that never fires and a brief that promises a check the file cannot
  make — the worst say/do gap there is. Unverified airframes get `None`, and
  the caller prints "not available" (`gates.brief_line`).
- **The readback gate** (`missiongen/gates.py`) is Fulda's set / not-set /
  advance triplet. Use `c_cockpit_param_in_range` with ±6 kHz, never
  equal-to (our ladder is on the 25 kHz raster; equal-to is reported to
  misbehave past one decimal). Flags 8976–8978. The cue that opens it sets
  `F_START`; the builder installs it AFTER `presets.apply` so the reminder can
  name the channel that really holds the agency.
- **Every rule stated gets enforced; every gate gets said.** Reflected writes
  the rule and hides the gate; Fulda builds the gate and never says. Do both.
- **The scorecard** (`cq_coach.SCORE`) is Rampagers' shutdown card: base 50,
  itemised, one line when clean. Triggers cannot sum, so it is itemised, not
  totalled — and the itemisation is the teaching.
- **The say/do check runs on us** (`missiongen/saydo.py`, last thing in
  `build()`). Card frequencies vs what the file holds; brief clock vs mission
  clock; voiced callsign vs DCS's fixed table. It found the VHF-only-jet bug on
  its first run. `tests/test_saydo.py` holds the library to zero findings —
  keep it there, and add a check whenever a new class of hand-copied number
  appears.
- **Known Issues in every brief** (`saydo.known_issues`). All four expert
  campaigns tell the pilot what the sim gets wrong. Ours is per mission.
- **The product shape is the folder.** `.cmp` + missions + Doc. See ROADMAP
  "Now".
- **The flight flies under a callsign DCS can say** (`missiongen/callsign.py`,
  v1.92.0). Never print a callsign the radio cannot speak; map it and keep
  the authentic one as the heritage line. And ALWAYS set `callsign_dict[1]`
  — pydcs writes only the name string, and the sim reads the index.

## 11. Known deferred work (as of v1.89.0)

Sampler pack endpoint + remote packs by URL + ed25519 pack signatures
(content architecture phase 4); a Sinai Cold War preset with Egypt as BLUE
beyond the Proud Phantom lineup; commissioned 70 TFS livery
(`scripts/dump_liveries.py --merge` unlocks nation-correct parked skins);
Tier 2 Lua grading (explicitly opt-in if ever); Rob still owes: revoking two burned GitHub PATs and
recording the 19 voiceover WAVs (6 brief pages + 13 cues, sheet at
`docs/WK_BNAI_VOICEOVER.md`, drop into `missiongen/data/wk_{coach,brief}/vo/`).

## 12. How to work with Rob

He is a strategist and a pilot, not a git user — commit for him, keep
explanations brief, and treat every squawk from the cockpit as a measured
fact about the product (he has been right every single time). When his words
are ambiguous, the cockpit reading usually wins over the code reading —
"green rings" meant DCS's helper gates, and it took three tries to hear it.
When a report repeats, stop patching and question the design: the wingman
took three rounds because the first two fixes treated a design limit as a
bug. State what a fix costs as plainly as what it buys. Credit belongs where
it's earned: Tricker's feedback is in the footer for exactly that reason.
