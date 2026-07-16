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

RADIO 1 ONLY, deliberately: radio 1 is the primary UHF set on every module we
ship (Hornet COMM1, Tomcat ARC-159, Viper COMM1, Hog ARC-164, F-4E ARC-164...).
Radios 2/3 are VHF-only on several airframes (A-10C VHF AM/FM) — writing UHF
agency freqs there would create invalid presets. COMM2 stays factory.

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


def _uhf_radio_id(radio):
    """Index of the module's UHF radio (the one that can tune our 225-400 MHz
    agency ladder), or None if the airframe has no UHF set.

    Our comm ladder is entirely UHF (Flight 305, Guard 243, Mother 264…). Radio
    1 is NOT always the UHF set: on the A-10C it's the VHF AM/FM ARC-186 (UHF is
    radio 2), on the Apache radio 1 is VHF and radio 2 UHF, and the Spitfire /
    MiG-21 / Ka-50 / Gazelle have NO UHF radio at all. We pick the radio whose
    default channels most land in the UHF band; if none do, presets are skipped.
    """
    # Rank by the FRACTION of default channels in the UHF band, not the raw
    # count: pydcs's A-10C radio 1 carries UHF default values too (a tie on
    # count), but its true UHF set is radio 2 (a PURE UHF default set). The
    # purer-UHF radio wins; ties break to the lower index (Hornet radios 1&2
    # are both pure UHF → radio 1). A radio less than half UHF is not a UHF set
    # (Spitfire/MiG-21/Ka-50/Gazelle → None → presets skipped).
    best, best_frac = None, 0.0
    for rid in sorted((radio or {}).keys()):
        vals = [v for v in (radio[rid].get("channels") or {}).values()
                if isinstance(v, (int, float))]
        if not vals:
            continue
        frac = sum(1 for v in vals if 225.0 <= v <= 400.0) / len(vals)
        if frac > best_frac:
            best, best_frac = rid, frac
    return best if best_frac >= 0.5 else None


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
        uhf = _uhf_radio_id(radio)
        if uhf is None:
            continue                           # no UHF set — our ladder can't load
        channels = radio[uhf].get("channels")
        if not channels:
            continue
        last = max(channels)                   # Guard rides the last channel
        this = {}
        for ch, agency, mhz in rows:
            if ch in channels and ch != last:  # never let an agency take Guard's slot
                channels[ch] = mhz
                this[agency] = ch
        channels[last] = guard_mhz
        this["Guard"] = "last ch"
        programmed = this                      # same type across the group
    return programmed
