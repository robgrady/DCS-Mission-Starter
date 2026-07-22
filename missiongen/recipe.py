"""Recipe: the full set of wizard inputs. A recipe + seed always regenerates the same starter."""
from dataclasses import dataclass, field, asdict
from typing import Optional, List


class RecipeError(ValueError):
    """A recipe field is invalid (bad enum value or out-of-range). User error →
    the API turns this into a 400/422 with the field message, never a 500."""


# Allowed values for the enum-like fields. Kept here (next to the dataclass) as
# the single source of truth; the server surfaces the same lists in /api/options.
RECIPE_ENUMS = {
    "coalition": ("blue", "red"),
    "start": ("cold", "warm", "runway"),
    "time_of_day": ("dawn", "day", "dusk", "night"),
    "weather": ("clear", "scattered", "overcast", "storm"),
    "density": ("sparse", "normal", "busy"),
    "threat_tier": ("auto", "light", "heavy", "mixed"),
    "dress_aircraft_mode": ("static", "parked_ai"),
    "dress_livery_style": ("squadron", "aggressors", "clean", "random"),
    "crew_difficulty": ("trainee", "qualified"),
}


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
    density: str = "normal"            # sparse | normal | busy (AD/ambient scale)

    # airfield population (BB-1..3 fine control)
    dress_fill: Optional[int] = None   # % of free parking stands to fill (0-100);
                                       # None = derive from density (25/45/70)
    dress_aircraft: bool = True        # parked aircraft on stands
    dress_gse: bool = True             # ground support equipment by occupied stands
    dress_infra: bool = True           # fuel farm / tents / barracks cluster
    dress_overrides: dict = field(default_factory=dict)
                                       # per-base fill overrides {airbase: 0-100}.
                                       # 0 = leave empty; an entry on a CIVILIAN
                                       # base force-populates it ("populate
                                       # anyway"); absent = inherit global.
    dress_aircraft_mode: str = "static"  # "static" (fast, inert, best-effort
                                       # facing) | "parked_ai" (uncontrolled
                                       # flights: DCS aligns to the painted
                                       # parking line exactly, but they cost
                                       # FPS, show as contacts, and pop in)
    dress_mix: Optional[dict] = None   # Ramp Composer: explicit {type_id: count}
                                       # for the PLAYER's fields. When set, places
                                       # exactly these aircraft (round-robin,
                                       # stand-aware) instead of the ramp theme;
                                       # fill% is ignored. None = use the theme.
    dress_theme: Optional[str] = None  # ramp theme key for the PLAYER's fields
                                       # (ramp_themes.json); None = map/era default.
                                       # Enemy fields always use their map/era default.
    dress_livery_style: str = "squadron"  # parked-aircraft skin style (global):
                                       # "squadron" (nation-correct mix, default) |
                                       # "aggressors" (adversary schemes where they
                                       # exist) | "clean" (DCS stock default) |
                                       # "random" (any scheme in the pack). Applies
                                       # to statics on BOTH sides. See dressing._pick_livery.

    # building blocks
    bb_dressing: bool = True           # BB-1..3 static aircraft, GSE, infrastructure
    bb_sams: bool = True               # BB-5..6 SAM sites + SHORAD

    # Threat Dial (v1.6.0): how MANY threats and what LEVEL (see threats.py)
    threat_intensity: int = 3          # 1 Minimal · 2 Light · 3 Moderate ·
                                       # 4 Heavy · 5 Maximum. Controls the random
                                       # count of extra area SAM sites + enemy CAP
                                       # flights on top of base airfield defense.
    threat_tier: str = "auto"          # auto (era doctrine) | light (SA-2/3,
                                       # MiG-21/23) | heavy (SA-10/11, Su-27/MiG-31)
                                       # | mixed. Era-gated (no anachronisms).
    bb_tanker: bool = True             # BB-11
    bb_awacs: bool = True              # BB-12
    bb_comms: bool = True              # BB-18 comms card in briefing
    bb_briefing: bool = True           # BB-21
    bb_kneeboard: bool = True          # BB-19 nav chart kneeboard pages
    bb_carrier: bool = False           # BB-9 carrier strike group (blue, coastal maps)
    bb_ambient: bool = True            # BB-13 ambient AI traffic between friendly fields

    bb_navpoints: bool = True          # BB-22 named geo reference points (F10 map + kneeboard)
    bb_alignment: bool = True          # Theater Identity P1: dress each base with its real owning nation (country + liveries). No-op where no theater_identity data.
    bb_historical_airspace: bool = False  # Theater Identity P3: real corridors/no-fly zones (F10 + brief). Default off = determinism-safe for existing share links.
    corridors: List[str] = field(default_factory=list)  # selected Air Corridor names: orient the threat axis + concentrate enemy AD/CAP down the lane. Empty = open theater.
    bb_dtc: Optional[bool] = None      # F-14B(U) DTC setup card (reference nav/threat/comms for the DTM). None = auto (on only for the F-14B(U)); True/False forces it.
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
    carrier_strike: bool = False                # air wing launches an A-6 medium-attack package on the threat axis (you escort)

    # F10 map graphics layers (v1.2.0): None = auto (draw everything that has
    # geometry); explicit list = only those keys (see graphics.LAYER_KEYS)
    map_layers: Optional[List[str]] = None

    # template packs
    template: Optional[str] = None     # None | backseat_izlid | backseat_intercept | rio_fleet_defense
    crew_difficulty: str = "qualified" # trainee (hints) | qualified (clean)

    seed: int = 1

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict, validate: bool = True) -> "Recipe":
        # Reject unknown fields instead of silently dropping them: a typo'd or
        # stale field (e.g. a renamed option) used to vanish without a trace,
        # so the caller got a *different* mission than they described. Fail loud.
        known = {f for f in cls.__dataclass_fields__}
        unknown = [k for k in d if k not in known]
        if unknown:
            raise RecipeError(
                f"Unknown recipe field(s): {', '.join(sorted(unknown))}. "
                f"Check for typos or an outdated client.")
        r = cls(**{k: v for k, v in d.items() if k in known})
        if validate:
            r.validate()
        return r

    def validate(self) -> "Recipe":
        """Reject invalid enum values and out-of-range numbers with a clear,
        field-level message BEFORE the engine runs. Catches the silent bugs the
        review found — e.g. coalition='purple' used to fall through to the RED
        side ('blue' if coalition=='blue' else red), and weather='banana' was
        applied as nothing. Returns self so it can be chained."""
        for field_name, allowed in RECIPE_ENUMS.items():
            val = getattr(self, field_name)
            if val not in allowed:
                raise RecipeError(
                    f"{field_name}={val!r} is not valid; expected one of "
                    f"{', '.join(allowed)}.")
        # map/era are keys into the data packs. Validate here with a clear
        # message; otherwise a bad key KeyErrors deep in the builder, which
        # (now that KeyError is no longer treated as a user error) would surface
        # as an opaque 500 instead of "unknown theater".
        from .resolver import load_json
        if self.map not in load_json("maps"):
            raise RecipeError(f"map={self.map!r} is not a known theater.")
        if self.era not in load_json("eras"):
            raise RecipeError(f"era={self.era!r} is not a known era.")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise RecipeError(f"seed must be an integer, got {self.seed!r}.")
        if not (1 <= self.slots <= 4):
            raise RecipeError(f"slots must be 1-4, got {self.slots!r}.")
        if self.dress_fill is not None and not (0 <= self.dress_fill <= 100):
            raise RecipeError(f"dress_fill must be 0-100, got {self.dress_fill!r}.")
        if not (1 <= self.threat_intensity <= 5):
            raise RecipeError(
                f"threat_intensity must be 1-5, got {self.threat_intensity!r}.")
        return self
