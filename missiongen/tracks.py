"""Training TRACKS — an ordered set of Library cards that travel together.

A track is not a new kind of content. Every ride in one is an ordinary
generated card with an ordinary recipe; the track is the ordering, the printed
guide, and the promise that they were designed as a course rather than
collected into a folder.

WHY THIS IS NOT A PACK. `missiongen/packs.py` handles CURATED content: static
.miz files uploaded through /admin onto the Fly volume, for syllabuses whose
geometry is hand-built and must not be regenerated. Tracks are the opposite —
they are generated from the same engine as everything else, ship with the code,
and need no volume, no upload and no ADMIN_PASSWORD. If a track's content is
wrong, it is fixed in a release like any other bug, not by re-uploading a zip.

The ordering lives on the cards (`track: {id, n}`) rather than in a list here,
so a card cannot be in a track without knowing it and the two cannot disagree.
"""
from __future__ import annotations

from .resolver import load_json


def all_tracks() -> dict:
    return {k: v for k, v in load_json("tracks").items() if not k.startswith("_")}


def get(track_id: str) -> dict | None:
    return all_tracks().get(track_id)


def rides(track_id: str) -> list:
    """[(n, key, template)] in flying order.

    Sorted by `n`, and a duplicate `n` inside one track is a data error rather
    than something to resolve quietly — two rides numbered 4 means a printed
    syllabus with two rides numbered 4.
    """
    out = []
    seen = {}
    for k, v in load_json("mission_templates").items():
        if k.startswith("_"):
            continue
        tr = v.get("track") or {}
        if tr.get("id") != track_id:
            continue
        n = tr.get("n")
        if n in seen:
            raise ValueError(
                f"track {track_id!r} has two rides numbered {n}: "
                f"{seen[n]!r} and {k!r}")
        seen[n] = k
        out.append((n, k, v))
    return sorted(out, key=lambda x: x[0])


def picker(track_id: str) -> dict:
    """The wizard's whole decision tree, precomputed:

        {era: {roster_key: [tanker_key, ...]}}

    Only combinations that actually WORK appear. An era with no era-legal
    receiver in this lane is absent; a receiver with no compatible tanker in
    that era is absent; so the wizard cannot offer a choice that then fails to
    build. That is the point of computing it here rather than in the browser —
    the rules (service windows, boom-vs-probe, tanker era gating) live in the
    engine, and a second copy in JavaScript would drift.
    """
    from . import aar
    t = get(track_id) or {}
    lane = t.get("lane")
    if not lane:
        return {}
    service = load_json("aircraft_service")
    eras = load_json("eras")
    keyed = _flyable_keyed()
    # The track's map bounds the era list before any aircraft rule does.
    # Caucasus is free and has no War-on-Terror preset, and the Academy's whole
    # packaging promise is that the only thing you must own is the receiver —
    # so an era that would force a paid map is not offered at all. Read from
    # the map data rather than hard-coded, so adding a preset adds the era.
    mp = load_json("maps").get(t.get("default_map") or "caucasus") or {}
    playable = set(mp.get("presets") or {})
    out = {}
    for era, era_cfg in eras.items():
        if era.startswith("_") or era == "wwii" or era not in playable:
            continue
        combos = {}
        for key in aar.receivers_for(lane, era, service, era_cfg, keyed):
            tks = aar.tankers_for(keyed[key], era,
                                  map_key=t.get("default_map") or "caucasus")
            if tks:
                combos[key] = tks
        if combos:
            out[era] = combos
    return out


def period_notes(track_id: str) -> dict:
    """{era: {tanker_key: note}} — tankers offered here whose service window
    does not cover the whole era. Offered, but labelled."""
    from . import aar
    out = {}
    for era, combos in picker(track_id).items():
        rows = {}
        for tks in combos.values():
            for tk in tks:
                if tk not in rows:
                    n = aar.period_note(tk, era)
                    if n:
                        rows[tk] = n
        if rows:
            out[era] = rows
    return out


def excluded(track_id: str) -> dict:
    """{era: [[tanker_key, reason], ...]} — tankers this lane could use but
    cannot in that era.

    Rob had to ask where the KA-6D went. It had not gone anywhere: the A-6 left
    the fleet in 1997 and the modern era starts in 2000, so the era gate was
    doing exactly its job — silently, which made a history lesson look like a
    missing feature. An interface that omits a thing owes the reason.
    """
    from . import aar
    t = get(track_id) or {}
    lane = t.get("lane")
    if not lane:
        return {}
    tree = picker(track_id)
    keyed = _flyable_keyed()
    out = {}
    for era, combos in tree.items():
        seen, rows = set(), []
        for key in combos:
            for tk, why in aar.tankers_excluded_by_era(
                    keyed[key], era,
                    map_key=t.get("default_map") or "caucasus"):
                if tk not in seen:
                    seen.add(tk)
                    rows.append([tk, why])
        if rows:
            out[era] = sorted(rows)
    return out


def _flyable_keyed() -> dict:
    """roster key -> DCS type id, for every PLAYER-flyable aircraft.

    TWO SOURCES, and missing the second is how the F-14B(U) vanished from this
    wizard the first time it ran: most airframes are pydcs classes with
    `flyable = True`, but modules pydcs has no class for — the F-14B(U) among
    them — come from `pending_aircraft()` and carry their type id in `label`.
    `resolve("planes.F_14B_U")` raises, so a mapping built only from the
    resolver silently drops exactly the aircraft Rob asked for.

    `tests/test_aar_wizard.py` pins this against the roster the options
    endpoint publishes, so the duplication cannot drift unnoticed.
    """
    from dcs import planes, helicopters
    from .pending import pending_aircraft
    out = {}
    for mod in (planes, helicopters):
        for name in dir(mod):
            if name.startswith("_"):
                continue
            cls = getattr(mod, name)
            if isinstance(cls, type) and getattr(cls, "flyable", False):
                out[name] = cls.id
    for key, cfg in pending_aircraft().items():
        if not cfg.get("verified"):
            continue
        # `provisional_id`, NOT `label`. The label is what the Library prints;
        # the provisional id is what the builder registers and what lands in
        # the .miz, and `aar.AAR_RECEIVERS` is keyed on the latter. Using the
        # label here offered the F-14B(U) in the wizard and then produced a
        # syllabus with no tanker in it.
        out[key] = cfg.get("provisional_id") or cfg["label"]
    return out


def resolve_choice(track_id: str, era=None, aircraft=None, tanker=None):
    """Validate a wizard selection and fill the gaps from the track's defaults.

    Returns (era, aircraft_key, tanker_key). Raises ValueError with a message
    written for the pilot, not the log, on anything that will not fly.
    """
    t = get(track_id)
    if not t:
        raise ValueError("No such training track.")
    tree = picker(track_id)
    era = era or (t.get("eras") or ["modern"])[0]
    if era not in tree:
        raise ValueError(
            f"The {t.get('lane')} syllabus has no aircraft that served in the "
            f"{era} era. Available: {', '.join(sorted(tree))}.")
    aircraft = aircraft or (t["aircraft"] if t["aircraft"] in tree[era]
                            else sorted(tree[era])[0])
    if aircraft not in tree[era]:
        raise ValueError(
            f"{aircraft} cannot fly this syllabus in the {era} era — either it "
            f"does not air-refuel with this system, or it was not in service. "
            f"Available: {', '.join(sorted(tree[era]))}.")
    tanker = tanker or (t["tanker"] if t["tanker"] in tree[era][aircraft]
                        else tree[era][aircraft][0])
    if tanker not in tree[era][aircraft]:
        raise ValueError(
            f"A {tanker} cannot refuel a {aircraft}. Available: "
            f"{', '.join(tree[era][aircraft])}.")
    return era, aircraft, tanker


def summary(track_id: str) -> dict | None:
    """The shape the Library card needs: metadata plus the ordered ride list."""
    t = get(track_id)
    if not t:
        return None
    rs = rides(track_id)
    if not rs:
        return None
    return {
        "id": track_id,
        "label": t["label"],
        "short": t.get("short") or t["label"],
        "premise": t.get("premise", ""),
        "blurb": t.get("blurb") or [],
        "lane": t.get("lane"),
        "service": t.get("service"),
        "aircraft": t.get("aircraft"),
        "tanker": t.get("tanker"),
        "eras": t.get("eras") or ["modern"],
        "default_map": t.get("default_map") or "caucasus",
        "guide": t.get("guide"),
        "featured": bool(t.get("featured")),
        "role": t.get("role", "training"),
        # A PAID DCS MODULE THE WHOLE TRACK DEPENDS ON. Not the same thing as
        # the ownership check the Library already does: that compares against
        # maps and aircraft the user has ticked, and DCS: Supercarrier is
        # neither — it is a boat and a set of radio procedures, so nothing in
        # the ownership picker can answer for it. Carried through so the track
        # panel can say it before somebody downloads a syllabus whose Marshal
        # will not answer.
        "requires": t.get("requires"),
        # The wizard's decision tree: era -> aircraft -> tankers, already
        # filtered to combinations that build. EMPTY for a track that offers no
        # choice — a syllabus pinned to one airframe has nothing to pick, and
        # rendering an empty wizard beside it looks like a broken control
        # rather than an absent one. `configurable` says which it is, so the
        # Library does not have to infer it from an empty dict.
        "picker": picker(track_id),
        "configurable": bool(picker(track_id)),
        "series": t.get("series"),
        "follows": t.get("follows"),
        "maps": t.get("maps") or [t.get("default_map") or "caucasus"],
        # Tankers this lane could use but not in that era, with the
        # reason. An omission nobody explains reads as a bug.
        "excluded": excluded(track_id),
        # Offered, but not period-perfect. Labelled rather than hidden.
        "period_notes": period_notes(track_id),
        "rides": [{
            "n": n,
            "key": k,
            "label": v["label"].split("— ", 1)[-1],
            "premise": (v.get("library") or {}).get("premise", ""),
            "graded": v.get("aar_grade") or None,
        } for n, k, v in rs],
    }


def summaries() -> dict:
    out = {}
    for tid in all_tracks():
        s = summary(tid)
        if s:
            out[tid] = s
    return out
