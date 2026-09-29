# Do we need to iterate on pydcs?

*Decision memo, 13 Aug 2026. Prompted by two pydcs surprises in v1.66.0.*

**Short answer: we already are — in the most expensive place possible. The move
isn't to fork pydcs; it's to stop hand-building around a stale copy of it.**

---

## 1. What we found

### Upstream is effectively frozen
pydcs/dcs: **last release 0.13.0, January 2021** — over five years ago. 1,171
commits on master, 38 open issues, 5 open PRs. Not abandoned, but not moving.

### The community already forked it
**dcs-retribution/pydcs** carries **1,242 commits** — roughly 70 ahead of
upstream — under the DCS Retribution project (the successor to DCS Liberation,
a large and actively developed campaign generator). Same LGPL-3.0 license.
The ecosystem has already voted on this question.

### We have quietly forked it too, in the worst possible way
This is the finding that decides the memo:

- Our vendored pydcs knows **11 terrains**: Caucasus, Channel, Persian Gulf,
  Nevada, Normandy, Syria, Sinai, Marianas, Germany, Kola, Falklands.
- It does **not** know **Afghanistan** — so we hand-built it:
  `missiongen/terrains/afghanistan/` is **4,602 lines**, including a 397 KB
  airports table.
- It does **not** know **Iraq** — which is sitting on the outstanding list as
  "Iraq terrain exports", i.e. the same job again.
- It's missing recent airframes (A-29B, UH-60L), and we already carry
  `pending_aircraft.json` with a provisional id so the F-14B(U) can fly at all.

So the cost of the stale library is not hypothetical. It is one 4,600-line
directory, one provisional-id mechanism, and one queued repeat of the whole
exercise for Iraq.

### The v1.66.0 bugs argue AGAINST forking, though
Both were in pydcs **convenience helpers**, not its core:

- `patrol_flight()` spawns an in-flight patrol at `Point(pos1.x - 10000, pos1.y)`
  — a hardcoded offset that ignores heading, with no way to opt out.
- unit heading is recomputed on save from the wp0→wp1 bearing unless the group
  sets `manualHeading`; and `unit.heading` is degrees while most of the geometry
  API is radians.

In both cases the fix was to **stop using the helper and use the primitives
underneath** (`flight_group_inflight` + `patrol_flight_to_group`). That is a
healthy relationship with a library, not a reason to own it. The low-level API
is fine; the helpers embed opinions.

## 2. The options

| | Option | Verdict |
|---|---|---|
| A | **Status quo** — vendored upstream, 33 lines of runtime patches, hand-build what's missing | Works today, and the bill grows with every new terrain and module |
| B | **Fork pydcs ourselves** | **No.** Our patches are 33 lines. A fork is a repo, forever, plus LGPL obligations we currently satisfy trivially by keeping the copy pristine and swappable |
| C | **Move the vendored copy to dcs-retribution/pydcs** | **Most likely the answer** — same license, actively maintained, ~70 commits ahead, proven in a bigger project |
| D | **Build the adapter seam** (`missiongen/dcslib.py`) | **Do this regardless.** It's what makes C cheap and reversible |

### Why not fork (B), stated plainly
1. **LGPL posture.** Today we vendor byte-for-byte upstream and document the
   separability, so a user can drop in their own build. Modifying it is legal
   and we ship source anyway, but we'd own the divergence permanently.
2. **DCS never stops moving.** New modules, terrains and unit types arrive
   constantly, and our entire value proposition is period-correct, current
   content. A fork means merging forever or slowly rotting — and rotting is
   what already produced the Afghanistan directory.
3. **Asymmetry.** 33 lines of patch versus a library to maintain.

## 3. What I'd do

**1 — Build the adapter seam first (`missiongen/dcslib.py`).**
One module owning every "pydcs does X, we want Y" translation: spawn exactly
here, heading is degrees, parking-slot keys, terrain resolution, the pending-id
mapping. That knowledge is currently spread across **81 comments** and a dozen
call sites. With the seam, swapping the library becomes a bounded change with
one place to look when it misbehaves. This is worth doing even if we never
switch.

**2 — Evaluate the Retribution fork, decided by one question.**
*Does it carry Afghanistan and Iraq terrain data?* If yes, switching deletes a
4,600-line directory and a queued repeat of it, and that alone justifies the
move. Cheap to check: clone it, import `dcs.terrain`, list the classes, and try
`resolve_terrain` on our twelve maps.

**3 — Verify any swap by OUTPUT, not by green tests.**
Generate the same N recipes on both libraries and byte-compare the `.miz` files
(we already hash artifacts this way). Missions changing is not automatically
bad — but it must be *seen and explained*, not discovered by a pilot. Anything
that changes gets a named reason.

**4 — Upstream the `patrol_flight` defect regardless.**
The hardcoded −10 km spawn that ignores heading is a genuine bug with no
opt-out. A small PR adding an explicit spawn position would be good citizenship
and would delete one of our workarounds — and it applies to whichever fork we
end up on.

**5 — Generalise the discipline that caught all of this.**
Two library defaults silently overrode deliberate values, and neither was
visible from the call site — only from measuring the built mission. The rule
worth writing down: **any library helper used for something geometrically or
semantically meaningful gets an assertion on the OUTPUT, not on the call.**
That is what `test_bfm_ladder.py` and `test_time_to_first_action.py` now do.

## 4. What this is not

This isn't urgent. Nothing is broken, the product ships, and the vendored copy
is pinned and stable. It's a **cost curve** question: every new DCS terrain
costs us thousands of lines while we stay where we are, and Iraq is next in the
queue. The seam (item 1) is a few hours; the evaluation (item 2) is one
afternoon and answers whether the rest is worth doing.

## 5. Open question for you

Iraq is on the list. Do you want me to **check the Retribution fork for
Afghanistan and Iraq terrain support before** anyone hand-builds Iraq? If it
has them, that single check saves the entire exercise — and if it doesn't, we
learn that the fork buys us less than hoped and the answer is probably to stay
put and keep the seam.

---

Sources: [pydcs/dcs](https://github.com/pydcs/dcs) ·
[dcs-retribution/pydcs](https://github.com/dcs-retribution/pydcs)
