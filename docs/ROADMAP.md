# DCS Sortie Starter — Roadmap

*August 2026 · owner-only, in the app at `/admin/roadmap` · the past lives in
CHANGELOG.md — this page is only ever about what's next.*

**North star:** "Select, don't search." A DCS pilot gets a living,
period-accurate mission in under a minute — no editor, no Lua. We set the
stage, you write the play. **You are never given a flight plan you did not ask
for**: waypoints are placed only where a routed strike *is* the mission (the
strike templates), where a **curated training ride's printed syllabus IS the
flight plan** (the White Knights rides — the route is the lesson, so the
mission carries it), or where the pilot switched on **Automatic waypoints**
(v1.53.0, off by default). There is no waypoint editor and none is planned:
where a mission needs a plan, the mission brings it.

**The boundary on Training:** *Training teaches only what the mission can
MEASURE, and only what unlocks a sortie you could not otherwise fly. Everything
else is reference, not coaching.*

Why this clause exists, written down at v1.104.1 so the next feature argument
has something to lose against. The generator scales on axes you can enumerate —
maps, eras, aircraft, mission kinds. You can see the end of each one, and "this
map works" is a state the product can actually reach. **Training has no such
list.** Every subject in aviation is defensible as training, so the category
will absorb anything offered to it: another syllabus, another squadron's paper,
another era's doctrine, another history chapter. Each addition is individually
correct and the sum drifts. Nothing inside the category ever says stop, so the
boundary has to be stated from outside it.

It compounds the wrong way, too. The unbounded half of the product is also the
expensive half to verify: routes, charts, briefs and file format are provable at
a desk, while a coached cue is provable only in a cockpit, by Rob, one sortie at
a time. v1.104.0 shipped a green suite, 29/29 mutations and a card that never
drew. **So the category with no natural edge is the one that consumes the
scarcest resource the project has.** That is the actual failure mode this clause
guards against, not untidiness.

The two tests, in order:

1. **CAN THE MISSION MEASURE IT?** This is already the engineering ethic —
   `formation_hud` and `aar_hud` both refuse to draw a lateral cue because the
   only range check is a sphere, and a training aid that invents a cue is worse
   than one that admits a gap. As a *product* rule it does real work: if Mission
   Editor conditions cannot observe it without Lua, it is not a coached feature.
   No exceptions bought with cleverness.
2. **DOES IT UNLOCK A SORTIE?** Formation unlocks flying with a lead. AAR
   unlocks range. BFM unlocks the fight. Case III unlocks the boat. A history
   chapter unlocks nothing — it is good, and it is *content*.

**The release valve, which is the half that makes the rule survive.** Failing
the tests does not kill an idea, it routes it to the cheap channel: a kneeboard
page, a guide section, a brief paragraph, a chart. Reference is nearly free.
Coaching costs art, a flag block, a trigger set, a mutation harness and a sortie
of the only cockpit we have. Most scope creep is a good idea arriving through
the expensive door; this clause is a door, not a wall. A rule that only ever
says no gets quietly ignored, and then it is worth less than nothing because it
also cost the argument.

**And Training gets a definition of done.** A course is finished when its
syllabus is flyable end to end and its check ride grades — not when it stops
being extensible, because it never does. **The F-4E pipeline is done at
v1.104.1.** No second aircraft's pipeline starts until somebody finishes the
first one, and "finishes" means a real pilot completing it, not us shipping it.

## ✅ Where the product is today (v1.105.0)

Everything shipped is documented release-by-release in
[CHANGELOG.md](CHANGELOG.md). **v1.105.0** publishes the pack format — all four kinds and how to author each, at /api/packformat — and retires the What's new page. **v1.104.2** puts the whole product into American English — the app said *aeroplane*, *centreline* and *manoeuvre*, and a US aviation product should not. **v1.104.1** moves the position ladder to the one screen position ever confirmed rendering in a cockpit, adds an F10 that draws one on demand, and stops the text coach repeating what the card already says. **v1.104.0** rebuilds the formation coaching as a position ladder you glance at, gives the AI lead the patience to wait for you, and turns the check-ride debrief into cards. **v1.103.1** puts the timing rides on the corridors too and repairs the Air Corridors knob. **v1.103.0** brings the standard map detail to Cold War Germany — the Central Region corridors, both sides of the line. **v1.102.0** brings the Authentic standard map detail to the Syria map — the Levant corridors, four home clusters, one chart. **v1.101.0** makes the corridor chart two panels and vector. **v1.100.0** draws the NTTR corridor chart — kneeboard page, brief page, the site. **v1.99.1** fixes the Mission Editor refusing to save a timing-package mission. **v1.99.0** threads every routed Nevada flight plan through the Nellis corridors (Sally, Alamo, FYTTR, the recoveries). **v1.98.1** moves the Phantom history chapter into ground school (School 1). **v1.98.0** names the pipeline: *Learn it, fly it,
fight it.* **v1.97.0** puts every generated document —
brief, kneeboard, guides, kit, the documentation pages — on one page
furniture, Authentic Style v2.1 (`missiongen/authentic.py`).
**v1.96.0** ends every UPT phase in a check
ride graded the way an instructor grades — U/F/G/E per item, Q/Q-/U
overall, critical items — from Mission Editor triggers alone
(`checkride.py`), with a pre-check that flies the check profile first.
**v1.95.0** opens the fourth door: the
**Training Pipeline** — three schools in the order every air force runs them
(UPT, FRS, MQT), laid over the tracks and cards that already exist, with a
history chapter, a check ride, planned units shown with their reasons, a
browser-local record and a squadron kit. First course: the F-4E.
**v1.94.0** puts a clock on every flight plan —
groundspeed, leg, cumulative and ETA per point, anchored on takeoff, a push
time or a TOT the way a planner anchors it, with the mission clock solved
backwards to meet it — writes the ETAs into the file (advisory on you, LOCKED
on an optional package flying two minutes ahead), grades you against them
with a timing coach, and ships four F-4E rides from Fassberg that teach it.
The short version: four doors — **Fly Now**
(one-screen picker: tanking, BFM, gun-belt and SAM strikes, air starts),
**Library** (25 curated missions across eras, roles and crews), **Builder**
(a six-screen wizard, nothing collapsed), **Train** (the pipeline) — over an engine with 12 era-gated
theaters and four eras (Afghanistan and Iraq on the official map exports), real parking and
headings — **your jet now takes the tightest stand that fits it**, so the one
wide apron stays free for the tanker (v1.68.0) — doctrinal air defenses with a guns-only
tier, carrier strike groups, tanker/AWACS with a real comm ladder, a briefing
pack (SITUATION/MISSION/EXECUTION, theater chart, diverts and fuel card),
in-jet kneeboards with the live threat picture, byte-deterministic share links,
and our own privacy-preserving product analytics (missions' shapes, never users') alongside Google Analytics, with the footer stating plainly what each of the two collects.

**v1.80.0** ships the product THIN: no missions in the image or the download, packs produced and uploaded through the admin, and the last in-request syllabus build deleted rather than cached around.\n\n**v1.79.0** makes the PACK the product's unit of published content: a public, specified format with a manifest, an upload flow that derives one from a folder of missions and lets you correct it before it goes live, and the four built-in syllabi shipped as artifacts rather than rebuilt on every download.\n\n**v1.78.1** stops the whole-track download building eleven missions inside the request — it took the server down — by pre-building the deterministic zips into the image.

**v1.78.0** opens the coached B'NAI with a six-page spoken brief the pilot pages through himself, with his controls locked until the last page hands them back and arms the coaching — and says plainly that a mission can hold the pilot but cannot press active pause for him.

**v1.77.0** teaches the B'NAI instead of only testing it: thirteen cues on the squadron's own drawing, one per decision in the attack, that re-arm after egress so the whole geometry can be flown again from the IP without reloading — with a slot for a recorded WSO voice and a card that says plainly what a Mission Editor condition cannot see.

**v1.76.4** gives every White Knights ride the wingman its card always promised — REX 2 as a separate flight, offset by the briefed spacing — and loads each delivery ride with the ordnance its own planning sheet calls for, period-correct AIM-7E-2s and AIM-9Js included, with the STORES block on the kneeboard tested against the pylons in the file.

**v1.76.3** puts the squadron's own attack diagrams — all five, reproduced from the pages of Conventional Tactics rather than redrawn — on the kneeboard and in the printed guide.

**v1.76.2** adds the split attack's LOW/HIGH half — the guide describes two splits and the syllabus taught one — taking Proud Phantom to ten rides, with a new guard asserting every attack and every delivery sheet in the document has a ride.\n\n**v1.76.1** gives all twenty White Knights rides a real flight plan, puts the ride card on the kneeboard where a pilot can read it at three hundred feet, flies them under the squadron's own REX callsign, and states the period livery in full while admitting DCS ships no 70 TFS skin.\n\n**v1.76.0** ships **The White Knights** — twenty missions in two tracks, built from four documents issued to a new arrival at the 70th Tactical Fighter Squadron at Moody AFB in January and February 1980. Eleven rides of Squadron Checkout in Cold War Germany, nine of Proud Phantom from Cairo West, the base the squadron actually deployed to that June. Every number is transcribed from the squadron's own paper; where a number cannot be flown as written in a theatre, the card prints both and says which governs.\n\n**v1.75.4** fixes the one Rob spotted next: the refuelling track sat below the terrain. Mount Elbrus is 18,510 ft and stands on the free Caucasus map, while the KC-130 and KA-6D were briefed at 15,000 and you started 1,000 ft below that. Every track now clears its map's highest ground by 3,000 ft measured for the RECEIVER, a tanker that cannot reach the resulting altitude is withdrawn with the reason printed, and a test reads the altitude back out of the generated PDF to prove the guide briefs what the mission flies.\n\n**v1.75.3** fixes four things found by flying it: the KA-6D shipped with no buddy store and could not give fuel, the pre-contact air start put you abeam the tanker pointing the wrong way, the A-6 was too slow for a Tomcat, and the guide printed two speeds where only the flown one belongs.\n\n**v1.75.2** makes tanker era-availability a rule derived from service windows rather than a hand-applied judgement — so the KA-6D buddy tanker is available to the Navy in both eras, labelled rather than hidden — and puts every kneeboard card plus the indicator artwork into the printed guide.\n\n**v1.75.1** tunes both from the cockpit: tanker track speed is now clamped into the RECEIVER's own comfortable band (so a Hercules speeds up for a fast jet and a KC-135 slows down for a Hog, and a pairing that cannot work says so), and the indicator moved to the left edge at eye level, halved in size, with a four-second floor between redraws.\n\n**v1.75.0** makes the Academy **configurable**: pick an era, an aircraft and a tanker, and the eleven missions, their briefs and the printed syllabus guide are all generated for that combination — the F-4E and the F-14B(U) included, Cold War on the same free map. Coaching moved out of the top-right corner into a **position indicator** at the bottom of the screen, built from a native picture action rather than script: two honest axes (fore/aft, high/low) and no invented lateral cue.

**v1.74.0** ships the **Air-to-Air Refuelling Academy**: two graded lane tracks — boom (USAF, Viper/KC-135) and probe-and-drogue (Navy/Marine, Hornet/KC-130) — eleven rides each, grouped as one Library card, with a printed syllabus guide per lane and a one-click download of the whole track. Ten of the eleven rides coach and grade you **inside the mission**, from Mission Editor triggers alone: envelope, speed, dwell and excursions, with fading closure calls and self-requested hints on F10. It does not claim to grade the plug — DCS triggers cannot see a refuelling event or read fuel — and every card says so.

**Both sides are armed** (v1.44.0 AI, v1.48.0 player) — enemy fits are a
curated table, your fit is composed from DCS's own per-pylon legal-store lists
and driven by the mission type you pick. **Ramps carry heavies** (v1.47.0):
stands are judged by the real airframe footprint, so tankers and AWACS can
actually park. **1,823 tests ship inside the download**, and
`scripts/release.sh` regenerates every derived artifact — pages, screenshots,
the PDF guide — and the pre-deploy check **blocks** on any that is behind, so
nothing in the documentation can quietly fall out of step with the product
(v1.49.1; this page is one of the things it now enforces). **v1.69.0** adds a **War on Terror
era** for Iraq and Afghanistan — the war ED actually built the Iraq North
region for — where nothing contests you in the air and the threat is guns, and
a served **Sources page** (`/api/sources`) tracing every claim the product
makes. **v1.68.0** gives Iraq seven
historically sourced air corridors, from the Kharg Island tanker-war lane to
the 36th and 33rd parallels. **v1.57.0** moves the site itself onto
Flightline — paper default, night toggle, semantic color, self-hosted fonts.
**v1.56.0** adopts
the Flightline Technical design system for every generated document — one token
source, vendored OFL fonts, an identity rail instead of the classification
banner, computed WCAG AA contrast. **v1.55.0** exports
the kneeboard as PNGs (OpenKneeboard, print, Discord) and moves every document
to a military-publication register — DD-175-style forms, classification-style
banners, black on white. **v1.54.0** puts the
composed loadout on a STORES kneeboard page — the fit had existed since v1.48.0
and been readable only on the desktop. **v1.53.0** adds
**Automatic waypoints** — an opt-in flight plan (WP1, IP, target, home) on the
F10 map, in the jet's nav system, in the F-14B(U) cartridge and on a kneeboard
leg card. Off by default, so the no-waypoints behavior is still what you get
unless you ask. **v1.52.0** caps a
ramp at six statics per squadron, so a flight line reads as several units
sharing a field rather than one unit pasted twenty times. **v1.51.0** rebuilds
the formation-flying syllabus — five stages from route position to a full
ramp-to-ramp sortie, an AI lead that is its own airplane rather than a slot in
your flight, radio coaching when you drift out of position, and an era-scaled
choice of airframe with lead's cruise derived from what you actually fly.

## ▶ Now

*Re-planned in v1.91.0 from the Expert Mission Dossier (`docs/technique_dossier.html`):
four complete commercial campaigns, 97 missions and 137 documents, read file by
file. The findings that set this list: every commercial campaign ships as a
folder (`.cmp` + missions + Doc), Reflected carries clock/fuel/stores between
chained sortie files by hand, the platform's score-keyed branching is used once
in 97 missions, and every say/do gap in expert work was a hand-copied number.*

- **The Doc folder.** Printed briefing PDF, kneeboard PDF and an inflight
  guide per map (channelization, parking, TACAN/ATC, SID/STAR, divert/NORDO,
  airfield diagram) as generator outputs, derived from the recipe so they
  cannot drift. Three of the missing pages are data pydcs already holds.
- **Campaign export.** A `.cmp` with chained sorties (Departure → exercise →
  RTB as separate files, clock advanced and fuel/stores carried — what MIG
  Killers does 45 times by hand) and score-keyed alternates per stage (what
  Raven One does once). No Lua; the platform does it.
- **Cockpit-parameter verification.** The readback gate is built and off on
  the F-14 and Hornet until `list_cockpit_params()` output arrives for each;
  then `missiongen/cockpit.py` gains two lines and Casmo's channel-2 problem
  is caught by the mission. Same path for gear/hook/flap arguments.
- **A five-minute gate.** 913 test functions parametrised across templates,
  eras and rides is the right shape (every expert gap was a per-mission
  number), but every test builds a whole .miz and the gate takes 15 minutes.
  Two changes, no refactor: cache built missions per test session (most
  files rebuild the same ten templates), and run the files a change touches
  first so a rename fails in a minute, not fifteen.
- **Trigger-only techniques still to land:** random cue variants with a
  busy-line flag, the descent staircase for the approach coach, corridor
  rules with SAM-state consequences, voice-only package members, and a
  termination guarantee in every coach. *Landed in v1.94.0:* the locked-ETA
  package member and the push/TOT timeline (Reflected's HOLD technique).
- **Authentic Style, the rest of it.** Landed in v1.97.0 for every PDF and
  documentation page. Still to do: the in-mission cue cards (White Knights
  coach cards, the AAR HUD) which are images in the cockpit rather than
  documents, the site's own interactive states (the specimen's Default →
  Hover → Selected → Focus → Disabled), and the Okabe–Ito series for any
  chart the product draws.
- **The pipeline, next courses.** In order of leverage: (1) the two planned
  FRS units for the F-4E — an instrument recovery ride (TACAN penetration,
  ILS to minimums; trigger-only glideslope coach) and radar work with Jester
  (uncoached first); (2) a **UPT school on a free trainer** so the pipeline
  is universal — the TF-51D is in every install, the T-45C is a community
  mod and must be labelled as one; (3) F-16C and F/A-18C courses, which
  reuse the B-course BFM cards, the AAR lanes and Case III and need only a
  history chapter and a contact phase each; (4) a squadron-branded kit
  (their standards on the gradesheet). Progress stays browser-local; a
  roster is a squadron's own business.
- **Fuel on the card.** The timing plan is the frame for it: a per-airframe
  burn table (climb / cruise / combat) turns each ETA into a planned fuel
  state, so JOKER and BINGO become computed numbers on the same rows
  instead of blank boxes. Needs data per module before code.
- **Timing on the other routed cards.** The clock is generic (any
  `bb_route` mission gets it); the coach and the package are opt-in. Next:
  time the White Knights and Case III cards the same way, and let a track
  card set its anchor per map.

- **Flightline Phase 3 — the heritage layer.** The slanted F-4E figure banners
  (one on the landing hero, chart figure titles), the guide PDF cover in the
  kit's cover language, grayscale hatching for WEZ rings so the theater chart
  survives a monochrome printer. Lands after Rob reviews Phase 2 in the wild.


- **AI loadouts, phase 3** — air-to-air is done on both sides, and the player's
  jet now derives strike/CAS/SEAD fits from pydcs's pylon data. The remaining
  gap is the AI *packages*: Iron Hand strikers and escorted bombers still fly
  the air-to-air table, so they do not yet carry what the brief says they do.
  The derivation built for the player is the obvious tool for it.
- **Verified liveries** — everything is built and inert until
  `scripts/dump_liveries.py --merge` runs against a real DCS install: the
  nation-correct ramp skins and the VF-11 Red Rippers default on the F-14B/B(U).
  Blocked on one command, not on code.
- **Quick Flight completion** — Pattern Work and The Boat cards; "what I own"
  filtering in the picker; spice presets refined by the analytics data.
- **Callsign polish** — per-squadron options in a dropdown (Gypsy/Victory/
  Fast Eagle...), and DCS-native callsign enum mapping where one exists.
- **Library health** — featured re-curation around the first-night user; two
  free Su-25T templates so a zero-purchase install has real content; a seat
  selector in the mission drawer so the SP·MP chips describe a real choice.

## ◇ Next

- **Chained rides as a syllabus.** Tracks packaged the way MIG Killers is:
  events with a graduation, and a syllabus document like Reflected's Topgun
  Class 01-69 PDF.
- **Bet 1 needs eyes.** The say/do reader must read kneeboard images, not
  only text — Reflected's in-game brief is "refer to the PDF", and the corpus
  scan came back n/a on 60 of 97 missions for that reason.
- **The Lua decision (Rob's).** Spoken callsigns from the paint, live fuel
  state, a switch as push-to-talk — Rampagers' best tricks need scripts. The
  library stays trigger-only; revisit as an opt-in for the campaign engine.

- **Verified magnetic variation per theater.** The flight-plan card publishes
  TRUE headings and says so, because pydcs exposes no declination and its runway
  heading is only the designator. A per-map/era table needs a source checked
  against the sim; a bundled WMM/IGRF model would silently expire. Until one
  exists, labelling is the honest answer.


- **Training tab** — Tanker Join-Up, Range Day, Pattern Work, Sandbox as
  Library cards (the picker's reps, saved as curated missions).
- **Helicopter role** — Apache/Hind/Huey templates, then FARP spawning
  (`home` currently resolves airports only).
- **User guide refresh cadence** — the guide updates with every UI release.

## ◈ Later (demand-gated — the analytics tab decides)

- **"Bandit fit" control** — an era-typical / heavy toggle on the Threats
  screen, for people who want the harder fight. Deliberately gated: the
  default being right and briefed is worth more than another knob.

- **Mixed-type flights** (`flights: [...]`) — watching the
  `want_mixed_flight` counter.
- **Anti-ship strike** — reuses the carrier anchor axis; seven curated maps.
- **CSAR** — the genuinely new mission type on the list.
- **Moving convoys** — road-following targets for the armed-recon missions.

---

*Rule of the page: this roadmap is updated in the same commit as any release
that ships one of its items. If you're reading a stale roadmap, that's a bug —
file it.*
