# Native DKS import validation — v1.112.0

Observed 3 October 2026 in the live Digital Kneeboard Simulator website.
This is a bounded import test, not a universal compatibility certificate.

## Fixture and method

Run `PYTHONPATH=.:vendor python scripts/build_validation_pack.py outputs/releases/1.112.0/flight-validation`.
The dks case is Caucasus, Modern, F-14B(U), seed 11203, four aircraft with
three High-skill AI wingmen, optional route/targets enabled, flight common
307.725 MHz and tanker 271.500 MHz. Other defaults resolve through the engine.

Native SHA-256: `922629e03b930d77333b74880447c4ff0a0770f876f8d853c4ed805d06158c7c`.

Created a new unpublished design through New kneeboard → Import .miz, selected
Uzi 1, confirmed F-14B(U)/Caucasus and created the design. Inspected WAYPOINTS,
FLT MEMBERS, COMMS, SUPPORT, LOADOUT and DTC against the saved native mission.
Retained screenshots and DOM-visible field observations in the release output.
The browser JSON download did not complete through automation; these are UI
observations, not a parsed export round trip. No Publish or Post to ATO action
was taken. Unpublished designs are still squadron-visible: see the official
[DKS design manual](https://www.digitalkneeboardsimulator.com/manual/designs).

## Observed comparison

| Field | Native fixture | DKS result |
| --- | --- | --- |
| Aircraft/map | F-14BU / Caucasus | F-14B(U) / Caucasus |
| Flight roles | One Player + three High AI | One human roster row, Uzi 1 Pilot #1; no AI roster rows |
| Takeoff | 42.180285 N, 42.467642 E | 42°10.817′ N, 042°28.059′ E |
| WP1 | 43.549316 N, 40.583596 E; 6,000 m; 222.222 m/s; ETA 1,502 s | 43°32.959′ N, 040°35.016′ E; 19,685 ft; 432 kt GS; T+00:25:02 |
| IP | 44.868616 N, 38.002646 E; 4,500 m; 222.222 m/s; ETA 2,644 s | 44°52.117′ N, 038°00.159′ E; 14,764 ft; 432 kt GS; T+00:44:04 |
| TARGET | 45.002862 N, 37.930236 E; 3,000 m; 222.222 m/s; ETA 2,716 s | 45°00.172′ N, 037°55.814′ E; 9,843 ft; 432 kt GS; T+00:45:16 |
| Landing | Unnamed landing point; zero altitude/speed/ETA | Unnamed STPT at matching coordinates; altitude 0, speed and ETA blank on initial inspection |
| Radio presets | Custom CH1 307.725 and CH4 271.500; AWACS CH3 251.475 | Both cockpit-radio tables retained these frequencies; agency labels blank |
| Tanker | Texaco, 271.500, TACAN 39Y, FL220 | Call sign, frequency, TACAN, altitude and track populated |
| AWACS | Overlord, 251.475, FL300 | Call sign, frequency, altitude and track populated |
| Payload | Two AIM-9M, four AIM-7P, two 300-gal tanks | All eight stores mapped to matching F-14 stations |
| Map drawings | Support labels, targets, SAM batteries/rings and bullseye | Visible on imported map; complete geometric equality not certified |
| Cartridge fields | Native F-14B(U) settings in .miz | Additional points/plot lines empty; CMDS aircraft defaults; cartridge fidelity unverified |

Native ETA values count from mission start (mission clock 12:00), rather than
seconds since midnight. DKS initially displayed them as elapsed times. Its
Calculate Flight Plan option can recompute speed/timing; preserve and compare
the original mission rather than assuming a subsequent export is identical.
The landing speed became a DKS planning default on a later view, confirming
that import presence is distinct from an unchanged planning round trip.

## Integration boundary and next checks

- Import `mission.miz`, not `mission_kit.zip`. The JSON sidecars are references,
  not a documented DKS import format. Compare comm agencies with comms.json and
  the brief; [DKS comm plan fields](https://www.digitalkneeboardsimulator.com/manual/comm-plan)
  include aircraft-specific radio tables.
- Keep the original `.miz` for flight roles, tasking and native cartridge data.
  AI roster omission does not change the downloaded DCS mission.
- Validate F-14B(U) cartridge export and cockpit loading separately, then test
  another aircraft/map and exported kneeboard page dimensions. See official
  [DKS export workflow](https://www.digitalkneeboardsimulator.com/manual/getting-started).
- ATO placement, public publication, a DKS MCP/tool contract, every aircraft/map,
  native task behavior and simulator flight validation are not certified here.

## Automated safeguards

The native Mission Kit test reads the saved .miz and compares every route
point's coordinate, altitude, speed and ETA with navigation.json, verifies the
mission checksum, DTC setup card presence and Player/High roles. Real-browser
guards cover readiness in all three generation doors at desktop and narrow
widths. Fault injection rejects false flight-pass claims, wrong human counts,
omitted ship dependency, incorrect carrier ownership, stale/cleared UI responses and broken route serialization.
