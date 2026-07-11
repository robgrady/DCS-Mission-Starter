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

    bb_navpoints: bool = True          # BB-22 named geo reference points (F10 map + kneeboard)
    bb_farps: bool = False             # BB-4 functional FARPs (helo ops; not WWII)
    bb_targets: bool = False           # BB-16 strike target packages in the enemy rear
    bb_range: bool = False             # BB-17 practice range in the friendly rear

    # carrier deck configuration (when bb_carrier)
    carrier_hull: Optional[str] = None          # key into carrier_decks.json; None = era default
    carrier_layout: str = "recovery"            # recovery | launch | packed
    carrier_deck_aircraft: List[str] = field(default_factory=list)  # pydcs keys to park
    carrier_equipment: bool = True              # tugs, MJ-1s, crash gear
    carrier_cap: bool = False                   # air wing launches a 2-ship CAP on the threat axis
    carrier_aew: bool = False                   # air wing launches an E-2 Hawkeye AEW orbit (AAW picture)

    # template packs
    template: Optional[str] = None     # None | backseat_izlid | backseat_intercept | rio_fleet_defense
    crew_difficulty: str = "qualified" # trainee (hints) | qualified (clean)

    seed: int = 1

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Recipe":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})
