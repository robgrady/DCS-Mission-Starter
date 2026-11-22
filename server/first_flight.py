"""Expose installed First Flight campaign presets without generating missions."""

from urllib.parse import quote

from fastapi import APIRouter, Response

from missiongen import packs
from missiongen.resolver import load_json

router = APIRouter()


def _lesson_files(profile, manifest):
    expected = [f"missions/{lesson['mission']}" for lesson in profile["lessons"]]
    installed = [lesson.get("files") or {} for lesson in manifest.get("syllabus") or []]
    if [lesson.get("mission") for lesson in installed] != expected:
        return None
    return [(entry["mission"], entry.get("brief") or "") for entry in installed]


def _pack_url(pack_id, path):
    return f"/api/pack/{quote(pack_id, safe='')}/{quote(path)}"


@router.get("/api/first-flight")
def first_flight(response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    choices = []
    for profile in load_json("first_flight")["profiles"]:
        pack_id = profile["id"]
        manifest = packs.get_manifest(pack_id)
        if not manifest or manifest.get("version") != profile["version"]:
            continue
        archive = profile["archive"]
        lessons = _lesson_files(profile, manifest)
        if lessons is None or any(not brief.lower().endswith(".pdf") for _, brief in lessons):
            continue
        declared = {record["path"] for record in manifest.get("files") or []}
        required = {archive, *(path for lesson in lessons for path in lesson)}
        if not required <= declared or any(packs.get_file(pack_id, path) is None for path in required):
            continue
        public = {key: value for key, value in profile.items() if key != "archive"}
        public["lessons"] = []
        for lesson, (mission, brief) in zip(profile["lessons"], lessons, strict=True):
            entry = {key: value for key, value in lesson.items() if key != "mission"}
            entry["mission_url"] = _pack_url(pack_id, mission)
            entry["brief_url"] = _pack_url(pack_id, brief) + "?inline=1"
            public["lessons"].append(entry)
        public["download_url"] = _pack_url(pack_id, archive)
        choices.append(public)
    return {"profiles": choices}
