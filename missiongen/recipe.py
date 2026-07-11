"""Recipe: the full set of wizard inputs. A recipe + seed always regenerates the same starter."""
from dataclasses import dataclass, field, asdict
from typing import Optional, List


@dataclass
class Recipe:
    map: str = "caucasus"              # key into maps.json
    era: str = "coldwar"               # key into eras.json
    coalition: str = "blue"            # player's side
    aircraft: str = "F_16C_50"         # pydcs class name (planes.* or helicopters.*)
    home_airbase: Optional[str] = None # airport name; None = first preset airbase
    slots: int = 1                     # 1 = single player, >1 = multiplayer clients
    start: str = "cold"                # cold | warm | runway
    time_of_day: str = "day"           # dawn | day | dusk | night
    weather: str = "clear"             # clear | scattered | overcast | storm
    density: str = "normal"            # sparse | normal | busy

    # building blocks
    bb_dressing: bool = True           # BB-1..3 static aircraft, GSE, infrastructure
    bb_sams: bool = True               # BB-5..6 SAM sites + SHORAD
    bb_tanker: bool = True             # BB-11
    bb_awacs: bool = True              # BB-12
    bb_comms: bool = True              # BB-18 comms card in briefing
    bb_briefing: bool = True           # BB-21
    bb_kneeboard: bool = True          # BB-19 nav chart kneeboard pages
    bb_carrier: bool = False           # BB-9 carrier strike group (blue, coastal maps)
    bb_ambient: bool = True            # BB-13 ambient AI traffic between friendly fields

    # template packs
    template: Optional[str] = None     # None | "backseat_izlid"

    seed: int = 1

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Recipe":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})
