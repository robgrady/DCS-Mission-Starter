"""Archived unit observations are opt-in native map drawings."""

from datetime import datetime

from dcs import Mission
import pytest

from missiongen import Recipe, generate
from missiongen.historical_deployments import add_deployment_references
from missiongen.resolver import load_json, resolve_terrain
from scripts.audit_library import inspect_archive


def _native_drawings(native):
    return [
        obj
        for layer in native["drawings"]["layers"].values()
        for obj in layer.get("objects", {}).values()
    ]


@pytest.mark.parametrize(("map_key", "day", "aircraft", "expected"), [
    ("afghanistan", "2010-01-01", "A_10C", {
        "Kandahar": ("Kandahar", ["354th EFS | A-10C"]),
    }),
    ("iraq", "2007-01-28", "F_16C_50", {
        "Balad": ("Balad Airbase", ["14th EFS | F-16", "510th EFS | F-16",
                                    "332nd EFS | F-16"]),
        "Al Asad": ("Al-Asad Airbase", ["74th EFS | A-10"]),
    }),
])
def test_deployment_squares_serialize_at_the_airfields(
    tmp_path, map_key, day, aircraft, expected
):
    common = dict(
        map=map_key, era="gwot", aircraft=aircraft, mission_date=day, seed=813,
        player_arm=False, bb_dressing=False, bb_ambient=False, bb_sams=False,
        bb_tanker=False, bb_awacs=False, bb_kneeboard=False, bb_navpoints=False,
    )
    before = tmp_path / "without-references.miz"
    after = tmp_path / "with-references.miz"
    generate(Recipe(**common, bb_historical_airspace=False), str(before))
    result = generate(Recipe(**common, bb_historical_airspace=True), str(after))

    original = inspect_archive(before)
    native = inspect_archive(after)
    unmarked = _native_drawings(original)
    assert all(not obj["name"].startswith("Historical deployment: ") for obj in unmarked)
    assert all(f"ARCHIVE {day}" not in obj.get("text", "") for obj in unmarked)

    marked = _native_drawings(native)
    squares = {
        obj["name"].removeprefix("Historical deployment: "): obj
        for obj in marked if obj["name"].startswith("Historical deployment: ")
    }
    labels = {
        obj["text"].split(" | ARCHIVE", 1)[0]: obj
        for obj in marked if f" | ARCHIVE {day}" in obj.get("text", "")
    }
    assert squares.keys() == labels.keys() == expected.keys()
    terrain = resolve_terrain(load_json("maps")[map_key]["terrain_class"])()
    for base, (key, assignments) in expected.items():
        square = squares[base]
        point = terrain.airports[key].position
        assert (square["mapX"], square["mapY"]) == pytest.approx((point.x, point.y))
        assert square["layerName"] == labels[base]["layerName"] == "Common"
        assert square["polygonMode"] == "rect" and square["width"] == square["height"]
        assert square["fillColorString"].endswith("00")
        assert all(assignment in labels[base]["text"] for assignment in assignments)
    assert len(result["stats"]["historical_deployments"]) == sum(
        len(assignments) for _, assignments in expected.values()
    )
    assert f"ARCHIVAL AIRFIELD OBSERVATIONS | {day}" in "\n".join(
        native["embedded_text"].values()
    )
    assert native["groups"] == original["groups"]


def test_archival_observation_does_not_carry_to_the_next_day():
    terrain = resolve_terrain(load_json("maps")["afghanistan"]["terrain_class"])()
    mission = Mission(terrain)
    mission.start_time = datetime(2010, 1, 2)
    assert add_deployment_references(mission, "afghanistan") == ([], [])
    assert not mission.drawings.get_layer_by_name("Common").objects


def test_archival_observation_creates_no_trigger_zone():
    terrain = resolve_terrain(load_json("maps")["afghanistan"]["terrain_class"])()
    mission = Mission(terrain)
    mission.start_time = datetime(2010, 1, 1)
    before = mission.triggers.dict()
    drawn, _ = add_deployment_references(mission, "afghanistan")
    assert len(drawn) == 1
    assert mission.triggers.dict() == before
