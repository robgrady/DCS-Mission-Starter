# Maintaining the historical mission Library

New information should improve the missions it affects, while retaining explicit
limits on historical claims and simulator validation. The reference register,
live authoring data, published pack revisions and descriptions all need review.
A green software suite is not independent historical certification.

Run the dependency inventory before a content review:

```sh
PYTHONPATH=.:vendor python scripts/audit_historical_content.py --output outputs/content-review/current.json
PYTHONPATH=.:vendor python scripts/audit_historical_content.py --previous outputs/content-review/previous.json --output outputs/content-review/current.json
```

The ledger enumerates every authored template/map/era combination, every mission
in locally produced official collections and every registered map reference.
It links relevant archive readings and unit observations, records content/evidence
fingerprints, flags changed records and retains removed IDs. A manually recorded
`claim_assessment` survives only an unchanged fingerprint; changed evidence moves
it to `previous_claim_assessment` for a fresh review. Unchanged means only
unchanged since that snapshot. It does not mean historically verified. Missing
sources and service-window conflicts are review candidates, not automatic edits.
Server-uploaded/community collections require an inventory of their actual
published revisions; they are not included merely because this checkout exists.

For each finding, retain the edition hash, physical page, publication precision,
claim period, original unit/aircraft designation and source access limitations.
Find affected mission dates, maps, bases, aircraft variants, courses and charts
in the ledger. Compare the specific claim with that source; record verified,
approximate, unsupported, conflicting or not yet reviewed. Check unit identity,
station dates, weapons and route geometry separately. A source supporting one
of those facts does not establish the others.

Review the actual `.miz` alongside its description, briefing and kneeboard.
`scripts/audit_library.py` generates readable native actor/route/task/trigger
facts for live templates. Published collections must be inspected from their
fixed revision bytes. Historical plausibility, native-file behavior and a DCS
flight are separate decisions. Keep unflown items marked unverified; do not
present a generated archive as a completed simulator checkride.

Revise the authoring source first, then regenerate all affected derived content.
Update the description if its promise exceeds what can be generated or measured.
Add a focused regression check and prove consequential guards by fault injection.
Increment the application semantic version for the delivery and the content
version of changed collections. Review the User Manual, run release gates,
publish immutable official revisions and retain the prior catalog pointers for
rollback. Preserve unrelated/community packs and private volume stores.

## Adapting training from another aircraft

T-45/CNATRA or other-aircraft material can inform a lesson's geometry or learning
objective. It does not certify the target aircraft's procedure. Record the source
aircraft/configuration, target DCS module/variant, transferable objective,
unsupported dependencies, adapted limits and how the outcome is measured.
Prefer the target aircraft's flight manual and modeled systems documentation for
cockpit steps, radar modes, navigation handling and performance limits.

Review at least radar search/track modes, display symbology, navigation-point
capacity and entry, INS alignment/update, TACAN/ILS availability, radio controls,
crew responsibilities, weapon delivery modes, speed/AOA/fuel limits and carrier
recovery aids. A training overlay named “HUD” in this code is a mission display;
it does not establish that the F-4 cockpit has modern avionics. A native waypoint
also does not prove automatic loading into its navigation computer.

The currently inspected authoring sources do not explicitly cite T-45 NATOPS.
White Knights identifies 70 TFS F-4 material; Case III identifies **CV NATOPS**
and target F-14/Hornet manuals. CV NATOPS is distinct from a T-45 aircraft flight
manual. External/community missions and undocumented adaptations still need
source attribution; a text search does not prove they have no T-45 influence.

Boeing's [VMTS program description](https://boeing.mediaroom.com/2009-02-05-Boeing-Receives-Contract-to-Add-Virtual-Radar-to-US-Navy-T-45-Training-System)
describes an embedded virtual radar training environment. Its simulated modes
must not be treated as F-4 capabilities or universal T-45 equipment. Heatblur's
[F-4 air-to-air radar documentation](https://f4.manuals.heatblur.se/systems/radar/air_to_air.html)
describes its actual search/acquisition/track controls. Its
[navigation computer documentation](https://f4.manuals.heatblur.se/systems/nav_com/ins.html)
describes two target points and aircraft-based inputs; its
[VOR/ILS documentation](https://f4.manuals.heatblur.se/systems/nav_com/vor_ils.html)
identifies instrument guidance and station requirements. These are the applicable
modeled-system references for adaptations, rather than a blanket assumption
that one aircraft is more advanced in every respect. Historical ARN-101/DMAS
material does not establish that capability in the currently modeled analog jet.
