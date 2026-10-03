"""Orchestrate ordered PyDCS placement phases after world resolution.

World/domain setup lives in build_context; artifact rendering and packaging
live in artifacts. Placement order is significant for RNG and parking.
"""



from ..build_context import CREW_OPS_TEMPLATES
PACKAGE_LEAD_S = 120

class MissionBriefing:
    def _briefing(self, map_cfg, era_cfg, preset, home, comms, stats, template_brief):
        r = self.recipe
        carrier_home = getattr(self, "_carrier_home", False) and self._csg
        where = self._csg.units[0].name if carrier_home else home.name
        if r.template in CREW_OPS_TEMPLATES:
            flight_line = ">> YOUR FLIGHT: see the template briefing below."
        else:
            try:
                ac = self._resolve_aircraft(r.aircraft).id
            except Exception:
                ac = r.aircraft
            if r.cq_ride:
                # A CASE III RIDE IS NOT PARKED, and saying so would be the
                # exact defect this product exists to remove. You begin
                # airborne, in the procedure, at a radial and a DME off the
                # ship — because the lesson is entirely between the marshal
                # fix and the ramp, and a ride that made you launch first
                # would spend fifteen minutes getting to it.
                from .. import cq as _cqb
                _rd = _cqb.ride(r.cq_ride) or {}
                flight_line = (
                    f">> YOUR FLIGHT: {ac}, airborne, recovering aboard "
                    f"{where}. CASE III {_rd.get('n', '')} of "
                    f"{len(_cqb.RIDES)} — {_rd.get('name', '')}. You start in "
                    f"the procedure, not on the deck. "
                    f"REQUIRES {_cqb.REQUIRES_MODULE}.")
            else:
                flight_line = (f">> YOUR FLIGHT: {ac} at {where}, {r.start} start. "
                               f"It's parked and ready — click Fly, or find it in the "
                               f"Mission Editor.")
            if getattr(comms, "channels", None):
                mother = ""
                if comms.channels.get("Carrier") == 2:
                    boat = next((cs for ag, cs, *_ in comms.entries
                                 if ag == "Carrier"), "Mother")
                    mother = f" {boat} is on CH 2."
                flight_line += (f" COMM1 presets are loaded — see the CHAN column "
                                f"on the comms card.{mother}")
        from .. import saydo as _sd
        _clock = _sd.mission_clock(self._mission) if getattr(self, "_mission", None) else None
        _heritage = stats.get("callsign_heritage")
        lines = [
            f"=== DCS SORTIE STARTER ===",
            f"{map_cfg['label']} | {era_cfg['label']} | {preset['frontline_hint']}",
            # THE CLOCK, IN THE BRIEF. Two of the four commercial campaigns on
            # the shelf brief a start time that is not the mission's. Ours is
            # read from the file at the moment the brief is written.
            (f"Mission clock: {_clock} local, {self._mission.start_time.day} "
             f"{self._mission.start_time.strftime('%b').upper()} "
             f"{self._mission.start_time.year}") if _clock else "",
            "",
            flight_line,
            f"Callsign: {stats.get('callsign', '')}." + (f" {_heritage}" if _heritage else ""),
            "",
        ]
        if r.cq_ride:
            # THE STARTER PARAGRAPH IS FALSE ON A TRAINING RIDE. "No objectives,
            # tasking or waypoints" describes a sandbox; this mission has a
            # flight plan, a procedure and grades. Printing the sandbox text
            # over a syllabus ride is a card describing a different mission.
            lines += [
                "This is a TRAINING RIDE, not a sandbox: a flight plan, cues at",
                "each gate, and grades on the parts DCS does not check for",
                "itself. The full card is below.",
                "",
                f"Recovering aboard: {where}",
            ]
        else:
            lines += [
                "This is a STARTER, not a scripted mission: the theater is dressed, air",
                "defenses are up, and tanker/AWACS are on station - but there are NO",
                "objectives, tasking or waypoints (no A/A, A/G, SEAD packages). Take off",
                "and free-fly, or open it in the Mission Editor and build your mission on top.",
                "",
                f"Home plate: {where}",
            ]
        qnh_hpa = getattr(self, "_qnh_hpa", None)
        if qnh_hpa:
            from .. import pressure
            lines.append(f"Altimeter (QNH): {pressure.format_qnh(qnh_hpa)} "
                         f"- set it before you taxi.")
        lines += [
            f"Static objects placed: {stats['statics']}",
            f"Air defense groups: {len(stats['sam_sites'])}",
            f"Support flights: {', '.join(stats['support']) or 'none'}",
        ]
        if stats.get("nttr"):
            # THE CORRIDORS, in the text the pilot reads in the sim.
            lines += [""] + list(stats["nttr"]["brief"])
        if getattr(self, "_timing", None):
            # THE CLOCK ON THE CARD, in the text the pilot reads in the sim.
            # Same rows the kneeboard and the PDF print, from one plan.
            from .. import timing as _tm1
            lines += [""] + _tm1.brief_lines(self._timing, where)
            if r.timing_coach:
                from .. import timing_coach as _tc1
                lines += [""] + _tc1.brief_lines(self._timing,
                                                 package=bool(r.timing_package))
        if stats.get("known_issues"):
            lines += ["", "WHAT DCS WILL GET WRONG:"]
            lines += [f"- {k}" for k in stats["known_issues"]]
        if stats.get("no_enemy_air"):
            # The single most important line in a GWOT brief, and it belongs in
            # the .miz text the pilot actually reads in DCS — not only in the
            # PDF. Silence here reads as "we forgot to list the enemy air",
            # which is the opposite of the intelligence.
            lines += [
                "",
                "NO ENEMY AIR FORCE. Nothing will contest you in the air. Every",
                "threat in this theater fires from the ground and most of it is",
                "optically aimed, which is why the transit altitude is high.",
            ]
        pat = stats.get("pattern")
        if pat:
            from ..pattern import activity_line
            lines.append(activity_line(pat))
        lines += [""]
        if r.bb_comms:
            lines.append(comms.card())
        if template_brief:
            lines.append(template_brief)
        lines += ["", f"Generated by DCS Sortie Starter | variation (seed) {r.seed} — "
                      "same settings + seed rebuild this exact mission; new seed = "
                      "a fresh layout of the same setup"]
        return "\n".join(lines)


