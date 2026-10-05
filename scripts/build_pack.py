#!/usr/bin/env python3
"""The producer: turn a spec into a published pack.

THE POINT OF THIS FILE, IN ONE SENTENCE: the generator stops being something a
download waits for and becomes the tool that MAKES the thing a pilot downloads.

WHAT A SPEC IS
--------------
`tracks.json` and `mission_templates.json`, unchanged. They are good authoring
inputs — a track already names its rides, their order, their premises and the
recipe each one resolves to, and there is a test suite around all of it. What
changes is WHO reads them: after this, only this script does. The server reads
a pack.

That is the whole architecture in two sentences, and it is why `tracks.json`
does not move: a spec that has to be rewritten to adopt a new distribution
model was never a spec, it was a coincidence.

DETERMINISM IS THE FEATURE
--------------------------
Seeds are fixed (`4400 + n`), the generator is reproducible, and the manifest
carries a digest over the content. So `--check` can rebuild a pack and compare
digests: a mismatch is either a real content change or a regression, and either
way somebody should look. No other content mechanism in this product has ever
had that.

Usage:
    PYTHONPATH=.:vendor python3 scripts/build_pack.py wk_proud_phantom
    PYTHONPATH=.:vendor python3 scripts/build_pack.py --all
    PYTHONPATH=.:vendor python3 scripts/build_pack.py --all --check
"""
import argparse
import io
import json
import pathlib
import shutil
import sys
import tempfile
import time
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from missiongen import __version__, generate, packfmt, tracks as _tracks  # noqa: E402
from missiongen.recipe import Recipe                                      # noqa: E402
from missiongen.resolver import load_json                                 # noqa: E402
from missiongen.templates import effective_recipe                         # noqa: E402

OUT = ROOT / "packs"

# The CONTENT version of each bundled pack. Bumped by hand when the content
# meaningfully changes — which is the entire point of it being separate from
# the app version. `built_with.app` records which release produced the bytes;
# this records what the author thinks changed.
CONTENT_VERSION = {
    "wk_checkout": "1.0.8",
    # 2.0: the rides flew from Israel. Egypt is the host nation, the squadron
    # is USAF and Cairo West is home — different missions, not a patch.
    # 3.0: the wingman moved INTO the player's flight — the two-ship is flown
    # differently and a pilot's notes about REX 2 stop being true.
    "wk_proud_phantom": "3.0.9",     # 3.0.6: correct the eleven-ride introduction
                                     # 1.1.1: the brief leaves the screen
                                     # 2.1: the wingman waits for your brief
                                     # 2.1.1: ...and then actually takes off
                                     # 2.2: the route runs west with a real
                                     #      target standing on the target leg
                                     # 2.3: gates on the coached ride, and the
                                     #      wingman gets his shelter to himself
    "aar_boom": "1.0.8",
    "aar_probe": "1.0.8",
    # v1.107.0 regenerates mission documents with the airfield guide and
    # exact measured stand directions. Patch content versions describe these
    # corrections independently of the application release version.
    "cq_case3_f14": "1.0.8",
    "cq_case3_hornet": "1.0.8",
    "timing_f4e": "1.0.8",
}

# Which terrain module each map key needs a pilot to own, in the words DCS
# uses. `requires` is only worth having if it names things a person can go and
# buy.
TERRAIN_NAME = {
    "germany": "Germany Cold War", "sinai": "Sinai", "caucasus": "Caucasus",
    "nevada": "Nevada NTTR", "syria": "Syria", "persiangulf": "Persian Gulf",
    "marianas": "Marianas", "normandy": "Normandy", "thechannel": "The Channel",
    "kola": "Kola", "afghanistan": "Afghanistan", "falklands": "Falklands",
    "iraq": "Iraq",
}


def spec_for(track_id: str) -> dict:
    t = _tracks.get(track_id)
    if not t:
        raise SystemExit(f"no such track: {track_id}")
    return t


def _module_name(aircraft_key: str) -> str:
    """The pilot-facing module name for an aircraft key.

    `display()`, not `designation()`. `requires.modules` is only worth having
    if it names something a person can go and buy, and nobody sells an
    "F-4E-45MC" — the store calls it the Phantom II. The designation alone
    reads like a variant code to anyone who is not already an owner.
    """
    try:
        from missiongen.acnames import display
        return (display(aircraft_key) or aircraft_key).replace("·", "—")
    except Exception:
        return aircraft_key.replace("_", "-")


def build(track_id: str, out_dir: pathlib.Path,
          era=None, aircraft=None, tanker=None) -> pathlib.Path:
    t = spec_for(track_id)
    rides = _tracks.rides(track_id)
    if not rides:
        raise SystemExit(f"{track_id} has no rides")

    wizard = bool(t.get("lane"))
    if wizard:
        era, aircraft, tanker = _tracks.resolve_choice(
            track_id, era or (t.get("eras") or ["modern"])[0],
            aircraft, tanker)
    else:
        era = era or (t.get("eras") or ["coldwar"])[0]
        aircraft = aircraft or t.get("aircraft")
        tanker = None

    tpl = load_json("mission_templates")
    work = pathlib.Path(tempfile.mkdtemp())
    files: dict = {}
    syllabus = []
    maps = set()
    modules = {_module_name(aircraft)}

    try:
        for n, key, card in rides:
            rc = effective_recipe(key, era, "" if wizard
                                  else (card.get("default_map") or ""))
            rc["template"] = key
            rc["aircraft"] = aircraft
            if tanker:
                rc["tanker_type"] = tanker
            # A FIXED seed. A printed syllabus that refers to "the tanker on
            # the northern track" must still be true for the next person who
            # downloads it; a track is a course, not a roll of the dice.
            rc["seed"] = 4400 + n
            r = Recipe.from_dict(rc)
            r.validate()
            stem = f"{n:02d}_{key}"
            miz = work / f"{stem}.miz"
            res = generate(r, str(miz), brief_dir=str(work))
            files[f"missions/{stem}.miz"] = miz.read_bytes()
            entry = {"n": n, "id": key,
                     "label": card.get("label") or key,
                     "premise": ((tpl.get(key) or {}).get("library")
                                 or {}).get("premise", ""),
                     "files": {"mission": f"missions/{stem}.miz"}}
            if res.get("brief_pdf"):
                bp = f"briefs/{stem}_brief.pdf"
                files[bp] = pathlib.Path(res["brief_pdf"]).read_bytes()
                entry["files"]["brief"] = bp
            syllabus.append(entry)
            if rc.get("map"):
                maps.add(rc["map"])

        # the printed guide, generated for THIS combination
        gdir = work / "guide"
        gdir.mkdir(exist_ok=True)
        if wizard:
            from missiongen import aar_guide as G
            pdf = G.build(track_id, t, __version__, out_dir=gdir,
                          aircraft=aircraft, tanker=tanker, era=era)
            md = G.markdown(track_id, t, __version__, out_dir=gdir,
                            aircraft=aircraft, tanker=tanker, era=era)
        else:
            from missiongen import wk_guide as G
            mk = t.get("default_map") or ""
            pdf = G.build(track_id, t, __version__, out_dir=gdir, map_key=mk)
            md = G.markdown(track_id, t, __version__, out_dir=gdir, map_key=mk)
        guide_rel = f"guide/{pathlib.Path(pdf).name}"
        files[guide_rel] = pathlib.Path(pdf).read_bytes()
        files["READ_ME_FIRST.md"] = pathlib.Path(md).read_bytes()

        from missiongen.historical_world import template_previews
        man = {
            "format": packfmt.FORMAT,
            "id": track_id,
            "label": t.get("label") or track_id,
            "version": CONTENT_VERSION.get(track_id, "1.0.0"),
            "author": "Rob Grady",
            "historical_context": template_previews(rides[0][1]),
            "requires": {
                "terrains": sorted(maps),
                "terrain_names": [TERRAIN_NAME.get(m, m) for m in sorted(maps)],
                "modules": sorted(modules),
            },
            "built_with": {
                "app": __version__,
                "generated": True,
                "spec": f"tracks.json#{track_id}",
                "seeds": "fixed",
            },
            "library": {
                "role": t.get("role", "training"),
                "threat": max((((tpl.get(k) or {}).get("library") or {})
                               .get("threat", 1)) for _n, k, _c in rides),
                "players": "SP",
                "premise": t.get("premise", ""),
                "eras": [era],
                "maps": sorted(maps) or None,
                "featured": bool(t.get("featured")),
            },
            "syllabus": syllabus,
            "docs": {"guide": guide_rel, "readme": "READ_ME_FIRST.md"},
        }
        man = packfmt.normalize(man, track_id, files)

        out_dir.mkdir(parents=True, exist_ok=True)
        tag = f"_{era}_{aircraft}_{tanker}" if wizard else ""
        dest = out_dir / f"{track_id}{tag}.sspack"
        buf = io.BytesIO()
        # ZIP_DEFLATED with a fixed date, so the same content produces the same
        # archive: `--check` compares digests, but a reproducible file is worth
        # having anyway the day somebody diffs two downloads.
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            zi = zipfile.ZipInfo("pack.json", date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, packfmt.dumps(man))
            for rel in sorted(files):
                zi = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(zi, files[rel])
        dest.write_bytes(buf.getvalue())
        return dest
    finally:
        shutil.rmtree(work, ignore_errors=True)


def bundled() -> list:
    """Which packs ship inside the image and the release.

    Derived from `tracks.json`: a PINNED track has one combination and no
    wizard, so there is exactly one artifact and it belongs in the product.
    Wizard tracks get their default combination for the same reason the
    Library's plain download button uses it.
    """
    out = []
    for tid, t in sorted(_tracks.all_tracks().items()):
        if tid.startswith("_"):
            continue
        if t.get("lane"):
            era = (t.get("eras") or ["modern"])[0]
            try:
                out.append((tid,) + tuple(
                    _tracks.resolve_choice(tid, era, None, None)))
            except ValueError:
                continue
        else:
            out.append((tid, (t.get("eras") or ["coldwar"])[0],
                        t.get("aircraft"), None))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("track", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="rebuild and compare digests; do not write")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    todo = bundled() if (a.all or a.list) else [
        (a.track,) + tuple(bundled_for(a.track))]
    if a.list:
        for row in todo:
            print("  ".join(str(x) for x in row))
        return

    out_dir = pathlib.Path(a.out)
    bad = 0
    for tid, era, ac, tk in todo:
        t0 = time.time()
        target = out_dir if not a.check else pathlib.Path(tempfile.mkdtemp())
        p = build(tid, target, era, ac, tk)
        man = json.loads(zipfile.ZipFile(p).read("pack.json"))
        if a.check:
            live = out_dir / p.name
            if not live.exists():
                print(f"  MISSING  {p.name} — never built")
                bad += 1
            else:
                was = json.loads(zipfile.ZipFile(live).read("pack.json"))
                same = was.get("digest") == man.get("digest")
                print(f"  {'ok      ' if same else 'CHANGED '} {p.name}")
                bad += 0 if same else 1
            shutil.rmtree(target, ignore_errors=True)
        else:
            print(f"  + {p.name}  {p.stat().st_size / 1e6:.1f} MB  "
                  f"v{man['version']}  {time.time() - t0:.0f}s")
    if a.check and bad:
        raise SystemExit(f"{bad} pack(s) differ from what is committed")


def bundled_for(track_id: str):
    for row in bundled():
        if row[0] == track_id:
            return row[1:]
    raise SystemExit(f"no such track: {track_id}")


if __name__ == "__main__":
    main()
