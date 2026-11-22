# F-4E Digital Kneeboard Simulator import

Tested on 21 November 2026 in the signed-in Digital Kneeboard Simulator
planner. The design **Sortie Starter test — Fly the Card (F-4E)** was created
as a standalone design in a single-member wing and left unpublished.

## Source mission

Use **Timing 1 — Fly the Card** from the Timing F-4E collection
(`timing_f4e` pack v1.0.13). The source file is
`missions/01_timing_1_flythecard.miz` with SHA-256
`0be49e35b31a1027be89ebd141b5c0a44cae6bff0977e6d855aaafe10cdf6334`.
Its ZIP integrity and pack checksum matched. The native mission has one
human F-4E-45MC aircraft in Chevy 1, a parking-hot start at Fassberg and a
12:00 local mission clock. The collection title says 1980. This native
mission is dated 21 June 1978, so use the native date when comparing the import.

In DKS, open **New kneeboard → Import**, select the native .miz, choose
**Chevy 1**, review the detected F-4E and CW Germany selections, then create
the standalone design. The importer offered 64 overlay items. The resulting
map showed the route and mission overlays.

## Route comparison

Coordinates in the left column are native values converted to decimal degrees.
DKS displayed them in degrees and decimal minutes (DDM). All five points
agreed within display rounding. The waypoint ETAs are elapsed from mission
start. The published lesson brief remains the reference for its separately
graded wheels-up checkpoint.

| Point | Native latitude, longitude | DKS latitude, longitude | DKS altitude | DKS speed | DKS ETA |
| --- | --- | --- | ---: | ---: | --- |
| Parking hot | 52.910613, 10.188272 | 52°54.637′ N, 010°11.296′ E | 0 ft | — | — |
| WP1 | 52.840084, 11.383334 | 52°50.405′ N, 011°23.000′ E | 14,764 ft | 405 kt GS | 00:09:56 |
| IP | 53.035331, 12.632853 | 53°02.120′ N, 012°37.971′ E | 9,843 ft | 405 kt GS | 00:16:54 |
| TARGET | 52.965097, 12.839884 | 52°57.906′ N, 012°50.393′ E | 7,874 ft | 405 kt GS | 00:18:10 |
| Landing | 52.919426, 10.184823 | 52°55.166′ N, 010°11.089′ E | 0 ft | Blank | Blank |

The imported landing point appeared as a generic steerpoint with a **Landing**
remark. The numeric en-route speed matches the native 208.333 m/s to the
nearest knot. The DKS map labels it as groundspeed, so compare any calculated
flight plan against the original brief before using its numbers in the lesson.

## Other imported fields

| Field | Native mission | DKS observation |
| --- | --- | --- |
| Aircraft, map and year | Heatblur F-4E-45MC, GermanyCW, 1978 | F4E, CW Germany, and 1978 in the map's magnetic-variation readout |
| Human roster | One Player aircraft, Chevy 1 Pilot #1 | One populated aircraft/callsign row. Pilot and WSO assignments blank. |
| Frequencies | 305.725 MHz on both CH1, 254.325 MHz on both CH7, 243.000 MHz on COMM CH18 and AUX CH20 | Both ARC-164 tables retained those sampled values in the same channels. |
| Radio labels | Flight, Tactical, Guard | Agency fields were blank. |
| Stores | Four AIM-7F, four AIM-9P, two 370-gallon tanks | Four AIM-7F and two tanks displayed. AIM-9Ps absent and both inner-wing rows displayed Empty. |
| Recovery | Native landing action | Location and Landing remark were present. A DKS planning row does not exercise the DCS recovery or completion logic. |

Use the original .miz for flying and its brief for the lesson timing and
comms. Review the DKS loadout and add agency labels before using a generated
kneeboard. This check covered the signed-in planner import. A pilot export,
cockpit loading, the campaign and lesson completion in DCS, and a Tacview
replay still need separate runs.

[DKS design and sharing manual](https://www.digitalkneeboardsimulator.com/manual/designs)
· [DKS airframe and import changelog](https://www.digitalkneeboardsimulator.com/manual/changelog)
