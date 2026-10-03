"""Dated historical facts, distinct from game coalition and visual nationality.

Legacy presets are broad historical adaptations. Missing sources/roles remain
unknown; assigning a PyDCS country never certifies territorial sovereignty.
"""
from dataclasses import dataclass
from datetime import date
from .resolver import load_json

@dataclass(frozen=True)
class Validity:
    valid_from: date | None = None
    valid_to: date | None = None

    def contains(self, when: date) -> bool:
        return (self.valid_from is None or self.valid_from <= when) and (
            self.valid_to is None or when <= self.valid_to)

    @classmethod
    def from_data(cls, entry):
        parse = lambda key: date.fromisoformat(entry[key]) if entry.get(key) else None
        interval = cls(parse('valid_from'), parse('valid_to'))
        if interval.valid_from and interval.valid_to and interval.valid_from > interval.valid_to:
            raise ValueError('Historical validity interval is reversed')
        return interval

@dataclass(frozen=True)
class BaseIdentity:
    name: str
    display_nation: str | None
    territorial_host: str | None
    military_operator: str | None
    mission_coalition: str | None
    validity: Validity
    sources: tuple[str, ...]

@dataclass(frozen=True)
class HistoricalSnapshot:
    mission_date: date
    classification: str
    bases: tuple[BaseIdentity, ...]
    sources: tuple[str, ...]
    notes: tuple[str, ...] = ()


CLASSIFICATIONS = {
    'reconstruction': 'Historical reconstruction',
    'historically_inspired_adaptation': 'Historically inspired adaptation',
    'fictional_exercise': 'Fictional exercise',
}


def resolve_setting(map_key, era, preset, template=None):
    """Authored map/lineup context, then template-specific era/map metadata.

    Dates are internal content defaults, not additional recipe/share fields.
    A template override only applies to its selected map and era.
    """
    from .templates import templates
    setting = dict(preset)
    tpl = templates().get(template, {})
    for block in (tpl.get('historical', {}),
                  tpl.get('historical_by_era', {}).get(era, {}),
                  tpl.get('historical_by_map', {}).get(map_key, {})):
        notes = [*setting.get("historical_notes", []), *block.get("historical_notes", [])]
        sources = [*setting.get("historical_sources", []), *block.get("historical_sources", [])]
        setting.update(block)
        setting["historical_notes"] = list(dict.fromkeys(notes))
        setting["historical_sources"] = list(dict.fromkeys(sources))
    setting.setdefault('historical_classification', 'historically_inspired_adaptation')
    if setting['historical_classification'] not in CLASSIFICATIONS:
        raise ValueError('Unknown historical classification')
    return setting


def scenario_date(setting, era_cfg):
    when = date.fromisoformat(setting['scenario_date']) if setting.get('scenario_date') else date(era_cfg['year'], 6, 21)
    if not era_cfg['window'][0] <= when.year <= era_cfg['window'][1]:
        raise ValueError('Authored scenario date is outside its era')
    return when


def preview(map_key, era, template=None, lineup=None):
    maps = load_json('maps')
    cfg = maps[map_key]
    preset = dict(cfg['presets'][era])
    if lineup:
        preset.update(cfg.get('lineups', {}).get(lineup, {}))
    setting = resolve_setting(map_key, era, preset, template)
    return {'date': scenario_date(setting, load_json('eras')[era]).isoformat(),
            'classification': setting['historical_classification'],
            'label': CLASSIFICATIONS[setting['historical_classification']],
            'notes': setting.get('historical_notes', []),
            'sources': setting.get('historical_sources', [])}


def brief_lines(history):
    return [f"HISTORICAL CONTEXT: {history.mission_date.isoformat()} — {CLASSIFICATIONS[history.classification]}",
            *history.notes,
            'Equipment is filtered by recorded weapon service year and DCS station compatibility; '
            'unknown service dates, operator availability and module variants are not historically certified.',
            *[f'Source: {url}' for url in history.sources]]


def snapshot(map_key, era, when: date, preset) -> HistoricalSnapshot:
    data = load_json('theater_identity').get(map_key, {}).get(era, {})
    roles = data.get('identities', {})
    rows = []
    for name, display_nation in data.get('bases', {}).items():
        identity = roles.get(name, {})
        validity = Validity.from_data(identity)
        if not validity.contains(when):
            continue
        # Coalition comes from the authored mission preset, not from the host.
        side = next((s for s in ('blue','red') if name in preset.get(s+'_airbases', [])), None)
        rows.append(BaseIdentity(name, identity.get('display_nation', display_nation),
                                 identity.get('territorial_host'), identity.get('military_operator'),
                                 side, validity, tuple(identity.get('sources', []))))
    classification = preset.get('historical_classification', 'historically_inspired_adaptation')
    sources = tuple(preset.get('historical_sources', []))
    if classification == 'reconstruction' and not sources:
        raise ValueError('Historical reconstruction requires sources')
    return HistoricalSnapshot(when, classification, tuple(rows), sources,
                              tuple(preset.get('historical_notes', [])))


def template_previews(key):
    """Same effective map/lineup precedence as generation, for catalog surfaces."""
    from .templates import templates, effective_recipe
    tpl = templates().get(key, {})
    out = {}
    maps = load_json('maps')
    for era in tpl.get('eras', []):
        allowed = tpl.get('maps') or list(maps)
        out[era] = {}
        for mk in allowed:
            if era not in maps.get(mk, {}).get('presets', {}):
                continue
            cfg = effective_recipe(key, era, mk)
            out[era][mk] = preview(mk, era, key, cfg.get('lineup'))
    return out
