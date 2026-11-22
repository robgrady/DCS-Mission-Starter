#!/usr/bin/env python3
"""Package the authored First Flight preview for DCS and Sortie Starter."""
from argparse import ArgumentParser
from io import BytesIO
import json
from pathlib import Path
import sys
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

from dcs import lua
from PIL import Image

from missiongen import __version__, kneeboard, packfmt
from missiongen.resolver import load_json
from scripts.build_first_flight_missions import BASE_POINTS, COMPLETION_POINTS, DONE, NATIVE_TYPE
from scripts.dissect_miz import groups, units_of

PROFILE_ID = "first_flight_t45c_caucasus"
CAMPAIGN_FOLDER = "First Flight - T-45C Caucasus"
CAMPAIGN_NAME = "First-Flight.cmp"
KNEEBOARD_FILES = {f"KNEEBOARD/IMAGES/{n:02d}_starter.png" for n in (1, 2)}


def zip_bytes(files):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        for path, data in sorted(files.items()):
            archive.writestr(ZipInfo(path), data, compress_type=ZIP_DEFLATED)
    return buffer.getvalue()


def zip_contents(data):
    with ZipFile(BytesIO(data)) as archive:
        files = {}
        for member, name in packfmt.safe_members(archive):
            if name in files:
                raise ValueError(f"Duplicate archive member: {name}")
            files[name] = archive.read(member)
        return files


def validate_scores(mission, mission_name):
    goals = mission.get("goals") or {}
    expected = (
        (BASE_POINTS, {"predicate": "c_time_after", "seconds": 1}),
        (COMPLETION_POINTS, {"predicate": "c_flag_is_true", "flag": DONE}),
    )
    modeled = [
        (goal.get("score"), (goal.get("rules") or {}).get(1))
        for goal in goals.values()
        if goal.get("side") == "OFFLINE" and len(goal.get("rules") or {}) == 1
    ]
    result = mission.get("result") or {}
    offline = result.get("offline") or {}
    if len(goals) != len(expected) or modeled != list(expected) or result.get("total") != len(expected):
        raise ValueError(f"{mission_name} has unexpected practice or completion scores")
    actions = {i: f"a_set_mission_result({score})" for i, (score, _) in enumerate(expected, 1)}
    conditions = {1: "return(c_time_after(1) )", 2: f"return(c_flag_is_true({DONE}) )"}
    if offline.get("actions") != actions or offline.get("conditions") != conditions:
        raise ValueError(f"{mission_name} has mismatched native scoring expressions")
    triggers = mission.get("trigrules") or {}
    if not any(
        rule.get("rules") and {"predicate": "a_set_flag", "flag": DONE} in (rule.get("actions") or {}).values()
        for rule in triggers.values()
    ):
        raise ValueError(f"{mission_name} has no qualifying rule that sets the completion flag")


def validate_mission(data, mission_name, terrain):
    members = zip_contents(data)
    if "mission" not in members:
        raise ValueError(f"{mission_name} does not contain a native mission")
    if {name for name in members if name.startswith("KNEEBOARD/IMAGES/")} != KNEEBOARD_FILES:
        raise ValueError(f"{mission_name} must contain the cue and source-study kneeboard pages")
    for name in sorted(KNEEBOARD_FILES):
        with Image.open(BytesIO(members[name])) as page:
            if page.format != "PNG" or page.size != (kneeboard.W, kneeboard.H):
                raise ValueError(f"{mission_name} has an invalid kneeboard image: {name}")
            page.verify()

    mission = lua.loads(members["mission"].decode("utf-8"))["mission"]
    if mission.get("theatre") != terrain or mission.get("requiredModules") != {NATIVE_TYPE: NATIVE_TYPE}:
        raise ValueError(f"{mission_name} has unexpected terrain or module requirements")
    aircraft = [unit for _, _, category, group in groups(mission) if category == "plane"
                for unit in units_of(group)]
    if [(unit.get("skill"), unit.get("type")) for unit in aircraft] != [("Player", NATIVE_TYPE)]:
        raise ValueError(f"{mission_name} must contain one player {NATIVE_TYPE} aircraft")
    validate_scores(mission, mission_name)


def validate_package(profile, manifest, files):
    """Read back the installed files, campaign descriptor and native lesson rules."""
    packfmt.verify(manifest, files)
    if (manifest.get("id"), manifest.get("version")) != (profile["id"], profile["version"]):
        raise ValueError("The pack identity does not match the First Flight profile")
    if (manifest.get("docs") or {}).get("campaign") != profile["archive"]:
        raise ValueError("The pack does not link the campaign ZIP")
    campaign_files = zip_contents(files[profile["archive"]])
    campaign = lua.loads(campaign_files[f"{CAMPAIGN_FOLDER}/{CAMPAIGN_NAME}"].decode("utf-8"))["campaign"]
    if campaign.get("startStage") != 1 or campaign.get("necessaryUnits") != {NATIVE_TYPE: NATIVE_TYPE}:
        raise ValueError("The campaign has an unexpected starting stage or module requirement")
    syllabus = manifest.get("syllabus") or []
    stages = campaign.get("stages") or {}
    if len(syllabus) != len(profile["lessons"]) or set(stages) != set(range(1, len(syllabus) + 1)):
        raise ValueError("The campaign and syllabus must contain the authored stages in order")
    for n, (lesson, published) in enumerate(zip(profile["lessons"], syllabus, strict=True), 1):
        mission_name = lesson["mission"]
        brief_name = f"{Path(mission_name).stem}-brief.pdf"
        mission_path, brief_path = f"missions/{mission_name}", f"briefs/{brief_name}"
        stage = stages[n].get("missions") or {}
        expected_links = {"mission": mission_path, "brief": brief_path}
        if published.get("n") != n or published.get("files") != expected_links:
            raise ValueError(f"The syllabus does not link the mission and brief for {lesson['id']}")
        if set(stage) != {1} or stage[1].get("file") != mission_name:
            raise ValueError(f"The campaign does not link the mission for {lesson['id']}")
        if stage[1].get("interval") != {1: 0, 2: 100} or stage[1].get("skipScore") != 100:
            raise ValueError(f"The campaign score interval or skip score changed for {lesson['id']}")
        if (campaign_files.get(f"{CAMPAIGN_FOLDER}/{mission_name}") != files[mission_path]
                or campaign_files.get(f"{CAMPAIGN_FOLDER}/Briefs/{brief_name}") != files[brief_path]):
            raise ValueError(f"The campaign and pack contain different files for {lesson['id']}")
        if not files[brief_path].startswith(b"%PDF-"):
            raise ValueError(f"{brief_name} is not a PDF")
        validate_mission(files[mission_path], mission_name, profile["map"]["label"])


def profile_for_campaign():
    return next(p for p in load_json("first_flight")["profiles"] if p["id"] == PROFILE_ID)


def package(native: Path, out: Path):
    profile = profile_for_campaign()
    version = profile["version"]
    folder = CAMPAIGN_FOLDER
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
    campaign = (native / CAMPAIGN_NAME).read_bytes()
    campaign_files = {"INSTALL.txt": readme_bytes, f"{folder}/{CAMPAIGN_NAME}": campaign}
    pack_files = {"INSTALL.txt": readme_bytes}
    syllabus = []
    for n, lesson in enumerate(profile["lessons"], 1):
        mission_name = lesson["mission"]
        brief_name = f"{Path(mission_name).stem}-brief.pdf"
        mission = (native / "illustrated" / mission_name).read_bytes()
        brief = (native / "illustrated" / brief_name).read_bytes()
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
    validate_package(profile, manifest, pack_files)
    pack_files["pack.json"] = packfmt.dumps(manifest).encode("utf-8")
    out.mkdir(parents=True, exist_ok=True)
    archive_name = Path(profile["archive"]).name
    (out / archive_name).write_bytes(campaign_zip)
    (out / Path(archive_name).with_suffix(".sspack")).write_bytes(zip_bytes(pack_files))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("native", type=Path, nargs="?", help="native mission build with illustrated/ outputs")
    parser.add_argument("out", type=Path, nargs="?", help="folder for campaign ZIP and Library .sspack")
    parser.add_argument("--check", type=Path, help="validate an existing .sspack without rebuilding it")
    args = parser.parse_args()
    try:
        if args.check is not None:
            if args.native is not None or args.out is not None:
                parser.error("use either --check PACK or NATIVE OUT")
            files = zip_contents(args.check.read_bytes())
            validate_package(profile_for_campaign(), json.loads(files["pack.json"]), files)
            print(f"Verified campaign, syllabus, native mission scoring and kneeboards in {args.check}")
        else:
            if args.native is None or args.out is None:
                parser.error("provide NATIVE OUT or --check PACK")
            package(args.native, args.out)
    except (BadZipFile, KeyError, OSError, ValueError) as error:
        parser.exit(1, f"First Flight package error: {error}\n")


if __name__ == "__main__":
    main()
