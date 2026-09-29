# Packs beyond the Library — separating canned missions from the code

*Written September 2026, against v1.104.2. Successor to
[content-architecture.md](content-architecture.md), whose phases 1–3 shipped in
v1.79.0 and v1.80.0. This document is about phase 4 and what Rob asked for
next: packs that can be uploaded to **Training** and the **Library** "as well
as others."*

> **Superseded in one respect — read [PACK_FORMAT.md](PACK_FORMAT.md) §2.2 and
> §7–§10 for the normative version.** This document proposed **three** kinds.
> The settled answer is **four**: `missions`, `course`, `reference` and
> **`theater`** — engine data such as published corridors, which ten of the
> product's thirteen maps still lack and which currently costs a full release
> per map. `theater` is different in kind from the other three: it is *input* to
> the generator rather than output of it, so it carries a stricter trust model
> (signed or owner-installed, schema-validated, stamped into the recipe so share
> links stay deterministic).
>
> Everything else below stands, and the spec implements it. Where the two
> disagree, **PACK_FORMAT.md is normative and this document is the reasoning**.

---

## The question, stated precisely

Today a pack lands in exactly one place. `pack.json` carries a `library {}`
block describing a Library card, `packs.list_packs()` returns installed packs,
and the Library endpoint merges them with the built-in templates. That is one
surface, hard-wired.

Rob wants three or more. The tempting move — add a `surface: "training"` field
and let each pack say where it goes — is the wrong one, and the rest of this
document is mostly about why, and what to do instead.

**The question is not "how does a pack reach Training?" It is "what kind of
thing is a course, and is it the same kind of thing as a mission pack?"**

It is not. Getting that distinction right is the whole design; everything else
follows mechanically.

---

## What the code already knows

`missiongen/courses.py` resolves a course into units of four kinds:

| kind | count in `f4e_pipeline` | what it references |
|---|---|---|
| `card` | 16 | a Library mission template, by id |
| `track` | 7 | a syllabus track, by id, optionally a ride range |
| `reading` | 3 | a markdown document, by name |
| `planned` | 4 | nothing — it does not exist yet, and says why |

**A course does not contain content. It references content by id, and it has a
first-class representation for content that is not there.** That is exactly the
right shape, it was arrived at for unrelated reasons, and it is the thing to
build on.

So the two artifacts are genuinely different:

- A **mission pack** is *content*: bytes a pilot flies, plus the documents that
  go with them. Self-contained, reusable, means the same thing wherever it is
  cited.
- A **course** is *curriculum*: an ordered path through content, with
  standards, a gradesheet, a check ride and a pilot's progress record. It is a
  work of authorship whose material is somebody else's bytes.

Collapsing them would mean the same formation ride ships once inside an F-4E
course and again inside an F-16 course, diverging quietly. Keeping them
separate means a ride is published once and cited many times.

---

## The proposal

### Three kinds, one container

Keep one `.sspack`, one manifest, one upload door, one integrity model, one
versioning model. Add a single discriminator:

```jsonc
{
  "format": 2,
  "kind": "missions",     // missions | course | reference   (default: "missions")
  "id": "wk_proud_phantom",
  "label": "…"
}
```

`kind` is **optional and defaults to `missions`**, so every pack that exists
today is valid under this change with no republish — the format's own
compatibility promise (§3 of `PACK_FORMAT.md`) requires nothing less.

| kind | carries | cites | appears in |
|---|---|---|---|
| `missions` | `.miz` files, briefs, kneeboards, card art | nothing | Library |
| `course` | readings, guide PDF, gradesheet template | mission packs, by id | Train |
| `reference` | documents only — PDFs, markdown, diagrams | nothing | cited by courses; a reading shelf |

`reference` is the third kind Rob's "as well as others" is reaching for, and it
earns its place for a reason given below.

### A course manifest

```jsonc
{
  "format": 2,
  "kind": "course",
  "id": "f4e_pipeline",
  "version": "1.0.0",
  "label": "F-4E Phantom II — Learn it, fly it, fight it",

  // WHAT CONTENT THIS COURSE NEEDS. Floating, not pinned — see below.
  "requires": {
    "packs":    [{ "id": "wk_squadron_checkout", "min_version": "1.0.0" },
                 { "id": "wk_proud_phantom",     "min_version": "1.0.0" }],
    "modules":  ["F-4E"],
    "terrains": ["germany", "sinai"]
  },

  "schools": [
    { "id": "upt", "label": "Ground School and UPT", "tagline": "Fly an airplane.",
      "units": [
        { "kind": "reading", "id": "howto",     "doc": "readings/pipeline_howto.md" },
        { "kind": "card",    "id": "form_route", "pack": "ss_sampler", "ride": "form_route" },
        { "kind": "track",   "id": "timing",     "pack": "wk_squadron_checkout",
          "from": 1, "to": 5, "check": true },
        { "kind": "planned", "id": "inst",
          "label": "Instrument recovery — TACAN penetration and ILS to minimums",
          "why": "needs an approach-quality glidepath the Mission Editor cannot see" }
      ] }
  ],

  "docs":  { "programme": "guide/f4e-pipeline.pdf" },
  "files": [ … ], "digest": "sha256:…"
}
```

A `card` or `track` unit gains a `pack` field: *which* published pack the ride
comes from. That is the only structural addition, and it is the join.

### The rule that stops this rotting

**A pack never declares where it appears. Surfaces query the installed set by
kind.**

```
Library  = every installed pack where kind == "missions"   (+ built-in templates)
Train    = every installed pack where kind == "course"
Readings = every installed pack where kind == "reference"  (+ those a course cites)
Fly Now  = the generator. Untouched. Not pack-driven, ever.
```

Three reasons this matters more than it looks:

1. **A `surface` field hands your information architecture to whoever uploads
   a pack.** A stranger's pack could plant itself in Training. Kind describes
   *what the thing is*; placement is the app's decision about its own UI, and
   those must not be the same field.
2. **Adding a surface later would mean republishing old packs.** With a query,
   a new surface is a new query over content that already exists.
3. It is the same discipline as `tracks.json` being the spec and the manifest
   being generated from it — one direction, one owner, no twin functions. That
   shape has already cost this codebase two live defects and the previous
   architecture doc calls the mitigation non-negotiable.

### Dependency direction is one-way

```
course  ──cites──▶  missions
   │
   └───cites──▶  reference
```

Courses know about mission packs. **A mission pack must never know it is in a
course.** If it did, a ride could not be cited by a second course without
editing the first, and the reuse that motivates the split disappears.

---

## The one code change that is not optional

`courses.resolve()` today **raises** on a reference it cannot honor:

```python
raise ValueError(f"course unit {unit.get('id')!r} names an unknown track {tid!r}")
```

with the comment *"that is a data error to fix, not a card to render."* That is
exactly right while courses live in the repo and ship with the code that
satisfies them — the reference cannot dangle, because both sides are in the
same commit.

**The moment a course is uploaded and its content is a separately-installed
pack, that invariant is gone and this line becomes a 500 on the Train page.**
A pilot who installs a course but not its missions is not a bug; it is Tuesday.

The fix costs almost nothing, because the mechanism already exists: an
unresolvable unit degrades to `kind: "planned"` with a `why`.

```python
# was: raise
return {"kind": "planned", "id": unit["id"], "label": unit.get("label") or tid,
        "why": f"needs the {unit['pack']} pack, which is not installed",
        "status": "unavailable"}
```

To the pilot, "not built yet" and "not installed yet" render the same way and
are both honest — the Train page already shows planned units with their
reasons, so the UI is done. Two statuses, not one, so the app can offer *"get
this pack"* for the second and nothing for the first.

This is the single highest-value change in the whole proposal: it converts a
hard coupling into a soft one, and it is about fifteen lines.

---

## Decisions worth arguing about

### Floating versions, not pinned

A course names `{"id": "wk_proud_phantom", "min_version": "1.0.0"}` and takes
whatever satisfies it. The alternative — pinning an exact version — is
seductive because it is reproducible, and wrong here: fixing one typo in a
mission pack would require republishing every course that cites it. That
cascade is how content systems calcify. `built_with` already records what
produced what, so nothing is ambiguous about the bytes a pilot holds; that is
provenance's job, and it does it without a cascade.

### Ids are a permanent promise

Course progress is browser-local, keyed on unit id, by design (no accounts,
nothing server-side). **Renaming a unit id silently resets a pilot's record**,
with no error and no way to detect it after the fact. So the format must say
so: ids are append-only; a renamed unit is a new unit; a guard asserts ids
never disappear between versions of the same course id. This is cheap to write
down now and impossible to retrofit once other people are publishing courses.

### Why `reference` is a real kind and not scope creep

The Training boundary settled at v1.104.1 says: *training teaches only what the
mission can measure, and only what unlocks a sortie you could not otherwise
fly — everything else is reference, not coaching*, and failing ideas route to
the cheap channel rather than being killed.

That rule only works if the cheap channel is actually cheap. Today a reading is
a markdown file in `missiongen/data/courses/`, so **adding one is a code
deploy** — which makes the "cheap" channel cost a release and the rule harder
to follow than to ignore. A `reference` pack makes it an upload.

The architecture should make the product rule the path of least resistance. As
things stand it does the opposite.

### What about `samples/`?

It becomes the **Sampler**, a `missions` pack, uploaded like everything else —
phase 4 as originally planned. It is 23 pre-built `.miz` files, 4.62 MB, dated
16 July, and it predates v1.80.0, the release whose entire point was that no
missions ship in the image or the download. `content-architecture.md` already
recorded it as *"a month stale, unserved, and nobody noticed."* It is now two
months stale and 23% of a release zip that cannot cross a 20 MB transfer limit.

Dropping it from the package takes the zip from 21.1 MB to **~15.4 MB**.

---

## What I would not do

- **Do not put missions inside a course pack.** One ride, one publication, many
  citations. Duplication here diverges silently and doubles the bytes.
- **Do not let a pack choose its surface.** Kind describes the thing; the app
  decides where things of that kind appear.
- **Do not collapse `courses.json` into the manifest by hand.** It is the
  *spec*; `build_pack.py` generates the manifest from it; the runtime reads
  only the manifest. One direction, exactly as `tracks.json` works today.
- **Do not make Fly Now or the Builder pack-driven.** They are per-pilot,
  cheap, and the product's actual differentiator. None of this touches them.
- **Do not require a manifest for a bare folder of `.miz` files.** The best
  property of the current system is that dropping a folder in produces a
  working card. That must survive; a folder with no manifest is a `missions`
  pack, because that is the default.

---

## Migration — five independently shippable steps

| # | Step | User-visible | Reversible |
|---|---|---|---|
| 1 | `kind` discriminator, defaulting to `missions`; spec + reader + guard | nothing | yes |
| 2 | `courses.resolve()` degrades to `planned` instead of raising; two statuses | a course with missing content renders instead of 500ing | yes |
| 3 | Course pack reader; `build_pack.py` emits `f4e_pipeline` as a course pack; upload it through `/admin` | Train reads an installed course | yes — repo course stays until it does |
| 4 | Sampler pack; drop `samples/` from the release package | zip 21.1 → ~15.4 MB, crosses the bridge again | yes |
| 5 | `reference` kind; move the three readings out of the repo | a reading is an upload, not a release | yes |

Step 3 is the one that proves the design, for the same reason v1.80.0 was right
to put the flagship syllabi through the public door: **if the F-4E pipeline
cannot be expressed as an uploadable course pack, the format is wrong, and it
is better to find that out on our own flagship than on somebody else's
upload.**

Steps 1, 2 and 4 are worth doing regardless of whether 3 and 5 ever happen.
Step 2 in particular is a latent 500 the moment any course references anything
installable, and it is fifteen lines.

---

## What this costs

- **A course and its content can be at different versions.** That is the point
  — content stops being welded to code — but it is a new class of support
  question. `built_with` and a visible "needs pack X ≥ 1.2" line are the
  answer, not silent rebuilding, which §2.4 already forbids.
- **A second kind of thing to author.** Mitigated by there being exactly one
  container, one upload flow, one integrity model and one admin screen.
- **A deploy still comes up empty** until packs are uploaded — the accepted
  cost of shipping thin, now extended to Training. The Train door needs the
  same gating the whole-syllabus button already got.
- **Somebody must remember to republish a course when its rides change.** The
  artifacts registry blocks a release on stale derived files; course packs
  belong in it for the same reason.
