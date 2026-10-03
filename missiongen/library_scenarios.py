"""Dedicated actors promised by Library cards, independent of ambient traffic."""
from dcs import task, condition, action, triggers
from dcs.point import PointAction
from .resolver import resolve


def _offset(point, metres, heading):
    return point.point_from_heading(heading, metres)


def add_actors(ctx, recipe, player, gfx):
    """Return factual briefing lines for newly placed actors."""
    m, own, enemy = ctx.mission, ctx.own_country, ctx.enemy_country
    key = recipe.template
    lines = []
    if key in ("bc_ti1", "wk_9_intercepts", "wk_10_threeship") and player:
        # Relative geometry uses the flight's actual initial route, not a
        # generic enemy airport or an incidental ambient flight.
        start = player.points[0]
        heading = (start.position.heading_between_point(player.points[1].position)
                   if len(player.points) > 1 else player.units[0].heading)
        pos = _offset(start.position, 25 * 1852, heading)
        altitude = start.alt + 2000 / 3.28084
        target = m.flight_group_inflight(enemy, "TRAINING Radar target", player.flight_type(),
                                         pos, altitude=int(altitude), speed=650,
                                         maintask=task.Nothing, group_size=1)
        target.add_waypoint(_offset(pos, 100000, heading), altitude=int(altitude), speed=650)
        target.points[0].tasks += [task.OptROE(task.OptROE.Values.WeaponHold),
                                  task.OptReactOnThreat(task.OptReactOnThreat.Values.NoReaction)]
        for u in target.units:
            u.pylons = {}
        ctx.stats["training_target"] = {"group": target.name, "range_nm": 25,
                                         "vertical_separation_ft": 2000}
        lines += ["TRAINING TARGET: one clean, weapon-hold aircraft 25 NM ahead",
                  "and 2,000 ft above your start altitude, on a straight 650 km/h leg.",
                  "No automatic coaching or role rotation. Reset/rebrief before another pass."]
    if key not in ("af_tic_cas", "af_convoy_overwatch", "f100_fulda_cas"):
        return lines
    # Aircraft/airport terrain coordinates are authored data; OnRoad lets DCS
    # route vehicles using the terrain's road graph. This is a notional local
    # exercise, not a surveyed Helmand operation or a historical battle.
    anchor = ctx.home.position
    begin = _offset(anchor, 6500, ctx.threat_bearing)
    end = _offset(begin, 6000, ctx.threat_bearing)
    if key == "f100_fulda_cas":
        armor = m.vehicle_group(enemy, "SCENARIO Advancing armor", resolve("vehicles.Armor.T_55"),
                                begin, group_size=4, move_formation=PointAction.OnRoad)
        armor.add_waypoint(end, move_formation=PointAction.OnRoad, speed=25)
        gfx["targets"].append((begin, "Advancing armor"))
        ctx.stats.setdefault("targets", []).append("Moving armor column")
        lines += ["TARGET: a four-vehicle armor column advances on a DCS road route.",
                  "Its starting position is marked; find and attack the moving column."]
    elif key == "af_convoy_overwatch":
        convoy = m.vehicle_group(own, "SCENARIO Friendly convoy", resolve("vehicles.Unarmed.M_818"),
                                 begin, group_size=4, move_formation=PointAction.OnRoad)
        convoy.add_waypoint(end, move_formation=PointAction.OnRoad, speed=20)
        ambush_pos = _offset(begin, 3500, ctx.threat_bearing)
        ambush = m.vehicle_group(enemy, "SCENARIO Ambush", resolve("vehicles.Armor.BTR_80"),
                                 _offset(ambush_pos, 500, ctx.threat_bearing + 90), group_size=2)
        ambush.late_activation = True
        zone = m.triggers.add_triggerzone(ambush_pos, radius=1200, name="CONVOY Ambush approach")
        t = triggers.TriggerOnce(comment="Convoy approaches ambush")
        t.rules.append(condition.PartOfGroupInZone(convoy.id, zone.id))
        t.actions += [action.ActivateGroup(ambush.id),
                      action.MessageToAll(m.string("Friendly convoy approaching the ambush area. Identify hostile vehicles before attacking."), 20)]
        m.triggerrules.triggers.append(t)
        gfx.setdefault("routes", []).append((begin, end, "FRIENDLY CONVOY road route"))
        gfx["targets"].append((ambush_pos, "Convoy ambush area"))
        ctx.stats.setdefault("targets", []).append("Convoy ambush")
        lines += ["FRIENDLY CONVOY: four trucks follow the marked road route at 20 km/h.",
                  "Two hostile armored vehicles activate as the convoy approaches the ambush zone.",
                  "Notional local road exercise; no automated mission score."]
    else:
        patrol = m.vehicle_group(own, "SCENARIO Patrol in contact", resolve("vehicles.Armor.M_113"),
                                 begin, group_size=2)
        hostile = m.vehicle_group(enemy, "SCENARIO TIC hostile", resolve("vehicles.Armor.BMP_2"),
                                  _offset(begin, 800, ctx.threat_bearing), group_size=2)
        jtac = m.vehicle_group(own, "SCENARIO JTAC Pointer", resolve("vehicles.Unarmed.Hummer"),
                               _offset(begin, 250, ctx.threat_bearing + 90))
        jtac.points[0].tasks.append(task.FACEngageGroup(
            hostile.id, visible=True, frequency=30, modulation=task.Modulation.FM,
            designation=task.Designation.Laser))
        gfx["targets"].append((hostile.units[0].position, "TIC hostile vehicles"))
        ctx.stats.setdefault("targets", []).append("TIC hostile vehicles")
        ctx.stats["jtac"] = {"group": jtac.name, "frequency_mhz": 30, "modulation": "FM"}
        lines += ["JTAC POINTER: 30.000 MHz FM, native DCS FAC task on the hostile group.",
                  "Friendly patrol is 800 m from the hostile vehicles. Verify friendlies and clearance.",
                  "No scripted 9-line or automatic danger-close clearance; use the DCS JTAC radio menu."]
    return lines


def complete_strike(ctx, strike, csg, gfx):
    """Task the actual strike against an emitted target, then recover at its ship."""
    if not strike or not csg:
        return []
    targets = [g for g in ctx.enemy_country.vehicle_group if g.name.startswith("TGT")]
    if not targets:
        return ["Strike flight has no generated target; assign one in the Mission Editor."]
    target = targets[0]
    point = strike.add_waypoint(target.units[0].position, altitude=3000, speed=700,
                               name="STRIKE ATTACK")
    point.tasks.append(task.AttackGroup(target.id, weapon_type=task.WeaponType.Bombs,
                                        group_attack=True, attack_limit=1))
    recovery = strike.add_waypoint(csg.units[0].position, altitude=0, speed=250,
                                   name="RECOVER AT CARRIER")
    recovery.type = "Land"
    recovery.action = PointAction.Landing
    recovery.link_unit = recovery.helipad_id = csg.units[0].id
    ctx.stats["carrier_strike_target"] = target.name
    gfx.setdefault("routes", []).append((point.position, recovery.position, "STRIKE RECOVERY"))
    return [f"STRIKE: {strike.name} carries unguided bombs, attacks {target.name},",
            "then follows its recovery leg to the carrier. Protect the ingress and return."]
