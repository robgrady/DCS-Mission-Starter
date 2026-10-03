#!/usr/bin/env python3
"""Insert the White Knights tracks into mission_templates.json and tracks.json.

IDEMPOTENT. Run it twice and the second run is a no-op. It rewrites the entries
it owns and touches nothing else, so re-running after editing `missiongen/wk.py`
is the intended way to keep the two files in step.

WHY A SCRIPT AND NOT HAND-EDITED JSON
-------------------------------------
Twenty cards with the same twelve fields is exactly the shape that acquires a
typo nobody notices — one card with `"era": "modern"`, one with the aircraft key
spelled the display way. The ride list, the labels and the map whitelists all
come out of `missiongen/wk.py`, so there is ONE source for what a ride is, and
this file only decides what a card looks like.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from missiongen import wk  # noqa: E402

DATA = ROOT / "missiongen" / "data"
AIRCRAFT = "F_4E_45MC"
ERA = "coldwar"

# Home fields. Germany: Ramstein, because that is where the 1980 CONUS F-4E
# rotation actually went (4 TFW, 336/334 TFS, Aug-Sep 1980) and where the
# Tactical Air Meet was held that June. Sinai: Cairo West for the deployment,
# Beni Suef for the checkout — it carries parallel 18R/18L, which is the runway
# designator on the squadron's own CQT diagram.
HOME = {"germany": "Ramstein", "sinai": "Beni Suef"}
HOME_PP = "Cairo West"

# Per-ride library blurb. One sentence, no promises the mission cannot keep.
PREMISE = {
    "wk_1_stepstart": "Step, start, taxi and the tactical split — on the "
                      "squadron's own comm card, with its own code names.",
    "wk_2_overhead": "Vectors to initial, the tactical overhead, and the "
                     "landing rule about the 4,000-foot marker.",
    "wk_3_cqt": "A stopwatch, not a sortie. Land, de-arm, and turn the "
                "aircraft in forty-five minutes.",
    "wk_4_lineabreast": "Five to seven miles line abreast, and the twenty "
                        "rules that keep two Phantoms out of each other.",
    "wk_5_commout": "Lead turns and nobody transmits. You read it off his "
                    "wing and your pit calls it.",
    "wk_6_ridge": "Crest the ridgeline level, then bunt or roll. Getting this "
                  "wrong is how you commit the nose too low.",
    "wk_7_threats": "Directive first, descriptive immediately after. Beam it, "
                    "chaff it, and keep going.",
    "wk_8_abort": "The ride designed to go wrong: inadvertent IMC, and the "
                  "abort altitude you computed before you left.",
    "wk_9_intercepts": "Forty-five degrees of bank, two minutes outbound, and "
                       "two thousand feet of separation until visual.",
    "wk_10_threeship": "Two attacking, one target, and a hard altitude block "
                       "that does not move when the roles rotate.",
    "wk_11_bfm": "The squadron's own directive calls, made to you as the "
                 "fight develops. Sixteen of them, with their parameters.",
    "pp_1_drag": "Twelve Phantoms got to Egypt somehow. A/A TACAN sixty-three "
                 "digits apart, and a refuelling order of 1, 3, 2, 4.",
    "pp_2_lald": "Fifteen degrees, two thousand feet, a hundred and twenty-one "
                 "mils. The shallowest delivery on the sheet.",
    "pp_3_dive30": "A real pop — forty-five degree climb, ten thousand foot "
                   "apex — and the wind corrections appear.",
    "pp_4_hidrag": "Pickling at a thousand feet, where your own weapons are "
                   "the threat. Everything after this exists because of frag.",
    "pp_5_divetoss": "If your DT works, press on. If it doesn't, revert at the "
                     "aim off distance and fly the direct.",
    "pp_6_echelon": "Same hemisphere, mutual support all the way to the pop, "
                    "and a five-second delay that keeps you out of trail.",
    "pp_7_double90": "Turn ninety into lead, hold eight seconds on his bomb "
                     "detonation, then ninety back. Frag clearance by clock.",
    "pp_8_bnai_coach": "The B'NAI with somebody in the pit. A cue on the "
                       "squadron's own drawing at every decision, and the "
                       "whole sequence re-arms so you can run it again.",
    "pp_8_bnai": "Israeli, 1973, built for the SA-6 — flown over the ground it "
                 "was invented on, with an SA-6 in the mission. No coaching: "
                 "this is ride 8 with the calls switched off.",
    "pp_9_splithigh": "The squadron's primary attack, taught last. Lead turns "
                      "30 and pops; you turn 45 and pop for almost ninety "
                      "degrees of angle off, above his frag.",
    "pp_9_split": "Two aimpoints ten thousand feet apart and a near head-on "
                  "egress. The hardest ride, and the guide says why.",
}

# Threat rating for the Library chip. The checkout is training; the attacks
# carry a real air defense.
THREAT = {"wk_1_stepstart": 1, "wk_2_overhead": 1, "wk_3_cqt": 1,
          "wk_4_lineabreast": 1, "wk_5_commout": 1, "wk_6_ridge": 1,
          "wk_7_threats": 3, "wk_8_abort": 1, "wk_9_intercepts": 2,
          "wk_10_threeship": 2, "wk_11_bfm": 2,
          "pp_1_drag": 1, "pp_2_lald": 1, "pp_3_dive30": 1, "pp_4_hidrag": 2,
          "pp_5_divetoss": 2, "pp_6_echelon": 3, "pp_7_double90": 3,
          "pp_8_bnai_coach": 4, "pp_8_bnai": 4,
          "pp_9_splithigh": 3, "pp_9_split": 3}


def recipe_for(key: str, ride: dict) -> dict:
    """The base recipe. Deliberately quiet: these are training sorties and a
    card that spawns an unbriefed AWACS is a card that lied about what is in
    the mission."""
    rc = {
        "aircraft": AIRCRAFT,
        # THE SQUADRON'S OWN CALLSIGN, from Standards Section II — "REX 1,
        # loud and clear", "REX 2 BREAK RIGHT". Set per card rather than in
        # callsigns.json, because REX belongs to the 70th and not to every
        # F-4E in the product.
        "callsign": "REX",
        "start": "warm",
        "bb_tanker": False,
        "bb_awacs": False,
        "bb_targets": False,
        "bb_ambient": False,
        "threat_intensity": 1,
        "time_of_day": "day",
        "weather": "clear",
    }
    n, track = ride["n"], ride["track"]
    if track == "wk_checkout":
        rc["home_airbase"] = HOME["germany"]
        if key == "wk_3_cqt":
            rc["start"] = "cold"          # the CQT ride begins on the chocks
        if key in ("wk_9_intercepts", "wk_10_threeship", "wk_11_bfm"):
            rc["start"] = "air"           # working area, over water
        if key == "wk_11_bfm":
            rc.update(bb_bfm=True, bfm_setup="neutral")
        if key == "wk_7_threats":
            rc.update(bb_sams=True, threat_intensity=3, threat_tier="mixed")
        if key == "wk_8_abort":
            rc["weather"] = "overcast"    # the ride is ABOUT the weather
        if key == "wk_6_ridge":
            rc["weather"] = "scattered"
    else:
        rc["home_airbase"] = HOME_PP
        if key == "pp_1_drag":
            rc.update(bb_tanker=True, tanker_type="kc135", start="air")
        if ride.get("delivery"):
            rc.update(bb_range=True)
        if key == "pp_4_hidrag":
            rc["weather"] = "overcast"    # low ceiling: what the Double 90 is for
        if ride.get("attack"):
            rc.update(bb_targets=True, threat_intensity=2)
        if key in ("pp_8_bnai", "pp_8_bnai_coach"):
            rc.update(bb_sams=True, threat_intensity=3, threat_tier="mixed")
        if key in ("pp_9_split", "pp_9_splithigh"):
            rc["threat_intensity"] = 3
    return rc


def card(key: str, ride: dict) -> dict:
    track = ride["track"]
    checkout = track == "wk_checkout"
    maps = wk.maps_for(key) or ["germany", "sinai"]
    default_map = maps[0] if not checkout else "germany"
    lbl_track = "Squadron Checkout" if checkout else "Proud Phantom"
    out = {
        "label": f"70 TFS White Knights {ride['n']} ({lbl_track}) — "
                 f"{ride['title']}",
        "eras": [ERA],
        "maps": list(maps),
        "default_map": default_map,
        "quick": False,
        "library": {
            "role": "training",
            "threat": THREAT[key],
            "players": "SP",
            "new": True,
            "featured": False,
            "module": "F-4E",
            "premise": PREMISE[key],
        },
        "recipe": recipe_for(key, ride),
        "wk_ride": key,
        "track": {"id": track, "n": ride["n"]},
    }
    out["historical"] = {"scenario_date": "1980-06-21",
        "historical_notes": ["The 1980 squadron syllabus is adapted to DCS. The date is an authored training reference; these are not archived individual sorties."]}
    if "sinai" in maps:
        out["historical_by_map"] = {"sinai": {"scenario_date": "1980-07-10"}}
    # Per-map overrides. The only field that actually changes is where you
    # start from; everything else the theater changes is derived in the brief.
    if checkout and "sinai" in maps:
        out["by_map"] = {"sinai": {"home_airbase": HOME["sinai"]}}
    return out


TRACKS = {
    "wk_checkout": {
        "label": "70th TFS White Knights — Squadron Checkout (F-4E, 1980)",
        "short": "White Knights · Checkout",
        "role": "training",
        "service": "USAF",
        "aircraft": AIRCRAFT,
        "eras": [ERA],
        "default_map": "germany",
        "guide": "white-knights-checkout",
        "featured": True,
        "series": "The White Knights, 1980",
        "premise": "Eleven rides from the three documents a new arrival at the "
                   "70th was handed in January and February 1980 — Standards, "
                   "Low Level Training, and Weapons Information Sheet No. 1. "
                   "Everything that makes you a wingman, and not a bomb "
                   "between them. Ends when you are signed off on a two-ship.",
        "blurb": [
            "The 347th was drafted into NATO contingency plans and never flew",
            "to Europe in the Phantom. This is the war it was assigned, flown",
            "as the plan. Your squadron's low-level contract meets a host",
            "nation with its own floor, and the card prints both numbers and",
            "tells you which one governs.",
        ],
    },
    "wk_proud_phantom": {
        "label": "70th TFS White Knights — Proud Phantom, Egypt 1980",
        "short": "White Knights · Proud Phantom",
        "role": "training",
        "service": "USAF",
        "aircraft": AIRCRAFT,
        "eras": [ERA],
        "default_map": "sinai",
        "guide": "white-knights-proud-phantom",
        "featured": True,
        "series": "The White Knights, 1980",
        "follows": "wk_checkout",
        "premise": "From 10 July to 3 October 1980 the 70th TFS flew twelve F-4Es "
                   "out of Cairo West, Egypt. Ten rides from the squadron's "
                   "Conventional Tactics guide of 27 January 1980 — five "
                   "delivery planning sheets and ALL FIVE two-ship attacks, "
                   "both halves of the split included — flown from the base "
                   "they actually deployed to. The B'NAI is taught twice: "
                   "once with a cue at every decision, once with nothing.",
        "blurb": [
            "The B'NAI attack was designed by the Israelis in the 1973 war to",
            "survive an SA-6 environment. Your squadron wrote it down five",
            "months before it deployed here. Fly it on this map and you are",
            "flying it over the ground it was invented on, with an SA-6 in",
            "the mission.",
        ],
    },
}


def main():
    tp = DATA / "mission_templates.json"
    tk = DATA / "tracks.json"
    templates = json.loads(tp.read_text())
    tracks = json.loads(tk.read_text())

    added = updated = 0
    for _n, key, ride in (wk.rides_in("wk_checkout")
                          + wk.rides_in("wk_proud_phantom")):
        new = card(key, ride)
        if key in templates:
            if templates[key] != new:
                updated += 1
            templates[key] = new
        else:
            templates[key] = new
            added += 1

    for tid, t in TRACKS.items():
        tracks[tid] = t

    tp.write_text(json.dumps(templates, indent=1, ensure_ascii=False) + "\n")
    tk.write_text(json.dumps(tracks, indent=1, ensure_ascii=False) + "\n")
    print(f"templates: +{added} new, {updated} updated, "
          f"{len(templates)} total")
    print(f"tracks: {sorted(tracks)}")


if __name__ == "__main__":
    main()
