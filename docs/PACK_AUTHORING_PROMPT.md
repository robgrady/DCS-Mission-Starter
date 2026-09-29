# How to build a Sortie Starter mission pack (`.sspack`)

> **What this document is.** Drop-in instructions for an AI assistant (or a
> person). Paste this whole file into any AI's prompt and it will know how to
> package DCS World missions into a `.sspack` that Sortie Starter installs
> cleanly. It is a condensed, action-oriented version of the normative spec
> (`PACK_FORMAT.md`, format 2); where the two disagree, the spec wins.

You are producing a **mission pack**: a ZIP archive containing DCS missions,
their documents, and a manifest that says what is inside, what a pilot must
own to fly it, and how it was made.

---

## 1. The container

Produce a **ZIP archive** with the extension `.sspack` (`.zip` also works —
the extension carries no meaning). Conventional layout:

```
pack.json                  the manifest — REQUIRED, at the archive root
missions/01_<id>.miz       the missions, numbered in flying order
briefs/01_<id>_brief.pdf   per-mission briefing documents (optional)
guide/<name>.pdf           pack-level documents (optional)
card.png                   Library card artwork (optional)
READ_ME_FIRST.md           readme (optional)
```

Only `pack.json` is required at a fixed place. **Paths written in the manifest
are the truth** — the folder names are convention, not rules.

Path rules — the installer refuses the whole archive on any violation:

- No absolute paths, no drive letters, no leading `/`.
- No `..` segments anywhere.
- No symlinks, no NUL bytes in names.
- (`__MACOSX/` and `._*` junk is ignored, but do not produce it.)

Use forward slashes. One optional wrapper directory around everything is
tolerated; producing none is cleaner.

## 2. The manifest — `pack.json`

UTF-8 JSON at the archive root. **No comments in the real file.** Three fields
are required; everything else is optional but valuable.

```json
{
  "format": 2,
  "id": "desert_storm_f14",
  "label": "Desert Storm — Tomcats over Iraq",

  "version": "1.0.0",
  "author": "Your Name",
  "license": "CC-BY-4.0",

  "requires": {
    "terrains": ["iraq"],
    "terrain_names": ["Iraq"],
    "modules": ["F-14A/B — Tomcat"],
    "dcs_min": "2.9"
  },

  "built_with": {
    "app": "hand-authored",
    "generated": false,
    "built_at": "2026-08-19"
  },

  "library": {
    "role": "strike",
    "threat": 4,
    "players": "SP",
    "premise": "One or two sentences a pilot reads on the card. What this is, and why it matters.",
    "image": "card.png",
    "eras": ["modern"],
    "maps": ["iraq"]
  },

  "syllabus": [
    {
      "n": 1,
      "id": "ds_1_cap",
      "label": "Opening Night CAP",
      "premise": "One line: what this mission is.",
      "files": {
        "mission": "missions/01_ds_1_cap.miz",
        "brief": "briefs/01_ds_1_cap_brief.pdf"
      }
    },
    {
      "n": 2,
      "id": "ds_2_strike",
      "label": "Bridge Strike, Day Two",
      "premise": "…",
      "files": { "mission": "missions/02_ds_2_strike.miz" }
    }
  ],

  "docs": {
    "guide": "guide/campaign_guide.pdf",
    "readme": "READ_ME_FIRST.md"
  },

  "files": [
    { "path": "missions/01_ds_1_cap.miz", "bytes": 1079233, "sha256": "<hex>" }
  ],
  "digest": "sha256:<hex>"
}
```

Field rules that matter:

- **`format`** — always the integer `2`.
- **`id`** — `[a-z0-9_]`, max 64 chars, stable across versions. Two packs with
  the same `id` are the same pack at different versions; the higher `version`
  wins on install. Never reuse an `id` for different content.
- **`label`** — the human name shown in the Library.
- **`version`** — semantic version **of the content**, not of any app.
  Correcting one premise line = `1.0.1`. Changed missions = minor or major.
- **`requires`** — the most valuable block in the format. `terrains` are
  terrain keys (`sinai`, `caucasus`, `iraq`, …); `terrain_names` the names a
  pilot can buy ("Sinai"); `modules` the aircraft as the DCS store names them
  ("F-4E-45MC — Phantom II", not an internal key). Without this block a pilot
  downloads eleven Sinai missions and finds out afterwards he does not own
  Sinai. A syllabus entry may carry its own `requires`; it is additive.
- **`library.role`** — one of `training | a2a | strike | sead | cas | carrier |
  historic`. `threat` is 1–5. `players` is `SP`, `MP`, or `SP·MP`.
- **`syllabus[].n`** — orders the list and MUST be unique inside the pack.
  Every `files.mission` must exist in the archive; an entry pointing at a
  missing file is dropped by the reader, not served.
- **`docs`** — keys are free-form; `guide` and `readme` get first-class
  download buttons.
- **Custom data** — put anything of your own under keys starting `x_`
  (e.g. `"x_discord": "…"`). They are preserved forever and never assigned
  meaning by the format.

## 3. Integrity — `files` and `digest`

List every regular file in the archive **except `pack.json` itself** in
`files`, each with its byte size and SHA-256 (lowercase hex). Then compute the
pack digest **over the manifest's own file list** — not over the ZIP — so it
is stable regardless of ZIP ordering, timestamps, or compression:

```python
import hashlib, json, pathlib

def build_integrity(root: pathlib.Path, manifest: dict) -> None:
    rows = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "pack.json":
            rel = p.relative_to(root).as_posix()
            data = p.read_bytes()
            rows.append({"path": rel, "bytes": len(data),
                         "sha256": hashlib.sha256(data).hexdigest()})
    manifest["files"] = rows
    joined = "\n".join(f"{r['path']}\x00{r['sha256']}"
                       for r in sorted(rows, key=lambda r: r["path"]))
    manifest["digest"] = "sha256:" + hashlib.sha256(
        joined.encode("utf-8")).hexdigest()
```

The installer verifies every hash and refuses the pack on any mismatch — a
truncated upload must fail at install, not when DCS silently declines to open
a `.miz`. If you cannot compute hashes, **omit `files` and `digest` entirely**
(the reader derives them); never write placeholder or guessed values.

## 4. What you may omit

The format is forgiving by design. A manifest with only `format`, `id`, and
`label` is valid — the reader derives the rest by scanning the archive:
missions become syllabus entries in path order, a PDF sharing a mission's
number becomes its brief, a PDF named like a guide/readme becomes a doc, the
first image becomes the card, and `requires` is read out of the first
mission's theatre and player aircraft. **Anything you write wins over
derivation** — so write the fields you know and leave gaps rather than
guessing.

## 5. What gets a pack rejected

Only these; everything else installs:

1. A path violating §1 (absolute, `..`, symlink, NUL).
2. `format` greater than 2.
3. A `sha256` in `files` that does not match the archive.
4. A `digest` that does not match `files`.
5. A `signature` that is present and does not verify (omit the field —
   unsigned is fine; wrong is fatal).
6. An archive with no missions and no documents at all.

## 6. Build procedure

1. Collect the `.miz` files. Name them `NN_<id>.miz`, numbered in flying
   order. Confirm each opens in DCS.
2. Collect documents: per-mission briefs, a pack guide, a readme, card art.
3. Write `pack.json` per §2. Set `requires` by opening one mission and reading
   its theatre and player aircraft — do not guess.
4. Compute `files` + `digest` per §3 (or omit both).
5. Zip everything with `pack.json` at the root. Forward slashes. Name it
   `<id>.sspack`.
6. Validate before shipping:
   - `pack.json` parses as JSON, `format` is `2`, `id` matches
     `[a-z0-9_]{1,64}`.
   - Every `syllabus[].files.*` and `docs.*` path exists in the archive.
   - `syllabus[].n` values are unique.
   - Re-run the digest computation and compare.
7. Upload at the server's `/admin` → Mission packs. A review page follows the
   upload; the pack appears in the Library once installed.

## 7. Style, for packs worth flying

- **The card must not promise what the mission lacks.** If the premise says
  "flown from Cairo West", the mission must start at Cairo West. Every claim in
  a label, premise, or brief should be checkable inside the `.miz`.
- One line of `premise` per mission: what it is and why it matters, in the
  voice of the era. No filler.
- `version` bumps with content honesty: patch for words, minor for added
  missions, major when existing missions change enough that a pilot's notes
  stop being true.
