# DCS Sortie Starter — User Guide

**Select, don't search.** Get a living DCS mission with period-inspired settings in under a
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
— behind the tanker at its assigned block, or in your chosen BFM geometry.

**📚 Library** — find individual **Missions** or multi-mission **Collections**.
Search titles, aircraft/nicknames, maps, activities and collection mission names.
Expand **Filters & sort** for aircraft, map, era, activity, mission setup and
**Threat** (opposition intensity, not pilot skill). Three featured picks appear
when unfiltered; each appears only once. Collection cards show their mission
count and fixed requirements.

Use **My DCS content** to declare installed maps, aircraft and additional
modules such as Supercarrier. These preferences stay on this device.
**Compatible with my content** checks all requirements of a fixed collection;
unknown or incomplete requirements remain unconfirmed and are excluded. For
configurable missions, it looks for a matching aircraft, era and map and opens
that combination in the detail view. Changing those selections refreshes the
summary. Generate from the detail or **Customize in Builder**. Ownership is
your declaration, not an inspection of your DCS installation.

A collection download contains its authored missions and does not change with
Builder selections. The detail lists the flying sequence and separate Mission
and Briefing links. Historical dates, classifications and sources remain in
the setting disclosure. **Train** organizes the same rides into a learning
sequence and records progress in this browser.

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
path), the **briefing pack** (a PDF — SITUATION/MISSION/EXECUTION brief,
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
2. Pick **who's flying** (just you, or a 2-4 ship), your side, home airfield,
   and aircraft. Choose **Veteran AI wingmen** to replace some human seats
   with AI pilots in your flight.
3. Toggle **building blocks** (everything is optional — defaults are sensible).
4. **Generate** — your Mission Kit appears and the `.miz` downloads. Drop it in
   `Saved Games/DCS/Missions/` and fly, or open it in the Mission Editor.
5. **Share** — "Copy share link" regenerates this *exact* mission for anyone:
   the same recipe + seed reproduces the mission within the same generator release.

*Privacy note: we count what missions get generated (map, aircraft, mission
type) to decide what to build next — never who generated them.*

### Flying with veteran AI wingmen

In **Builder → Flight → Who's flying**, choose **4-ship** and set **Veteran AI
wingmen** to **3** for your aircraft plus three AI wingmen. This creates a
single-player mission: put the `.miz` in `Saved Games/DCS/Missions/` and fly.
The wingmen use DCS **High** skill, the level labelled veteran here, and belong
to your own flight. Use the wingman radio menu to command them.

For a two- or three-ship, you can likewise assign up to one or two AI wingmen.
If two or more aircraft remain human seats, they are multiplayer clients;
host the mission through **Multiplayer → New Server**. Leave the AI count at
**None — human seats** to keep the existing multiplayer setup. Reducing flight
size reduces the AI count as needed to retain at least one human aircraft.
Share links and saved Builder settings retain this choice.

All aircraft in the flight use the selected airframe and loadout. AI wingmen
follow native DCS behavior; this option does not script attack geometry or
formation procedures. Fixed crew-ops flights and authored Case III recovery
rides do not offer this option. Existing training rides retain their authored
wingmen when no custom AI count is selected.

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
- **Pattern traffic** — AI aircraft recovering into, or departing from, your own
  field at mission start (landing / takeoff / both; fighters, cargo, helicopters
  or mixed; up to 8 aircraft). *Formation departures* — departing aircraft
  lining up on the runway and rolling as two-ship sections, using DCS 2.9.30's
  AI runway line-up — appears here once the feature's encoding has been
  verified against a Mission-Editor-saved file; until then the option is
  not offered rather than offered and ignored.
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

- **Crew Ops: Jester IZLID Strike (F-14B(U), pilot seat)** — you fly;
  Jester operates the back seat. Run designation from the F10 CREW menu:
  start the IZLID, confirm its effect, then cease. Progress is player-paced.
- **Crew Ops: Iceman GCI Intercept (F-14B(U), RIO seat)** — command the AI
  pilot from the F10 CREW menu while running the intercept from the pit.
- **RIO Fleet Defense (F-14A/B)** — use the cockpit Iceman menu in solo play,
  or fly with a human crewmate. It does not use the B(U) mission-command API.

The F-4E training rides are a separate course; these F-14 crew-command
features do not apply to the Phantom.

Templates are one of the three places waypoints appear (the AI pilot needs
steerpoints to fly). The second is a **curated training ride** — the White
Knights rides carry the squadron's own route automatically, since flying that
exact ground track is the lesson. The third is **Automatic waypoints**, the
tickbox on the Targets screen — off unless you turn it on, and it builds
WP1 → IP → TARGET → home with a kneeboard leg card to fly it off.

## Share links & recipes

A starter is defined by its **recipe** (your wizard selections + a seed). Share
links encode the recipe, not the file. Within one generator release, the same
recipe and seed reproduce the same mission. Later releases may correct content
or update DCS compatibility while retaining the recipe; keep the downloaded
`.miz` when you need an exact archived mission. Change the seed to reroll the details while
keeping your selections.

## Missions through an AI assistant (MCP)

An MCP-compatible assistant can connect to
**https://dcs-mission-starter.fly.dev/mcp/** using **Streamable HTTP**. Add this
URL as a remote MCP server in your assistant's settings; configuration names
vary by client. Sortie Starter's public tools do not require a login. The
public agent guide is available at **/api/mcp-guide**, indexed by **/llms.txt**,
and as the MCP resource **sortiestarter://integration-guide**.

Ask the assistant to search the catalog, inspect a mission's requirements,
validate your selections, and generate a mission. For example: “Build a modern
Caucasus F-16 four-ship with three veteran AI wingmen and a kneeboard.” You
still need to own the relevant DCS map and aircraft modules.

Generation returns a mission manifest plus links to the **mission .miz** and
**full mission kit ZIP**. Download and unzip the kit, then put `mission.miz` in
`Saved Games/DCS/Missions/`. Use single-player for one human aircraft and
multiplayer for two or more human seats. Available briefs, kneeboard PNGs,
DTC setup card, `comms.json`, and `navigation.json` accompany the mission.
DTC files are supplied only when the selected aircraft supports them and
rendering succeeds. Check the manifest's file list and warnings.

Links regenerate the recipe on the stated app version and check its native
mission checksum. If mission content changes, ask for fresh links. After a deployment,
a link from an older version returns “another app version”; ask the assistant
to generate fresh links. Keep downloaded files for an exact archive. A busy
generator asks you to retry after three seconds. Recipe validation checks
fields and template defaults; generation makes the final compatibility checks.

The assistant's recipe schema includes numeric limits and the human-seat rule:
**1–4 aircraft**, with **0–3 veteran AI wingmen** and always at least one human
aircraft. Other bounds include parking fill (0–100%), pattern traffic (1–8),
threat intensity (1–5) and timing hold (0–15 minutes). Fixed crew-ops and Case III
rides still refuse custom veteran wingmen. Validate the selected recipe before
generation; these limits do not replace the final compatibility checks.

Published packs remain authored downloads: the assistant retrieves their
pack link rather than rebuilding a `pack_` template. Missions are not saved
in an account or installed in another application. DKS import compatibility
still needs testing with DKS; this connection does not place files in its ATO.

## FAQ

**The mission won't load / units are missing.** Make sure you own the map, and for
carrier decks with CVN-71/72/73/75 you need the Supercarrier module (the Stennis
deck works in the base game; the Forrestal comes with the F-14).

**Can I edit the starter?** Yes — that's the point. Open it in the Mission Editor;
everything is ordinary groups and statics you can move, delete, or build on.

**Why can't I pick aircraft X in era Y?** Hard era gate by service window — e.g.
the Hornet entered service in 1987, so it can't appear in a Cold War (1965–1985)
starter. This is a broad era filter, not certification that every module variant served on the authored scenario date.

**What is the "War on Terror" era for?** Iraq and Afghanistan missions with a
**2003–2025 aircraft service-window filter**. This broad preset is not a claim
that a particular conflict or deployment lasted through 2025; named scenarios
retain their authored dates. Its defining setting is the opposition: there is
no enemy air force and no radar SAM; the threat is guns and MANPADS, which is
why the transit profile sits higher than Modern's. If you want MiGs over Iraq,
pick Modern instead.


## Parking, skins and historical fidelity

Parked aircraft use measured stand directions where survey data exists. Iraq
now has surveyed directions at all 20 airfields; other surveyed maps use their
own measurements. Unsurveyed stands use a geometric estimate. The Channel and
Falklands still need direction surveys. Stand size and direction are separate:
a parking stand can have exact size information without a measured direction.

Static skins are selected by aircraft model, nation and era only when the
livery name has been verified. Cold War USA F-4 statics use verified USAF skins
where available. Other combinations use DCS stock skins; this does not promise
an era-specific skin for every aircraft. The wider curated livery collection
remains unavailable until its folder names are verified against a DCS install.

Library briefs identify DCS substitutions and what a training mission can
measure. For example, the refueling grade measures position and stability;
it cannot confirm a fuel transfer. Follow each ride's printed standards and
known issues. Historical overlays distinguish sourced boundaries from
approximate or illustrative geometry; map-era presets are broad settings,
not exact historical reconstructions of every aircraft and installation.

### Scenario dates and historical context

Library mission details show an authored **scenario date** and identify the
setting as a **historically inspired adaptation** or **fictional exercise**.
Expand **Setting, sources & adaptations** before generating. The same context
appears in the mission description, Markdown/PDF brief and an additional
kneeboard page. Published packs use the context supplied with their stored
revision; older or externally authored packs may have no historical metadata.

Named settings have their own dates: Proud Phantom uses **10 July 1980**, the
fighter arrival date (advance parties arrived earlier); the White Knights
checkout uses a 1980 reference day. Sinai's October War setting uses **6 October
1973**, Falklands **21 May 1982**, the expanded Kola NATO exercise **21 June
2024**, and Afghanistan OEF **21 June 2011**, before the base handovers. These
are training anchors, not reconstructions of the individual day's sorties.

Known weapon service windows are checked against the actual mission year for
player, adversary and carrier strike fits. Unknown service dates remain
uncertified; station compatibility does not establish national/operator
availability. The aircraft picker still filters by the broader era, so later
module variants can remain as disclosed training substitutions.

Historical overlays are references, not automatic routing or violation grading:

- **Berlin:** approximate corridor terminals; the 10,000-ft limit is an exercise
  rule. Historical altitude and escort permissions were more complex.
- **Nevada:** the 14-vertex R-4808N polygon uses the **1995 FAA boundary**, also
  retained on earlier-era training missions. Its trigger zone is a bounding
  circle, not the legal polygon.
- **Syria:** the Euphrates sketch references a **7 February 2018** coalition
  report. Four approximate points do not establish a precise operational line
  or its continuous validity; the 2015 flight-safety MOU did not create it.
- **Afghanistan:** the Kabul circle and Helmand rectangle are illustrative.
  Operational dates, vertical limits and controlling agencies are unknown.

The Normandy and Marianas WWII presets use broad campaign basing substitutions:
Carpiquet and Tinian were not Allied operational bases on the default June
1944 date. Falklands Mount Pleasant is a postwar substitution. Display
nationality is distinct from territorial host, visiting operator and game
coalition; it does not certify an aircraft roster.

## Release identity and the manual

The version beside the title identifies the running release. Reload the page
after a deployment to load its latest controls and version. The downloadable
User guide uses this same version on its cover. Every release reviews this
manual and updates its instructions when behavior, controls or limitations
change. The PDF is generated from this document so both copies stay aligned.
