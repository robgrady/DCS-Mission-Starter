# Sortie Starter Pack format

**Versions 2 and 3. Normative.** This document defines the format; the code
implements it. Where `missiongen/packs.py` and this document disagree, this
document is correct and the code is a bug.

A pack is a **published unit of Sortie Starter content**, with a manifest
describing what is inside, what a pilot needs to own in order to use it, and
how it was produced.

**There are four kinds of pack** (§2.2). Format 2 describes exactly one of them
— a collection of missions and their documents — and remains the current,
recommended format for that kind. Format 3 adds the `kind` field and the three
kinds that are not missions:

| Kind | Payload | Read by | `format` |
|---|---|---|---|
| `missions` | `.miz` files and their documents | the Library | 2 or 3 |
| `course` | a curriculum citing other packs | Train | 3 |
| `reference` | documents only | the reading shelf | 3 |
| `theater` | data the **generator consumes** | the generator | 3 |

The first three are **output**: they carry bytes the generator produced, or
inert documents, and a bad one harms only the pilot who installed it. The
fourth is **input**: it changes what the generator makes, for every mission on
that map, and it is therefore governed by a stricter trust model (§10). That
distinction is the most important line in this document.

A reader that supports only format 2 is a valid reader. It refuses format 3
with a sentence (§3.2) and keeps working forever on mission packs.

This format is **public**. A `.sspack` is a file somebody can hand to a friend,
publish, or sell, and it may come from someone other than us. That single fact
is why this document exists, why unknown fields are preserved, why every file
is hashed, and why the compatibility rules below are promises rather than
implementation details.

---

## 1. The container

A pack is a **ZIP archive**. The conventional extension is `.sspack`; `.zip` is
accepted and means the same thing. Renaming one to the other must never change
how it is read.

```
pack.json                  the manifest — REQUIRED at the archive root
missions/*.miz             the missions
briefs/*.pdf               per-mission documents
guide/*.pdf                pack-level documents
card.png                   artwork
```

Nothing in that layout is mandatory except `pack.json`. **Paths inside the
manifest are the truth**; the directory names above are convention, and a
reader must not infer meaning from them.

A single bare `.miz` file is also accepted as input and becomes a one-mission
pack. That is an **import convenience, not the format** — the result of
importing one is a normal pack with a normal manifest.

### 1.1 Path rules — normative

A reader **MUST** reject, without extracting, any archive containing a member
whose path:

- is absolute, or begins with `/` or a drive letter;
- contains a `..` segment;
- contains a NUL byte;
- is a symlink or any non-regular entry.

A reader **MUST** ignore `__MACOSX/` entries and files beginning with `._`.

A reader **MAY** strip a single common top-level directory (so an archive that
wraps everything in `my-pack/` behaves identically to one that does not).

---

## 2. The manifest

`pack.json`, UTF-8, JSON. Comments are not permitted (the examples in this
document use `//` for exposition only).

### 2.1 Required fields

| Field | Type | Meaning |
|---|---|---|
| `format` | integer | The version of THIS specification. `2` for a mission pack; `3` for any other `kind` (§2.2). |
| `id` | string | Stable identity. `[a-z0-9_]{1,64}`. Two packs with the same `id` are the same pack at different versions. |
| `label` | string | Human name, shown in the Library. |

Everything else is optional. A manifest containing only those three fields is
valid, and a reader must produce a usable pack from it by deriving the rest
(§5).

### 2.2 `kind` — what sort of pack this is

| Field | Type | Meaning |
|---|---|---|
| `kind` | string | `missions` \| `course` \| `reference` \| `theater`. Default `missions`. |

`kind` says **what the thing is**. It does not say where the application shows
it — that is the application's decision about its own interface, and a pack
that could choose its own placement would let its author dictate somebody
else's navigation. Surfaces select packs by kind; packs do not select surfaces.

**Normative rules:**

- A manifest **MUST NOT** declare `kind` other than `missions` unless it also
  declares `format: 3` or higher. The reason is §3.1: a format 2 reader
  preserves fields it does not understand but does not act on them, so a course
  pack offered to it would install as a mission pack containing no missions.
  Silently wrong is worse than refused, and §3.2 already specifies refusal.
- A manifest omitting `kind` **MUST** be read as `missions`, at any format.
  Every pack that exists today is therefore valid unchanged, and a plain
  mission pack **SHOULD** continue to declare `format: 2` so that it installs
  on the widest range of readers.
- An **unrecognised** `kind` **MUST** be refused with an explanation, and
  **MUST NOT** be coerced to `missions`. This is the opposite of the rule for
  an unknown `library.role` (§2.6), and deliberately so: a wrong role shows the
  pilot a mislabelled card, while a wrong kind means a reader has no idea what
  the payload is or which subsystem consumes it.
- A pack has exactly one kind. A pack that would be two things is two packs.

### 2.3 Content identity

| Field | Type | Meaning |
|---|---|---|
| `version` | string | **Semantic version of the CONTENT**, not of the application. `1.0.0`. Independent by design: correcting a premise line is a new content version and not a new product release. |
| `author` | string | Who made it. |
| `license` | string | SPDX identifier or free text. |
| `homepage` | string | URL. |

**Version ordering.** Readers compare `version` by semantic-version rules. When
two packs share an `id`, the higher `version` wins; on a tie, the more locally
installed one wins (installed beats bundled). A reader **MUST NOT** merge two
packs with the same `id`.

### 2.4 `requires` — what the pilot must own

```jsonc
"requires": {
  "terrains": ["sinai"],        // terrain module keys
  "modules":  ["F-4E"],         // aircraft modules, as DCS names them
  "dcs_min":  "2.9"             // minimum DCS version, optional
}
```

This is the most valuable field in the format and the reason format 2 exists.
Without it a pilot downloads eleven Sinai missions and discovers afterwards
that he does not own Sinai.

A reader **SHOULD** show these before the download and **MUST NOT** refuse to
install a pack because of them — owning a module is the pilot's business, not
the installer's, and a pack downloaded today may be flown after a purchase
tomorrow.

An entry in `syllabus[]` may carry its own `requires`, which is **additive** to
the pack's: the ride needs both.

### 2.5 `built_with` — provenance

```jsonc
"built_with": {
  "app": "1.79.0",                      // what produced the bytes
  "generated": true,                    // false for hand-authored missions
  "spec": "tracks.json#wk_proud_phantom",
  "seeds": "fixed",
  "built_at": "2026-08-18"
}
```

A pack that was generated knows what generated it. When the generator improves,
this is what tells you a pack predates the improvement. Readers **MUST NOT**
silently rebuild or "upgrade" content on the strength of this field — it is a
statement of fact, not an instruction.

### 2.6 `library` — the card

```jsonc
"library": {
  "role": "training",       // training | a2a | strike | sead | cas | carrier | historic
  "threat": 4,              // 1-5
  "players": "SP",          // SP | MP | SP·MP
  "premise": "…",           // one or two sentences
  "image": "card.png",      // path inside the pack
  "eras": ["coldwar"],
  "maps": ["sinai"]
}
```

An unknown `role` **MUST** be treated as `training` rather than rejected.

### 2.7 `syllabus` — ordered contents

```jsonc
"syllabus": [
  { "n": 1,
    "id": "pp_1_drag",
    "label": "Tanker Drag to Egypt",
    "premise": "…",
    "files": { "mission": "missions/01_pp_1_drag.miz",
               "brief":   "briefs/01_brief.pdf",
               "kneeboard": "kneeboards/01.zip" },
    "requires": { "modules": ["F-4E"] } }
]
```

`n` orders the list and **MUST** be unique within a pack. A missing `n` sorts
after every present one, in array order. An entry whose `files.mission` does
not exist in the archive **MUST** be dropped by the reader, not served.

Format 1 called this `events` and used a flat `miz`/`brief_pdf` pair. Both
spellings are accepted on read (§4).

### 2.8 `docs` — pack-level documents

```jsonc
"docs": { "guide": "guide/syllabus.pdf", "readme": "READ_ME_FIRST.md" }
```

Keys are free-form; `guide` and `readme` are conventional and get first-class
buttons. A value pointing at a file not in the archive **MUST** be dropped.

### 2.9 `files` and `digest` — integrity

```jsonc
"files": [
  { "path": "missions/01_pp_1_drag.miz", "bytes": 1079233, "sha256": "…" }
],
"digest": "sha256:…"
```

`files` **SHOULD** list every regular file in the archive except `pack.json`
itself. `digest` is computed over the manifest's own file list, so it is
stable regardless of ZIP ordering, timestamps or compression:

```
digest = sha256( "\n".join(f"{path}\x00{sha256}" for path,sha256 in sorted(files by path)) )
```

**Reader obligations:**

- If `files` is present, a reader **MUST** verify every listed file's `sha256`
  at install time and **MUST** refuse the pack if any differ. A truncated
  upload is a corrupt pack, and serving a `.miz` that DCS silently fails to
  open is the worst possible outcome.
- If `digest` is present, a reader **MUST** recompute it from `files` and
  refuse the pack on mismatch.
- A file present in the archive but absent from `files` is **allowed** and is
  served normally. Additive manifests must not be made impossible by strict
  readers.
- If `files` is absent entirely, the reader computes it (§5) and the pack
  becomes self-describing from then on.

### 2.10 `signature` — optional

```jsonc
"signature": { "alg": "ed25519", "key_id": "…", "sig": "base64…" }
```

Signs `digest`, nothing else. A reader **MUST** treat an absent signature as
"unsigned", not as "invalid", and **MUST** treat a *present but wrong*
signature as a hard failure. Unsigned packs remain installable; how much a
reader trusts them is policy, not format.

---

## 3. Compatibility — the promises

These are the rules that make the format safe to publish. They are tested, not
merely stated.

1. **Unknown fields survive.** A reader **MUST** preserve fields it does not
   understand when it rewrites a manifest. A pack that round-trips through an
   older reader must not lose the newer reader's data.
2. **A higher `format` fails with a sentence, not a stack trace.** A reader
   encountering `format: 3` **MUST** refuse the pack and say so in words a
   person can act on ("this pack needs a newer Sortie Starter"). It **MUST
   NOT** guess.
3. **A lower `format` is upgraded on read, never on disk-in-place.** Format 1
   manifests are read as format 1 and normalised to the current in-memory
   shape. Nothing rewrites an author's file without being asked.
4. **Missing is not invalid.** Every field outside §2.1 is optional forever. A
   future version may add fields; it may not make an existing optional field
   required.

   **Optionality is per-kind.** A field a kind depends on (a `course`'s
   `schools`, a `theater`'s `theater.map`) is required only of packs declaring
   that kind, and only from the format that introduced the kind. This is not a
   loophole in rule 4: no pack that was valid before becomes invalid, because
   the kinds carrying those requirements did not exist before. **`missions`
   gains no new required field, ever** — that is the promise rule 4 is actually
   making, and the one strangers' files depend on.
5. **`id` and `format` are the only things a reader may rely on before
   validating.** Everything else is read after path checks.
6. **Extensions go in `x_`.** A field beginning `x_` is reserved for
   third-party use and will never be assigned meaning by this specification.

---

## 4. Reading format 1

Format 1 is what shipped before this document. It had no `format` key.

| Format 1 | Format 2 |
|---|---|
| *(absent)* | `format: 2` |
| `events[]` | `syllabus[]` |
| `events[].miz` | `syllabus[].files.mission` |
| `events[].brief_pdf` | `syllabus[].files.brief` |
| `role`, `threat`, `players`, `premise`, `image`, `eras`, `maps` at top level | inside `library` |
| `module: "F-4E"` (display string) | `requires.modules: ["F-4E"]` |
| *(none)* | `version`, `built_with`, `files`, `digest`, `signature` |

A manifest with no `format` key **MUST** be read as format 1. Both spellings are
accepted on read at every level, so a format 1 pack installs unchanged and a
hand-edited hybrid works.

---

## 5. Deriving a manifest

A reader **MUST** be able to install an archive with no `pack.json` at all, or
one containing only `id` and `label`. This is the property that makes the
format usable by someone who has never read this document: drop a folder of
`.miz` files in and get a working pack.

Derivation rules:

- Every `.miz`, sorted by path, becomes a `syllabus` entry with `n` in order.
- A `.pdf` sharing a number with a mission (`AWI_07.miz` ↔ `Brief_07.pdf`) or
  containing the mission's stem becomes that entry's `brief`.
- Unpaired PDFs whose names contain `guide` or `read`/`first` become
  `docs.guide` / `docs.readme`.
- The first image becomes `library.image`.
- `requires.terrains` is read from the first mission's `theatre`;
  `requires.modules` from its player aircraft.
- `files` and `digest` are computed from the archive.
- The result is marked `"derived": true` so a UI can say "auto-detected".

Derivation **MUST NOT** overwrite anything the author supplied. An
author-provided field always wins; derivation fills gaps.

**Derivation only ever produces a `missions` pack.** A reader **MUST NOT**
infer any other `kind` from an archive's contents. A folder of PDFs is a
mission pack with no missions and some documents — not a `reference` pack —
because guessing wrong about kind means guessing wrong about which subsystem
consumes the payload. The other three kinds are things an author declares on
purpose; only `missions` is something you can fall into by dropping a folder,
and that is the one case worth the convenience.

---

## 6. What a reader must reject

Only these. Everything else is a gap to be filled, not an error.

1. A path failing §1.1.
2. `format` greater than the reader supports.
3. A `sha256` in `files` that does not match the archive.
4. A `digest` that does not match `files`.
5. A `signature` that is present and does not verify.
6. An archive with an **empty payload for its kind**: a `missions` pack with no
   missions and no documents, a `course` with no units, a `reference` with no
   documents, a `theater` with no data files. There is nothing to publish.
7. An unrecognised `kind` (§2.2).
8. A `kind` other than `missions` at `format` below 3 (§2.2).
9. A `theater` pack failing the trust or schema rules of §10 — the only kind a
   reader refuses on the strength of *where it came from* rather than what is
   in it.

A pack that is merely *odd* — no manifest, unknown role, missing artwork,
paths that do not follow convention — installs.

Note the shape of rules 6–9: everything that was permissive about mission packs
stays permissive, and the new strictness applies only to the kinds that did not
exist before. No pack that installs today stops installing.

---

## 7. `course` packs

A course is a **curriculum**: an ordered path through content, with standards, a
gradesheet and a pilot's progress record. It is a work of authorship whose
material is somebody else's bytes.

**A course pack carries no missions.** It cites them. This is the whole reason
`course` is a separate kind rather than a flag on a mission pack: one ride,
published once, may be cited by an F-4E course and an F-16 course without
shipping twice or diverging.

```jsonc
{
  "format": 3,
  "kind": "course",
  "id": "f4e_pipeline",
  "version": "1.0.0",
  "label": "F-4E Phantom II — Learn it, fly it, fight it",

  "requires": {
    "packs":    [{ "id": "wk_squadron_checkout", "min_version": "1.0.0" }],
    "modules":  ["F-4E"],
    "terrains": ["germany", "sinai"]
  },

  "schools": [
    { "id": "upt", "label": "Ground School and UPT", "tagline": "Fly an airplane.",
      "units": [
        { "kind": "reading", "id": "howto", "doc": "readings/pipeline_howto.md" },
        { "kind": "card",    "id": "form_route",
          "pack": "ss_sampler", "ride": "form_route" },
        { "kind": "track",   "id": "timing",
          "pack": "wk_squadron_checkout", "from": 1, "to": 5, "check": true },
        { "kind": "planned", "id": "inst",
          "label": "Instrument recovery — TACAN penetration and ILS",
          "why": "needs an approach-quality glidepath the Mission Editor cannot see" }
      ] }
  ],

  "docs": { "program": "guide/f4e-pipeline.pdf" }
}
```

### 7.1 `requires.packs` — floating, not pinned

Each entry is `{ "id": …, "min_version": … }`. A course takes **any** installed
version of a cited pack at or above `min_version`.

A course **MUST NOT** pin an exact content version. Pinning is superficially
attractive — it is reproducible — and it is wrong here: correcting one typo in
a widely-cited mission pack would require republishing every course that names
it. That cascade is how content systems calcify. Provenance is `built_with`'s
job (§2.5), and it does that job without a cascade.

### 7.2 Units

A unit is one of four kinds, mirroring what the runtime already resolves:

| `kind` | Cites | Additional fields |
|---|---|---|
| `card` | one ride in a `missions` pack | `pack`, `ride` |
| `track` | a run of rides in a `missions` pack | `pack`, `from`, `to`, `check` |
| `reading` | a document, in this pack or a `reference` pack | `doc`, or `pack` + `doc` |
| `planned` | nothing — it does not exist yet | `label`, `why` |

`planned` is not a placeholder for lazy authoring. It is how a curriculum states
a gap honestly, and it is load-bearing for §7.4.

### 7.3 Unit ids are a permanent promise

**A reader stores a pilot's progress against `units[].id`.** That record is
local to the pilot's browser, by design — no accounts, nothing server-side —
which means there is no server copy to migrate and no way to detect the damage
after the fact.

Therefore, within one course `id`:

- A unit `id` **MUST NOT** be reused for different material.
- A renamed unit is a **new** unit; the old id has been deleted and every pilot
  who completed it loses that tick, silently.
- Ids **SHOULD** be treated as append-only across versions.
- A producer **SHOULD** assert that no unit id present in version *n* has
  vanished in version *n+1* without a deliberate note.

This is cheap to state now and impossible to retrofit once other people are
publishing courses.

### 7.4 Unresolvable units degrade; they do not fail

A course whose cited pack is not installed is **not an error**. A pilot who has
a course and not its missions is an ordinary Tuesday, and the case gets more
ordinary the moment courses and missions are published separately.

A reader:

- **MUST NOT** refuse to install a course because a cited pack is absent;
- **MUST NOT** raise, or return an error status, when rendering it;
- **MUST** present an unresolvable unit as `planned`, carrying a `why` that
  names the missing pack;
- **SHOULD** distinguish `status: "planned"` (does not exist yet) from
  `status: "unavailable"` (exists, not installed) so it can offer the second
  one a way to get the pack and say nothing about the first.

To a pilot the two render alike and both are honest. The distinction exists so
the application can act on one of them.

---

## 8. `reference` packs

Documents, and nothing else: readings, study sets, scanned diagrams, printed
guides, checklists.

```jsonc
{
  "format": 3,
  "kind": "reference",
  "id": "f4e_aar_study",
  "version": "1.0.0",
  "label": "Air-to-air refuelling — the F-4E study set",
  "docs": {
    "index":    "READ_ME_FIRST.md",
    "boom":     "readings/boom-technique.md",
    "to_1f4e1": "documents/TO-1F-4E-1-extract.pdf"
  },
  "requires": { "modules": [] }
}
```

- A `reference` pack **MUST NOT** contain `.miz` files. If it has missions it is
  a `missions` pack with documents, which is already supported and is the right
  answer.
- `docs` keys are free-form. `index` is conventional and gets first billing.
- A `course` unit of kind `reading` **MAY** cite `{ "pack": …, "doc": … }` to
  reach a document in a reference pack, subject to §7.1 and §7.4.

**Why this is a kind and not a rounding error.** The product rule settled at
v1.104.1 — *training teaches only what the mission can measure, and only what
unlocks a sortie you could not otherwise fly; everything else is reference, not
coaching* — routes rejected ideas to a cheap channel instead of killing them.
That rule only holds if the channel is genuinely cheap. While a reading is a
markdown file inside `missiongen/`, adding one is a code deploy, and the "cheap"
option costs a release. A `reference` pack makes it an upload. **The format
exists to make the product rule the path of least resistance.**

---

## 9. `theater` packs

Data the **generator consumes**: published corridors, historical airspace,
gates, chart specifications — the material that today lives in
`missiongen/data/` and can only change by shipping the application.

```jsonc
{
  "format": 3,
  "kind": "theater",
  "id": "corridors_kola",
  "version": "1.0.0",
  "label": "Kola — Northern Fleet corridors, 1985",

  "theater": {
    "map": "kola",                       // exactly one map
    "provides": ["corridors"],           // corridors | airspace | parking | chart
    "eras": ["coldwar"],
    "schema": 1                          // the DATA schema version, not the pack format
  },

  "data": { "corridors": "data/corridors/kola.json" },
  "docs": { "sources": "SOURCES.md" }
}
```

### 9.1 Why this one is different

Every other kind is **output** — bytes the generator made, or inert documents.
Installing a bad one produces a bad download for the person who installed it,
and uninstalling it ends the problem.

A theater pack is **input**. It changes what the generator makes, on that map,
for every mission anyone builds afterwards. Two consequences follow, and both
are normative:

**(a) Determinism.** The product's first invariant is *same recipe + seed =
byte-identical mission, forever*, and share links depend on it. A theater pack
changes generated output, so a mission generated with one installed is not
reproducible by a reader without it.

- A generator **MUST** record every applied theater pack's `id` and `version` in
  the recipe, and therefore in the share link.
- A reader resolving a share link that names a theater pack it does not have
  **MUST** say so rather than silently generating a different mission.
- Bumping a theater pack's `version` **MUST** be treated as changing generated
  output, even when the author believes the change is cosmetic.

**(b) Trust.** A stranger's mission pack is a download. A stranger's theater
pack is code-adjacent: it steers routes, gates and airspace for everyone using
that map.

- A theater pack **MUST** be either signed by a trusted key (§2.10) or installed
  through an authenticated owner session. Anonymous upload of a theater pack
  **MUST** be refused.
- A theater pack **MUST** validate against the published schema named by
  `theater.schema` before any part of it is applied. Partial application is
  forbidden: it applies whole or not at all.
- A reader **MUST NOT** apply a theater pack to any map other than the single
  one named in `theater.map`.
- Uninstalling a theater pack **MUST** restore the built-in data for that map,
  with no residue.

### 9.2 Why it is worth the extra rules

Ten of the product's thirteen maps have no published corridors. The three that
do — Nevada, Syria, Germany — each cost a full release: research, a data file, a
chart, documentation, the release gate, a deploy. Nothing in that sequence
needed a code change; it was data, gated behind a code path.

`theater` is the kind that converts that recurring release into an upload. It
carries the strictest rules in this document precisely because it is the only
kind that can change what the machine makes.

---

## 10. Trust model — summary

| Kind | Anonymous upload | Signature | Schema-validated | Affects others' output |
|---|---|---|---|---|
| `missions` | allowed | optional | no | no |
| `course` | allowed | optional | manifest only | no |
| `reference` | allowed | optional | manifest only | no |
| `theater` | **refused** | **required unless owner-installed** | **required** | **yes** |

The rule behind the table: **a pack that only the installer can be harmed by is
open; a pack that changes what the generator produces is gated.** Nothing about
the container, the manifest, the integrity model or the upload path differs
between them — one door, four kinds, and the trust bar set by consequence
rather than by category.

---

## 11. Authoring — how to build each kind

Normative rules are above; this section is the practical route through them. Every
skeleton here is a complete, valid manifest: copy one, change the strings, zip
the folder, upload it.

**The two rules worth remembering before you start.** Only `pack.json` must be
at a fixed place — every other path is whatever your manifest says it is. And
`id` is forever: it is how the system knows an update is an update rather than a
new pack, so choose it once and never reuse it for different material.

### 11.1 A mission pack

The common case, and the only kind you can produce without reading anything: put
`.miz` files in a folder, zip it, upload it. The reader derives a manifest (§5)
and you get a working Library card. Everything below is refinement.

```
my-pack/
  pack.json
  missions/01_opening_cap.miz
  briefs/01_opening_cap.pdf
  card.png
```

```json
{
  "format": 2,
  "id": "desert_storm_f14",
  "label": "Desert Storm — Tomcats over Iraq",
  "version": "1.0.0",
  "author": "Your Name",
  "license": "CC-BY-4.0",
  "requires": { "terrains": ["iraq"], "modules": ["F-14A/B — Tomcat"] },
  "library": {
    "role": "strike", "threat": 4, "players": "SP",
    "premise": "One or two sentences a pilot reads on the card.",
    "image": "card.png", "eras": ["modern"], "maps": ["iraq"]
  },
  "syllabus": [
    { "n": 1, "id": "ds_1_cap", "label": "Opening Night CAP",
      "files": { "mission": "missions/01_opening_cap.miz",
                 "brief":   "briefs/01_opening_cap.pdf" } }
  ]
}
```

Spend your effort on `requires` and on each `premise`. `requires` is what stops
a pilot downloading eleven missions for a terrain he does not own; the premises
are the whole card.

### 11.2 A course pack

A curriculum. It contains **no missions** — it cites them from mission packs
that are published separately, which is what lets one ride serve several
courses.

```
my-course/
  pack.json
  readings/how-this-works.md
  guide/program.pdf
```

```json
{
  "format": 3,
  "kind": "course",
  "id": "f14_workup",
  "label": "F-14 Workup — nugget to section lead",
  "version": "1.0.0",
  "requires": {
    "packs": [{ "id": "desert_storm_f14", "min_version": "1.0.0" }],
    "modules": ["F-14A/B — Tomcat"]
  },
  "schools": [
    { "id": "basics", "label": "Airmanship", "tagline": "Fly the airplane.",
      "units": [
        { "kind": "reading", "id": "intro", "doc": "readings/how-this-works.md" },
        { "kind": "card", "id": "first_cap",
          "pack": "desert_storm_f14", "ride": "ds_1_cap" },
        { "kind": "planned", "id": "night_traps",
          "label": "Night traps",
          "why": "not written yet" }
      ] }
  ],
  "docs": { "program": "guide/program.pdf" }
}
```

Three things that will bite you if you skip them:

1. **Never renumber or rename a unit `id`.** Progress lives in each pilot's
   browser, keyed on that id. Rename one and every pilot who finished it loses
   the tick, silently, with no way to get it back (§7.3).
2. **Cite with `min_version`, never an exact version** (§7.1). Pin it and every
   typo fix in the mission pack forces you to republish the course.
3. **Use `planned` honestly.** A course that names a gap and says why reads as
   authored. One that quietly omits it reads as finished and disappoints.

A course whose cited pack is not installed still works — the units it cannot
resolve show as planned, with a note naming the missing pack (§7.4). You do not
have to ship them together.

### 11.3 A reference pack

Documents, nothing else. Readings, study sets, scanned diagrams, checklists.
The cheapest thing to publish and the easiest to keep current.

```
my-reference/
  pack.json
  READ_ME_FIRST.md
  readings/boom-technique.md
  documents/extract.pdf
```

```json
{
  "format": 3,
  "kind": "reference",
  "id": "aar_study_set",
  "label": "Air-to-air refuelling — a study set",
  "version": "1.0.0",
  "docs": {
    "index": "READ_ME_FIRST.md",
    "boom":  "readings/boom-technique.md",
    "manual": "documents/extract.pdf"
  }
}
```

No `.miz` files (§8). If you have missions and documents, that is a mission pack
with documents, which is §11.1.

A course reaches a document here with a `reading` unit naming both:
`{ "kind": "reading", "id": "boom", "pack": "aar_study_set", "doc": "boom" }`.

### 11.4 A theater pack

Data the generator consumes — published corridors and airspace for one map.
**This is the one kind that changes what the application produces**, so it
carries rules the others do not (§9, §10): it must be signed or installed by the
owner, it must validate against the data schema, it applies whole or not at all,
and it touches exactly the one map it names.

```
my-theater/
  pack.json
  data/corridors/kola.json
  SOURCES.md
```

```json
{
  "format": 3,
  "kind": "theater",
  "id": "corridors_kola",
  "label": "Kola — Northern Fleet corridors, 1985",
  "version": "1.0.0",
  "theater": {
    "map": "kola",
    "provides": ["corridors"],
    "eras": ["coldwar"],
    "schema": 1
  },
  "data": { "corridors": "data/corridors/kola.json" },
  "docs": { "sources": "SOURCES.md" }
}
```

Two obligations that are yours rather than the format's:

- **Cite your sources.** A corridor a pilot flies is a claim about the real
  world. `docs.sources` is conventional and the product's own theater data is
  held to it.
- **Treat every version bump as changing generated output**, even a cosmetic
  one. Missions built against your pack record its `id` and `version` in the
  share link, and a pilot resolving that link without your pack is told so
  rather than quietly given a different mission (§9.1).

### 11.5 Before you upload

- Does `pack.json` parse as JSON, with no comments and no trailing commas?
- Does every path in the manifest exist in the archive, spelled identically?
- Is `id` new, or deliberately the same as the pack you are updating — with a
  higher `version`?
- Non-`missions` kinds: is `format` set to `3`?
- Course packs: has any unit `id` changed since the last version?
- Theater packs: is it signed, or are you the owner installing it?

A pack that is merely odd — no manifest, unknown role, missing artwork, unusual
paths — installs (§6). The refusals are the short list in §6, and each one names
what is wrong.
