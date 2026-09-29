"""Check rides: the silent sortie at the end of a phase, graded the way an
instructor grades — per item, against a standard, with critical items.

THE FRAMEWORK, ABBREVIATED FOR A GAME
-------------------------------------
A real formation block is a dozen sorties: each maneuver seen three to five
times against a rising standard, a pre-check flown to the check profile with
the instructor talking, then the check with him silent. Rob: "keep the same
framework but abbreviate it as a game." So a phase here is:

    the graded rides   each maneuver once, coach on
    the PRE-CHECK      the check profile, coach on, this engine running and
                       printing its card labelled PRACTICE
    the CHECK          the same profile, silent, this engine's card is the
                       grade

Nobody is surprised on a check ride. That is the design intent, kept.

HOW AN INSTRUCTOR'S GRADE IS MADE OF TRIGGERS
---------------------------------------------
Per ITEM, on the USAF scale — U (out of parameters, not corrected), F (out,
recognised and corrected), G (in, with small timely corrections), E (in,
corrections almost invisible) — and an overall Q / Q- / U for the check.
The Mission Editor cannot see a wingline or the size of a correction, but
it can count seconds: a continuous trigger evaluates about once a second,
and `IncreaseFlag` is a stopwatch. So each item is TIME IN THE BAND as a
share of the item's window:

    E  >= 90 %      G  >= 75 %      F  >= 50 %      U  below

There is no division in the Editor. Ratios are tested with paired counters:
"IN >= 0.9 x TOTAL" is "IN x 10 >= TOTAL x 9", kept as two flags that grow
by 10 and 9 per tick and compared with FlagIsLessThanFlag. Three ratios,
three pairs per item.

The items on a formation check come from what the profile makes lead DO,
read off lead's own airplane: bank inside +/-12 deg and vertical speed
inside +/-2.5 m/s is STRAIGHT AND LEVEL; bank beyond 20 deg is TURNS;
vertical speed beyond 2.5 m/s is CLIMBS AND DESCENTS. Then a PITCHOUT is
called, and the REJOIN is graded on the clock: back in the band inside 90 s
is an E, 150 a G, 240 an F.

CRITICAL ITEMS — a U for the check whatever else happened:
    * inside the collision band (12 m of lead) for any tick after joining;
    * lost: outside 400 m for 30 s straight before the pitchout;
    * never rejoined within 300 s of the pitchout.

Bands are radial — the Editor's moving zone has no bearing — so "in
position" is a sphere around lead of POSITION_M, not a wingline. The card
says so, and the gradesheet leaves the line, the corrections and the radio
to the instructor. That is the honest split: the sim fills the parameter
items, the IP fills technique.

FLAG BLOCK 8700-8749. Nothing else in the product uses 87xx.
"""
from __future__ import annotations

from pathlib import Path

CARD_DIR = Path(__file__).parent / "data" / "checkride"

# --- the debrief cards (v1.104.0) --------------------------------------- #
#
# Rob: "a continuous display of information that happens quickly that is too
# difficult to watch and navigate."
#
# He was describing this, exactly. The card used to be eight to twelve separate
# MessageToGroup calls fired two to six seconds apart into the DCS top-right
# corner, each set to hold for forty seconds — so they stacked, scrolled, and
# shoved one another off the screen faster than anybody could read them. A
# debrief nobody can read is not a debrief.
#
# Now it is one PICTURE at a time in the middle of the screen, eight seconds
# apart, in the order an instructor would say them: the three items, the rejoin,
# any critical, then the overall. `clearview` makes each replace the last, so
# there is never more than one thing on screen. The art is
# scripts/build_checkride_cards.py; if it is missing the ride falls back to the
# old text rather than losing the grade altogether.
CARD_FIRST_S = 2         # first item, after the "here comes the card" line
CARD_STEP_S = 8          # one card at a time, at reading pace
CARD_HOLD_S = 900        # replaced by the next card, never expires mid-read
CARD_SIZE_PCT = 30

# --- bands (metres from lead) ------------------------------------------- #
COLLISION_M = 12
POSITION_M = 60
LOST_M = 400
LOST_S = 30

# --- lead-state thresholds ---------------------------------------------- #
LEVEL_BANK = 12          # deg: |bank| below this, and |vs| below LEVEL_VS, is level
TURN_BANK = 20           # deg: |bank| above this is a turn
LEVEL_VS = 2.5           # m/s
JOIN_SETTLE_S = 20       # in the band this long after start = joined, grading arms

# --- rejoin clock ------------------------------------------------------- #
REJOIN_E_S, REJOIN_G_S, REJOIN_F_S, REJOIN_MAX_S = 90, 150, 240, 300

# --- the ratio ladder --------------------------------------------------- #
# (grade, in-multiplier, total-multiplier): in*a >= tot*b <=> in/tot >= b/a
LADDER = (("E", 10, 9), ("G", 4, 3), ("F", 2, 1))

# --- flags ------------------------------------------------------------- #
F_BASE = 8700
F_ARM = 8700            # joined; grading is live
F_PITCH = 8701          # pitchout called
F_WENT_OUT = 8702       # left the band after the pitchout (a rejoin needs a departure)
F_REJOINED = 8703
F_REJOIN_T = 8704       # seconds from pitchout to rejoin
F_CRIT = 8705           # a critical item was busted
F_LOSTSAID = 8706
F_CARD = 8707
F_ANY_F = 8708
F_ANY_U = 8709
F_CRIT_WHY = 8710       # 1 collision, 2 lost, 3 never rejoined
F_SETTLE = 8711         # in the band; the join-settle timer runs on it
# per item: 6 counters (in x10, tot x9, in x4, tot x3, in x2, tot x1)
ITEMS = ("level", "turns", "vertical")
ITEM_LABEL = {"level": "Straight and level", "turns": "Turns",
              "vertical": "Climbs, descents and speed", "rejoin": "Rejoin"}


def item_flags(item: str) -> dict:
    i = ITEMS.index(item)
    base = 8712 + 6 * i
    return {"e_in": base, "e_tot": base + 1, "g_in": base + 2, "g_tot": base + 3,
            "f_in": base + 4, "f_tot": base + 5}


F_LAST = 8712 + 6 * len(ITEMS) - 1       # 8729


def attach(m, player_group, lead_group, profile_seconds: int, warnings=None,
           practice: bool = False, label: str = "Formation") -> int:
    """Wire the engine. `profile_seconds` is when lead finishes the graded
    profile and the pitchout is called. Returns trigger count. NEVER RAISES."""
    warnings = warnings if warnings is not None else []
    if m is None or player_group is None or lead_group is None:
        return 0
    try:
        from dcs import action as A
        from dcs import condition as C
        from dcs import triggers as Tr

        me, lead = player_group.units[0], lead_group.units[0]
        n = 0
        head = "PRE-CHECK (practice)" if practice else "CHECK RIDE"

        cards = {}
        for stem in ([f"{i}_{g}" for i in ITEMS for g in ("E", "G", "F", "U", "none")]
                     + [f"rejoin_{g}" for g in ("E", "G", "F", "U")]
                     + [f"crit_{k}" for k in (1, 2, 3)]
                     + [f"overall_{k}" for k in ("q", "qm", "u", "uc")]):
            f = CARD_DIR / f"checkride_{stem}.png"
            if f.is_file():
                cards[stem] = m.map_resource.add_resource_file(str(f))
        use_cards = len(cards) == 26

        def pic(stem):
            """One card, center screen, replacing whatever was there.

            `.value`, NOT the enum member: pydcs writes what it is handed
            straight into the Lua, and an Enum stringifies to an undefined
            variable that DCS refuses to compile."""
            return A.PictureToGroup(
                player_group, cards[stem], CARD_HOLD_S, True, 0,
                A.PictureAction.HorzAlignment.Center.value,
                A.PictureAction.VertAlignment.Center.value,
                CARD_SIZE_PCT, A.PictureAction.SizeUnits.WindowSize.value)

        def card_acts(stem, text, secs=40):
            """A picture where there is art for it, the old text where there is
            not. Never both: two channels saying the same thing at once is how
            the corner filled up in the first place."""
            return [pic(stem)] if use_cards else [msg(text, secs)]

        def msg(text, secs=20):
            return A.MessageToGroup(player_group.id, m.string(text), secs)

        # ALL OR NOTHING: the whole engine reaches the mission together or not
        # at all. pydcs reads TriggerOnce.predicate at SAVE time, so a
        # half-attached set does not lose the grading, it loses the .miz.
        pending = []

        def rule(comment, conds, actions, once=True):
            nonlocal n
            t = (Tr.TriggerOnce if once else Tr.TriggerContinious)(comment=comment)
            for c in conds:
                t.rules.append(c)
            for a in actions:
                t.actions.append(a)
            pending.append(t)
            n += 1

        inside = lambda r: C.UnitInMovingZone(me.id, r, lead.id)          # noqa: E731
        outside = lambda r: C.UnitOutsideMovingZone(me.id, r, lead.id)     # noqa: E731
        armed, not_pitched = C.FlagIsTrue(F_ARM), C.FlagIsFalse(F_PITCH)
        lead_level = [C.UnitBankWithin(lead.id, -LEVEL_BANK, LEVEL_BANK),
                      C.UnitVerticalSpeedWithin(lead.id, -LEVEL_VS, LEVEL_VS)]
        # A turn either way is two rules, not one Or: pydcs's Or is a bare
        # marker between rule rows and reads badly in the Editor.
        lead_turn_l = [C.UnitBankWithin(lead.id, -89, -TURN_BANK)]
        lead_turn_r = [C.UnitBankWithin(lead.id, TURN_BANK, 89)]
        lead_up = [C.UnitVerticalSpeedWithin(lead.id, LEVEL_VS, 60)]
        lead_dn = [C.UnitVerticalSpeedWithin(lead.id, -60, -LEVEL_VS)]

        # --- brief and arm ------------------------------------------------ #
        rule(f"Check: {head} brief", [C.TimeAfter(5)],
             [msg(f"{head} — {label}. Join and settle in fingertip. Grading "
                  f"starts {JOIN_SETTLE_S} s after you are in position and runs "
                  f"until lead calls the pitchout. Silent until the card." if not practice else
                  f"{head} — {label}. Same profile as the check, coach on. The "
                  f"card at the end is what the check will score.", 25)])
        # Joined: in the band; the settle timer runs on a flag set by presence.
        rule("Check: in position (settle)", [C.FlagIsFalse(F_ARM), inside(POSITION_M),
                                            C.FlagIsFalse(F_SETTLE)],
             [A.SetFlag(F_SETTLE)], once=False)
        rule("Check: reset settle", [C.FlagIsFalse(F_ARM), outside(POSITION_M),
                                    C.FlagIsTrue(F_SETTLE)],
             [A.ClearFlag(F_SETTLE)], once=False)
        rule("Check: armed", [C.FlagIsFalse(F_ARM), C.TimeSinceFlag(F_SETTLE, JOIN_SETTLE_S)],
             [A.SetFlag(F_ARM), msg("Joined. Grading is live.", 6)])

        # --- the items: paired counters ---------------------------------- #
        def counters(item, lead_conds_list):
            f = item_flags(item)
            for k, conds in enumerate(lead_conds_list):
                tot = [A.IncreaseFlag(f["e_tot"], 9), A.IncreaseFlag(f["g_tot"], 3),
                       A.IncreaseFlag(f["f_tot"], 1)]
                inn = [A.IncreaseFlag(f["e_in"], 10), A.IncreaseFlag(f["g_in"], 4),
                       A.IncreaseFlag(f["f_in"], 2)]
                rule(f"Check: {item} total ({k})", [armed, not_pitched] + conds, tot, once=False)
                rule(f"Check: {item} in band ({k})", [armed, not_pitched, inside(POSITION_M)] + conds,
                     inn, once=False)

        counters("level", [lead_level])
        counters("turns", [lead_turn_l, lead_turn_r])
        counters("vertical", [lead_up, lead_dn])

        # --- critical items --------------------------------------------- #
        rule("Check: CRITICAL collision band", [armed, inside(COLLISION_M), C.FlagIsFalse(F_CRIT)],
             [A.SetFlag(F_CRIT), A.SetFlagValue(F_CRIT_WHY, 1),
              msg("CRITICAL — inside the collision band.", 8)])
        rule("Check: lost — start clock", [armed, not_pitched, outside(LOST_M), C.FlagIsFalse(F_LOSTSAID)],
             [A.SetFlag(F_LOSTSAID)])
        rule("Check: lost — back", [C.FlagIsTrue(F_LOSTSAID), inside(LOST_M), C.FlagIsFalse(F_PITCH)],
             [A.ClearFlag(F_LOSTSAID)], once=False)
        rule("Check: CRITICAL lost", [armed, not_pitched, C.TimeSinceFlag(F_LOSTSAID, LOST_S),
                                     outside(LOST_M), C.FlagIsFalse(F_CRIT)],
             [A.SetFlag(F_CRIT), A.SetFlagValue(F_CRIT_WHY, 2),
              msg("CRITICAL — lost wingman: outside 400 m for 30 s.", 8)])

        # --- the pitchout and the rejoin --------------------------------- #
        rule("Check: pitchout", [armed, C.TimeAfter(profile_seconds)],
             [A.SetFlag(F_PITCH),
              msg('LEAD: "Two, pitch out — take spacing, then rejoin fingertip."', 12)])
        rule("Check: rejoin clock", [C.FlagIsTrue(F_PITCH), C.FlagIsFalse(F_REJOINED)],
             [A.IncreaseFlag(F_REJOIN_T, 1)], once=False)
        rule("Check: went out", [C.FlagIsTrue(F_PITCH), outside(POSITION_M * 4)],
             [A.SetFlag(F_WENT_OUT)])
        rule("Check: rejoined", [C.FlagIsTrue(F_WENT_OUT), C.FlagIsFalse(F_REJOINED), inside(POSITION_M)],
             [A.SetFlag(F_REJOINED), msg("Rejoined.", 5)])
        rule("Check: CRITICAL never rejoined",
             [C.FlagIsTrue(F_PITCH), C.FlagIsFalse(F_REJOINED), C.TimeSinceFlag(F_PITCH, REJOIN_MAX_S),
              C.FlagIsFalse(F_CRIT)],
             [A.SetFlag(F_CRIT), A.SetFlagValue(F_CRIT_WHY, 3), A.SetFlag(F_REJOINED)])

        # --- the card ----------------------------------------------------- #
        rule("Check: open the card", [C.FlagIsTrue(F_REJOINED), C.TimeSinceFlag(F_REJOINED, 8)],
             [A.SetFlag(F_CARD),
              msg(f"{head} DEBRIEF — {label}. Items graded U / F / G / E on time in "
                  f"the {POSITION_M} m band; overall Q, Q- or U. One card at a time.", 20)])
        after = lambda s: C.TimeSinceFlag(F_CARD, s)                    # noqa: E731
        for i_item, item in enumerate(ITEMS):
            f = item_flags(item)
            lab = ITEM_LABEL[item]
            at = after(CARD_FIRST_S + i_item * CARD_STEP_S)
            # E: tot*9 < in*10 ; G: tot*3 < in*4 (and not E) ; F: tot*1 < in*2 ; else U.
            e = C.FlagIsLessThanFlag(f["e_tot"], f["e_in"])
            g = C.FlagIsLessThanFlag(f["g_tot"], f["g_in"])
            fg = C.FlagIsLessThanFlag(f["f_tot"], f["f_in"])
            rule(f"Check card: {item} E", [at, e],
                 card_acts(f"{item}_E", f"E  {lab} — 90 % or better in the band."))
            rule(f"Check card: {item} G", [at, C.FlagIsLessThanFlag(f["e_in"], f["e_tot"]), g],
                 card_acts(f"{item}_G", f"G  {lab} — 75 % or better."))
            rule(f"Check card: {item} F", [at, C.FlagIsLessThanFlag(f["g_in"], f["g_tot"]), fg],
                 card_acts(f"{item}_F", f"F  {lab} — 50 % or better; out of position and corrected.")
                 + [A.SetFlag(F_ANY_F)])
            rule(f"Check card: {item} U", [at, C.FlagIsLessThanFlag(f["f_in"], f["f_tot"])],
                 card_acts(f"{item}_U", f"U  {lab} — under 50 % in the band.") + [A.SetFlag(F_ANY_U)])
            rule(f"Check card: {item} not flown", [at, C.FlagEquals(f["f_tot"], 0)],
                 card_acts(f"{item}_none",
                           f"—  {lab} — no window flown (lead never did it while you were joined)."))
        r_at = after(CARD_FIRST_S + len(ITEMS) * CARD_STEP_S)
        rule("Check card: rejoin E", [r_at, C.FlagIsLess(F_REJOIN_T, REJOIN_E_S + 1)],
             card_acts("rejoin_E", f"E  Rejoin — inside {REJOIN_E_S} s."))
        rule("Check card: rejoin G", [r_at, C.FlagIsMore(F_REJOIN_T, REJOIN_E_S), C.FlagIsLess(F_REJOIN_T, REJOIN_G_S + 1)],
             card_acts("rejoin_G", f"G  Rejoin — inside {REJOIN_G_S} s."))
        rule("Check card: rejoin F", [r_at, C.FlagIsMore(F_REJOIN_T, REJOIN_G_S), C.FlagIsLess(F_REJOIN_T, REJOIN_F_S + 1)],
             card_acts("rejoin_F", f"F  Rejoin — inside {REJOIN_F_S} s.") + [A.SetFlag(F_ANY_F)])
        rule("Check card: rejoin U", [r_at, C.FlagIsMore(F_REJOIN_T, REJOIN_F_S)],
             card_acts("rejoin_U", f"U  Rejoin — longer than {REJOIN_F_S} s.") + [A.SetFlag(F_ANY_U)])
        crit_text = {1: "inside the collision band", 2: "lost wingman for 30 s",
                     3: "never rejoined inside 300 s"}
        c_at = after(CARD_FIRST_S + (len(ITEMS) + 1) * CARD_STEP_S)
        for k, why in crit_text.items():
            rule(f"Check card: critical {k}", [c_at, C.FlagEquals(F_CRIT_WHY, k)],
                 card_acts(f"crit_{k}",
                           f"CRITICAL ITEM — {why}. The check is a U regardless of the items above."))
        # Overall. Order of evaluation: U beats Q-, Q- beats Q. The text line
        # stays alongside the picture for this one only — it is the result the
        # pilot writes on the gradesheet, and it should survive in the log.
        o_at = after(CARD_FIRST_S + (len(ITEMS) + 2) * CARD_STEP_S)
        rule("Check card: overall U", [o_at, C.FlagIsTrue(F_CRIT)],
             card_acts("overall_uc", "OVERALL: U — re-fly the check.", 60)
             + ([msg("OVERALL: U — a critical item; re-fly the check.", 60)] if use_cards else []))
        rule("Check card: overall U (items)", [o_at, C.FlagIsFalse(F_CRIT), C.FlagIsTrue(F_ANY_U)],
             card_acts("overall_u", "OVERALL: U — an item below 50 %. Re-fly the check.", 60)
             + ([msg("OVERALL: U — an item below 50 %. Re-fly the check.", 60)] if use_cards else []))
        rule("Check card: overall Q-", [o_at, C.FlagIsFalse(F_CRIT), C.FlagIsFalse(F_ANY_U), C.FlagIsTrue(F_ANY_F)],
             card_acts("overall_qm", "OVERALL: Q- — qualified with discrepancies.", 60)
             + ([msg("OVERALL: Q- — qualified with discrepancies. Additional training on the F items.", 60)] if use_cards else []))
        rule("Check card: overall Q", [o_at, C.FlagIsFalse(F_CRIT), C.FlagIsFalse(F_ANY_U), C.FlagIsFalse(F_ANY_F)],
             card_acts("overall_q", "OVERALL: Q — qualified.", 60)
             + ([msg("OVERALL: Q — qualified. Record it on the gradesheet; the IP grades line, corrections and radio.", 60)] if use_cards else []))
        m.triggerrules.triggers.extend(pending)
        return n
    except Exception as exc:                              # pragma: no cover
        warnings.append(f"check ride not attached: {exc}")
        return 0


def brief_lines(practice: bool = False) -> list[str]:
    head = "PRE-CHECK" if practice else "CHECK RIDE"
    L = [f"=== {head}: FINGERTIP ===",
         "Graded the way an instructor grades: per item, against a standard,",
         "with critical items. The sim fills what it can see; the IP fills",
         "the rest on the gradesheet.",
         "",
         f"  Band: in position = within {POSITION_M} m of lead (radial — the sim",
         "  cannot see the wingline). Grading arms 20 s after you settle in.",
         "  ITEMS  Straight and level · Turns · Climbs, descents and speed —",
         "         each is time in the band while lead is doing it:",
         "         E 90 %+ · G 75 %+ · F 50 %+ · U below.",
         "         Rejoin after the pitchout: E <= 90 s · G <= 150 s · F <= 240 s.",
         f"  CRITICAL  inside {COLLISION_M} m of lead · outside {LOST_M} m for {LOST_S} s ·",
         f"            not rejoined within {REJOIN_MAX_S} s. Any one is a U.",
         "  OVERALL  Q all items G or better · Q- an F item · U a U item or a critical.",
         "",
         ("The coach stays on for this one; the card at the end is what the check will score."
          if practice else
          "Silent. One brief, the pitchout call, then the card. Nobody is surprised on a check ride —"
          " if you are, fly the pre-check again."),
         "",
         "  THE CARD IS A SEQUENCE OF PICTURES, center screen, one every 8 s: the",
         "  three items, the rejoin, any critical, then the overall. One thing on",
         "  screen at a time, at reading pace — it used to be a dozen lines of",
         "  corner text inside six seconds, which is not a debrief, it is a",
         "  blur. Let it run; the overall is the last card."]
    return L
