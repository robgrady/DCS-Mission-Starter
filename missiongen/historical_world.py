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
    return HistoricalSnapshot(when, classification, tuple(rows), sources)
