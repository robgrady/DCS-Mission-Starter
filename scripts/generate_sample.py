#!/usr/bin/env python3
"""CLI smoke test: generate sample starters for both maps."""
import sys, json, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from missiongen import Recipe, generate

SAMPLES = [
    Recipe(map="caucasus", era="coldwar", aircraft="F_4E_45MC", seed=42),
    Recipe(map="caucasus", era="coldwar", aircraft="F_4E_45MC", seed=42,
           template="backseat_izlid"),
    Recipe(map="caucasus", era="coldwar", aircraft="F_4E_45MC", seed=5,
           template="backseat_intercept"),
    Recipe(map="syria", era="modern", aircraft="F_16C_50", seed=7),
    Recipe(map="thechannel", era="wwii", aircraft="SpitfireLFMkIX", seed=44),
    # Roosevelt, recovery deck: LA clear, deck spotted forward, helos in the corral
    Recipe(map="syria", era="modern", aircraft="FA_18C_hornet", seed=31,
           bb_carrier=True, carrier_hull="cvn_71", carrier_layout="recovery",
           carrier_deck_aircraft=["FA_18C_hornet", "F_14B", "E_2C", "SH_60B"],
           carrier_cap=True, carrier_aew=True),
    # Roosevelt, launch deck: cats + taxi flow clear, spares aft
    Recipe(map="syria", era="modern", aircraft="FA_18C_hornet", seed=32,
           bb_carrier=True, carrier_hull="cvn_71", carrier_layout="launch",
           carrier_deck_aircraft=["FA_18C_hornet", "E_2C", "SH_60B"]),
    # Forrestal, coldwar recovery deck with Tomcats
    Recipe(map="caucasus", era="coldwar", aircraft="F_14A_135_GR", seed=33,
           bb_carrier=True, carrier_hull="forrestal", carrier_layout="recovery",
           carrier_deck_aircraft=["F_14A", "E_2C", "S_3B"],
           carrier_cap=True, carrier_aew=True),
    # Persian Gulf everything: Truman launch deck, FARPs, targets, range
    Recipe(map="persiangulf", era="modern", aircraft="AH_64D_BLK_II", seed=51,
           bb_carrier=True, carrier_hull="cvn_75", carrier_layout="launch",
           carrier_deck_aircraft=["FA_18C_hornet", "S_3B"],
           bb_farps=True, bb_targets=True, bb_range=True),
    # RIO fleet defense: MP crew Tomcats vs a Backfire raid off Guam
    Recipe(map="marianas", era="modern", aircraft="F_14B", seed=88,
           template="rio_fleet_defense", bb_carrier=True, carrier_hull="cvn_73",
           carrier_layout="launch", carrier_deck_aircraft=["F_14B", "E_2C"]),
    # NTTR red flag: Nellis vs Groom Lake/Tonopah, nav points + targets + range
    Recipe(map="nevada", era="modern", aircraft="F_16C_50", seed=75,
           bb_targets=True, bb_range=True),
    # South Atlantic 1982: HMS Invincible task force, Harriers, no AEW (history)
    Recipe(map="falklands", era="coldwar", aircraft="AV8BNA", seed=82,
           bb_carrier=True, carrier_hull="invincible", carrier_layout="recovery",
           carrier_deck_aircraft=["AV8BNA"], carrier_cap=True),
    # Marianas: GW (CSG-5) launch deck west of Guam vs the northern islands
    Recipe(map="marianas", era="modern", aircraft="FA_18C_hornet", seed=61,
           bb_carrier=True, carrier_hull="cvn_73", carrier_layout="launch",
           carrier_deck_aircraft=["FA_18C_hornet", "E_2C", "SH_60B"],
           carrier_cap=True, carrier_aew=True),
]


def validate_miz(path):
    """Structural validation: proper zip, mission Lua parses as a table."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        assert "mission" in names, f"no mission file in {names}"
        content = z.read("mission").decode("utf-8", errors="replace")
        assert content.startswith("mission"), "mission Lua doesn't start with table def"
        for key in ('["coalition"]', '["weather"]', '["triggers"]'):
            assert key in content, f"missing {key}"
    return len(names)


if __name__ == "__main__":
    outdir = Path(__file__).parent.parent / "samples"
    outdir.mkdir(exist_ok=True)
    for old in outdir.glob("*.miz"):
        old.unlink()
    for r in SAMPLES:
        tag = r.template or (f"{r.carrier_hull}_{r.carrier_layout}" if r.bb_carrier else "starter")
        out = outdir / f"{r.map}_{r.era}_{r.aircraft}_{tag}_{r.seed}.miz"
        result = generate(r, str(out))
        n = validate_miz(out)
        print(f"OK {out.name}: {result['stats']['statics']} statics, "
              f"{len(result['stats']['sam_sites'])} AD groups, "
              f"{n} files in miz, warnings={result['warnings']}")
