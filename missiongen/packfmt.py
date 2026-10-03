"""The pack format — the implementation of `docs/PACK_FORMAT.md`.

THAT DOCUMENT IS NORMATIVE AND THIS FILE IS NOT. The format is public: a
`.sspack` is a file somebody can hand to a friend, publish, or sell, and it may
arrive from someone who has never seen this repository. When the spec and this
module disagree, the spec is right and this module has a bug. Every section
reference below (§2.8, §5, ...) points at the paragraph this code implements.

WHY THIS IS A SEPARATE MODULE FROM `packs.py`
---------------------------------------------
`packs.py` is STORAGE — where installed packs live on a volume, how they are
written, deleted and served. This is FORMAT — what a pack is, what a reader
must accept, and what it must refuse. They were one file, and that is fine
while there is exactly one producer and one consumer; it stops being fine the
moment the format is something other people write against.

Splitting them also makes the format testable without touching a disk, which is
what lets the compatibility promises in §3 be tested rather than merely stated.

THE ONE-DIRECTION RULE
----------------------
The stored manifest is ALWAYS format 2. `card_view()` projects it into the
older flat shape the Library UI still reads. That projection is derived, never
stored, and never read back — two shapes on disk is the twin-source problem
that has already cost this codebase two live defects.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

FORMAT = 2                      # the version of the SPEC this module implements

ROLES = ("training", "a2a", "strike", "sead", "cas", "carrier", "historic")

# §2.1 — the only characters an id may contain.
_ID_RE = re.compile(r"[^a-z0-9]+")

_THEATRE_MAP = {
    "Nevada": "nevada", "Caucasus": "caucasus", "PersianGulf": "persiangulf",
    "Syria": "syria", "Normandy": "normandy", "TheChannel": "thechannel",
    "MarianaIslands": "marianas", "SinaiMap": "sinai", "Kola": "kola",
    "Afghanistan": "afghanistan", "GermanyCW": "germany",
    "Falklands": "falklands",
}


class PackError(ValueError):
    """A pack a reader must refuse (§6), with a sentence a person can act on.

    Every message here is written for the pilot or the owner uploading the
    file, not for a log. "This pack needs a newer Sortie Starter" is actionable;
    a KeyError is not.
    """


def slug(s: str) -> str:
    return _ID_RE.sub("_", (s or "pack").lower()).strip("_") or "pack"


# --------------------------------------------------------------------------- #
# §1.1 path rules
# --------------------------------------------------------------------------- #
def safe_members(zf: zipfile.ZipFile) -> list:
    """[(ZipInfo, normalised name)] for members a reader may extract.

    REFUSING RATHER THAN SANITISING. A path with `..` in it is not a typo to be
    cleaned up, it is an archive trying to write outside its own directory, and
    the honest response is to drop it on the floor.
    """
    out = []
    for i in zf.infolist():
        if i.is_dir():
            continue
        n = i.filename.replace("\\", "/")
        if n.startswith("/") or ".." in n.split("/") or "\x00" in n:
            continue
        if "__MACOSX" in n or Path(n).name.startswith("._"):
            continue
        if re.match(r"^[A-Za-z]:", n):          # drive letters
            continue
        # symlinks and other non-regular entries live in the high bits of
        # external_attr; a symlink whose target is /etc/passwd is the whole
        # reason this check exists.
        if (i.external_attr >> 16) & 0o170000 == 0o120000:
            continue
        out.append((i, n))
    return out


def read_archive(data: bytes) -> dict:
    """{path: bytes} from a .sspack/.zip, with a single wrapper dir stripped."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise PackError("That file is not a readable .zip or .sspack.")
    members = safe_members(zf)
    if not members:
        raise PackError("The archive is empty, or every path in it was unsafe.")
    tops = {n.split("/")[0] for _i, n in members if "/" in n}
    strip = len(tops) == 1 and all("/" in n for _i, n in members)
    files = {}
    for i, n in members:
        key = n.split("/", 1)[1] if strip else n
        if key:
            files[key] = zf.read(i)
    return files


# --------------------------------------------------------------------------- #
# §2.8 integrity
# --------------------------------------------------------------------------- #
def file_list(files: dict) -> list:
    """The `files` array: every regular file except the manifest itself."""
    return [{"path": p, "bytes": len(b),
             "sha256": hashlib.sha256(b).hexdigest()}
            for p, b in sorted(files.items())
            if p not in ("pack.json", "manifest.json")]


def digest_of(file_list_: list) -> str:
    """§2.8. Over the MANIFEST'S list, not over the archive.

    Deliberately independent of zip ordering, timestamps and compression, so
    the same content produces the same digest whoever zipped it and with which
    tool. A digest that changed when you re-zipped an unchanged folder would be
    a digest nobody could use.
    """
    body = "\n".join(f"{e['path']}\x00{e['sha256']}"
                     for e in sorted(file_list_, key=lambda e: e["path"]))
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def verify(man: dict, files: dict) -> None:
    """§2.8 + §6. Raises PackError on anything a reader must refuse."""
    listed = man.get("files")
    if listed:
        have = {p: hashlib.sha256(b).hexdigest() for p, b in files.items()}
        for e in listed:
            p, want = e.get("path"), e.get("sha256")
            if not p or not want:
                continue
            if p not in have:
                raise PackError(
                    f"The manifest lists “{p}” but the archive does not "
                    f"contain it. The pack is incomplete.")
            if have[p] != want:
                raise PackError(
                    f"“{p}” does not match its checksum. The pack is corrupt "
                    f"— re-download or rebuild it.")
        want_digest = man.get("digest")
        if want_digest and want_digest != digest_of(listed):
            raise PackError(
                "The pack's digest does not match its own file list. It has "
                "been modified since it was built.")
    if man.get("signature"):
        _verify_signature(man)


def _verify_signature(man: dict) -> None:
    """§2.9. Present-and-wrong is a hard failure; absent is simply unsigned.

    Verification of a real key is Phase 4; until then a signature block that
    is malformed is still refused, because a reader that ignores a field it
    does not understand is exactly how a signature becomes decorative.
    """
    sig = man.get("signature") or {}
    if not isinstance(sig, dict) or not sig.get("alg") or not sig.get("sig"):
        raise PackError("This pack carries a malformed signature block.")
    if sig.get("alg") != "ed25519":
        raise PackError(
            f"This pack is signed with “{sig.get('alg')}”, which this version "
            f"cannot check. A newer Sortie Starter may be able to.")


# --------------------------------------------------------------------------- #
# facts read out of a mission, for §5 derivation
# --------------------------------------------------------------------------- #
def mission_facts(raw: bytes) -> dict:
    """Theatre and player aircraft, without importing pydcs's heavy stack.

    Best-effort by design: a pack must install even when this fails, because
    the alternative is refusing somebody's missions over a regex."""
    facts = {}
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
        txt = z.read("mission").decode("utf-8", "replace")
        m = re.search(r'\["theatre"\]\s*=\s*"([^"]+)"', txt)
        if m:
            facts["theatre"] = m.group(1)
        for pat in (
            r'\["type"\]\s*=\s*"([^"]+)"[^}]*?\["skill"\]\s*=\s*"(?:Player|Client)"',
            r'\["skill"\]\s*=\s*"(?:Player|Client)"[^}]*?\["type"\]\s*=\s*"([^"]+)"',
        ):
            tm = re.search(pat, txt, re.S)
            if tm:
                facts["aircraft"] = tm.group(1)
                break
    except Exception:
        pass
    return facts


def _pretty(name: str) -> str:
    s = re.sub(r"\.miz$", "", name, flags=re.I)
    s = re.sub(r"[_\-]+", " ", s).strip()
    return s[:1].upper() + s[1:]


# --------------------------------------------------------------------------- #
# §5 derivation
# --------------------------------------------------------------------------- #
def derive(pid: str, files: dict) -> dict:
    """A complete format 2 manifest from the archive alone.

    THE PROPERTY THIS PROTECTS: somebody who has never read the specification
    drops a folder of .miz files in and gets a working pack. If that ever stops
    being true the format has become a barrier instead of a container.
    """
    mizzes = sorted(n for n in files if n.lower().endswith(".miz"))
    pdfs = sorted(n for n in files if n.lower().endswith(".pdf"))
    imgs = sorted(n for n in files
                  if n.lower().endswith((".png", ".jpg", ".jpeg")))

    facts = mission_facts(files[mizzes[0]]) if mizzes else {}
    theatre = _THEATRE_MAP.get(facts.get("theatre", ""))

    used = set()

    def brief_for(miz):
        stem = Path(miz).stem
        num = re.search(r"(\d+)", stem)
        for p in pdfs:
            if p in used:
                continue
            # lookarounds, not \D: the number is often at the very end of the
            # name ("Brief_01"), where a trailing \D can never match.
            if num and re.search(rf"(?<!\d){re.escape(num.group(1))}(?!\d)",
                                 Path(p).stem):
                return p
            if stem.lower() in Path(p).stem.lower():
                return p
        return None

    syllabus = []
    for i, m in enumerate(mizzes, 1):
        b = brief_for(m)
        if b:
            used.add(b)
        entry = {"n": i, "id": slug(Path(m).stem),
                 "label": _pretty(Path(m).name), "premise": "",
                 "files": {"mission": m}}
        if b:
            entry["files"]["brief"] = b
        syllabus.append(entry)

    docs = {}
    for p in [p for p in pdfs if p not in used]:
        low = Path(p).stem.lower()
        key = ("guide" if "guide" in low else
               "readme" if ("read" in low or "first" in low) else None)
        if key and key not in docs:
            docs[key] = p

    fl = file_list(files)
    man = {
        "format": FORMAT,
        "id": pid,
        "label": pid.replace("_", " ").title(),
        "version": "1.0.0",
        "requires": {},
        "library": {
            "role": "training", "threat": 3, "players": "SP",
            "premise": f"{len(syllabus)} mission"
                       f"{'s' if len(syllabus) != 1 else ''} in this pack.",
            "image": imgs[0] if imgs else None,
            "eras": ["modern"],
            "maps": [theatre] if theatre else None,
        },
        "syllabus": syllabus,
        "docs": docs,
        "files": fl,
        "digest": digest_of(fl),
        "derived": True,
    }
    if theatre:
        man["requires"]["terrains"] = [theatre]
    if facts.get("aircraft"):
        man["requires"]["modules"] = [facts["aircraft"]]
    return man


# --------------------------------------------------------------------------- #
# §4 reading format 1
# --------------------------------------------------------------------------- #
_LIBRARY_KEYS = ("role", "threat", "players", "premise", "image",
                 "eras", "maps", "featured")


def upgrade(man: dict) -> dict:
    """Format 1 -> the in-memory format 2 shape. §4.

    IN MEMORY ONLY. Nothing rewrites an author's file because a reader happened
    to open it — §3 rule 3. The upgraded shape is what this process works with;
    what gets written to disk is a decision the INSTALLER makes, not the reader.
    """
    man = dict(man or {})
    fmt = man.get("format")
    if isinstance(fmt, int) and fmt > FORMAT:
        # The wording is the SPEC'S (§3 rule 2): the person holding the file
        # needs to know what to do about it, and the action is "get a newer
        # Sortie Starter", not "this is invalid".
        raise PackError(
            f"This pack needs a newer Sortie Starter — it is format {fmt} and "
            f"this version understands up to format {FORMAT}.")
    if fmt == FORMAT:
        return man

    lib = dict(man.get("library") or {})
    for k in _LIBRARY_KEYS:
        if k in man and k not in lib:
            lib[k] = man.pop(k)
    man["library"] = lib

    if "events" in man and "syllabus" not in man:
        man["syllabus"] = _upgrade_entries(man.pop("events"))

    # `module` was a DISPLAY STRING in format 1 and is the single most useful
    # thing in format 2, so it is promoted rather than dropped: a pilot needs
    # to know he cannot fly this before he downloads it.
    req = dict(man.get("requires") or {})
    if man.get("module") and not req.get("modules"):
        req["modules"] = [man["module"]]
    if lib.get("maps") and not req.get("terrains"):
        req["terrains"] = [m for m in lib["maps"] if m]
    man["requires"] = req
    man["format"] = FORMAT
    return man


def _upgrade_entries(events: list) -> list:
    """format 1 `events[]` -> format 2 `syllabus[]`, both spellings accepted."""
    out = []
    for e in events or []:
        e = dict(e)
        files = dict(e.get("files") or {})
        if e.get("miz") and "mission" not in files:
            files["mission"] = e["miz"]
        if e.get("brief_pdf") and "brief" not in files:
            files["brief"] = e["brief_pdf"]
        e.pop("miz", None)
        e.pop("brief_pdf", None)
        e["files"] = files
        if "id" not in e and files.get("mission"):
            e["id"] = slug(Path(files["mission"]).stem)
        out.append(e)
    return out


# --------------------------------------------------------------------------- #
# normalize: author's manifest + derived gaps -> a stored format 2 manifest
# --------------------------------------------------------------------------- #
def normalize(raw: dict | None, pid: str, files: dict) -> dict:
    """§5: derivation fills gaps, the author always wins.

    Also enforces §6: this is where a pack gets refused, and the only place.
    """
    if not any(k.lower().endswith(".miz") for k in files) and not any(
            k.lower().endswith((".pdf", ".md", ".txt")) for k in files):
        raise PackError(
            "There is nothing to publish in that archive — no missions and no "
            "documents.")

    author = upgrade(raw or {})
    out = derive(pid, files)

    # UNKNOWN FIELDS SURVIVE (§3 rule 1). Anything this version does not
    # understand is copied through untouched, so a pack that round-trips
    # through an older reader does not lose a newer reader's data.
    for k, v in author.items():
        if k in ("library", "requires", "docs", "syllabus", "files",
                 "digest", "derived"):
            continue
        if v not in (None, "", [], {}):
            out[k] = v

    for key in ("library", "requires", "docs"):
        merged = dict(out.get(key) or {})
        for k, v in (author.get(key) or {}).items():
            if v not in (None, "", [], {}):
                merged[k] = v
        out[key] = merged

    syl = _upgrade_entries(author.get("syllabus") or author.get("events") or [])
    if syl:
        out["syllabus"] = syl
    out["derived"] = not bool(raw)
    out["id"] = pid
    out["format"] = FORMAT

    if out["library"].get("role") not in ROLES:
        out["library"]["role"] = "training"
    if out["library"].get("image") and out["library"]["image"] not in files:
        out["library"]["image"] = None
    out["docs"] = {k: v for k, v in out["docs"].items() if v in files}

    # An entry whose mission is not in the archive is dropped, not served (§2.6)
    keep = []
    for e in out["syllabus"]:
        f = dict(e.get("files") or {})
        if f.get("mission") not in files:
            continue
        for k in list(f):
            if f[k] not in files:
                f.pop(k)
        e["files"] = f
        keep.append(e)
    out["syllabus"] = keep

    # The integrity block always describes what is ACTUALLY here. An author's
    # stale hash list is verified first (below) and then replaced, so a pack
    # cannot be stored describing files it does not have.
    verify(author, files)
    out["files"] = file_list(files)
    out["digest"] = digest_of(out["files"])
    return out


# --------------------------------------------------------------------------- #
# the projection the Library UI reads
# --------------------------------------------------------------------------- #
def card_view(man: dict) -> dict:
    """Format 2 -> the flat shape the current UI reads. DERIVED, NEVER STORED.

    This exists so the format can move ahead of the frontend without a flag
    day. It is one-directional on purpose: nothing reads a card view back, so
    there is exactly one source of truth on disk.
    """
    lib = man.get("library") or {}
    req = man.get("requires") or {}
    out = dict(man)
    out.update({
        "role": lib.get("role", "training"),
        "threat": lib.get("threat", 3),
        "players": lib.get("players", "SP"),
        "premise": lib.get("premise", ""),
        "historical_context": man.get("historical_context") or {},
        "image": lib.get("image"),
        "eras": lib.get("eras") or ["modern"],
        "maps": lib.get("maps"),
        "featured": bool(lib.get("featured")),
        "module": (req.get("modules") or [None])[0],
        "events": [
            {"n": e.get("n"), "label": e.get("label"),
             "premise": e.get("premise", ""),
             "miz": (e.get("files") or {}).get("mission"),
             "brief_pdf": (e.get("files") or {}).get("brief")}
            for e in man.get("syllabus") or []
        ],
    })
    return out


def dumps(man: dict) -> str:
    return json.dumps(man, indent=1, ensure_ascii=False, sort_keys=False)
