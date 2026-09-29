#!/usr/bin/env python3
"""Write the recording sheet for the coached B'NAI — the brief and the cues.

GENERATED, NOT HAND-WRITTEN, and that is the whole point. The mission fires
`wk_brief_<key>.wav` for brief page `<key>` and `wk_bnai_<key>.wav` for cue
`<key>`; a hand-kept recording sheet is a second list of those filenames, and
the failure mode is silent — you record nineteen takes, name one of them the
way the sheet says instead of the way the code says, and that one line is just
quiet with nothing to tell you why. So the sheet comes out of
`wk_brief.PAGES` and `wk_coach.PHASES`, which are the lists the triggers are
built from.

Usage:  PYTHONPATH=.:vendor python3 scripts/build_wk_voiceover_sheet.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from missiongen import wk, wk_brief, wk_coach     # noqa: E402

OUT = ROOT / "docs" / "WK_BNAI_VOICEOVER.md"

# What the pilot is doing when the line lands. Recording direction, not
# geometry — the geometry is in `wk_coach.PHASES` and in the guide, and this
# is the only thing a person at a microphone actually needs that the code
# cannot derive.
DIRECTION = {
    "lowlevel": "Settled, unhurried. Nothing is happening yet and he wants it "
                "to stay that way.",
    "trail": "Businesslike. This is housekeeping before the work starts.",
    "ip": "A shade quicker. The turn is happening now, not in a moment.",
    "runin": "Flat and quiet. This is the line that should make him "
             "uncomfortable — nobody is watching your six.",
    "pup": "Sharp. This is a cue with a two-second window and the whole "
           "attack hangs off it. Loudest line on the sheet.",
    "rollin": "Urgent, but not a shout. He is telling you where to look.",
    "apex": "Half a beat calmer. The airplane is doing the work here.",
    "track": "Clipped, one parameter at a time, like reading a checklist "
             "with the target in the windscreen.",
    "release": "The only line that repeats a word. Say it twice because "
               "that is how it is said.",
    "pullout": "Hard and downward. Get out.",
    "twos_pass": "Alert. You have gone from attacker to cover and the job "
                 "changed completely.",
    "egress": "Level again. The work is done and the decision is a "
              "judgment call, so it should sound like one.",
    "reattack": "Warm. This is the only line on the sheet that is allowed "
                "to sound pleased.",
}

# The six brief pages. These are a DIFFERENT recording job from the cues and
# the sheet says so rather than running them together: the pilot is sitting
# still with his controls locked, reading, so the register is a squadron
# briefer at a lectern rather than a WSO with two seconds to make a call.
BRIEF_DIRECTION = {
    "situation": "Unhurried, slightly formal. This is the opening of a mass "
                 "brief and everybody in the room already knows most of it.",
    "target": "Level, then harden on the SA-6 sentence. That is the one fact "
              "in the brief that explains the whole shape of the attack.",
    "attack": "Instructional. Slow down on the IP turn — it is the sentence "
              "he will get wrong first.",
    "pop": "Numbers, clearly, with a beat between them. The roll-in-below-"
           "apex aside deserves its own pace; it is the thing pilots assume "
           "is a typo.",
    "wingman": "Deliberate. Every clause here is somebody covering somebody.",
    "coaching": "Warmer, and end on 'You have the airplane' as a handover, "
                "not as a sign-off. That line is the moment his controls "
                "come back.",
}

FORMAT = [
    "**Format.** WAV, mono, 44.1 kHz, 16-bit. DCS will play anything it can "
    "decode, but that is what the rest of the product's audio is and matching "
    "it means one fewer thing to rule out when a cue is silent.",
    "**Level.** These play as a COCKPIT sound, not a radio transmission — "
    "the WSO is a foot behind your head, not on a frequency. No radio filter, "
    "no squelch, no compression artifacts. Dry and close.",
    "**Length — the CUES only.** Keep every cue take under four seconds. Its "
    f"picture holds for {wk_coach.HOLD_S} seconds and its text for "
    f"{wk_coach.TEXT_S}, and a call still talking after the moment it "
    "describes has passed is worse than no call. The BRIEF pages have no "
    "such limit: they stay up until the pilot presses SPACE.",
    "**Takes.** Record them in any order. The mission checks each file "
    "separately, so thirteen sessions of one line each works exactly as well "
    "as one session of thirteen.",
]


def markdown() -> str:
    L = [f"# {wk.SQUADRON} — coached B'NAI, WSO recording sheet", "",
         f"*Generated from `missiongen/wk_brief.py` and "
         f"`missiongen/wk_coach.py` — the same two lists the mission's "
         f"triggers are built from. Do not hand-edit: run "
         f"`scripts/build_wk_voiceover_sheet.py` instead, or the filenames "
         f"here and the filenames the mission asks for will drift apart.*",
         "",
         "## Where the files go", "",
         "```",
         f"{wk_brief.AUDIO_DIR.relative_to(ROOT)}/     <- the brief pages",
         f"{wk_coach.AUDIO_DIR.relative_to(ROOT)}/     <- the cues in the air",
         "```", "",
         "Drop a WAV in and the next build wires it to its cue. Drop nothing "
         "in and that cue still shows its picture and prints its text — the "
         "line is optional, one line at a time, so a half-recorded set is a "
         "perfectly good build.", "",
         "## How to record them", ""]
    L += [f"- {s}" for s in FORMAT]
    L += ["", "## Part one — the brief", "",
          f"{len(wk_brief.PAGES)} pages, played before the sortie starts "
          f"while the pilot's controls are locked. These are LONGER than the "
          f"cue lines and the four-second rule does not apply to them — a "
          f"page stays up until he presses SPACE, so take the time the "
          f"sentence needs.", ""]
    for i, (key, head, _pic, text) in enumerate(wk_brief.pages(), start=1):
        L += [f"### B{i}. `{wk_brief.audio_path(key).name}`", "",
              f"> {text}", "",
              f"- **On screen:** the page headed **{head}**.",
              f"- **Delivery:** {BRIEF_DIRECTION.get(key, '')}", ""]
    L += ["", "## Part two — the cues in the air", "",
          f"{len(wk_coach.PHASES)} lines, in the order you hear them.", ""]
    for i, (key, marker, directive, call, after) in enumerate(
            wk_coach.PHASES, start=1):
        L += [f"### C{i}. `{wk_coach.audio_path(key).name}`", "",
              f"> {call}", "",
              f"- **On screen:** the ring on **{marker.replace('_', ' ')}**, "
              f"with **{directive}** across the bottom.",
              f"- **Delivery:** {DIRECTION.get(key, '')}", ""]
    L += ["## What happens after the last line", "",
          f"About {wk_coach.REATTACK_DELAY_S} seconds past the egress point "
          f"the sequence re-arms from **{wk_coach.RESET_TO.upper()}**, so "
          f"lines {wk_coach.IDX[wk_coach.RESET_TO] + 1} onward play again on "
          f"every re-attack. Lines 1 and 2 are heard once per sortie; the "
          f"rest are heard as many times as the pilot flies it. Record them "
          f"like something you would not mind hearing eight times.", ""]
    return "\n".join(L)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(markdown(), encoding="utf-8")
    have = (sum(1 for k in wk_coach.KEYS if wk_coach.has_audio(k))
            + sum(1 for k in wk_brief.KEYS if wk_brief.has_audio(k)))
    total = len(wk_coach.PHASES) + len(wk_brief.PAGES)
    print(f"{OUT.relative_to(ROOT)} — {total} lines, {have} recorded")


if __name__ == "__main__":
    main()
