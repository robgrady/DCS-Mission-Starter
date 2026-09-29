# Critique of my own migration plan

*13 Aug 2026. Rob asked me to evaluate the plan I just gave. Six modifications,
in order of how much they change the answer.*

**The headline: I conflated a content need (Iraq) with an infrastructure change
(swap libraries), because the fork was the vehicle I discovered it through.
They are separable, and separating them removes almost all the risk.**

---

## 1. Deploy before you swap — the sequencing is wrong

Live is **v1.51.1**. We have **fifteen** releases built and undeployed
(1.52 → 1.66). My plan put a library swap on top of that stack.

If anything misbehaves in the wild after that deploy, the cause is ambiguous
across fifteen releases *plus* a library change — and the library change is
precisely the one that touches everything. That is a self-inflicted debugging
problem.

**Modification: deploy v1.66.0 first, let it soak, then treat the library as
its own release with nothing else in it.** No code changes; it costs a week and
buys an unambiguous bisect.

## 2. Take the data we lack, not the library we have — the big one

I verified this after writing the plan: **the Iraq terrain package is liftable
as-is.** Its imports are `dcs.mapping`, `dcs.terrain.{Terrain, Airport,
ParkingSlot, Runway, RunwayApproach, MapView}`, `dcs.terrain.projections`,
`dcs.atcradio`, `dcs.beacons` — every one of which **our current pydcs already
provides**. Nothing in it needs the fork's engine.

We also already have the pattern: `missiongen/terrains/` exists precisely
because we did this for Afghanistan.

So the choice isn't "swap or don't". It's:

| | Move | Gets us | Risk |
|---|---|---|---|
| **A** | Vendor `iraq/` into `missiongen/terrains/` | **Iraq, now** | Near zero — additive, a map that doesn't exist yet has nothing to regress |
| **B** | Swap the whole library | Iraq + Afghanistan deletion + 5 years of engine changes | Touches every mission we generate |

**Modification: do A now. Decide B separately, on its own merits, later.** The
value of the fork that we actually needed — a terrain we don't have — carries
none of the risk of the fork we'd be adopting.

Note the asymmetry: **new terrain is risk-free precisely because it's new.**
Re-importing Afghanistan or Germany means replacing data we have already tuned
against. Importing Iraq replaces nothing.

## 3. Build the seam AFTER the spike, not before

I recommended the adapter seam first, on the grounds that it makes the swap
"bounded and reversible". Rethinking it: that's **speculative generality**. I
don't yet know what the seam needs to abstract — I'd be designing an interface
against imagined variance and then discovering the real variance afterwards.

The seam also doesn't make the swap safer. What makes it safe is the
verification (§4). The seam pays off for *maintenance* and *future* swaps.

**Modification: if we do the swap, run it as a throwaway branch spike FIRST and
let the actual breakages define the seam's interface.** Possibly the spike shows
we don't need a seam at all — in which case I'd have built an abstraction for
nothing.

## 4. Byte-comparison is the wrong primary instrument

I said "byte-compare and explain every diff". That sounds rigorous and would
fail in practice:

- `planes.py` differs by **2,218 lines**. Unit ids, payload tables and
  performance figures move, so the mission diff will be enormous and mostly
  noise. "Explain every diff" collapses under its own weight, and what actually
  happens is that I start rationalising them.
- More fundamentally: **a byte diff tells you THAT something changed, never
  whether it is WORSE.**

**Modification: diff SEMANTICS, not bytes.** Extract the properties we care
about from both builds and compare those — and we already have every extractor,
scattered through the suite:

| Invariant | Where it already lives |
|---|---|
| ramp occupancy per field | `test_squadron_cap`, the Nellis fill work |
| player spawn geometry | `test_bfm_ladder`, `test_time_to_first_action` |
| loadout legality | the pylon/loadout tests |
| every preset airbase resolves | the map/era gate |
| threat counts by tier | the threat-dial tests |
| briefing/kneeboard present | the docs tests |

Byte-diff gets **demoted to a smoke signal** ("did anything change at all?"),
which is genuinely useful as a tripwire and useless as a review tool.

## 5. The hazard I hadn't flagged: 9,550 hand-measured numbers

`parking_headings.json` holds **9,550 individually measured per-slot parking
headings** across ten maps — **2,220 on Germany alone**, keyed by slot *name*
('01', '02', …).

Germany is exactly the map the fork re-exports, with a 24,145-line airports
table against our smaller one. If a re-export renumbers or renames slots, every
one of those measurements silently points at the wrong stand — aircraft face
the wrong way, and **no test catches it**, because the tests assert headings are
*applied*, not that they are *correct for that stand*. It is a purely visual
regression: invisible to the suite, obvious in the cockpit.

I spot-checked Zweibrucken, Wittstock and Ramstein: slot names are **identical**
between the two exports, so the hazard does not appear to have materialised. But
the fact that I found that out by hand, after writing the plan, is the finding.

**Modification: write the guard regardless of what we decide** — assert that
every slot name in `parking_headings.json` still exists on its terrain. That is
a cheap test protecting nine and a half thousand measurements that currently
have nothing standing behind them. It should exist even if we never touch
pydcs again.

## 6. Pin a commit, not a branch

The fork ships from a `retribution` branch with no releases or tags. Vendoring
from a moving branch is worse than vendoring a five-year-old release in one
specific way: **you cannot say what you have.** Upstream at least had "0.13.0".

**Modification: pin the SHA, record it in `PYDCS_PROVENANCE.md`, and treat every
update as a deliberate event that re-runs the same verification.** Same rule if
we only lift the Iraq package: record which commit it came from.

---

## The revised plan

1. **Deploy v1.66.0.** Clear the fifteen-release backlog before anything
   structural.
2. **Write the parking-headings guard.** Cheap, protects 9,550 measurements,
   useful forever.
3. **Vendor the Iraq terrain package** into `missiongen/terrains/`, pinned to a
   named commit. Ship Iraq as a map. Near-zero risk, and it is the thing that
   was actually wanted.
4. **Build the semantic differ** as a script — because it's the tool that makes
   *any* future library decision cheap, and it costs little.
5. **Then, separately and unforced, decide on the full swap** — spike on a
   branch, let it define the seam, verify semantically, and only if the case
   still holds.

## What would change my mind

If the fork carried something we need in the **engine** rather than in the
data — a DCS format change that breaks mission loading in a future patch, say —
then the swap becomes urgent and the terrain packages stop being the point.
Worth watching, not worth pre-empting.

The `patrol_flight` bug is unchanged in the fork, so the upstream PR is worth
filing either way.
