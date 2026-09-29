"""BB-19: cockpit radio presets aligned to the mission's comm plan.

The kneeboard tells the pilot WHAT the frequencies are; this module puts them
IN THE JET so nothing needs to be typed on the UFC before push. Channels are
derived from the same CommsPlan the kneeboard renders, so cockpit and card
cannot disagree by construction.

Channel plan (mirrors common wing SOPs — flight on 1, Mother on 2, gas on 4,
Guard last):
  CH 1  Flight     (DCS clobbers CH 1 with the flight's assigned frequency
                    anyway — we plan WITH the engine, not against it)
  CH 2  Mother     (carrier missions)
  CH 3  AWACS      (or AEW when the mission has an E-2 but no E-3)
  CH 4  Tanker
  CH 5  Angel      (plane guard, carrier flight-ops missions)
  CH 6  CAP common
  CH 7  Tactical
  CH 8  AEW        (only when AWACS also exists and took CH 3)
  last  Guard 243.000

Only agencies that EXIST in this mission are programmed; untouched channels
keep the module's factory defaults.

EVERY UHF SET IN THE JET, NOT JUST ONE. This module used to program a single
radio — "the best one" — and left the others on pydcs's factory numbers. Casmo
flew a Tomcat into a Case III and reported: "It says carrier on channel 2 but I
had to manually tune it to the freq."

He was on the other radio. The F-14 has TWO full UHF sets: the pilot's ARC-159
(radio 1, 20 presets) and the RIO's ARC-182 (radio 2, 30 presets, 225-400 MHz
among other bands) — and the RIO's set is the one most crews use for boat
comms, because it is the one that can also go below 225 MHz. We programmed
radio 1 and left radio 2 holding pydcs's factory table, where channel 2 is
258.000. The card said CH2 = Mother; the cockpit, on that radio, said 258.000.
The card was true about a radio he wasn't using, which is the same as false.

So: program every radio that is genuinely a UHF set, and let the card be true
whichever one the pilot has keyed.

WHICH RADIOS ARE UHF SETS. Measured across all 78 airframes we ship, by the
fraction of each radio's DEFAULT channels that land in 225-400 MHz. The
distribution is bimodal and the gap is the answer:

    100%  a real UHF set   F-14 r1+r2, Hornet r1+r2, F-4E r1+r2, A-10C r2,
                           Mirage F1 r2, Apache r2, F-16C r1, F-15E r1, ...
    0%    a VHF set        A-10C r1 (ARC-186), F-16C r2, Apache r1+r3+r4, ...
    85-95% ambiguous       AV-8B r1 (85%), AJS37 r1 (91%), MiG-29 r1 (95%)

Pure UHF is the rule. The ambiguous three keep the OLD behavior — the single
best radio at >= 50% — because they have no pure set at all and dropping them
to zero presets would be a regression dressed as a fix. Below 50% nothing is
programmed (Spitfire / MiG-21 / Ka-50 / Gazelle have no UHF radio at all), and
the card then prints no CHAN column rather than promising a channel that
isn't there.

Aircraft-side TACAN / ICLS / Link4 are COCKPIT STATE and cannot be preset from
a .miz by any mission editor — the kneeboard Boat Card carries those values.

Aircraft-side TACAN / ICLS / Link4 are COCKPIT STATE and cannot be preset from
a .miz by any mission editor — the kneeboard Boat Card carries those values.
"""

CHANNEL_ORDER = [
    ("Flight", 1), ("Carrier", 2), ("AWACS", 3), ("Tanker", 4),
    ("Plane guard", 5), ("CAP", 6), ("Tactical", 7), ("AEW", 8),
]


def plan_from_comms(comms):
    """Derive (channel, agency, MHz) rows from the comm ladder actually built
    for this mission. Returns (rows, guard_mhz)."""
    ag = {}
    for agency, _cs, freq, _tacan, _notes in comms.entries:
        if agency not in ag:
            try:
                ag[agency] = float(freq)
            except (TypeError, ValueError):
                pass
    rows = []
    aew_takes_3 = "AWACS" not in ag           # E-2-only mission: AEW is the picture
    for agency, ch in CHANNEL_ORDER:
        if agency == "AEW" and aew_takes_3:
            continue
        if agency in ag:
            rows.append((ch, agency, ag[agency]))
    if aew_takes_3 and "AEW" in ag:
        rows.append((3, "AEW", ag["AEW"]))
    rows.sort()
    return rows, ag.get("Guard", 243.0)


UHF_LO, UHF_HI = 225.0, 400.0     # the band our whole agency ladder lives in


def _uhf_fraction(radio, rid):
    """What share of this radio's DEFAULT channels are UHF. None = no channels."""
    vals = [v for v in (radio[rid].get("channels") or {}).values()
            if isinstance(v, (int, float))]
    if not vals:
        return None
    return sum(1 for v in vals if UHF_LO <= v <= UHF_HI) / len(vals)


def _uhf_radio_ids(radio):
    """Every radio in this airframe that can carry our 225-400 MHz ladder.

    Returns a sorted list of radio indices — usually one, two on the airframes
    with a second UHF set (F-14 pilot + RIO, Hornet COMM1 + COMM2, F-4E), and
    empty on an airframe with no UHF radio at all.

    A radio is a UHF set when EVERY default channel is in band. That test, not
    a count and not "radio 1", is what separates the A-10C's ARC-186 (radio 1,
    0% — a VHF set that would take our frequencies and be unable to tune them)
    from its ARC-164 (radio 2, 100%). See the module docstring for the measured
    table and for why three airframes fall back to the old best-radio rule.
    """
    fracs = {rid: _uhf_fraction(radio, rid) for rid in sorted((radio or {}).keys())}
    fracs = {rid: f for rid, f in fracs.items() if f is not None}
    pure = [rid for rid, f in fracs.items() if f == 1.0]
    if pure:
        return pure
    # No pure UHF set: the AV-8B / AJS37 / MiG-29 case. Keep the old rule so
    # they don't lose the presets they have today, but only one radio and only
    # if it is more UHF than not.
    if fracs:
        best = max(fracs, key=lambda rid: (fracs[rid], -rid))
        if fracs[best] >= 0.5:
            return [best]
    return []


def apply(group, rows, guard_mhz):
    """Program the module's UHF radio from the comm ladder.

    Returns the {agency: channel} map ACTUALLY programmed (so the briefing card
    and kneeboard advertise only channels that exist and were written — the
    "cockpit and paper agree" invariant). Empty dict = nothing programmed
    (all-VHF airframe, or no ME-settable radios): the caller then prints no
    CHAN column. Guard is reserved on the last channel BEFORE agencies, so it
    can never silently overwrite an agency (the old bug clobbered CH8 AEW)."""
    programmed = {}
    for u in group.units:
        try:
            u.set_radio_preset()               # load the module's factory template
        except Exception:
            continue
        radio = u.radio or {}
        this = {}
        for uhf in _uhf_radio_ids(radio):      # every UHF set in this cockpit
            channels = radio[uhf].get("channels")
            if not channels:
                continue
            last = max(channels)               # Guard rides this radio's last channel
            # Name what we program, the way the Mission Editor does when a
            # hand fills the preset table (`channelsNames`). The name shows in
            # the ME's radio page and in modules that render preset labels;
            # the frequency is what matters, the name is how a pilot checks
            # it without the card in hand.
            names = radio[uhf].setdefault("channelsNames", {})
            for ch, agency, mhz in rows:
                if ch in channels and ch != last:   # never take Guard's slot
                    channels[ch] = mhz
                    names[ch] = agency
                    this[agency] = ch
            channels[last] = guard_mhz
            names[last] = "Guard"
            this["Guard"] = "last ch"
        if this:
            programmed = this                  # same type across the group
    return programmed
