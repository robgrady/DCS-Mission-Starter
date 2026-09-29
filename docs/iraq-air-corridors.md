# Iraq air corridors — what the history supports

*Military aviation history review, 14 August 2026. Source-based; every corridor
below is traced to a citable account, and where the sources disagree I say so
rather than picking the tidier version.*

---

## The question

The Iraq map shipped in v1.67.0 with **no air corridors at all**, which meant
the Builder's corridor section was empty on the map with arguably the richest
air history on the shelf. This is the review that fixes that.

A corridor in this product is deliberately thin: a compass **bearing** from the
friendly base centroid and a **reach** in metres. Selecting one swings the
mission's threat axis, concentrates enemy CAP down the lane, and writes two
lines into the brief. It places **no player waypoints** — that rule doesn't
bend for history.

So the bar for including a corridor is not "did something happen there." It is:

1. **Documented.** A named operation or a published account, not folklore.
2. **On the map.** The DCS Iraq theatre runs roughly 29.2°N–37.0°N,
   39.0°E–50.5°E — H-3 in the west, Bashur in the north, Kharg Island in the
   south-east. Half of Iraq's air history happened off this box.
3. **A different mission from the ones already on the list.** Two lanes 15°
   apart are one lane and a duplicate in the picker.

---

## What shipped — seven corridors

### Iran–Iraq War, 1980–88 (`coldwar` — you fly the Iraqi Air Force)

| Corridor | Bearing / reach | Why |
|---|---|---|
| **Kharg Island Strike Lane** | 125° × 875 km | The tanker war |
| **Jafati Valley** | 64° × 320 km | Anfal, Halabja, Val-Fajr 10 |
| **H-3 Raid Track** | 350° × 250 km | 4 April 1981 |

**Kharg Island Strike Lane.** From February 1984 and heavily from 14 August
1985, the Iraqi Air Force ran repeated strikes at the Kharg terminal — by
mid-November 1985 CSIS counts at least 37 separate attacks on the island, and
around 60 major strikes by the end of that December. The profile is the
interesting part for us: aircraft flew "at extremely low altitudes and suddenly
popped up," and could tank over Iraq before crossing. The defense was **MIM-23
HAWK on the island** (CSIS notes batteries were reportedly inoperable in some
periods), **ZSU-23-4 and AAA**, and **F-14A / F-4E** area defense. The lane's
875 km reach lands within 1.4 km of Kharg's own airfield, so this is the full
historical run, not a gesture at it.

*Caveat we are not hiding:* the Iraqi fields that actually flew this — Shaibah,
Tallil, Qalat Salih — are not on the DCS map. Sources put Nasiriyah "about 300
miles from Kharg Island." From our western coldwar basing it is a longer sortie
than the real one was. The **axis** is history; the **range** is a consequence
of which airfields ED modelled.

**Jafati Valley.** The best-fitting scenario space on the whole map, and it
serves both eras. Human Rights Watch's *Genocide in Iraq* documents the First
Anfal (23 Feb – 19 Mar 1988) over the Jafati valley — Sergalou, Bergalou,
Yakhsamar, Haladin — "just a few miles east of the vital Dukan Dam," with "as
many as fifteen or twenty aircraft joining in the attacks," Sukhoi
fighter-bombers plus Pilatus PC-7/PC-9. Halabja fell to Iran in Operation Zafar
7 (part of Val-Fajr 10) and was struck on 16 March 1988 by "Iraqi MiG and
Mirage aircraft" in sorties of seven or eight. Kirkuk → Halabja is 152 km on
102°; Kirkuk → Sulaymaniyah 88 km on 083°. **HRW does not name the launching
airbases** — Kirkuk and K1 are the obvious candidates on geography alone, and
that inference is mine, not the source's.

**H-3 Raid Track.** The single best-documented deep ingress of the war, and
here you are on the receiving end of it. On 4 April 1981 eight Iranian F-4s
with F-14A cover flew Hamadan → Lake Urmia (395 km on 315°) → west along the
Iraqi–Turkish border mountains → south down western Iraq to the H-3 complex,
**below 300 ft throughout, including all four in-flight refuellings**, with
three F-5Es from Tabriz flying a diversion toward Kirkuk. Our lane points north
at the Jazira border ridges — the last leg, the part that is on our map.

*Sources disagree* on the total distance (Wikipedia ~3,500 km, Atlantic Council
~3,000 km) and on whether the tankers staged from Palmyra in Syria (Wikipedia
says yes; the Atlantic Council account has both refuellings over Lake Urmia and
the border). Syrian complicity is plausible — Damascus was aligned with Tehran
— but it is the weaker claim.

### Coalition operations, 1991–2011 (`modern`)

| Corridor | Bearing / reach | Why |
|---|---|---|
| **Northern Watch (36th Parallel)** | 348° × 250 km | 1997–2003 |
| **Southern Watch (33rd Parallel)** | 134° × 258 km | 1992–2003 |
| **Karbala Gap** | 172° × 167 km | April 2003 |
| **Western Scud Box** | 252° × 345 km | 1991 |

**Northern Watch.** 1 January 1997 to a final combat air patrol on 17 March
2003, stood down 1 May. North of the 36th parallel, ~45 aircraft from Incirlik,
**36,000 sorties** — the longest combat operation in EUCOM's history. RAF
Jaguar GR3, USAF F-15E and F-16CJ, USN/USMC EA-6B. **SA-3** sites are named;
"the most common threat was from anti-aircraft guns" — ZSU-23-4, S-60 57 mm,
100 mm. The predecessor, Provide Comfort, ran 5 April 1991 – 31 December 1996
over the same line.

The line itself is the interesting bit on our map: **36°N passes just north of
Erbil (36.24°N) and just south of Bashur (36.61°N)**, so Bashur is inside the
no-fly zone, Erbil is marginally inside, and Qayyarah West and Sulaymaniyah are
outside it. That is a real mission-design seam, not a decoration.

**Southern Watch.** Announced 26 August 1992, flying from the 27th. Originally
everything south of the **32nd parallel**; pushed north to the **33rd** after
Operation Desert Strike (3–4 September 1996). GlobalSecurity says "September
1996," Wikipedia says "1996 … following Desert Strike in August 1996" — the
operation itself was 3–4 September, so treat that as the date and the sources
as loose. Threat: **SA-6** and AAA engagements documented, plus a MiG-25
intercept incident in December 1992. On our map **33°N runs just south of
Baghdad and BIAP (33.26°N)** — under the post-1996 rules the patrolled airspace
came right up to the edge of the capital.

**Karbala Gap.** 2–4 April 2003. A 20–25 mile (32–40 km) strip with the
Euphrates to the east and Lake Razazah to the west; 3rd ID crossed at Musayyib.
Republican Guard **Medina** and **Nebuchadnezzar** Divisions held it. The air
story is the 11th Aviation Regiment's deep attack of 23–24 March: 32 AH-64s
sent against the Medina "corridor near Najaf" with the standard preparatory
artillery suppression **deliberately omitted**, into "a fusillade of small-arms
and anti-aircraft fire" — one Apache down, crew captured, nearly the whole
regiment damaged. The corrected TTP on 26 March added a four-minute artillery
prep, Apaches firing while moving rather than hovering, and F/A-18 escorts
suppressing the flanks: no losses, seven AD guns destroyed. That is a
better mission brief than anything I could invent.

*Honesty note:* **no source I found names the specific SAM systems in the gap.**
Roland, SA-8, SA-9 and ZSU-23-4 were all in the Republican Guard inventory, so
that is what the corridor briefs — as inference, stated as such here.

**Western Scud Box.** The term is authentic — Air & Space Forces Magazine:
"The allies designated several 'Scud boxes' to help strike aircraft narrow the
search." **The published boundaries are not.** RAND's MR-1408 chapter on
coalition Scud-hunting is the right source and is paywalled. What is solid: a
western launch basket around **H-2, H-3, Ar Rutbah, Al Qaim and Wadi al Amiq**
ranged on Israel, hunted by F-15E with LANTIRN, A-10 and F-16 plus SAS and
Delta road-watch teams; the H-2/H-3 complex carried **13 SAM batteries**. So the
corridor is named "Western Scud Box" and points at Ar Rutbah, rather than
asserting a "Scud Box North" with coordinates nobody has published.

---

## What I found and did **not** ship, and why

**Package Q, 19 January 1991.** 72 F-16Cs plus escort, the largest single
package of the war; two F-16s of the 614th TFS lost, both pilots POW. The route
is documented only to the granularity of "flew up Iraq's western side toward
Syria before making a right turn toward Baghdad" — the turn point is not
published. Geometrically that final leg is ≈090° into Baghdad, which from our
modern centroid is not a corridor at all: **the centroid is already at
Baghdad.** The mission is real; our two-number mechanism can't express it
without lying about where it starts. A better home for it is a Library
template with the western fields as home plate.

**Operation Opera / Osirak, 7 June 1981.** The terminal run — Saudi/Jordanian
border corner to Tuwaitha, 460 km on 084° — is a genuinely good DCS corridor.
It does not work *here*: in the coldwar preset the player flies Iraqi, so the
reactor is on their own side of the line. It is a Library mission, not a
corridor.

**Operation Ugly Baby / "Happy Valley," 22 March 2003.** Six MC-130Hs carrying
~300 Green Berets, Turkey's overflight refusal quadrupling the infiltration
distance, five hours at night below 500 ft, one aircraft hit 19 times over the
AAA belt north-west of Mosul, LZs at **Bashur and Sulaymaniyah** — both on our
map. Superb material. Cut because its lane sits 18° and 50 km from Northern
Watch's, and two corridors that close are one corridor and a duplicate. It
belongs in the Library.

**Post-2003 Baghdad airspace.** I could not confirm the existence, name or
boundaries of a "Baghdad Restricted Operating Zone" in any authoritative open
source, and **the widely-repeated BIAP "corkscrew" approach has no citable
authority I could find** — what is documented is the 22 November 2003 DHL A300
hit by an SA-14 at ~8,000 ft during a rapid climbout. The properly-sourced 2003
framework is the Wathen/Air University account of OIF airspace control: seven
tanker tracks along the Saudi border each 30 × 70 nm, named "driveways" feeding
strike packages to them, a dedicated C2ISR corridor, UAV and missile ROZs, and
1,800 ACMs in the database with ~1,200 managed daily. Good doctrine reading,
wrong shape for a two-number corridor.

**Kill boxes.** The CGRS grid — 30′ × 30′ cells (~30 × 24 nm), subdividable
into quadrants, halves, or the nine 10′ blocks numbered like a telephone keypad
that were actually used in combat — is trivially reproducible across the whole
map and is *not* a corridor. Worth remembering as a separate feature: open by
default beyond the FSCL, closed short of it. MG Leaf reported V Corps'
reluctance to open boxes short of the FSCL left **~80% of AI sorties departing
without engaging**, against ~80% weapons employment in the MEF's area. That is
a scenario premise in itself.

**Off the map entirely:** the Sirri and Larak shuttle raids, Iraq's declared
27°30′N exclusion zone, Val-Fajr 8 (Faw) and Karbala-5 (Basra), every Iranian
city target of the War of the Cities, and every coalition operating base
(Incirlik, Al Jouf, Prince Sultan, Ali Al Salem, Al Minhad, Aviano).

---

## Sources

- [CSIS, *Lessons of the Iran-Iraq War* — Ch. 7](https://csis-website-prod.s3.amazonaws.com/s3fs-public/legacy_files/files/media/csis/pubs/9005lessonsiraniraqii-chap07.pdf) · [Ch. 14](https://csis-website-prod.s3.amazonaws.com/s3fs-public/legacy_files/files/media/csis/pubs/9005lessonsiraniraqii-chap14.pdf) · [Ch. 6, Gulf War](https://csis-website-prod.s3.amazonaws.com/s3fs-public/legacy_files/files/media/csis/pubs/941015lessonsgulfiv-chap06.pdf)
- [Human Rights Watch, *Genocide in Iraq* — The First Anfal](https://www.hrw.org/reports/1993/iraqanfal/ANFAL3.htm)
- [Wikipedia — H-3 airstrike](https://en.wikipedia.org/wiki/H-3_airstrike) · [Atlantic Council on the H-3 raid](https://www.atlanticcouncil.org/blogs/iransource/how-iranian-phantoms-pulled-off-one-of-the-most-daring-airstrikes-in-recent-memory/) · [H-3 Air Base](https://en.wikipedia.org/wiki/H-3_Air_Base)
- [Wikipedia — Operation Kaman 99](https://en.wikipedia.org/wiki/Operation_Kaman_99) · [Halabja massacre](https://en.wikipedia.org/wiki/Halabja_massacre) · [War of the cities](https://en.wikipedia.org/wiki/War_of_the_cities) · [Operation Opera](https://en.wikipedia.org/wiki/Operation_Opera)
- [From Balloons to Drones — Iraqi air defenses in Desert Storm](https://balloonstodrones.com/2022/10/19/looking-back-at-iraqi-air-defences-during-operation-desert-storm/) · [Electric Avenue: EW vs the IADS](https://balloonstodrones.com/2022/01/20/desertstorm30-electric-avenue-electronic-warfare-and-the-battle-against-iraqs-air-defences-during-operation-desert-storm/)
- [Air & Space Forces Magazine — "Package Q"](https://www.airandspaceforces.com/article/package-q/) · ["Scud War, Round Two"](https://www.airandspaceforces.com/article/0492scud/) · ["Ambush at Najaf"](https://www.airandspaceforces.com/article/1003najaf/)
- [Army University Press — Task Force Normandy staff-ride packet](https://www.armyupress.army.mil/Portals/7/educational-services/staff-rides/VSR/Task-Force-Normandy/1.%20Task%20Force%20Normandy%20Read%20Ahead%20Guidance%20and%20Packet.pdf)
- [Haulman, *Crisis in Iraq: Operation PROVIDE COMFORT*, AFHSD](https://media.defense.gov/2012/Aug/23/2001330108/-1/-1/0/Op%20Provide%20Comfort.pdf) · [GlobalSecurity — Southern Watch](https://www.globalsecurity.org/military/ops/southern_watch.htm) · [Wikipedia — Operation Northern Watch](https://en.wikipedia.org/wiki/Operation_Northern_Watch)
- [Wathen, "The Miracle of Operation Iraqi Freedom Airspace Management," Air University](https://www.airuniversity.af.edu/Portals/10/ASPJ/journals/Chronicles/wathen.pdf) · [CENTAF, *OIF – By The Numbers*](https://mronline.org/wp-content/uploads/2020/03/oifcentaf.pdf) · [CGSC, "Joint Doctrine and the Kill Box"](https://cgsc.contentdm.oclc.org/digital/api/collection/p4013coll3/id/108/download)
- [ARSOF History — Operation Ugly Baby](https://arsof-history.org/articles/v1n1_op_ugly_baby_page_1.html) · [Operation Viking Hammer](https://arsof-history.org/articles/v1n1_op_viking_hammer_page_1.html) · [Air Commando Association — Task Force Viking](https://aircommando.org/task-force-viking-and-the-ugly-baby-mission/)
- [Wikipedia — Battle of the Karbala Gap (2003)](https://en.wikipedia.org/wiki/Battle_of_the_Karbala_Gap_(2003)) · [Operation Northern Delay](https://en.wikipedia.org/wiki/Operation_Northern_Delay) · [2003 Baghdad DHL shootdown](https://en.wikipedia.org/wiki/2003_Baghdad_DHL_attempted_shootdown_incident)
