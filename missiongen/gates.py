"""Readback gates: the mission checks the radio instead of assuming it.

THE TECHNIQUE, AND WHERE IT CAME FROM
-------------------------------------
Fulda 1979 builds every frequency handoff as three triggers:

    "X Freq set by Jester"   the WSO tunes it if he holds the radios
    "X Freq NOT set"         a reminder after ~30 s if the pilot hasn't
    "X Freq set -> next"     the story advances only when the radio is right

and the effect is that a pilot who tunes the wrong channel finds out in
thirty seconds instead of flying around blind. That is exactly what Casmo
reported against our Case III mission — "it says carrier on channel 2 but I
had to manually tune it" — so this is the direct fix, done the way the best
trigger-only author in the corpus does it.

WHAT IT REFUSES TO DO
---------------------
It will not install a gate on a cockpit parameter we have not verified
(see cockpit.py). A gate on a wrong name never fires, the reminder nags for
the whole ride, and the brief has promised a check the mission cannot make.
So `readback()` returns None for an unsupported airframe, adds a warning,
and the caller prints "not available for this airframe" in the brief.

WHY A RANGE, NOT EQUAL-TO
-------------------------
Our comm ladder sits on the 25 kHz raster (265.225 and the like). The one
first-hand report on `c_cockpit_param_equal_to` says values with more than
one decimal "get a bit screwed up"; Fulda's gates are all one-decimal
frequencies. `c_cockpit_param_in_range` with a ±6 kHz window matches the
same tune without depending on how the module prints the value.
"""
from __future__ import annotations

from . import cockpit

# Flags. The cq_coach registry is 8940–8979; these sit at its top end and are
# documented there.
F_START = 8976      # the gate is open (set by the caller's cue)
F_DONE = 8977       # the radio was seen on the right frequency
F_REMIND = 8978     # first reminder has fired (so the second can)

WINDOW_MHZ = 0.006  # ±6 kHz: inside the 25 kHz raster, outside any neighbor
REMIND_S = 30       # Fulda's cadence
REMIND2_S = 90


def readback(m, group, aircraft: str, freq_mhz: float, label: str,
             chan=None, radio: str = "comm1", start_flag: int = F_START,
             warnings=None):
    """Install the set / not-set / done triplet. Returns the DONE flag or None.

    `start_flag` is set by whoever opens the gate (a cue, a phase). The caller
    owns that; this function only reacts to it. NEVER RAISES: a mission
    without a gate beats a mission that failed to build.
    """
    warnings = warnings if warnings is not None else []
    param = cockpit.radio_param(aircraft, radio)
    if not param:
        # Not a warning: the brief line says it, in the pilot's language.
        # A warning here would fire on every Tomcat and Hornet ride and
        # teach people to ignore the warnings list.
        return None
    try:
        from dcs import action as A
        from dcs import condition as C
        from dcs import triggers as Tr

        ftxt = cockpit.freq_text(freq_mhz)
        where = f"CH {chan}" if chan else radio.upper()
        lo, hi = freq_mhz - WINDOW_MHZ, freq_mhz + WINDOW_MHZ

        def msg(text, secs):
            return A.MessageToGroup(group.id, m.string(text), secs)

        def add(comment, conds, actions, once=True):
            t = (Tr.TriggerOnce if once else Tr.TriggerContinious)(comment=comment)
            for c in conds:
                t.rules.append(c)
            for a in actions:
                t.actions.append(a)
            m.triggerrules.triggers.append(t)

        # set -> done. The confirmation is short: the pilot did it right and
        # should hear that, not a paragraph.
        add(f"Readback: {label} set",
            [C.FlagIsTrue(start_flag), C.FlagIsFalse(F_DONE),
             C.CockpitParamInRange(param, lo, hi)],
            [A.SetFlag(F_DONE),
             msg(f"RADIO CHECK — {label} {ftxt} confirmed.", 6)])
        # not set -> remind, twice, then stop nagging.
        add(f"Readback: {label} NOT set",
            [C.TimeSinceFlag(start_flag, REMIND_S), C.FlagIsFalse(F_DONE),
             C.FlagIsFalse(F_REMIND)],
            [A.SetFlag(F_REMIND),
             msg(f"SET {radio.upper()} TO {label}: {ftxt} ({where}).", 12)])
        add(f"Readback: {label} still NOT set",
            [C.TimeSinceFlag(start_flag, REMIND2_S), C.FlagIsFalse(F_DONE),
             C.FlagIsTrue(F_REMIND)],
            [msg(f"STILL NOT ON {label}. {ftxt} — {where}. Marshal cannot "
                 f"hear you until you are.", 12)])
        return F_DONE
    except Exception as exc:                              # pragma: no cover
        warnings.append(f"readback gate not installed: {exc}")
        return None


def brief_line(aircraft: str, label: str, freq_mhz: float, chan=None) -> str:
    """The one sentence the brief prints about the gate — true either way."""
    ftxt = cockpit.freq_text(freq_mhz)
    where = f" (CH {chan})" if chan else ""
    nice = aircraft.replace("_hornet", "").replace("_", " ")
    if cockpit.supports_readback(aircraft):
        return (f"Radio check: the coach confirms COMM1 on {label} {ftxt}{where} "
                f"after check-in and reminds you at 30 and 90 seconds if it "
                f"is not.")
    return (f"Radio check: not available for the {nice} yet — the cockpit "
            f"parameter that exposes its radio is unverified, so the mission "
            f"cannot read your tune. Set {label} {ftxt}{where} yourself before "
            f"calling Marshal.")
