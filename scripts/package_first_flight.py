#!/usr/bin/env python3
"""Package the authored First Flight preview for DCS and Sortie Starter."""
from argparse import ArgumentParser
from io import BytesIO
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

from missiongen import __version__, packfmt
from missiongen.resolver import load_json

PROFILE_ID = "first_flight_t45c_caucasus"


def zip_bytes(files):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for path, data in sorted(files.items()):
            archive.writestr(ZipInfo(path), data, compress_type=ZIP_DEFLATED)
    return buffer.getvalue()


def package(native: Path, out: Path):
    profile = next(p for p in load_json("first_flight")["profiles"] if p["id"] == PROFILE_ID)
    version = profile["version"]
    folder = "First Flight - T-45C Caucasus"
    readme = rf"""First Flight - T-45C Caucasus {version}
Two-sortie DCS flight-test candidate

REQUIREMENTS
Caucasus terrain and the VNAO T-45C v1.02 community mod.
Get the mod and its install instructions from the maintainer:
{profile["requirements"][0]["url"]}

INSTALL
Extract this ZIP and copy the "{folder}" folder into:
  %USERPROFILE%\Saved Games\DCS\Missions\Campaigns\en
Use the active Saved Games profile if yours has a different name. Keep
First-Flight.cmp next to both mission files. In DCS, open Campaigns > User
and select First Flight. For standalone practice, open either .miz from
Mission. The brief PDFs are in the Briefs folder.

FLY
FAM-01 First Flight starts airborne. FAM-02 Ramp to Air starts on the ramp
with the engine running. Use the mission-specific kneeboard card first.
The following page reproduces a CNATRA P-1212 figure for study.

The package was prepared for flight testing. Check mission loading, the
T-45C front seat and starting states, prompts, scoring and campaign advance
in Windows DCS. Keep the DCS build, mod build and logs with observations.
"""
    readme_bytes = readme.encode("utf-8")
    campaign = (native / "First-Flight.cmp").read_bytes()
    campaign_files = {"INSTALL.txt": readme_bytes, f"{folder}/First-Flight.cmp": campaign}
    pack_files = {"INSTALL.txt": readme_bytes}
    syllabus = []
    for n, lesson in enumerate(profile["lessons"], 1):
        mission_name = lesson["mission"]
        brief_name = f"{Path(mission_name).stem}-brief.pdf"
        mission = (native / "illustrated" / mission_name).read_bytes()
        brief = (native / "illustrated" / brief_name).read_bytes()
        if f'"{mission_name}"'.encode() not in campaign:
            raise ValueError(f"Campaign does not reference {mission_name}")
        with ZipFile(BytesIO(mission)) as archive:
            pages = [name for name in archive.namelist() if name.startswith("KNEEBOARD/IMAGES/")]
            if archive.testzip() is not None or "mission" not in archive.namelist() or len(pages) < 2:
                raise ValueError(f"{mission_name} must contain the mission and both kneeboard pages")
        if not brief.startswith(b"%PDF-"):
            raise ValueError(f"{brief_name} is not a PDF")
        campaign_files[f"{folder}/{mission_name}"] = mission
        campaign_files[f"{folder}/Briefs/{brief_name}"] = brief
        mission_path = f"missions/{mission_name}"
        brief_path = f"briefs/{brief_name}"
        pack_files[mission_path] = mission
        pack_files[brief_path] = brief
        syllabus.append({
            "n": n,
            "id": lesson["id"].lower().replace("-", "_"),
            "label": f"{lesson['id']} {lesson['title']}",
            "premise": lesson["objective"],
            "files": {"mission": mission_path, "brief": brief_path},
        })

    campaign_zip = zip_bytes(campaign_files)
    pack_files[profile["archive"]] = campaign_zip
    manifest = packfmt.normalize({
        "format": 2,
        "id": PROFILE_ID,
        "label": "First Flight - T-45C Caucasus",
        "version": version,
        "author": "Sortie Starter SimTeam",
        "requires": {
            "terrains": [profile["map"]["id"]],
            "modules": ["VNAO T-45C v1.02 community mod"],
        },
        "library": {
            "role": "training",
            "players": "SP",
            "threat": 1,
            "premise": "Two unarmed familiarization lessons at Kobuleti. Flight testing pending.",
            "eras": ["modern"],
            "maps": [profile["map"]["id"]],
        },
        "built_with": {
            "app": __version__,
            "generated": True,
            "spec": "First Flight",
        },
        "docs": {"readme": "INSTALL.txt", "campaign": profile["archive"]},
        "syllabus": syllabus,
    }, PROFILE_ID, pack_files)
    pack_files["pack.json"] = packfmt.dumps(manifest).encode("utf-8")
    out.mkdir(parents=True, exist_ok=True)
    archive_name = Path(profile["archive"]).name
    (out / archive_name).write_bytes(campaign_zip)
    (out / Path(archive_name).with_suffix(".sspack")).write_bytes(zip_bytes(pack_files))


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("native", type=Path, help="native mission build with illustrated/ outputs")
    parser.add_argument("out", type=Path, help="folder for campaign ZIP and Library .sspack")
    args = parser.parse_args()
    package(args.native, args.out)
