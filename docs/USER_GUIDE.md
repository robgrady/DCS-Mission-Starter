# DCS Mission Starter — User Guide

**Select, don't search.** Pick a map, an era, and an aircraft; download a `.miz` where the
world is already alive — airfields dressed with period-correct aircraft and equipment,
working SAM sites, support flights on station, a carrier strike group with a properly
spotted deck — and build *your* mission on top in the DCS Mission Editor.

**We set the stage — you write the play.** The starter never places your waypoints.
Flight planning is yours.

---

## Quick start

1. Open the wizard, pick a **map** and an **era**. The era is a hard filter: a WWII
   starter will not offer you a Hornet, and a modern starter will not offer a Spitfire.
2. Pick your **side, home airfield, and aircraft** (the full DCS flyable roster,
   filtered to the period). Choose single-player or multiplayer client slots,
   start type, time, and weather.
3. Toggle **building blocks** (everything is optional — defaults are sensible).
4. Optionally pick a **template pack** (e.g. Backseat Ops for the F-4E).
5. **Generate** — the `.miz` downloads. Drop it in `Saved Games/DCS/Missions/`
   and fly it, or open it in the Mission Editor and keep building.
6. **Share** — "Copy share link" gives you a URL that regenerates this exact
   starter for anyone who clicks it. Paste it in your squadron Discord.

## The standard comm ladder

Every starter uses the same predefined comms, so learn it once:

| Agency        | Callsign | Freq (UHF) | TACAN | Notes |
|---------------|----------|------------|-------|-------|
| Guard         | —        | 243.00     | —     | monitored |
| Your flight   | (varies) | 305.00     | —     | flight common |
| Tactical      | —        | 254.00     | —     | inter-flight coordination |
| AWACS         | Overlord | 251.00     | —     | land-based E-3/A-50 |
| Tanker        | Texaco   | 253.00     | 39Y   | speeds/altitudes per type |
| Carrier       | Mother   | 264.00     | 71X   | ICLS 11 · Link4 336 · ACLS on |
| CAP           | (squadron) | 258.00   | —     | carrier air wing |
| AEW Hawkeye   | (squadron) | 259.00   | —     | carrier air wing |
| FARPs         | (name)   | 127.50+    | —     | 0.25 steps per pad |

The same ladder is printed on the in-jet **kneeboard** (comms card page) and in the
mission briefing. All carrier systems are pre-activated: TACAN 71X "STN", ICLS
channel 11, Link4 on 336, and ACLS — tune and go.

## Building blocks

- **Airfield dressing** — era/faction-correct static aircraft on real parking stands,
  ground support equipment, fuel farms, tents, comms towers. Density: sparse/normal/busy.
- **Air defenses** — complete, functional SAM sites with doctrinal layouts (SA-2/3/6/11,
  Hawk, Patriot by era/side) plus SHORAD at fields. WWII gets flak, not SAMs.
- **Tanker / AWACS** — on station behind friendly lines with the standard freqs above.
  Not available in WWII (no AAR or AWACS in 1944 — the era gate is strict).
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

Templates are the one exception to the no-waypoints rule (the AI pilot needs
steerpoints to fly).

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
