"""Expose installed First Flight campaign presets without generating missions."""

from fastapi import APIRouter, Response

from missiongen import packs
from missiongen.resolver import load_json

router = APIRouter()


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
        files = {record["path"] for record in manifest.get("files") or []}
        if archive not in files or packs.get_file(pack_id, archive) is None:
            continue
        expected = [f"missions/{lesson['mission']}" for lesson in profile["lessons"]]
        installed = [
            lesson.get("files", {}).get("mission")
            for lesson in manifest.get("syllabus") or []
        ]
        if installed != expected or any(
            mission not in files or packs.get_file(pack_id, mission) is None
            for mission in expected
        ):
            continue
        public = {key: value for key, value in profile.items() if key != "archive"}
        public["lessons"] = [
            {key: value for key, value in lesson.items() if key != "mission"}
            for lesson in profile["lessons"]
        ]
        public["download_url"] = f"/api/pack/{pack_id}/{archive}"
        choices.append(public)
    return {"profiles": choices}
