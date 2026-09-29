#!/usr/bin/env python3
"""Cut static instances from the vendored variable fonts.

ReportLab embeds only a variable font's DEFAULT instance, so <b> in prose
had no bold to resolve to. fontTools' instancer cuts real static faces
(OFL permits derivative fonts; the license files ship alongside). Re-run
only if the variable fonts are updated. Idempotent.
"""
import pathlib
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

D = pathlib.Path(__file__).resolve().parent.parent / "missiongen" / "data" / "brand" / "fonts"
CUTS = (("SourceSerif4-VF.ttf", {"wght": 400, "opsz": 20}, "SourceSerif4-Regular.ttf"),
        ("SourceSerif4-VF.ttf", {"wght": 700, "opsz": 20}, "SourceSerif4-Bold.ttf"),
        ("SourceSans3-VF.ttf", {"wght": 400}, "SourceSans3-Regular.ttf"),
        ("SourceSans3-VF.ttf", {"wght": 600}, "SourceSans3-Semibold.ttf"),
        ("SourceSans3-VF.ttf", {"wght": 700}, "SourceSans3-Bold.ttf"))

for src, axes, out in CUTS:
    inst = instancer.instantiateVariableFont(TTFont(D / src), axes, updateFontNames=True)
    inst.save(D / out)
    print("wrote", out)
