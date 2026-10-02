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

**v1.105.0** on Fly.io: four doors (Fly now · Library · Train · Builder),
eleven theaters, 78 airframes, the Authentic Style across every document,
the pack format published (`/api/packformat`, four kinds), the F-4E pipeline
through its check ride, published corridors on Nevada, Syria and Cold War
Germany. **v1.106.0 is in flight:** the comm plan is a table the pilot
overwrites, and every station, radio, card and kneeboard follows.

## The bets

Four themes carry the next two quarters. Everything in Now/Next hangs off one
of them; an item that hangs off none is a candidate for *Later* or for no.

1. **Truth.** The thing no commercial campaign has: a file that cannot
   disagree with its brief. Comm plan shipped. Remaining gaps are in the
   cockpit, where only a sortie can look.
2. **The pipeline, finished before it is widened.** One aircraft flown to
   graduation beats three shipped. Growth is by reuse (BFM cards, AAR lanes,
   Case III are airframe-agnostic), not by new syllabi.
3. **Dash-One.** The squadron platform is its own product (dash-one.app):
   the ladder, the pilot-owned record, attestation, Tacview evidence. Sortie
   Starter is its mission engine. The boundary: *generation, cards, packs
   stay here; records, squadrons, credit live there.* Progress in this app
   stays browser-local by design — a roster is Dash-One's business.
4. **The Doc folder and the campaign.** What every commercial campaign ships
   and we do not yet: a printed brief, a kneeboard PDF, an in-flight guide
   per map, and chained sorties with the clock and fuel carried — all derived
   from the recipe so they cannot drift.

## ▶ Now

- **Ship 1.106.0.** Comm plan table, preset channel names in the `.miz`, the
  timing-ride regression (51-minute rides) fixed. *Bet 1.*
- **Close the F-14B(U) front-seat question in the cockpit.** The file, the
  card and both radios agree; Heatblur's own missions program the jet the
  same way. Discriminator: fly the same mission in the plain F-14B. The ME
  now shows channel names, which is the second way to check. Rob's sortie,
  not code. *Bet 1.*
- **Source control.** The 1.104–1.106 tree is back in git; the push to
  GitHub is blocked on authorization. Until it lands, the Dropbox working
  folder is the backup. *Hygiene — nothing else is safe until this is.*
- **Rebuild the three lost generators** (`build_packformat_html`,
  `build_checkride_cards`, `build_formation_hud`): the outputs ship, the
  scripts died with the old build environment. Then re-register them in the
  artifacts freshness list so it can never happen silently again.
- **Mutation harness audit.** A `-k` filter that matches nothing is read as
  "caught" (pytest exit 5). Finish the audit of every runner before the
  next release leans on a green harness.

## ◇ Next

- **A squadron's ladder inside its pack.** The comm table is per mission and
  per browser; a `comms` block in a course pack makes it per squadron, so
  every mission in the pack is on the SOP without anyone typing. *Bet 3.*
- **The Dash-One handoff.** Course and reference packs are the unit Dash-One
  consumes; each flight ships its `.miz` plus artifact set; mission states
  (draft · practice · validation-candidate · validated) agreed on both sides.
  Design before code — the PRD is on the Dash-One side. *Bet 3.*
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
- **A five-minute gate.** Cache built missions per test session and run the
  touched files first; the suite is 4,100 tests and ten minutes. Every bet
  pays for itself faster when a rename fails in a minute.
- **Fuel on the card** — a per-airframe burn table turns each ETA into a
  planned fuel state; JOKER and BINGO become computed numbers. Data before
  code. **Timing on the other routed cards** (White Knights, Case III).
- **AI loadouts, phase 3** — Iron Hand strikers and escorted bombers still
  carry the air-to-air table. **Verified liveries** — blocked on one
  command against a real DCS install. **Verified magnetic variation** —
  until a per-theater table exists, TRUE and labelled is the honest answer.

## ◈ Later (demand-gated — the analytics tab decides)

- Helicopter role and FARP basing · Quick Flight completion (Pattern Work,
  The Boat) · callsign polish · library re-curation around the first-night
  user · "bandit fit" toggle · mixed-type flights · anti-ship strike · CSAR ·
  moving convoys · the heritage layer of Flightline.

## Decided — and not re-opening without a reason

- **No waypoint editor.** Where a mission needs a plan, the mission brings it.
- **No Lua in the library.** Trigger-only, so every mission is inspectable
  and portable. Revisit only as an opt-in for the campaign engine.
- **No accounts, nothing server-side about a pilot.** Progress is
  browser-local; squadrons and records are Dash-One.
- **Channels are fixed.** Frequencies are what SOPs differ on; the ladder's
  shape is what makes it learnable.
- **This page is the owner's.** The public reads the changelog.

---

*Rule of the page: this roadmap is updated in the same commit as any release
that ships one of its items, and the version line above is checked by the
release script. A stale roadmap is a bug — file it.*
