"""The coached B'NAI: a cue at every decision point, and a second run at it.

WHY THIS RIDE EXISTS
--------------------
The B'NAI is the hardest thing in the syllabus and it was taught the way
everything else is taught: read the card on the ground, fly it, find out
afterwards. That is a fine CHECK ride and a poor TEACHING one. The geometry has
about ten decisions in it, most of them two seconds wide, and the pilot is at
three hundred feet with no time to reconstruct a diagram from memory.

So this ride puts the squadron's own drawing on the screen at the moment each
decision arrives, with the call that goes with it, and then lets you fly the
whole thing again from the same IP without reloading.

WHY THE PIT CALL IS NOT JESTER
------------------------------
It cannot be. There is no Mission Editor action that makes the F-4E's AI WSO
say an arbitrary line, and no Lua goes inside our `.miz` files. Pretending
otherwise would mean shipping a card that promises a voice the file cannot
produce — the exact defect this whole track was built to avoid.

What we ship instead is honest: `SoundToGroup`, which DCS plays as a cockpit
sound rather than a radio transmission. That is the right channel anyway — a
WSO leaning forward in the back seat is intercom, not a frequency — and the
voice in it is the squadron's own recorded WSO, not an impersonation of
somebody else's character.

THE SOUND IS OPTIONAL, BY DESIGN
--------------------------------
`SoundToGroup` is emitted for a phase ONLY when that phase's WAV is present on
disk. Missing audio costs you the voice and nothing else: the picture and the
text still fire, on the same trigger, at the same instant. A half-recorded set
degrades one line at a time rather than failing the build, so the recording can
land in whatever order it lands in.

WHY EDGE-TRIGGERED, AND WHY STRICTLY SEQUENTIAL
-----------------------------------------------
Two rules, both learned the hard way elsewhere in this codebase:

  * A DCS continuous trigger re-evaluates every second. A picture drawn every
    second is a strobe, so every phase disarms itself the moment it fires
    (`aar_hud` does the same, for the same reason).
  * Every phase additionally requires the PREVIOUS phase's flag. Without that,
    a run-in that clips the edge of the target zone fires the release cue on
    the way IN, and the pilot is told to pickle at four hundred knots and three
    hundred feet. Sequencing is not tidiness here; it is the difference between
    a coach and a liar.

Flag block 8880-8899. `aar_grade` owns 8810-8839, `aar_hud` 8840-8859,
`formation` 8801, `crewops` 200/300.
"""
from __future__ import annotations

from pathlib import Path

from . import wk

ASSET_DIR = Path(__file__).parent / "data" / "wk_coach"
AUDIO_DIR = ASSET_DIR / "vo"

# --- flags ------------------------------------------------------------------
#
# A COLLISION THAT SHIPPED. F_ARM was 8890, and the phase block is F_PHASE + i
# with thirteen phases — so phase 10, `twos_pass`, WAS the arm flag. Two
# consequences, both silent: firing the cover-two cue re-armed the sequence,
# and the re-attack's clear-everything loop switched the coaching OFF, so the
# second run — the entire point of the ride — worked once and then died. Caught
# by a test written for something else, which is the usual way.
#
# F_ARM now sits at the TOP of the block with room underneath, and
# `test_the_flag_blocks_do_not_overlap` asserts the gap rather than trusting
# anyone to remember it when a fourteenth phase is added.
F_PHASE = 8880          # 8880 + i: phase i has fired this pass (i < 16)
F_ARM = 8899            # the whole sequence is live (cleared while resetting)
F_PHASE_MAX = 16        # how many phases the block has room for

# --- how the cue behaves ----------------------------------------------------
HOLD_S = 6              # seconds the picture stays up
TEXT_S = 8              # seconds the text stays up: outlives the picture, so
                        # a pilot who was looking outside can still read it
SIZE_PCT = 30           # per cent of window width
HORZ, VERT = "Center", "Bottom"     # low center: peripheral vision, not a
                                    # box over the target you are trying to see
REATTACK_DELAY_S = 20   # after egress, before "come back round"
TWOS_PASS_DELAY_S = 15  # after your pullout, while two is still in

_FT_M = 0.3048
NM_FT = 6076.12


def _pup_ft() -> int:
    """The pull-up distance, from the delivery sheet the ride actually flies.

    NOT from the diagram. The B'NAI page's "4.5 NM" is where mutual support
    ends — the guide's own prose says so in the split attack's section — and
    reading it as a pull-up distance would put the cue two and a half miles
    early. The sheet's number is the one tied to the release parameters we
    print on the same card, so it is the one that governs.
    """
    return int(wk.DELIVERIES["lald15"]["pup_ft"])


# --- the sequence -----------------------------------------------------------
#
# (key, marker, directive, call)
#
#   marker    which point on the squadron's drawing gets the "you are here"
#             ring, and therefore which card is shown
#   directive the word burned large on the card. This is what you read in the
#             pop; the call is what you hear.
#   call      the WSO line. Written in the vocabulary of WSO_CALLS and the
#             guide's own geometry paragraph, so nothing here is invented
#             phrasing dressed up as period voice.
#
PHASES = [
    ("lowlevel", "run_in", "300 FEET",
     "Level at three hundred, four hundred knots. Lead's on the target side "
     "of the formation.", None),

    ("trail", "split", "TRAIL 2-3",
     "Set your trail. Two to three miles. IP coming up ninety left.",
     "lowlevel"),

    ("ip", "split", "TURN INBOUND",
     "IP. Lead turns inbound now. You turn away, then back in behind him.",
     "trail"),

    ("runin", "run_in", "NO COVER",
     "Run-in. No cross coverage from here to the pop. Eyes out.", "ip"),

    ("pup", "pup", "PULL UP — 30",
     "Pull-up point. Pull to thirty degrees. Now.", "runin"),

    ("rollin", "rollin", "ROLL IN",
     "Roll-in. Roll and pull, target off the nose.", "pup"),

    ("apex", "apex", "APEX",
     "Apex. Nose coming through — find the target.", "rollin"),

    ("track", "track", "TRACK",
     "Track point. Wings level, one twenty-one mils, five hundred knots.",
     "apex"),

    ("release", "track", "PICKLE",
     "Two thousand feet. Pickle, pickle.", "track"),

    ("pullout", "pullout", "OFF AND DOWN",
     "Off target, turning recovery. Get to the deck and take the egress "
     "heading.", "track"),

    ("twos_pass", "egress", "COVER TWO",
     "Two is in from the other side. You are covering his six now.",
     "pullout"),

    ("egress", "egress", "LINE ABREAST",
     "Keep the turn in until you are on egress heading or line abreast, "
     "whichever matters more right now.", "pullout"),

    ("reattack", "run_in", "AGAIN",
     "Good pass. Come back round to the IP and we will run the whole thing "
     "again.", "egress"),
]

# Where the second pass picks up. Everything BEFORE this key is marked done at
# reset, so a pilot who turns straight back to the IP — which is what the
# re-attack cue tells him to do — gets the IP call rather than silence while
# the sequence waits for him to re-fly a twenty-mile low level he has already
# flown once.
RESET_TO = "ip"

KEYS = [p[0] for p in PHASES]
MARKERS = sorted({p[1] for p in PHASES})
IDX = {k: i for i, k in enumerate(KEYS)}


def prereq(key: str) -> str | None:
    """The phase that must have fired before this one may.

    NOT simply "the previous entry". Two phases hang off `track` rather than
    off each other: RELEASE fires only if you actually descend through the
    release altitude inside the target area, and PULLOUT must still fire for a
    pass that never got there. Chaining PULLOUT behind RELEASE would mean one
    bad pop wedges the ride for the rest of the sortie — no egress cue, no
    re-arm, no second run. The whole point of this ride is the second run.
    """
    return phase(key)[4]


def phase(key: str) -> tuple:
    for p in PHASES:
        if p[0] == key:
            return p
    raise KeyError(key)


RINGS = ("red", "green")   # every palette the card builder produces


def card_path(key: str, ring: str = "red") -> Path:
    """One card per PHASE and per ring palette. Ring positions are shared;
    directives are not; the ring color is the pilot's, chosen in the recipe
    (`coach_ring`). Red keeps its original name so every mission ever built
    still names the file it shipped with."""
    stem = f"wk_coach_{key}" if ring == "red" else f"wk_coach_{ring}_{key}"
    return ASSET_DIR / f"{stem}.png"


def audio_path(key: str) -> Path:
    return AUDIO_DIR / f"wk_bnai_{key}.wav"


def has_audio(key: str) -> bool:
    """Whether Rob's take for this line has landed yet."""
    return audio_path(key).is_file()


def cards_ready(ring: str = "red") -> bool:
    return all(card_path(k, ring).is_file() for k in KEYS)


def brief_lines() -> list:
    """The coaching block for the kneeboard.

    It states what fires, where it fires, and — the part that matters — what
    the coaching CANNOT see, because a training aid that implies it is watching
    everything is a training aid you will trust at the wrong moment.
    """
    n_vo = sum(1 for k in KEYS if has_audio(k))
    L = ["== HOW THIS RIDE COACHES YOU ==",
         f"{len(PHASES)} cues, one per decision in the B'NAI. Each one puts "
         f"the squadron's own drawing low on your screen with a ring around "
         f"where you are, and calls it from the back seat.",
         "",
         "The cues fire in ORDER. Cutting a corner does not skip you ahead — "
         "it leaves you on the last cue you actually earned, which is itself "
         "information.",
         ""]
    if n_vo == 0:
        L += ["VOICE: not in this build. Every cue still shows the picture and "
              "prints the call as text. Nothing about the geometry changes.",
              ""]
    elif n_vo < len(KEYS):
        L += [f"VOICE: {n_vo} of {len(KEYS)} lines recorded. The rest are "
              f"picture and text only.", ""]
    L += ["-- WHAT THE COACHING CANNOT SEE --",
          "Mission Editor conditions can read your position, your altitude and "
          "your speed. That is the whole list.",
          "",
          "So it cannot see your dive angle, your bank, your mil setting or "
          "your pipper. It knows you reached the pull-up point; it does not "
          "know whether you pulled to thirty degrees or to fifteen. It knows "
          "you came down through two thousand feet in the target area; it does "
          "not know whether the bombs went where you were looking.",
          "",
          "It is a metronome for a sequence you already studied, not a grader. "
          "The grade is the crater.",
          "",
          "-- THE SECOND RUN --",
          f"About {REATTACK_DELAY_S} seconds after you cross the egress point "
          f"the whole sequence re-arms. Come back round to the IP and every "
          f"cue fires again, same target, same geometry. Fly it until the "
          f"calls are telling you what you were already doing.",
          ]
    return L


# --------------------------------------------------------------------------- #
# Wiring it into the mission
# --------------------------------------------------------------------------- #
def _alt_m(ft, map_key):
    """A sheet altitude — which is height above the TARGET — as the MSL metres
    a DCS condition compares against. Same `msl_ft` the waypoints use, so the
    cue and the flight plan cannot disagree about where four thousand feet is.
    """
    from . import wk_route
    return wk_route.msl_ft(ft, map_key) * _FT_M


def attach(m, player_group, ride_key: str, map_key: str, home_pos,
           warnings=None, armed_externally: bool = False,
           ring: str = "red") -> int:
    """Wire the coaching in. Returns the number of phases wired, 0 if it did
    not attach.

    NEVER RAISES — the same contract `aar_grade.attach` and `aar_hud.attach`
    hold. A missing card, a pydcs drift or a leg table that changed shape costs
    the coaching and leaves a flyable mission behind; it does not fail a build
    that a pilot is waiting on.
    """
    try:
        if not (wk.RIDES.get(ride_key) or {}).get("coach"):
            return 0
        from dcs import condition as C, action as A, triggers as Tr
        from . import wk_route

        if ring not in RINGS:
            ring = "red"
        missing = [k for k in KEYS if not card_path(k, ring).is_file()]
        if missing:
            raise FileNotFoundError(
                f"cue cards missing: {missing[:3]} — run "
                f"scripts/build_wk_coach_cards.py")

        pos = wk_route.leg_positions(home_pos, ride_key, map_key)
        need = ("LOW LEVEL", "TRAIL SET", "IP", "PULL-UP", "TARGET", "EGRESS")
        gone = [n for n in need if n not in pos]
        if gone:
            raise KeyError(f"coached B'NAI leg table is missing {gone}")

        me = player_group.units[0]
        d = wk.DELIVERIES["lald15"]
        ax = wk_route.axis_deg(map_key)
        NM_M = 1852.0

        def zone(point, radius_m, name):
            return m.triggers.add_triggerzone(
                point, radius=radius_m, hidden=True, name=name)

        # The run-in cue sits halfway between the IP and the pull-up point, so
        # "no cross coverage from here to the pop" arrives while that is
        # actually true rather than at the moment it stops being true.
        half_nm = ((36 - _pup_ft() / NM_FT) - 26) / 2.0
        z = {
            "lowlevel": zone(pos["LOW LEVEL"], 2.0 * NM_M, "WKC LOW LEVEL"),
            "trail": zone(pos["TRAIL SET"], 1.5 * NM_M, "WKC TRAIL"),
            "ip": zone(pos["IP"], 1.2 * NM_M, "WKC IP"),
            "runin": zone(wk_route._offset(pos["IP"], half_nm * NM_M, ax),
                          1.2 * NM_M, "WKC RUN-IN"),
            # the pull-up RING: centered on the target at the sheet's own
            # pull-up distance, so the cue fires when the RANGE is right no
            # matter which way the pilot came at it
            "pup": zone(pos["TARGET"], _pup_ft() * _FT_M, "WKC PULL-UP RING"),
            "target": zone(pos["TARGET"], 2.0 * NM_M, "WKC TARGET AREA"),
            "egress": zone(pos["EGRESS"], 2.0 * NM_M, "WKC EGRESS"),
        }

        res = {k: m.map_resource.add_resource_file(str(card_path(k, ring)))
               for k in KEYS}
        snd = {k: m.map_resource.add_resource_file(str(audio_path(k)))
               for k in KEYS if has_audio(k)}

        def flag(key):
            return F_PHASE + IDX[key]

        def fired(key):
            return A.SetFlag(flag(key))

        def show(key):
            _k, _mk, directive, call, _after = phase(key)
            acts = [
                A.PictureToGroup(
                    player_group, res[key], HOLD_S,
                    True,                    # clearview: replace, never stack
                    0,
                    # `.value`, not the enum member — pydcs writes whatever it
                    # is handed straight into the Lua table and an Enum
                    # stringifies to an undefined variable. The mission builds
                    # and then will not OPEN.
                    getattr(A.PictureAction.HorzAlignment, HORZ).value,
                    getattr(A.PictureAction.VertAlignment, VERT).value,
                    SIZE_PCT, A.PictureAction.SizeUnits.WindowSize.value),
                # `m.string`, not a bare str: pydcs stores a dictionary key
                # and a raw string has no `.id`. It fails at SAVE, not at
                # append, so the mistake surfaces a long way from its cause.
                A.MessageToGroup(player_group.id,
                                 m.string(f"{directive} — {call}"), TEXT_S),
            ]
            if key in snd:
                acts.append(A.SoundToGroup(player_group.id, snd[key]))
            acts.append(fired(key))
            return acts

        # --- the conditions, phase by phase ------------------------------- #
        #
        # A phase may carry MORE THAN ONE condition set. Each set becomes its
        # own trigger and they are an OR: whichever comes true first fires the
        # cue and sets the flag, which disarms the others. That is how a pop
        # flown shallower than the sheet still gets an apex call — on a timer
        # instead of an altitude — rather than wedging the sequence at the
        # last stage the pilot flew exactly.
        def inz(k):
            return C.UnitInZone(me.id, z[k].id)

        def outz(k):
            return C.UnitOutsideZone(me.id, z[k].id)

        def hi(ft):
            return C.UnitAltitudeHigher(me.id, _alt_m(ft, map_key))

        def lo(ft):
            return C.UnitAltitudeLower(me.id, _alt_m(ft, map_key))

        def since(key, secs):
            return C.TimeSinceFlag(flag(key), secs)

        RULES = {
            "lowlevel": [[inz("lowlevel")]],
            "trail": [[inz("trail")]],
            "ip": [[inz("ip")]],
            "runin": [[inz("runin")]],
            "pup": [[inz("pup")]],
            "rollin": [[hi(d["pdp_ft"])]],
            "apex": [[hi(d["apex_ft"])], [since("rollin", 12)]],
            "track": [[lo(d["apex_ft"] - 800)], [since("apex", 10)]],
            # RELEASE has no timer fallback ON PURPOSE. Every other fallback
            # keeps the sequence moving; a timed "pickle" would be the coach
            # telling you to drop when it has no idea where you are. It fires
            # when you are actually low and actually over the target, or it
            # does not fire.
            "release": [[lo(d["release_ft"]), inz("target")]],
            "pullout": [[C.FlagIsTrue(flag("release")), outz("target")],
                        [since("track", 25)]],
            "twos_pass": [[since("pullout", TWOS_PASS_DELAY_S)]],
            "egress": [[inz("egress")], [since("pullout", 75)]],
            "reattack": [[since("egress", REATTACK_DELAY_S)]],
        }

        # WHO TURNS THE COACHING ON.
        # A ten-second timer was right when the ride began on the chocks with
        # nothing in front of it. With a brief in front of it that timer runs
        # out while the pilot is still on page two, and the first cue fires
        # before he has been told what a cue is. So when a brief is attached
        # it owns this flag and sets it on the page that hands back the
        # controls; the timer is the fallback for a ride with no brief.
        if not armed_externally:
            opening = Tr.TriggerOnce(comment="WK coach: arm")
            opening.rules.append(C.TimeAfter(10))
            opening.actions.append(A.SetFlag(F_ARM))
            m.triggerrules.triggers.append(opening)

        wired = 0
        for key in KEYS:
            for n, conds in enumerate(RULES[key]):
                t = Tr.TriggerContinious(
                    comment=f"WK coach: {key}" + (f" ({n + 1})" if n else ""))
                t.rules.append(C.FlagIsTrue(F_ARM))
                t.rules.append(C.FlagIsFalse(flag(key)))
                pre = prereq(key)
                if pre:
                    t.rules.append(C.FlagIsTrue(flag(pre)))
                for c in conds:
                    t.rules.append(c)
                for a in show(key):
                    t.actions.append(a)
                if key == "reattack":
                    # THE SECOND RUN. Clear the whole pass, then hand back the
                    # stages the pilot is not being asked to re-fly, so the
                    # next cue he gets is the one the card just told him to go
                    # and get. Clearing the reattack flag last also stops this
                    # trigger re-firing: TimeSinceFlag on a cleared flag is
                    # false, so the chain cannot free-run.
                    for k2 in KEYS:
                        t.actions.append(A.ClearFlag(flag(k2)))
                    for k2 in KEYS[:IDX[RESET_TO]]:
                        t.actions.append(A.SetFlag(flag(k2)))
                m.triggerrules.triggers.append(t)
                wired += 1
        return wired
    except Exception as exc:                       # pragma: no cover - guard
        if warnings is not None:
            warnings.append(f"B'NAI coaching not attached: {exc}")
        return 0
