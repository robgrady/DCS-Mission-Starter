# First Flight campaign

This flight-test candidate contains FAM-01 First Flight and FAM-02 Ramp to Air
at Kobuleti in the VNAO T-45C v1.02. The two sorties use quiet daylight,
single-player front-seat starts, on-screen coaching and empty pylons.

## Build

From the repository root, with the pinned runtime dependencies installed:

```sh
PYTHONPATH=.:vendor python scripts/build_first_flight_missions.py /path/to/new/native
python scripts/build_first_flight_documents.py /path/to/new/native
python scripts/package_first_flight.py /path/to/new/native /path/to/new/output
```

Use a fresh output folder. The campaign ZIP is for DCS players. The companion
.sspack is the same campaign plus Library entries and integrity metadata.
Install the .sspack through the normal Mission packs admin workflow. The Train
picker uses its declared pack ID and version and serves the checked campaign
attachment. Each selectable combination has its own authored content.

## Evidence and credit

The T-45C display name and native `T-45` class were checked directly against
`entry.lua` and `VNAO_T45.lua` in the [VNAO v1.02 release archive](https://www.mediafire.com/file/v4fqcx95ynicq72/VNAO_T45.zip/file).
Its bundled Caucasus ILS QuickStart also supplies the native `requiredModules`
shape. This campaign uses original mission geometry and rules.
The campaign requires the separate [VNAO community mod](https://forum.dcs.world/topic/203816-vnao-t-45-goshawk/).

The original illustrations come from the supplied Navy publication *Flight
Training Instruction: Familiarization, T-45 Strike*, CNATRA P-1212
(Rev. 02-19), 2019. FAM-01 uses Figure 3-1 (printed p. 3-2, PDF p. 26).
FAM-02 uses the ground-movement row of Figure B-2 (printed p. B-5, PDF p. 115).
Each brief and source-study kneeboard cites its figure. The displayed study
values are part of the source artwork. The authored lesson card gives the
in-game cues.

## DCS acceptance

On Windows, use a clean DCS Saved Games profile and record the DCS and mod
builds. Verify Campaigns > User lists the campaign and both missions open
from Mission. Check the airborne and engine-running parking starts, controls,
kneeboard readability and the F10 hint action. Fly both positive paths and
retry after a missed step. Confirm campaign advance from FAM-01 and completion
after FAM-02, including the behavior of early exit and DCS's Skip command.
Keep archive inspection, native scoring simulation, DCS flights and human
beginner playtest observations in separate evidence entries.
