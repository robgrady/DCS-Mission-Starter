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
    Recipe(map="syria", era="modern", aircraft="F_16C_50", seed=7),
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
    for r in SAMPLES:
        tag = r.template or "starter"
        out = outdir / f"{r.map}_{r.era}_{r.aircraft}_{tag}_{r.seed}.miz"
        result = generate(r, str(out))
        n = validate_miz(out)
        print(f"OK {out.name}: {result['stats']['statics']} statics, "
              f"{len(result['stats']['sam_sites'])} AD groups, "
              f"{n} files in miz, warnings={result['warnings']}")
