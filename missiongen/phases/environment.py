from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from ..build_context import WorldContext
from ..resolver import load_json
from .. import dressing
if TYPE_CHECKING:
    from ..builder import StarterBuilder
from .player import PlayerPlacement

@dataclass(frozen=True)
class EnvironmentPlacement:
    """Facts passed to subsequent phases; mission/stat mutations stay ordered."""
    enemy_flies: bool
    ambient_aircraft: tuple[str, ...]
    static_objects: int


def place_environment(builder: StarterBuilder, ctx: WorldContext, player: PlayerPlacement) -> EnvironmentPlacement:
    self = builder
    r = builder.recipe
    _get_country = ctx.country
    carrier_home = ctx.carrier_home
    enemy_country = ctx.enemy_country
    enemy_fields = ctx.enemy_fields
    era_cfg = ctx.era_cfg
    home = player.home
    m = ctx.mission
    map_cfg = ctx.map_cfg
    own_country = ctx.own_country
    own_fields = ctx.own_fields
    preset = ctx.preset
    stats = ctx.stats
    # --- building blocks -------------------------------------------------
    # Does the enemy fly at all? `threats.TIER_CAP` is the single source of
    # truth, and in the GWOT era the answer is no. Read once, here, because
    # three separate things downstream depend on it: enemy ambient traffic,
    # the SITUATION paragraph, and (via the empty SAM pools) whether the
    # area threat belt is guns.
    _enemy_side_key = "red" if r.coalition == "blue" else "blue"
    from .. import threats as _thr_amb
    enemy_flies = bool(_thr_amb.cap_types_for(r.era, _enemy_side_key, "auto"))
    stats["no_enemy_air"] = not enemy_flies

    # ambient traffic BEFORE dressing so AI aircraft claim parking slots first
    if r.bb_ambient:
        from .. import ambient
        enemy_side = _enemy_side_key
        stats["ambient"] += ambient.add_ambient_traffic(
            m, own_country, own_fields, era_cfg[r.coalition], r.density,
            self.rng, "friendly")
        # Enemy ambience only where the enemy HAS an air force. The GWOT
        # era's red parked_planes are derelict Iraqi Air Force airframes
        # left where they stood; ambient traffic would taxi them out and
        # fly them, which is the single most wrong thing this era could do.
        if enemy_flies:
            stats["ambient"] += ambient.add_ambient_traffic(
                m, enemy_country, enemy_fields, era_cfg[enemy_side], r.density,
                self.rng, "enemy")

    # BB-23: aircraft in the pattern at the player's own field. Also before
    # dressing, so departing traffic gets its parking stand first. Skipped
    # when home plate is the boat (no runway pattern to fly).
    if getattr(r, "bb_pattern", False) and not carrier_home and home is not None:
        from .. import pattern
        _lineup_on = bool(getattr(r, "pattern_lineup", False))
        names = pattern.add_pattern_traffic(
            m, own_country, home, era_cfg[r.coalition],
            r.pattern_mode, r.pattern_kind, r.pattern_count,
            self.rng, self.warnings, lineup=_lineup_on, map_key=r.map)
        if names:
            _nm = set(names)
            _ac = sum(len(g.units) for g in (list(own_country.plane_group)
                                              + list(own_country.helicopter_group))
                      if g.name in _nm)
            stats["pattern"] = {
                "names": names, "mode": r.pattern_mode,
                "kind": r.pattern_kind, "field": home.name,
                "lineup": _lineup_on, "aircraft": _ac or len(names)}

    if r.bb_dressing:
        enemy_side = "red" if r.coalition == "blue" else "blue"
        # ramp themes: player's choice for own fields; enemy fields always
        # use their map/era default (era-gated by structure)
        own_tkey, own_theme = dressing.resolve_theme(
            r.era, r.coalition, preset, r.dress_theme, self.warnings)
        _, enemy_theme = dressing.resolve_theme(r.era, enemy_side, preset)
        if own_tkey:
            stats["ramp_theme"] = own_tkey
        dress_kw = dict(fill=r.dress_fill,
                        include_aircraft=r.dress_aircraft,
                        include_gse=r.dress_gse,
                        include_infra=r.dress_infra,
                        aircraft_mode=r.dress_aircraft_mode,
                        era=r.era,
                        on=m.start_time.date().isoformat(),
                        ramp_heavies=getattr(r, "ramp_heavies", "auto"),
                        livery_style=getattr(r, "dress_livery_style", "squadron"))
        # ONLY MILITARY INSTALLATIONS get ramp dressing. Civilian airports
        # (McCarran, Dubai Intl, Murmansk...) stay undressed — no combat
        # aircraft rows on an airline apron. They remain usable as home
        # plate and for ambient traffic; classification is per map/era
        # (Tinian 1944 is a bomber base; Tinian today is a civil field).
        civilian = set(preset.get("civilian_airbases", []))
        overrides = r.dress_overrides or {}
        # measured painted-line headings for THIS map (parking_headings.json);
        # static aircraft at a listed field face the exact heading instead of
        # the geometric guess. Absent map/field => geometric guess (no change).
        try:
            field_hdgs = load_json("parking_headings").get(r.map, {})
        except Exception:
            field_hdgs = {}
        skipped = []

        # Bases with covered parking (sun-shelters over the stands, e.g.
        # Kandahar): the per-aircraft GSE truck is offset to the side of the
        # jet and lands on the shelter's curved roof — DCS clamps it to that
        # sloped mesh so the truck sits tilted on top. We have no scenery
        # geometry to place around, so GSE is suppressed at these bases;
        # aircraft (placed AT the stand, which fits under the arch) are kept.
        covered_ramp = set(map_cfg.get("covered_ramp", []))

        def _dress(ap, country, cfg, theme, side, mix=None):
            ov = overrides.get(ap.name)
            # civilian fields stay empty UNLESS explicitly overridden
            # ("populate anyway"); an override of 0 empties ANY field
            if ov is None and ap.name in civilian:
                skipped.append(ap.name); return 0
            if ov == 0:
                skipped.append(ap.name); return 0
            kw = dict(dress_kw)
            if ap.name in covered_ramp:
                kw["include_gse"] = False       # trucks would clip the shelters
            if ov is not None:
                kw["fill"] = ov
            kw["field_heading"] = field_hdgs.get(ap.name)
            kw["mix"] = mix
            kw["map_key"] = r.map
            # Per-FIELD ramp identity: Nellis is the Red Flag ramp, the test
            # sites that share the map are not. Only consulted when the map
            # actually names this field — otherwise the caller's theme wins,
            # because it may already carry something more specific.
            #
            # `side` is PASSED IN, not inferred. v1.47.0 worked it out with
            # `theme is own_theme`, an identity check against a value the
            # caller had already transformed: `_atheme()` merges an aligned
            # nation's roster over the side theme and returns a NEW dict, so
            # the check was false for every internationally-aligned base and
            # flipped it to the enemy side. Incirlik — blue, Turkish, NATO —
            # came out parked with A-50s, Il-76s, Su-24s and MiG-29s.
            # ONLY the per-field table may override, and only for a field it
            # actually names. The caller's `theme` has already been through
            # resolve_theme (with the user's explicit choice) and then
            # through _atheme, which merges an aligned nation's roster over
            # it. Re-resolving here for any other reason throws that away —
            # which is the second instance of the same bug, and would have
            # put the map's default ramp on Akrotiri the moment someone
            # picked a theme in the Builder.
            per_field = ((preset.get(f"{side}_field_themes") or {})
                         .get(ap.name))
            field_theme = None
            if per_field and not align_bases.get(ap.name):
                _k, field_theme = dressing.resolve_theme(
                    r.era, side, preset, None, airport_name=ap.name)
            return dressing.dress_airfield(
                m, ap, country, cfg, r.density, self.rng,
                theme=field_theme or theme, **kw)

        # International Alignment (Theater Identity P1): dress each base with
        # its REAL owning nation's country so statics carry the right national
        # identity + liveries (Israeli base -> Israeli jets, RAF Akrotiri ->
        # RAF, Syrian bases -> Syrian). Additive: no data => side default.
        align_bases = {}
        if r.bb_alignment:
            from .. import alignment
            align_bases = {identity.name: identity.display_nation
                           for identity in ctx.historical.bases if identity.display_nation}
        aligned_used = set()

        def _acountry(ap, default_c, side):
            nat = align_bases.get(ap.name)
            if not nat:
                return default_c
            try:
                c = _get_country(nat, side)
                aligned_used.add(nat)
                return c
            except Exception:
                return default_c

        def _atheme(ap, side_theme):
            # aligned base -> that nation's fast-jet roster merged over the
            # side theme (nation-correct TYPES, not just skins). No roster
            # for the nation/era => side theme unchanged.
            nat = align_bases.get(ap.name)
            if not nat:
                return side_theme
            from .. import alignment
            return alignment.roster_theme(r.era, nat, side_theme)

        # the custom mix (Ramp Composer) applies to the PLAYER's own fields;
        # enemy fields always dress from their era/map theme
        for ap in own_fields:
            stats["statics"] += _dress(
                ap, _acountry(ap, own_country, r.coalition),
                era_cfg[r.coalition], _atheme(ap, own_theme),
                r.coalition, mix=r.dress_mix)
        for ap in enemy_fields:
            stats["statics"] += _dress(
                ap, _acountry(ap, enemy_country, enemy_side),
                era_cfg[enemy_side], _atheme(ap, enemy_theme), enemy_side)
        from ..dressing import livery_pack_verified as _lv
        if r.dress_livery_style != "clean" and not _lv():
            self.warnings.append(
                "Parked statics use source-verified era/nation skins where "
                "available, otherwise DCS stock skins. The broader curated "
                "livery pack is unverified, so its names are not written. Run "
                "scripts/dump_liveries.py --merge against your DCS install "
                "to enable nation-correct skins.")
        if aligned_used:
            stats["alignment"] = sorted(aligned_used)
        if skipped:
            stats["civilian_undressed"] = skipped

    return EnvironmentPlacement(enemy_flies, tuple(stats["ambient"]), stats["statics"])
