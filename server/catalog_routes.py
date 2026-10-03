"""DCS Sortie Starter — API server.

Run:  uvicorn server.app:app --reload
Then open http://127.0.0.1:8000
"""
import logging

from fastapi import APIRouter

from missiongen import Recipe, __version__
from missiongen.recipe import Recipe, RECIPE_ENUMS
from missiongen.resolver import load_json
from missiongen import deck as _deck
from missiongen import courses as _courses_mod
from missiongen import aar as _aar_mod
from missiongen import lineup as _lineup_mod

log = logging.getLogger("missionstarter")

from .library_routes import _pack_templates, _published_tracks

router = APIRouter()

def _theme_mix(theme):
    """Flatten a ramp theme's weighted planes/large/helos lists into a default
    {type_id: count} composition the Ramp Composer pre-populates from. Weights
    double as sensible starting counts (a Red Flag ramp is authored that way)."""
    mix = {}
    for key in ("planes", "large", "helos"):
        for entry in theme.get(key, []):
            ref = entry[0]
            weight = entry[1] if len(entry) > 1 else 1
            tid = ref.split(".")[-1]
            mix[tid] = mix.get(tid, 0) + int(weight)
    return mix


def flyable_aircraft():
    """FR-1: every current flyable DCS aircraft, straight from the pydcs unit DB."""
    import dcs.planes as planes
    import dcs.helicopters as helicopters
    out = []
    for mod, kind in ((planes, "plane"), (helicopters, "helicopter")):
        for name in dir(mod):
            if name.startswith("_"):
                continue
            cls = getattr(mod, name)
            if isinstance(cls, type) and getattr(cls, "flyable", False):
                out.append({"key": name, "id": cls.id, "kind": kind,
                            "can_refuel": _aar_mod.can_refuel(cls.id)})
    out.sort(key=lambda a: a["id"])
    service = load_json("aircraft_service")
    for a in out:
        a["service"] = service.get(a["key"])   # [from, to|null] or null=unknown
    # modules pydcs has no native class for; verified ones list as normal jets
    from missiongen.pending import pending_aircraft
    for key, cfg in pending_aircraft().items():
        # a verified/released module is a normal selectable jet, not "upcoming"
        out.append({"key": key, "id": cfg["label"], "kind": cfg["kind"],
                    "service": service.get(key),
                    "can_refuel": _aar_mod.can_refuel(cfg["provisional_id"]),
                    "upcoming": not cfg.get("verified", False)})
    # re-sort AFTER appending pending modules so e.g. the F-14B(U) alphabetizes
    # into the F-14 cluster instead of dangling at the bottom of the dropdown
    # where nobody scanning the roster finds it.
    out.sort(key=lambda a: a["id"])
    return out


@router.get("/api/options")
def options():
    maps = load_json("maps")
    eras = load_json("eras")
    from missiongen.historical_world import preview, template_previews
    return {
        "version": __version__,
        # Formation departures (pattern_lineup) exist only when lineup.py
        # holds a verified DCS encoding; the Builder hides the knob otherwise.
        "lineup_supported": _lineup_mod.supported(),
        "maps": {k: {"label": v["label"], "free": v["free"],
                     "has_carrier": "carrier" in v,
                     "lineups": v.get("lineups", {}),
                     "presets": {e: {"blue_airbases": p["blue_airbases"],
                                     "red_airbases": p["red_airbases"],
                                     "blue_country": p["blue_country"],
                                     "red_country": p["red_country"],
                                     "civilian_airbases": p.get("civilian_airbases", []),
                                     "historical_context": preview(k, e)}
                                 for e, p in v["presets"].items()}}
                 for k, v in maps.items()},
        "eras": {k: {"label": v["label"], "window": v.get("window")}
                 for k, v in eras.items()},
        "aircraft": flyable_aircraft(),
        "air_corridors": {k: v for k, v in load_json("air_corridors").items()
                          if not k.startswith("_")},
        "recipe_defaults": Recipe().to_dict(),
        "templates": {
            # kind: "full" = the .miz places a flown route/waypoints (crew-ops);
            # "open" = a dressed theater, no waypoints placed (you fly/build it).
            # tasked = ships a suggested-tasking brief. Scenario templates are open
            # starters (north star: no flight plan you did not ask for —
            # strike routes, training syllabi and the opt-in tickbox are the
            # three asks), most
            # with a suggested-tasking brief; crew-ops are full missions.
            **{k: {"label": v["label"], "eras": v.get("eras", []),
                   "maps": v.get("maps"), "needs_carrier": v.get("needs_carrier", False),
                   "needs_acls": v.get("needs_acls", False),
                   "recipe": v.get("recipe", {}),
                   # per-era overrides (see missiongen/templates.py): a card that
                   # spans eras cannot pin one aircraft
                   "by_era": v.get("by_era") or {},
                   "by_map": v.get("by_map") or {},
                   "historical_context": template_previews(k),
                   # per-era list of airframes this card is willing to fly.
                   # Formation training uses it so the Library can offer a
                   # choice instead of pinning one jet — the syllabus is
                   # airframe-agnostic and pinning made it look F-16-only.
                   "aircraft_choices": v.get("aircraft_choices") or {},
                   # Track membership. The Library uses it to keep a track's
                   # rides OUT of the loose grid — without it every ride shows
                   # twice, once in its track and once alphabetically.
                   "track": v.get("track"),
                   "kind": (v.get("library") or {}).get("kind", "open"),
                   "tasked": bool(v.get("brief")),
                   # quick: owned by the Quick Flight picker, hidden in Library
                   "quick": v.get("quick", False),
                          "library": v.get("library"), "default_map": v.get("default_map")}
               for k, v in load_json("mission_templates").items()
               # Pack reconciliation: a pack card only exists if its .miz
               # actually shipped. A deploy without packs/ (e.g. the core zip
               # alone) hides the cards instead of showing twelve broken
               # download buttons; /api/health lists what's missing.
               if not k.startswith("_")},
            # packs live on the volume, uploaded via /admin — merged in here so
            # the Library treats them exactly like built-in templates
            **_pack_templates(),
            "backseat_izlid": {"kind": "full", "tasked": True, "label": "F-14B(U) Pilot + Jester: IZLID Strike — you fly, Jester designates on your call",
                               "eras": ["modern"], "aircraft_locked": True, "default_map": "caucasus",
                               "recipe": {"aircraft": "F_14B_U"},
                               "library": {"role": "strike", "new": True, "featured": True, "module": "F-14B(U)",
                                           "threat": 3, "players": "SP",
                                           "premise": "You fly, Jester works the back seat — run the IZLID designation on your call through the F10 crew menu."}},
            "backseat_intercept": {"kind": "full", "tasked": True, "label": "F-14B(U) RIO + Iceman: GCI Intercept — Iceman flies YOUR calls from the back seat",
                                   "eras": ["modern"], "aircraft_locked": True, "default_map": "caucasus",
                                   "recipe": {"aircraft": "F_14B_U"},
                                   "library": {"role": "a2a", "new": True, "featured": True, "module": "F-14B(U)",
                                               "threat": 3, "players": "SP",
                                               "premise": "You're the RIO; Iceman flies your calls from the front seat — build the AWG-9 picture and commit on the raid."}},
            "rio_fleet_defense": {"kind": "full", "tasked": True, "label": "F-14 RIO: Fleet Defense — the AWG-9 vs a Backfire raid (solo or MP crew, works today)",
                                  "eras": ["coldwar", "modern"], "aircraft_locked": True, "default_map": "caucasus",
                                  "recipe": {"aircraft": "F_14B"},
                                  "library": {"role": "a2a", "new": True, "featured": True, "module": "F-14B(U)",
                                              "threat": 4, "players": "SP · MP",
                                              "premise": "Classic Tomcat outer-air-battle — manage the Phoenix picture against a saturating raid on the fleet."}},
        },
        # Training tracks: ordered sets of the cards above. The Library renders
        # one grouped card per track instead of eleven loose ones, and each
        # ride still opens as the ordinary card it is.
        # `published` says whether a whole-syllabus download exists for this
        # track — i.e. whether somebody has produced and uploaded its pack.
        # Without it the UI would keep offering a button that now answers 409,
        # which is a worse experience than the 502 it replaced: at least the
        # 502 looked like a failure.
        "tracks": _published_tracks(),
        # Training COURSES: the pipeline above the tracks (missiongen/courses.py).
        # Summaries only; the Pipeline door fetches a course in full on open.
        "courses": _courses_mod.summaries(),
        # Tanker labels and track figures, so the wizard can name what it is
        # offering instead of printing a key like "kc135mprs".
        "tankers": {k: {"label": v["label"], "boom": v["boom"],
                        "ias_kt": v["ias_kt"], "alt_ft": v["alt_ft"],
                        "callsign": v["callsign"]}
                    for k, v in _aar_mod.TANKERS.items()},
        "ramp_themes": {
            era: {side: {k: {"label": t["label"], "desc": t["desc"],
                             "mix": _theme_mix(t)}
                         for k, t in sides.items() if k != "default"}
                  for side, sides in eras_t.items()}
            for era, eras_t in load_json("ramp_themes").items()
            if isinstance(eras_t, dict)},
        "map_theme_defaults": {
            mk: {e: {s: p.get(f"{s}_theme") for s in ("blue", "red")}
                 for e, p in mv["presets"].items()}
            for mk, mv in maps.items()},
        "carriers": _deck.hulls_for_options(),
        "carrier_capable": load_json("carrier_capable"),
        "static_catalog": load_json("static_catalog"),
        "enums": {
            # "air" was omitted here because air starts used to be
            # template-only. They are not any more — the formation syllabus
            # REQUIRES one — and a value the engine accepts but the UI never
            # offers is worse than either: opening an air-start card in the
            # Builder set `start = "air"` on a <select> with no such option, so
            # the control silently showed nothing and the setting was lost the
            # moment anything else was changed.
            "start": list(RECIPE_ENUMS["start"]),
            "time_of_day": ["dawn", "day", "dusk", "night"],
            "weather": ["clear", "scattered", "overcast", "storm"],
            "density": ["sparse", "normal", "busy"],
            "pattern_mode": ["landing", "takeoff", "both"],
            "pattern_kind": ["fighter", "cargo", "helicopter", "mixed"],
        },
    }

