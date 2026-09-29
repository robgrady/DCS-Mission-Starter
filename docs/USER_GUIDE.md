# DCS Sortie Starter — User Guide

**Select, don't search.** Get a living, period-accurate DCS mission in under a
minute — no editor, no Lua. We set the stage, you write the play: you are never
handed a flight plan you did not ask for — and there is no waypoint editor,
because none is needed. Waypoints appear only where the mission itself calls
for them: a routed strike (the strike templates), a curated training ride
whose printed syllabus IS the flight plan (the White Knights rides carry the
squadron's own route, because the route is the lesson), or the **Automatic
waypoints** tickbox you switch on yourself.

## The four doors

**⚡ Fly Now** — the fastest path. One screen, three picks: *what do you want to
practice* (Tanker Time, BFM Merge, Kill the Guns, Beat the SAM), *in what*, and
*where*. Era, base, weather and comms are derived for you; a single "spice"
notch sets the opposition (calm / realistic / hostile) and the 🎲 re-rolls a
fresh layout of the same picks. Tanker Time and BFM Merge start you **airborne**
— at FL200 behind the tanker, or two miles abeam your adversary.

**📚 Library** — curated, ready-to-fly missions: air-to-air, strike, SEAD, CAS,
carrier and crew ops, historic scenarios, and the routed Cold War gun-belt
strike pack. Filter by era, aircraft, map, and what you own.

**🎓 Train** — the Training Pipeline. *Learn it, fly it, fight it.* Three schools in the order every air
force runs them: *Ground School and UPT* (the history chapter, then fly an airplane —
formation, timing, the tanker, in any jet), *FRS — Know Your Jet* (the
contact phase, systems, the squadron's tactical checkout, weapons, and a check
ride), *MQT — Fight the Jet* (employment). Every ride is a generated Library
mission with its brief and kneeboard; where the Mission Editor can see what
you are doing it grades you and opens a scorecard, and where it cannot the
card says so. Units that are not built yet are shown as **planned**, with the
reason. Tick units done as you fly them to the standard on their brief — the
record lives in your browser and nowhere else. A virtual squadron takes the
**squadron kit** (printed program, a gradesheet with one row per ride, the
readings) and downloads the missions from each track. The first course is the
F-4E Phantom II.

**🛠 Builder** — the full wizard. Theater, era, coalition, aircraft, airfield
dressing, the Threat Dial (including the guns-only tier: AAA belts, zero SAMs),
support, corridors, map graphics — everything, in seven screens.

## Your mission kit

Every generate ends with the **Mission Kit**: the `.miz` (with its install
path), the **briefing pack** (a 3-page PDF — SITUATION/MISSION/EXECUTION brief,
theater chart with the numbered threat order of battle, comms/nav card with
diverts and fuel boxes — plus Markdown for Discord), the **kneeboard** riding
in-jet (RShift+K: comms card, airfield data, theater overview with the live
threat rings), the loaded **flight plan** on routed strike missions, and the
**DTC setup card** for the F-14B(U). On the **Nevada map the flight plan is
threaded through the Nellis corridors** — the FLEX turnout, the Sally Corridor
or the Alamo Corridor to the north ranges, FYTTR and Indian Springs to the
south range, the west road round the Box, and a published recovery home — with
the corridors and gates drawn on the F10 map and briefed with their sources.
On the **Syria map** the same standard applies — the Levant corridors: from
the Galilee fields up the coast and over the Bekaa, or J14 to Rosh Pina and
over Hermon; from Akrotiri the SIDs to IREFA and the sea road to NIKAS; from
Incirlik the W74 Northern Watch road and the Hatay and Kilis gates; from
Muwaffaq Salti the Amman TMA and L200 to Al-Tanf — with a Levant chart in the
kneeboard and the brief. On **Cold War Germany** (Cold War era only) it is the
Central Region of 1985, either side of the line: from the Eifel, the Hunsrück,
the Pfalz and Rhein-Main over the Taunus to the Low Level Transit Routes
through the HAWK belt — the Fulda Gap at Point Alpha, the Werra at
Herleshausen, the Harz road to Helmstedt, the Hof corridor; from the Rhineland
and the Weser the A2 to Helmstedt and the Heath to the Elbe crossings; and,
flying red, from the Berlin ring, Merseburg or Parchim along the GDR's own
flight lines to the same six gates. The ADIZ, the HAWK and Nike belts, the
Berlin corridors, the LFAs and the ranges are on the chart.

### Formation: the position ladder

The formation stages put a small card on the LEFT of your screen at eye level —
the same side lead is on, clear of the comms menu and the message log — that
names the one input to make: **HOLD**, **ADD POWER**,
**EASE OFF**, **COME UP**, **COME DOWN**, **OPEN OUT**, **REJOIN**, and
**STEADY**, which means "you are out of position but already closing at the
right rate, so add nothing". Read it with the edge of your vision; you should
never have to leave lead to use it. A ladder at the top shows your range —
CLOSE, SLOT, OUT, LOST. It cannot show left/right (the mission measures range
from lead, not which side you are on), so lateral comes from the sight picture.
Turn it off any time with F10 → *FORMATION: turn the position ladder OFF*.

**Can't see it?** F10 → *FORMATION: show the position ladder now* draws one
immediately. Do that on the ramp before you take off: if a card appears, the
ladder is working and will follow you all sortie; if nothing appears, the
picture is not rendering on your machine and the sortie is not the place to
find that out. While the ladder is fitted, lead stops nagging you in the corner
— the card says it, so the text does not repeat it.

Lead also waits for you: at the first two route points he orbits until you have
been in the slot for fifteen seconds, then flies the profile. He gives up after
a few minutes and goes anyway. Neither happens on a check ride.

## Quick start (Builder path)

1. Pick a **map** and an **era**. The era is a hard filter: a WWII starter will
   not offer you a Hornet, and a modern starter will not offer a Spitfire.
2. Pick **who's flying** (just you, or a 2-4 ship of client seats for
   multiplayer), your side, home airfield, and aircraft.
3. Toggle **building blocks** (everything is optional — defaults are sensible).
4. **Generate** — your Mission Kit appears and the `.miz` downloads. Drop it in
   `Saved Games/DCS/Missions/` and fly, or open it in the Mission Editor.
5. **Share** — "Copy share link" regenerates this *exact* mission for anyone:
   same recipe + seed = the identical file, byte for byte.

*Privacy note: we count what missions get generated (map, aircraft, mission
type) to decide what to build next — never who generated them.*

## The standard comm ladder

Every starter uses the same predefined comms, so learn it once:

| Ch   | Agency        | Callsign   | Freq (UHF) | TACAN | Notes |
|------|---------------|------------|------------|-------|-------|
| 1    | Your flight   | (varies)   | 305.725    | —     | flight common — DCS loads it on CH 1 |
| 2    | Carrier       | Mother     | 264.425    | 71X   | ICLS 11 · Link4 336 · ACLS on |
| 3    | AWACS         | Overlord   | 251.475    | —     | land-based E-3/A-50 |
| 4    | Tanker        | Texaco     | 253.625    | 39Y   | speeds/altitudes per type |
| 5    | Plane guard   | Angel      | 262.050    | —     | carrier flight ops |
| 6    | CAP           | (squadron) | 258.175    | —     | carrier air wing |
| 7    | Tactical      | —          | 254.325    | —     | inter-flight coordination |
| 8    | AEW Hawkeye   | (squadron) | 259.925    | —     | carrier air wing (CH 3 when there is no AWACS) |
| last | Guard         | —          | 243.000    | —     | monitored — fixed by regulation |
| —    | FARPs         | (name)     | 127.525+   | —     | 0.25 steps per pad |

The same ladder is printed on the in-jet **kneeboard** (comms card page) and in the
mission briefing, and it is loaded into every UHF preset radio the jet has
(both sets in an F-14 or a Hornet). All carrier systems are pre-activated:
TACAN 71X "STN", ICLS channel 11, Link4 on 336, and ACLS — tune and go.

### Your own comm plan

Squadrons have their own SOP. In the Builder, **Support & presentation →
Comm plan** shows the ladder as a table: a *Default* column and a *This
mission* column. Leave it alone and nothing changes. Overwrite a cell and
everything that prints or programs that frequency follows — the tanker's own
radio, the AWACS, the boat, the cockpit presets, the card, the kneeboard and
the F-14B(U) DTC page — and the card marks the row *custom*.

What the table refuses, and why: **Guard** is 243.000 by regulation and cannot
be moved; a frequency **off the 25 kHz raster** (253.630) is refused with the
nearest channel named, because no radio can tune it; a frequency **outside
UHF 225–400** is refused unless the aircraft's own radios reach it (a
Mustang's VHF flight frequency is fine for a Mustang). Two rows on one
frequency are allowed with a warning — co-channel is legal, sometimes
intended, often a slip. **Channels are fixed**: that is what makes the plan
learnable across every starter.

*Profiles* save a set of overrides in this browser under a name ("Squadron
SOP") and fill the table on demand. The overrides ride in the recipe, so a
**share link** reproduces the mission with the custom plan — the wingman does
not need the profile. *Copy JSON* gives the overrides as a `comms` block for
the API (`{"comms": {"tanker": 271.5}}`).

## Building blocks

- **Airfield dressing** — era/faction-correct static aircraft on real parking stands,
  ground support equipment, fuel farms, tents, comms towers. Density: sparse/normal/busy.
- **Air defenses** — complete, functional SAM sites with doctrinal layouts (SA-2/3/6/11,
  Hawk, Patriot by era/side) plus SHORAD at fields. WWII gets flak, not SAMs, and
  the **War on Terror** era gets no SAMs at all — the threat there is truck-mounted
  and emplaced guns, dense and low, and the Threat Dial scales the gun line.
- **Enemy air** — CAP flights and the BFM adversary spawn with an era- and
  role-correct weapons fit: a 1978 MiG-21 carries R-13Ms and R-60s, a modern
  MiG-29S carries R-27ERs, R-77s and R-73s. You never pick the enemy's loadout —
  era and mission type imply it — but you are always told what it is. Look for
  the **ENEMY AIR** block on the theater chart and on the in-jet kneeboard: it
  names the fit and what it means for how you fight him. At Threat Dial
  intensity 1–2 the bandits carry a lighter fit, so the dial changes the
  character of the fight and not only the head count.
- **Tanker / AWACS** — on station behind friendly lines with the standard freqs above.
  Not available in WWII (no AAR or AWACS in 1944 — the era gate is strict). In the
  **War on Terror** era there is no red AWACS, because there is no red air force.
- **Carrier strike group** — see below.
- **Ambient air traffic** — AI transports starting up and flying between friendly fields.
- **Functional FARPs** — pads with the fuel/ammo/command/comms vehicles required for
  rearm/refuel to actually work.
- **Strike targets** — depot / convoy / C2 packages in the enemy rear, each with a
  trigger zone ready for your own mission logic.
- **Practice range** — bombing ring and strafe line in the friendly rear.
- **Nav kneeboard** — comms card, airfield data (runways, stands), and a theater
  overview schematic, rendered into the jet's kneeboard.

## The carrier strike group

Pick a hull and you get its **real strike group**: the Roosevelt sails as CSG-9 with
USS Lake Erie (CG-70) and DESRON 23 destroyers; the Truman as CSG-8 with USS
Gettysburg; the Forrestal as a 1980s Med battle group with USS Ticonderoga. Screen
stations follow doctrine: plane-guard destroyer astern, AAW cruiser on the beam,
pickets on the bow quarters. The group steams into wind on BRC.

**Deck configuration** follows real spotting practice:

- **Recovery** — the landing area is clear (angle, waist cats, EL4, port stern);
  the bow is packed in tight uniform herringbone rows across the cat tracks,
  E-2s nose-out on the point, helos in the corral.
- **Launch** — cats, JBDs, and taxi flow clear; spares spotted aft.
- **Packed** — port-visit deck, everything fouled including the angle. No-fly.

Check the aircraft types you want on deck; rows are spotted one squadron per row.
Deck equipment (tugs, MJ-1 loaders, crash gear) sits at real stations. Optionally
launch the air wing's **CAP** (2-ship on the threat axis at 25k, e.g. VFA-146
Blue Diamonds) and **E-2 Hawkeye** AEW orbit covering the force.

## Template packs

- **Backseat Ops: IZLID Designation (F-4E)** — you fly the back seat; Iceman flies
  the jet and Jester lases a convoy with the IZLID on a scripted timeline.
- **Backseat Ops: GCI Intercept (F-4E, experimental)** — Iceman holds CAP, GCI
  commits you onto inbound Backfires; you run the intercept from the pit.

Templates are one of the three places waypoints appear (the AI pilot needs
steerpoints to fly). The second is a **curated training ride** — the White
Knights rides carry the squadron's own route automatically, since flying that
exact ground track is the lesson. The third is **Automatic waypoints**, the
tickbox on the Targets screen — off unless you turn it on, and it builds
WP1 → IP → TARGET → home with a kneeboard leg card to fly it off.

## Share links & recipes

A starter is defined by its **recipe** (your wizard selections + a seed). Share
links encode the recipe, not the file — the same link always regenerates the same
mission, even after DCS updates. Change the seed to reroll the details while
keeping your selections.

## FAQ

**The mission won't load / units are missing.** Make sure you own the map, and for
carrier decks with CVN-71/72/73/75 you need the Supercarrier module (the Stennis
deck works in the base game; the Forrestal comes with the F-14).

**Can I edit the starter?** Yes — that's the point. Open it in the Mission Editor;
everything is ordinary groups and statics you can move, delete, or build on.

**Why can't I pick aircraft X in era Y?** Hard era gate by service window — e.g.
the Hornet entered service in 1987, so it can't appear in a Cold War (1965–1985)
starter. This keeps every starter period-authentic.

**What is the "War on Terror" era for?** Iraq and Afghanistan, 2003–2020. It offers
the same aircraft as Modern — the difference is not what you fly, it's what flies
back. Nothing does. There is no enemy air force and no radar SAM; the threat is
guns and MANPADS, which is why the transit profile sits higher than Modern's. If
you want MiGs over Iraq, pick Modern instead.
