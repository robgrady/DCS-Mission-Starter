"""Which installed pack, if any, answers a track download.

ONE SOURCE OF PACKS: THE VOLUME. There is no bundled tier. A pack is produced
by `scripts/build_pack.py`, uploaded through `/admin`, and lives on the Fly
volume — so adding, correcting or removing content never touches an image and
never needs a deploy.

That was tried the other way for one release. Building the four syllabi into
the image made it 44 MB heavier and the release zip 59 MB, which is large
enough that it stopped being handable over a normal channel; and worse, it
welded a corrected premise line to a deployment. Thin product, content
uploaded.

THE ID IS THE JOIN. A track and its published pack share an id, so
`wk_proud_phantom` in `tracks.json` and `wk_proud_phantom` on the volume are
the same syllabus: one authored as a spec, the other as the artifact built from
it. That is the only coupling between the generator and the pack model, and it
is deliberately just a string.
"""
from __future__ import annotations

from pathlib import Path


def installed_pack(track_id: str) -> dict | None:
    """The installed pack whose id matches this track, or None."""
    from missiongen import packs as _packs
    for man in _packs.list_packs():
        if man.get("id") == track_id and man.get("events"):
            return man
    return None


def pack_zip(track_id: str) -> Path | None:
    """The whole-syllabus download for an installed pack, or None."""
    from missiongen import packs as _packs
    if installed_pack(track_id) is None:
        return None
    try:
        return _packs.all_zip(track_id)
    except Exception:
        return None
