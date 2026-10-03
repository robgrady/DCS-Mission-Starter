"""Mission packs — curated .miz collections, uploaded not deployed.

The AWI syllabus taught the lesson: 28 MB of missions baked into the repo made
the release zip untransferable, the docker image fat, and every content update
a code deploy — which then failed twice for reasons invisible locally. Packs
are CONTENT, so they belong where the sponsor logos already live: on the Fly
volume, uploaded through /admin, surviving deploys, needing no rebuild.

Drop in either:
  * a .zip — any layout. A `pack.json` at its root (or one level down) is used
    if present; otherwise one is DERIVED by inspecting the missions.
  * a single .miz — becomes a one-mission pack.

pack.json (every field optional except id/label — the rest is derived):
  {
    "id": "awi_basics",
    "label": "AWI Basics — All-Weather Intercept Syllabus",
    "role": "training",          # Library tab
    "premise": "...",            # card copy
    "eras": ["modern"], "maps": ["nevada"],
    "module": "F-14B(U)", "threat": 3, "players": "SP",
    "image": "card.png",         # card art, path inside the pack
    "docs": {"guide": "AWI_In_Flight_Guide.pdf", "readme": "READ_ME.pdf"},
    "events": [ {"n":1,"label":"...","miz":"...","brief_pdf":"...",
                 "premise":"..."} ]
  }

Layout on the volume: <DATA_DIR>/<id>/  — files as uploaded, plus a normalised
pack.json written at install time so serving never re-derives anything.
"""
from __future__ import annotations

import logging
import hashlib
import tempfile
from functools import wraps
import os
import json
import shutil
import threading
import zipfile
from pathlib import Path

from . import packfmt
from .packfmt import PackError          # noqa: F401  (re-exported for callers)

log = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get(
    "PACKS_DATA_DIR", str(Path(__file__).parent.parent / "instance" / "packs")))

MAX_UPLOAD_BYTES = 256 * 1024 * 1024
ROLES = packfmt.ROLES

_lock = threading.RLock()


def _serialized(fn):
    @wraps(fn)
    def call(*args, **kwargs):
        with _lock:
            return fn(*args, **kwargs)
    return call


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _slug(s: str) -> str:
    return packfmt.slug(s)


# --------------------------------------------------------------------------- #
# install / remove
# --------------------------------------------------------------------------- #
def install(data: bytes, filename: str, pack_id: str | None = None,
            label: str | None = None) -> dict:
    """Install an uploaded .sspack/.zip/.miz. Returns the stored manifest.

    STORAGE ONLY. Everything about WHAT a pack is — the path rules, the
    integrity checks, the format-1 upgrade, the derivation — lives in
    `packfmt`, which implements `docs/PACK_FORMAT.md`. This function decides
    where the bytes go and nothing else.
    """
    if not data:
        raise PackError("Empty upload.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise PackError(
            f"Upload too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).")

    name = Path(filename or "pack").name
    low = name.lower()
    if low.endswith(".miz"):
        # §1: a bare mission is an IMPORT CONVENIENCE, not the format. What
        # comes out is a normal one-mission pack with a normal manifest.
        files = {name: data}
        default_id = packfmt.slug(Path(name).stem)
    elif low.endswith((".zip", ".sspack")):
        files = packfmt.read_archive(data)
        default_id = packfmt.slug(Path(name).stem)
        tops = {n.split("/")[0] for n in files if "/" in n}
        if len(tops) == 1:
            default_id = packfmt.slug(list(tops)[0])
    else:
        raise PackError(
            "Upload a .sspack, a .zip of missions, or a single .miz file.")

    raw = None
    for cand in ("pack.json", "manifest.json"):
        if cand in files:
            try:
                raw = json.loads(files[cand].decode("utf-8"))
            except Exception:
                raise PackError(f"{cand} is not valid JSON.")
            break

    # id precedence: what the admin typed > what the pack declares > the file
    # name. The manifest's own id must outrank the archive's name, or a pack
    # renamed in transit installs under a different id than it documents.
    pid = packfmt.slug(pack_id or (raw or {}).get("id") or default_id)
    man = packfmt.normalize(raw, pid, files)
    if label:
        man["label"] = label

    # Write the complete replacement before moving any published content.
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".stage-", dir=DATA_DIR))
    backup = stage.with_name(stage.name.replace(".stage-", ".previous-", 1))
    dest = DATA_DIR / pid
    try:
        for rel, blob in files.items():
            if rel in ("pack.json", "manifest.json"):
                continue
            fp = stage / rel
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_bytes(blob)
        (stage / "pack.json").write_text(packfmt.dumps(man), encoding="utf-8")
        # Readers/cache creation share this lock. A failed publish restores the
        # old directory; staged and backup directories never enter the catalog.
        with _lock:
            had_previous = dest.exists()
            if had_previous:
                os.replace(dest, backup)
            try:
                os.replace(stage, dest)
            except BaseException:
                if had_previous:
                    os.replace(backup, dest)
                raise
            if had_previous:
                shutil.rmtree(backup, ignore_errors=True)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return man


def delete(pid: str) -> None:
    with _lock:
        d = (DATA_DIR / _slug(pid))
        if d.is_dir() and d.resolve().parent == DATA_DIR.resolve():
            shutil.rmtree(d)


def _version_tuple(v: str) -> tuple:
    parts = []
    for chunk in str(v or "0").split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts + [0, 0, 0])[:3]


@_serialized
def list_packs() -> list:
    """Every installed pack, as the Library's flat card view.

    Stored as format 2, HANDED OUT as `packfmt.card_view` — one shape on disk,
    one projection for the UI, and nothing reads the projection back. See the
    one-direction rule at the top of `packfmt`.
    """
    found = {}
    try:
        dirs = sorted(p for p in DATA_DIR.iterdir() if p.is_dir() and not p.name.startswith("."))
    except OSError:
        dirs = []
    for d in dirs:
        mf = d / "pack.json"
        if not mf.exists():
            continue
        try:
            man = packfmt.upgrade(json.loads(mf.read_text(encoding="utf-8")))
        except Exception:
            # A manifest we cannot read is a pack we do not list. It is still
            # on disk and still downloadable by anyone with the id; hiding it
            # from the Library is the conservative half of that.
            continue
        man["syllabus"] = [
            e for e in man.get("syllabus") or []
            if (e.get("files") or {}).get("mission")
            and (d / e["files"]["mission"]).exists()]
        man["size_mb"] = round(
            sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / 1e6, 1)
        man["source"] = "installed"
        if not man["syllabus"]:
            continue
        # §2.2: two packs sharing an id are the same pack at different
        # versions, and the higher one wins. With one storage tier this can
        # only happen if somebody puts two directories on the volume by hand,
        # but the rule is the format's and it costs four lines to honor.
        prev = found.get(man["id"])
        if prev and _version_tuple(prev.get("version")) > _version_tuple(
                man.get("version")):
            continue
        found[man["id"]] = man
    return [packfmt.card_view(m) for _k, m in sorted(found.items())]


@_serialized
def get_file(pid: str, rel: str) -> Path | None:
    """Resolve a file inside a pack, refusing anything outside it."""
    base = (DATA_DIR / _slug(pid)).resolve()
    if not base.is_dir():
        return None
    try:
        f = (base / rel).resolve()
    except Exception:
        return None
    if base not in f.parents and f != base:
        return None
    return f if f.is_file() else None


@_serialized
def get_manifest(pid: str) -> dict | None:
    """The stored format 2 manifest for an installed pack, or None.

    Bundled packs are deliberately NOT editable: they are part of a release,
    and a change that survives a deploy has to be a change to the release.
    Editing one in place would produce a machine whose content nobody could
    reproduce from the repository — which is the property bundling exists to
    guarantee.
    """
    mf = DATA_DIR / packfmt.slug(pid) / "pack.json"
    if not mf.is_file():
        return None
    try:
        return packfmt.upgrade(json.loads(mf.read_text(encoding="utf-8")))
    except Exception:
        return None


@_serialized
def update_manifest(pid: str, patch: dict) -> dict:
    """Apply an author's corrections to an installed pack's manifest.

    THE WORKFLOW THIS EXISTS FOR: somebody builds a set of historically
    accurate missions in the Mission Editor, drops the folder in, and the
    system writes a manifest by looking at the files. That manifest is a good
    guess and a guess is not authorship — the labels are filenames, the
    premise is a placeholder, the order is alphabetical and nothing knows the
    history. This is where the author replaces the guess.

    The patch is merged over the stored manifest, re-normalised against the
    files that are actually on disk, and re-verified. Anything the author
    supplies wins; anything they leave alone keeps whatever derivation found.
    `derived` becomes False the moment a human has touched it, so the admin
    stops describing it as auto-detected.
    """
    pid = packfmt.slug(pid)
    base = get_manifest(pid)
    if base is None:
        raise PackError("No such pack.")
    d = DATA_DIR / pid
    files = {str(f.relative_to(d)): f.read_bytes()
             for f in d.rglob("*") if f.is_file() and f.name != "pack.json"}

    merged = dict(base)
    for k, v in (patch or {}).items():
        if k in ("library", "requires", "docs", "built_with"):
            sub = dict(merged.get(k) or {})
            sub.update({kk: vv for kk, vv in (v or {}).items()
                        if vv not in (None, "")})
            merged[k] = sub
        elif v not in (None, ""):
            merged[k] = v

    man = packfmt.normalize(merged, pid, files)
    man["derived"] = False
    with _lock:
        fd, temporary = tempfile.mkstemp(prefix=".manifest-", dir=d)
        os.close(fd)
        tmp = Path(temporary)
        try:
            tmp.write_text(packfmt.dumps(man), encoding="utf-8")
            os.replace(tmp, d / "pack.json")
        finally:
            tmp.unlink(missing_ok=True)
    return man


def manifest_bytes(pid: str) -> bytes | None:
    """The manifest as a downloadable file.

    So an author can drop it back into the folder they uploaded and the pack
    becomes self-describing — the next upload of that folder, to this server or
    anybody else's, carries their words rather than re-deriving a guess. That
    round trip is what makes the format worth publishing.
    """
    man = get_manifest(pid)
    return packfmt.dumps(man).encode("utf-8") if man else None


@_serialized
def all_zip(pid: str):
    """The whole pack as one download, zipped once and cached by mtime.

    Lives here rather than in the server because `packref` needs it too, and a
    second implementation of "zip up a pack" is the twin-function shape this
    codebase keeps paying for. Keyed on the newest file's mtime, so a re-upload
    or a manifest edit invalidates it without anybody remembering to.
    """
    import tempfile
    import zipfile as _z
    pid = packfmt.slug(pid)
    base = DATA_DIR / pid
    if not base.is_dir():
        return None
    files = [f for f in base.rglob("*") if f.is_file()]
    if not files:
        return None
    # NANOSECONDS, and the file count. Second-resolution mtime is the same
    # trap the mutation harness hit with CPython's .pyc cache: an author fixes
    # the titles on the review screen within a second of the last download and
    # the stamp does not move, so the bundle he hands out still carries his old
    # words. Caught by a test that edited a manifest fast enough.
    stamp = f"{max(f.stat().st_mtime_ns for f in files)}_{len(files)}"
    namespace = hashlib.sha256(str(DATA_DIR.resolve()).encode()).hexdigest()[:12]
    cache = Path(tempfile.gettempdir()) / f"ss_pack_{namespace}_{pid}_{stamp}.zip"
    if not cache.exists():
        fd, temporary = tempfile.mkstemp(prefix=cache.name + ".part-", dir=cache.parent)
        os.close(fd)
        tmp = Path(temporary)
        try:
            with _z.ZipFile(tmp, "w", _z.ZIP_DEFLATED) as z:
                for f in sorted(files):
                    z.write(f, f"{pid}/{f.relative_to(base)}")
            os.replace(tmp, cache)
        finally:
            tmp.unlink(missing_ok=True)
    return cache
