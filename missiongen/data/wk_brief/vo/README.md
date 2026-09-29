# Coached B'NAI — WSO voice lines

Drop `wk_bnai_<phase>.wav` in here and the next build wires it to that cue.

The filenames are not a convention to remember: `docs/WK_BNAI_VOICEOVER.md` is
generated from `missiongen/wk_coach.py`, which is the same list the mission
triggers are built from, so the sheet cannot ask for a name the mission does
not look for.

A missing file costs exactly one line. The picture and the text still fire, on
the same trigger, at the same instant.
