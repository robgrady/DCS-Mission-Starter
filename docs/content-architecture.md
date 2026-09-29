# Packaged content vs. the generator — an architecture exploration

*Written August 2026, against v1.78.1. The open decisions at the foot of this
document were settled on 18 August 2026 and are recorded there; the work is
proceeding in the four phases described.*

---

## The one number

**56 of the 90 Library templates offer the pilot no choice at all** — one era,
no aircraft options, nothing to configure. 62% of the catalog.

Those 56 are not "generator content" in any meaningful sense. They are
*published missions* that happen to be recomputed, from source, on every single
download. The White Knights are the extreme case: 22 rides whose every number
is transcribed from a 1980 squadron document, whose diagrams are scans of that
document's pages, and which are byte-identical for every person who downloads
them — reassembled from Python on demand, eleven at a time, inside an HTTP
request.

That is the whole problem in one sentence. Everything below follows from it.

---

## What exists today

Five mechanisms deliver mission bytes. They were each added for a good local
reason and nobody has ever looked at them together.

| # | Mechanism | Bytes are | Who authors | Where it lives |
|---|---|---|---|---|
| 1 | `/api/generate`, `/api/dl` | built per request (~1–3 s) | the pilot | nowhere; streamed and discarded |
| 2 | Library cards | built per request | developer, in `mission_templates.json` | repo |
| 3 | Track `all.zip` | built per request, ~31 s | developer, in `tracks.json` | repo |
| 4 | `prebuilt/` zips | built at image build | developer, derived | Docker image, 44 MB |
| 5 | Packs | **static, uploaded** | **the owner, via `/admin`** | Fly volume |
| — | `samples/` | static, committed | developer | repo, **and no endpoint serves them** |

Mechanism 5 is the one that already works the way Rob is describing. It has a
manifest, it accepts an upload, it serves bytes, it needs no deploy, and it is
the only content path in the product that a non-developer can use. It was built
for the AWI syllabus after 28 MB of committed missions made the release zip
untransferable — the lesson was already learned once, in `missiongen/packs.py`,
and then not applied to anything else.

Mechanism 4 is three days old and exists only because mechanism 3 was taking
the server down.

---

## The category error

The product treats **composition** and **distribution** as the same act.

- **Composition** is the engine: recipe → mission. Genuinely per-pilot,
  genuinely variable, about a second, and the reason this product exists.
- **Curation** is authorship: *this* syllabus, *these* eleven rides in *this*
  order, with a printed guide, a recorded voice and a scanned diagram. It is a
  work with an author's intent. It is produced *using* the generator the way a
  book is produced using a word processor.
- **Distribution** is getting bytes to a pilot.

Today curation is expressed as source code, and curated content is distributed
by re-running composition. Every symptom traces back to that:

- **The 502.** Building eleven missions in a request killed the machine. Fixed
  with a cache in the image — a workaround for doing the work at all.
- **44 MB of version-keyed zips** in the image, which have to be rebuilt and
  redeployed for a typo in a premise line.
- **Content changes need a code deploy.** The White Knights syllabus is
  `wk.py`, 2,000 lines of Python. A corrected date is a release.
- **`samples/` is a month stale, unserved, and nobody noticed** — because
  nothing in the system knows it is content.
- **Two guide mechanisms**: the AAR lanes serve committed PDFs, the White
  Knights generate theirs per request. Same artifact, two paths.
- **56 of the 60 track combinations still build in-request.** The pre-build
  covers 4. `aar_probe` alone has 48 combinations and one of them is covered.
  The landmine that produced the 502 is still armed for anyone who changes a
  tanker in the wizard.

---

## The proposal, in one line

**Promote the pack to the product's only unit of published content, make the
generator the tool that produces packs, and let the request path do nothing but
serve bytes.**

The generator does not shrink in importance — it changes job, from a
request-time renderer to the authoring tool for everything the product ships.
That is a stronger position, not a weaker one: it becomes reproducible,
diffable and testable, and it stops being on the critical path of a download.

### Three tiers, one format

| Tier | Ships in | Changing it needs | Example |
|---|---|---|---|
| ~~Bundled~~ | *tried and reversed — see the decisions below* | | |
| **Installed** | the Fly volume, via `/admin` | an upload | everything: the White Knights, AWI Basics, anything Rob makes |
| **Remote** *(later)* | a URL in a catalog | a catalog edit | community or paid packs |

One format, one manifest, one Library rendering path, three places the bytes
can come from. The Library merges all three and dedupes by `id`.

---

## The manifest

Today's `pack.json` is a Library card with an event list, and it is *derived by
regexing the .miz* when absent. That is right for "drop a folder in and it
works", and insufficient as a standard. Proposed **pack format 2**, additive so
every existing pack keeps working:

```jsonc
{
  "format": 2,                      // the SPEC version, not the content's
  "id": "wk_proud_phantom",
  "version": "1.2.0",               // the CONTENT's version, independent of the app's
  "label": "70th TFS White Knights — Proud Phantom, Egypt 1980",
  "author": "Rob Grady",
  "license": "…",

  // WHAT THE PILOT MUST OWN. Today `module` is a display string, so a pilot
  // downloads eleven Sinai missions and finds out afterwards.
  "requires": {
    "terrains": ["sinai"],
    "modules": ["F-4E"],
    "dcs_min": "2.9"
  },

  // PROVENANCE. Same discipline as every number this product prints.
  "built_with": {
    "app": "1.78.1",
    "generated": true,
    "spec": "tracks.json#wk_proud_phantom",
    "seeds": "fixed"
  },

  "library": { "role": "training", "threat": 4, "players": "SP",
               "premise": "…", "image": "card.png",
               "eras": ["coldwar"], "maps": ["sinai"] },

  // The syllabus — what `tracks.json` holds today, moved INTO the artifact.
  "syllabus": [
    { "n": 1, "id": "pp_1_drag", "label": "Tanker Drag to Egypt",
      "premise": "…",
      "files": { "mission": "missions/01_pp_1_drag.miz",
                 "brief": "briefs/01_brief.pdf" },
      "requires": { "modules": ["F-4E"] } }
  ],

  "docs": { "guide": "guide/white-knights-proud-phantom.pdf",
            "readme": "READ_ME_FIRST.md" },

  // INTEGRITY. Every file, hashed. A truncated upload is detected, not served.
  "files": [
    { "path": "missions/01_pp_1_drag.miz", "bytes": 1079233,
      "sha256": "…" }
  ],
  "digest": "sha256:…"              // over the sorted file list
}
```

Four things this buys that today's format cannot:

1. **`requires`** — the Library can say "you need the Sinai terrain" *before*
   the download, and gray out what a pilot cannot fly. This is the single most
   valuable field and it is currently a display string.
2. **`files[].sha256` + `digest`** — a pack that arrived corrupt is refused at
   install rather than serving a broken `.miz` that DCS silently fails to open.
3. **`built_with`** — a pack knows which app version and which spec produced
   it. When the generator improves, the manifest is what tells you this pack
   predates the improvement. No silent staleness.
4. **`version`, independent of the app's** — content and code stop being
   locked together. Today a fix to a premise line is a product release.

---

## The producer pipeline

```
tracks.json + mission_templates.json          →  the SPEC (authoring input)
        │
        │  scripts/build_pack.py <spec>       →  runs the generator, once
        ▼
   packs/<id>-<version>.sspack (a zip)        →  the ARTIFACT
        │
        ├─ bundled into the image / release
        ├─ uploaded through /admin
        └─ published to a URL
```

The spec stays where it is — `tracks.json` and the ride tables are good
authoring inputs and the tests around them are worth keeping. What changes is
that they stop being read at request time. `build_pack.py` is the only thing
that reads them, and it emits an artifact with a manifest.

Because seeds are fixed and the build is deterministic, **a pack build is
testable the way the cue cards now are**: rebuild it, compare the digest, and a
mismatch is either a real content change or a regression. That guard does not
exist for any of the five current mechanisms.

`.sspack` is a zip with a manifest at the root — same as today, so today's
uploads still install, and a pilot who renames it to `.zip` can open it.

---

## The hard question: 60 combinations

The two refuelling lanes are configurable by era × aircraft × tanker: **10
combinations for `aar_boom`, 48 for `aar_probe`**. Pre-building all of them is
roughly 400 MB. Pre-building one, which is what happens now, leaves 56 paths
that do the thing that killed the machine.

This is where the pack model has to be honest rather than universal. Three
options, and I would take the first:

**(a) A pack per lane at its default, and per-ride generation for everything
else.** The whole-track zip button appears only when a pack exists for that
combination. Change the tanker and the button becomes "generate each ride" —
which already exists, is one mission at a time, and is safe. The wizard stays;
the eleven-missions-in-one-request path disappears entirely.

**(b) Async job + progress.** A build queue, a job id, the browser polls.
Handles every combination, and is a real subsystem — job store, cleanup, a
spinner where there is now a link, and a new class of failure.

**(c) Pre-build everything.** 400 MB of image for downloads almost nobody
requests. No.

Option (a) is the honest one: it says out loud that a *custom* academy is a
generated thing and a *published* academy is an artifact, and it stops
pretending the two are the same product feature.

---

## Migration

Each phase is independently shippable and independently reversible.

**Phase 1 — formalise the format.** Pack format 2: `requires`, hashes,
`digest`, `version`, `built_with`. Upgrade v1 manifests on install. Nothing
else changes. *Ships alone, no user-visible change except better error
messages.*

**Phase 2 — the producer.** `scripts/build_pack.py`. Emit the two White Knights
tracks as bundled packs. The Library reads them as packs. Delete `prebuilt/`
and the in-request track build for pinned tracks. *This is the phase that pays
off the 502.*

**Phase 3 — the lanes.** Ship a pack per AAR lane default; switch custom
combinations to per-ride generation; retire `_track_zip_path` entirely.

**Phase 4 — the catalog.** `samples/` becomes a real "Sampler" pack that is
actually served. Optionally: remote packs by URL, and signing.

---

## What this costs, and what we lose

Stated plainly, because the argument is weaker if the costs are hidden:

- **A generator improvement no longer silently improves shipped content.** A
  better loadout rule reaches published packs only when they are rebuilt and
  republished. That is *reproducibility* — you can tell exactly what a pilot
  has — and it is also a step somebody has to remember. Mitigation: the
  artifacts registry already blocks a release on stale derived files; packs go
  in it.
- **Bundled packs grow the image and the release zip.** The two White Knights
  packs are ~31 MB. Mitigation: bundle only those, and only because they are
  the product's flagship content; everything else is installed or remote.
- **Two places a syllabus could be described** — `tracks.json` and the pack
  manifest. This is the twin-function shape that has already cost this codebase
  two live defects. Mitigation is non-negotiable: `tracks.json` is the *spec*,
  the manifest is *generated from it*, and the runtime reads **only** the
  manifest. Never both.
- **Version skew.** A pack built by 1.78 served by 1.90. The manifest carries
  `built_with`; the UI can say so; nothing is silently rebuilt.

---

## What I would not change

- **The generator stays, and stays first-class.** Fly Now, the Builder and
  share links are per-pilot by nature, cheap, and the product's actual
  differentiator. None of this touches them.
- **`mission_templates.json` stays as the spec** for standalone cards. A card
  that genuinely offers era and aircraft choices should keep generating — there
  are 34 of those and they are the ones the generator is *for*.
- **The upload path stays exactly as friendly as it is.** Dropping a bare
  folder of `.miz` files and getting a working Library card is the best thing
  about the current pack system. Format 2 must not make a manifest mandatory.

---

## Decisions — settled 18 August 2026

1. ~~**Bundled.**~~ **Reversed on 19 August 2026, after one release.**
   Bundling was tried: the image gained 44 MB and the release zip reached
   59 MB, large enough that it could no longer be handed over an ordinary
   channel. The deciding argument was not the size, though — it was the
   coupling. Content welded into an image can only change by deploying, and
   the whole point of the pack model is that a corrected premise line is not a
   deploy.

   **The product now ships THIN.** No packs in the image, none in the release
   zip, none in git. `scripts/build_pack.py` produces a `.sspack`; it is
   uploaded through `/admin` like any other pack. There is exactly one storage
   tier — the volume — and the flagship syllabi go through the same door as
   everybody else's content, which is the strongest possible test of that
   door.

   The cost is real and is accepted: a fresh deploy comes up with an empty
   Library until the packs are uploaded. That is why the whole-syllabus button
   is now gated on publication rather than assuming content exists.
2. **Content versions independently of the app.** A corrected premise line is a
   pack republish, not a product release. `built_with.app` records which
   version produced the bytes, so nothing is ambiguous about what a pilot has.
3. **The format is PUBLIC and portable from day one.** A `.sspack` is a file
   somebody can hand to a friend, publish, or eventually sell. That is a
   commitment to strangers' files, and it raises the bar in three specific
   ways, all of which are now requirements rather than nice-to-haves:
   - a **normative specification** (`docs/PACK_FORMAT.md`) that the code
     implements rather than defines;
   - **forward compatibility rules** that are written down and tested — an
     unknown field must survive a round trip, and a future `format` number must
     fail with an explanation rather than a stack trace;
   - **signing**, because a public format means packs that did not come from
     us. `digest` is the thing signed.
4. **All four phases.** In order, each independently shippable.
