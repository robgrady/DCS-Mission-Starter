# What else is in the fork worth taking?

*Product review, 14 Aug 2026. Read from the fork's actual code and history at
`dcs-retribution/pydcs @ 3a79b8ed`, not from commit titles.*

**First, a correction to my own earlier framing.** I described upstream pydcs as
"frozen since January 2021" and implied our vendored copy is five years stale.
That is wrong in an important way: upstream's last *release* was 2021, but its
*master* kept moving, and our copy is from that master. Measured against the
fork, ours is not behind everywhere — it is the **only one of the two that has
`Terrain.utc_offset`**, which is precisely why the Iraq package needed an
adaptation to load.

The two libraries have **diverged**, not raced. That makes cherry-picking the
right posture, and it makes a wholesale swap look worse, not better, than it did
yesterday.

---

## Where each is ahead

| Module | Ours | Fork | Reading |
|---|---|---|---|
| `weapons_data.py` | 4,161 | 13,467 | fork — but see below, it's the same 276 weapons |
| `planes.py` | 36,293 | 37,363 | fork — newer DCS exports (tracks 2.9.28) |
| `weather.py` | 401 | 411 | fork — `auto_fog` |
| `task.py` / `mission.py` | — | +19 / +15 | fork, marginally |
| `Terrain.utc_offset` | ✅ | ✗ | **ours** |
| Terrains | 11 | 14 | fork — Afghanistan, Iraq, Germany Cold War |

## The findings, ranked by product value

### 1. Terrain — the only thing with clear, immediate user value ✅ *taken*
Iraq shipped in v1.67.0. The remaining terrain question is whether to replace
our **hand-built Afghanistan** (4,602 lines, and its projection is marked
*"provisional"* in our own source) with the fork's official export.

**Recommendation: yes, but as its own release, gated on the guard we now have.**
Afghanistan carries 460 measured parking headings; `test_parking_headings.py`
will now say immediately whether an export swap invalidates them. That test is
what makes this a twenty-minute job instead of a leap of faith.

### 2. Weapon settings — real new capability, and a genuine product idea
`weapon_settings.py` + 10,553 lines of settings data give **619 weapons** their
DCS-editor settings: fuze type, function delay, burst, ripple. Worth being
precise about what it is *not*: the weapon list itself is unchanged — **276
CLSIDs in both copies**. The 9,000 new lines are settings metadata, not new
stores.

The product angle is real though. We already brief the loadout on a STORES
kneeboard page. Fuzing is the classic thing a mud-mover gets wrong and never
finds out about — a retarded delivery with an instantaneous fuze frags you.
**"Fuze: 4 s delay" on the kneeboard, set correctly in the mission**, is
exactly the kind of quiet correctness this product is built on.

**Recommendation: worth a spike, not a swap.** The data file is liftable the
same way the terrain was; nothing in it needs the fork's engine.

### 3. Dynamic spawn / neutral bases — watch, don't chase
The fork adds `Airport.is_neutral()` on top of `dynamic_spawn`, which **our
copy already has**. DCS Dynamic Spawn lets players spawn into slots at runtime
rather than at fixed, pre-placed ones.

For us this is mostly a **multiplayer** feature, and our product is
single-player-shaped today (`slots` exists but MP is not the center of gravity).
The neutral-base helper is six lines we could write ourselves in an afternoon if
we ever wanted it.

**Recommendation: no action. Revisit if MP becomes a priority.**

### 4. The parking-prioritisation fix — small, real, and ours to make
The fork changed pydcs's slot sort:

```
ours:  sorted(free_slots, key=lambda x: (x.helicopter, x.slot_name))
fork:  sorted(free_slots, key=lambda x: (x.helicopter, x.width, x.slot_name))
```

Adding `width` means the narrowest adequate stand is used first, so a fighter
stops occupying the one wide stand a tanker needed. That is **exactly the class
of bug we fixed by hand in v1.47.0** for our own ramp dressing — but this sort
governs `flight_group_from_airport`, i.e. where **the player** parks.

**Recommendation: adopt the behavior, not the file.** It's one line, and it
belongs in our own placement code where we can test it, rather than in a
vendored library we've promised to keep pristine.

### 5. Newer aircraft exports — the real long-term argument
`planes.py` is 1,070 lines further along and tracks DCS 2.9.28. This is the
thing that will eventually force the decision: every DCS module release widens
the gap, and `pending_aircraft.json` (our provisional-id mechanism) is the
tax we already pay for it.

**Recommendation: no action now; this is the clock to watch.** When a module
Rob wants is missing and the provisional-id trick can't cover it, that is the
signal, and by then the semantic differ will make the swap measurable.

### 6. Hygiene worth stealing, not adopting
- **Python 3.12 support** (they dropped 3.9) — check ours independently.
- **`.miz` deserialisation fix for `enable_fog`** — only matters if we ever
  *read* missions; we only write them.
- **Projection fixes** — relevant to our provisional Afghanistan projection.

## The shape of the recommendation

The fork's value to us is **data, not engine**: terrains, weapon metadata,
newer unit exports. Every one of those is liftable in isolation, which is what
v1.67.0 demonstrated with Iraq.

Ranked, with sizes:

| | Item | Value | Size |
|---|---|---|---|
| 1 | **Official Afghanistan export** (replaces 4,602 hand-built lines + a provisional projection) | high | small, now that the heading guard exists |
| 2 | **Weapon settings → fuzing on the kneeboard** | medium-high, and distinctive | medium (spike first) |
| 3 | **Parking sort by width** in our own placement | small but real | one line + a test |
| 4 | Newer unit exports | deferred | the clock to watch |
| 5 | Dynamic spawn / neutral bases | no action | — |

Nothing here changes the standing conclusion: **take the data, leave the
engine.** The engine divergence now runs in both directions, and swapping it
wholesale would trade a library we understand for one we would then have to
re-learn — while replacing airport data underneath 9,550 measurements we cannot
easily retake.
