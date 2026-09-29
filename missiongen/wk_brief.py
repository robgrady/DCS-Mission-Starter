"""The spoken brief, and holding the pilot until he has read it.

WHAT ROB ASKED FOR, AND WHAT DCS ACTUALLY ALLOWS
------------------------------------------------
The ask was a voiced mission brief with the airplane at ACTIVE PAUSE until the
pilot has finished reading. Half of that is not available to a mission file and
saying so plainly is cheaper than discovering it in the cockpit:

  * ACTIVE PAUSE CANNOT BE PRESSED BY A MISSION. It is a client keybind
    (LWin+Pause by default). There is no Mission Editor action for it, and no
    Lua goes inside our `.miz`. A card promising the mission will pause itself
    would be the say/do gap with the volume up.

What IS available is better than a workaround, because it is what ED's own
training missions are built from:

  * `START WAIT USER RESPONSE` halts the trigger sequence until the pilot
    presses SPACE. BACKSPACE takes him back a page. One key, no menu.
  * `START PLAYER SEAT LOCK` takes the controls away for the duration, so he
    cannot fly off in the middle of a sentence. Released on the last page, once,
    by exactly one trigger.

Between them the pilot is held and the brief waits for him, which is the thing
he actually wanted. Whether ED's engine also freezes the world during a wait is
ED's behavior and not ours, so the card claims the seat lock — which we
control — and tells him active pause is still his key to press if he wants the
sky to stop as well.

THE DOCUMENTED FOOTGUN
----------------------
From the Mission Editor forum thread on this action: choosing the BACK branch
leaves the CONTINUE flag live, so the next page can fire both ways at once. The
fix, which every branch below applies without exception: `STOP WAIT USER
RESPONSE` first, then clear BOTH flags, and only then show anything. A page that
clears one flag and not the other is the bug this paragraph exists to prevent.

WHY THE COACHING CANNOT ARM ITSELF ANY MORE
-------------------------------------------
`wk_coach` used to arm on a timer ten seconds in. With a brief in front of it
that timer would run out while the pilot was still on page two, so the first cue
could fire before he had been told what a cue is. The brief now owns the arming
flag: the coaching goes live when the pilot takes the jet, and not before.

Flag block 8900-8939. `wk_coach` owns 8880-8899, `aar_hud` 8840-8859,
`aar_grade` 8810-8839, `formation` 8801, `crewops` 200/300.
"""
from __future__ import annotations

from pathlib import Path

from . import wk

ASSET_DIR = Path(__file__).parent / "data" / "wk_brief"
AUDIO_DIR = ASSET_DIR / "vo"

# --- flags ------------------------------------------------------------------
F_CONT = 8900       # 8900 + i: the pilot pressed SPACE on page i
F_BACK = 8920       # 8920 + i: he pressed BACKSPACE on page i
F_DONE = 8939       # the brief is finished and he has the airplane

# --- presentation -----------------------------------------------------------
PAGE_S = 600        # how long a page stays on screen. Deliberately long: the
                    # page is up until HE advances it, so a picture that timed
                    # out would leave him reading a blank sky.
SIZE_PCT = 62       # per cent of window width. Much larger than a cue card —
                    # this one is read sitting still, not glanced at in a pop.
HORZ, VERT = "Center", "Center"
SEAT = 1            # front seat. The F-4E's back seat has full controls, so a
                    # WSO player is locked out of a jet he could otherwise fly;
                    # the ride is briefed single-seat and the card says so.


def _pages():
    """The six pages, built from the same data every other card is built from.

    NOTHING HERE RESTATES A NUMBER. Every figure is read out of `wk` at call
    time, so a corrected delivery sheet corrects the brief, the kneeboard and
    the cue card in one edit. A brief with its own copy of the pop numbers is
    a fourth place for them to be wrong.
    """
    from . import wk_coach
    a = wk.ATTACKS["bnai"]
    d = wk.DELIVERIES["lald15"]
    lo, hi = a["trail_nm"]
    name, date = wk.DOCS["tactics"]
    return [
        ("situation", "SITUATION", None,
         f"You are a new wingman in the {wk.SQUADRON}, the {wk.NICKNAME}, "
         f"flying F-4E Phantoms with tail code {wk.TAILCODE} under the "
         f"callsign {wk.CALLSIGN} — on the sim's radio, {wk.RADIO_CALLSIGN}. "
         f"From June to the third of October, "
         f"nineteen eighty, twelve of the squadron's aircraft deployed to "
         f"Cairo West in Egypt for exercise Proud Phantom. That is where you "
         f"are sitting. Your squadron commander is {wk.COMMANDER}."),

        ("target", "TARGET AND THREAT", None,
         "Your target is on the Egyptian range, thirty miles down the run-in "
         "axis. There is an SA-6 in this mission. That is not scenery — the "
         "attack you are about to fly was designed to survive exactly that "
         "missile, by an air force that had to solve it in a real war, and "
         "the whole shape of the thing only makes sense once you know what "
         "it is avoiding."),

        ("attack", "THE ATTACK", "attack",
         f"The B'NAI. {a['definition']} You will fly it as a {lo} to {hi} "
         f"mile in-trail formation. Approach the IP at nearly ninety degrees "
         f"angle off, with lead on the side of the formation nearest the "
         f"target. At the IP lead turns inbound and you turn away, then back "
         f"in behind him. From that point to the pop, nobody is covering "
         f"your six."),

        ("pop", "THE POP", "pop",
         f"Off the low angle low drag sheet. Pull up {d['pup_ft']:,} feet "
         f"from the target and climb {a['climb_deg_lead']} degrees. Roll in "
         f"at {d['pdp_ft']:,} feet — that is below your apex of "
         f"{d['apex_ft']:,}, and it is not a misprint, because you begin the "
         f"pull-down at roll-in and the airplane coasts up to apex as the "
         f"nose comes through. Release at {d['release_ft']:,} feet, "
         f"{d['angle']} degrees, {d['release_kt']} knots, {d['mils']} mils. "
         f"Six Mark eighty-twos, low drag."),

        ("wingman", "YOUR WINGMAN", "egress",
         "Your number two is in YOUR flight, on your wing. He starts when "
         "you start, taxis when you taxi, and forms up after takeoff — no "
         "separate schedule, no airplane flying the mission without you. "
         "The two-ship geometry on the card is yours to fly; when you want "
         "his bombs on the target, send him with the radio menu — Flight, "
         "Engage. The doctrine is unchanged: one aircraft attacks while the "
         "other stays low covering his six, and off target you both keep "
         "turning until you are on egress heading or line abreast, whichever "
         "matters more at the time."),

        ("coaching", "HOW THIS RIDE COACHES YOU", None,
         f"{len(wk_coach.PHASES)} calls, one at every decision, each with the "
         f"squadron's own drawing and a ring around where you are. The route "
         f"itself is marked with training gates — green boxes over each "
         f"waypoint, drawn the moment you take the airplane. The cues "
         f"cannot see your dive angle or your mil setting — a trigger reads "
         f"position, altitude and speed, and that is the entire list. About "
         f"{wk_coach.REATTACK_DELAY_S} seconds after the egress point the "
         f"whole sequence re-arms, so come back round to the IP and fly it "
         f"again. Source for everything you have just heard: {name}, {date}. "
         f"You have the airplane."),
    ]


PAGES = _pages()
KEYS = [p[0] for p in PAGES]
IDX = {k: i for i, k in enumerate(KEYS)}


def pages():
    """Rebuilt on call, so a data fix in `wk` reaches the brief without an
    import-order dance. `PAGES` above is the convenience copy for callers that
    only want the keys."""
    return _pages()


def page_path(key: str) -> Path:
    return ASSET_DIR / f"wk_brief_{key}.png"


def clear_path() -> Path:
    """The blank page that takes the brief off the screen.

    DCS HAS NO "REMOVE PICTURE" ACTION — `PictureToGroup` with `clearview` is
    the only way to stop showing one, and it works by showing another. So the
    last page's SPACE draws this for a second instead of leaving the brief up
    for the ten minutes its own duration was set to.
    """
    return ASSET_DIR / "wk_brief_clear.png"


def audio_path(key: str) -> Path:
    return AUDIO_DIR / f"wk_brief_{key}.wav"


def has_audio(key: str) -> bool:
    return audio_path(key).is_file()


def pages_ready() -> bool:
    return all(page_path(k).is_file() for k in KEYS) and clear_path().is_file()


def brief_lines() -> list:
    """What the kneeboard says about the hold.

    The honest paragraph is the point of this block: the mission holds YOU, it
    does not hold the WORLD, and the pilot needs to know which of those he is
    getting before he decides whether to reach for the pause key himself.
    """
    n_vo = sum(1 for k in KEYS if has_audio(k))
    L = ["== THE BRIEF, BEFORE YOU FLY ==",
         f"{len(KEYS)} pages on screen before the sortie starts. SPACE goes "
         f"forward, BACKSPACE goes back a page. Take as long as you like — "
         f"nothing advances until you press something.",
         "",
         "YOUR CONTROLS ARE LOCKED until the last page. That is deliberate "
         "and it is the part we can actually do: a mission can take the stick "
         "off you, and it hands it back on the final page.",
         "",
         "WHAT IT CANNOT DO IS PRESS ACTIVE PAUSE FOR YOU. That is a keybind "
         "on your machine — LWin+Pause by default — and no Mission Editor "
         "action reaches it. If you want the sky stopped as well as the "
         "stick, press it yourself; the brief will wait either way.",
         ""]
    if n_vo == 0:
        L += ["VOICE: not in this build. Every page still shows and prints in "
              "full.", ""]
    elif n_vo < len(KEYS):
        L += [f"VOICE: {n_vo} of {len(KEYS)} pages recorded.", ""]
    return L


# --------------------------------------------------------------------------- #
# Wiring
# --------------------------------------------------------------------------- #
def attach(m, player_group, ride_key: str, arm_flag: int,
           warnings=None) -> int:
    """Wire the brief in. Returns the number of pages wired, 0 if it did not.

    `arm_flag` is set on completion — that is how the coaching learns it may
    start. NEVER RAISES, same contract as the rest of the attach family.
    """
    try:
        if not (wk.RIDES.get(ride_key) or {}).get("brief"):
            return 0
        from dcs import condition as C, action as A, triggers as Tr

        pg = pages()
        missing = [k for k, *_ in pg if not page_path(k).is_file()]
        if not clear_path().is_file():
            missing.append("clear")
        if missing:
            raise FileNotFoundError(
                f"brief pages missing: {missing[:3]} — run "
                f"scripts/build_wk_brief_pages.py")

        res = {k: m.map_resource.add_resource_file(str(page_path(k)))
               for k, *_ in pg}
        blank = m.map_resource.add_resource_file(str(clear_path()))
        snd = {k: m.map_resource.add_resource_file(str(audio_path(k)))
               for k, *_ in pg if has_audio(k)}

        def show(i):
            key, head, _pic, text = pg[i]
            acts = [
                A.PictureToGroup(
                    player_group, res[key], PAGE_S,
                    True, 0,
                    getattr(A.PictureAction.HorzAlignment, HORZ).value,
                    getattr(A.PictureAction.VertAlignment, VERT).value,
                    SIZE_PCT, A.PictureAction.SizeUnits.WindowSize.value),
                A.MessageToGroup(
                    player_group.id,
                    m.string(f"[{i + 1}/{len(pg)}] {head}\n\n{text}\n\n"
                             f"SPACE to continue"
                             + ("  ·  BACKSPACE to go back" if i else "")),
                    PAGE_S),
            ]
            if key in snd:
                acts.append(A.SoundToGroup(player_group.id, snd[key]))
            # ...and immediately start waiting on THIS page's pair.
            acts.append(A.StartWaitUserResponse(F_CONT + i, F_BACK + i))
            return acts

        def settle():
            """Close the wait and clear BOTH flags of every page.

            BOTH, and every page, not just the one that fired. The forum
            thread on this action is explicit: taking the BACK branch leaves
            the CONTINUE flag set, and a stale flag one page later fires two
            branches at once. Clearing the whole block is a dozen actions and
            removes the entire class."""
            acts = [A.StopWaitUserResponse()]
            for j in range(len(pg)):
                acts.append(A.ClearFlag(F_CONT + j))
                acts.append(A.ClearFlag(F_BACK + j))
            return acts

        # --- open: lock him in, then page one ----------------------------- #
        first = Tr.TriggerOnce(comment="WK brief: hold and page 1")
        first.rules.append(C.TimeAfter(5))
        first.actions.append(A.StartPlayerSeatLock(SEAT))
        for a in show(0):
            first.actions.append(a)
        m.triggerrules.triggers.append(first)

        wired = 1
        for i in range(len(pg)):
            # SPACE
            t = Tr.TriggerContinious(comment=f"WK brief: next from {i + 1}")
            t.rules.append(C.FlagIsTrue(F_CONT + i))
            for a in settle():
                t.actions.append(a)
            if i + 1 < len(pg):
                for a in show(i + 1):
                    t.actions.append(a)
            else:
                # THE RELEASE, and the only place it happens. One trigger owns
                # handing the airplane back and arming the coaching, so there
                # is no path where the pilot is flying a ride whose cues never
                # went live.
                # TAKE THE BRIEF OFF THE SCREEN. Every other page is replaced
                # by the next one, so only the LAST page needs this — and
                # without it the last page sits over the canopy for the full
                # ten minutes of its own duration while the pilot flies. There
                # is no action that removes a picture; showing a blank one for
                # a second is the whole of the available mechanism.
                t.actions.append(A.PictureToGroup(
                    player_group, blank, 1, True, 0,
                    getattr(A.PictureAction.HorzAlignment, HORZ).value,
                    getattr(A.PictureAction.VertAlignment, VERT).value,
                    SIZE_PCT, A.PictureAction.SizeUnits.WindowSize.value))
                # ...and the text with it. `clearview` on an empty message is
                # what clears the message window.
                t.actions.append(A.MessageToGroup(
                    player_group.id, m.string(" "), 1, True))
                t.actions.append(A.StopPlayerSeatLock())
                t.actions.append(A.SetFlag(F_DONE))
                t.actions.append(A.SetFlag(arm_flag))
            m.triggerrules.triggers.append(t)
            wired += 1

            # BACKSPACE. On page one it re-shows page one rather than doing
            # nothing, because a key that appears to be ignored reads as a
            # broken mission.
            b = Tr.TriggerContinious(comment=f"WK brief: back from {i + 1}")
            b.rules.append(C.FlagIsTrue(F_BACK + i))
            for a in settle():
                b.actions.append(a)
            for a in show(max(0, i - 1)):
                b.actions.append(a)
            m.triggerrules.triggers.append(b)
            wired += 1
        return wired
    except Exception as exc:                       # pragma: no cover - guard
        if warnings is not None:
            warnings.append(f"B'NAI brief not attached: {exc}")
        return 0
