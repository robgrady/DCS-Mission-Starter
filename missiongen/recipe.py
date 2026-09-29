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
    "coach_ring": ("red", "green"),
    "start": ("cold", "warm", "runway", "air"),
    "time_of_day": ("dawn", "day", "dusk", "night"),
    "weather": ("clear", "scattered", "overcast", "storm"),
    "density": ("sparse", "normal", "busy"),
    "threat_tier": ("auto", "light", "heavy", "mixed", "guns"),
    "dress_aircraft_mode": ("static", "parked_ai"),
    "dress_livery_style": ("squadron", "aggressors", "clean", "random"),
    "ramp_heavies": ("none", "light", "auto", "surge"),
    "player_load": ("light", "standard", "heavy"),
    # Formation training: which stage of the syllabus. None = not a formation
    # sortie (every other mission the tool makes).
    "formation": (None, "route", "close", "energy", "rejoin", "takeoff",
                  "precheck", "check"),
    "crew_difficulty": ("trainee", "qualified"),
    # The BFM ladder. Three perches plus the everyday neutral fight; see
    # missiongen/bfm.py for the geometry and the standards each one is flown to.
    # The last six are the AETC B-course setups (9,000/6,000/3,000 ft, both
    # offensive and defensive); the first four are ours and are kept because
    # share links minted against them must keep building the same mission.
    "bfm_setup": ("neutral", "offensive", "defensive", "high_aspect",
                  "off_9k", "off_6k", "off_3k",
                  "def_9k", "def_6k", "def_3k"),
    # Which tanker to meet. None = matched to the receiver (boom vs probe) and
    # to whether you are off the boat. See missiongen/aar.py.
    "tanker_type": (None, "kc135", "kc135mprs", "kc130", "s3b", "ka6d", "il78"),
    "pattern_mode": ("landing", "takeoff", "both"),
    "pattern_kind": ("fighter", "cargo", "helicopter", "mixed"),
    # The kind of sortie the Builder is set up for. Mirrors the roles the
    # curated templates already carry (library.role in mission_templates.json)
    # so the two doors describe missions the same way.
    "mission_kind": ("open", "a2a", "strike", "cas", "sead", "carrier",
                     "training"),
    # What the route's clock is anchored on. See missiongen/timing.py.
    "timing_anchor": ("takeoff", "push", "tot"),
}


@dataclass
class Recipe:
    map: str = "caucasus"              # key into maps.json
    era: str = "coldwar"               # key into eras.json
    coalition: str = "blue"            # player's side
    lineup: Optional[str] = None       # key into maps.json <map>.lineups —
                                       # a named ORDER OF BATTLE that replaces
                                       # the era preset's countries and airfield
                                       # ownership. An era says WHEN; a lineup
                                       # says WHO, and one map+era can honestly
                                       # have more than one. Sinai's Cold War
                                       # preset is October 1973 (Israel blue,
                                       # Egypt red); Proud Phantom is June 1980
                                       # with the USAF flying out of Cairo West
                                       # as Egypt's guest. Both are Sinai, both
                                       # are Cold War, and nothing short of this
                                       # can express the second — which is why
                                       # eleven rides advertised as "flown from
                                       # the base they actually deployed to"
                                       # were built taking off from Israel to
                                       # bomb it. None = the era preset.
    aircraft: str = "F_16C_50"         # pydcs class name (planes.* or helicopters.*)
    home_airbase: Optional[str] = None # airport name; None = first preset airbase
    coach_gates: bool = False          # DCS's native helper gates — the green
                                       # "fly through the box" squares from the
                                       # training missions — drawn along the
                                       # player's flight plan. A Mission Editor
                                       # trigger action (a_show_route_gates_for
                                       # _unit), NOT Lua: the no-script
                                       # guarantee holds.
    coach_ring: str = "red"            # the you-are-here ring on the coached
                                       # cue cards. A presentation choice, so it
                                       # lives in the RECIPE rather than the
                                       # ride: the green variant of the coached
                                       # B'NAI is the SAME ride — same route,
                                       # same cues, same wingman — differing in
                                       # exactly the color of the ring.
    cq_ride: Optional[str] = None      # key into cq.RIDES — the Case III night
                                       # recovery syllabus. Set by a template,
                                       # never by the wizard: a Case III ride
                                       # is an airborne start at a point
                                       # computed from the carrier's own BRC,
                                       # which is not a knob a picker can
                                       # offer. Implies home_airbase=CARRIER
                                       # and requires DCS: Supercarrier.
    slots: int = 1                     # 1 = single player, >1 = multiplayer clients
    start: str = "cold"                # cold | warm | runway | air (airborne;
                                       # position picked by the template's
                                       # air_start flag — tanker/merge/generic)
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
    player_arm: bool = True            # arm YOUR jet from the mission kind. It used
                                       # to spawn clean on every kind, described as
                                       # "your loadout is yours to set in the Mission
                                       # Editor" — but that was the same missing
                                       # payload data that left the bandits clean
                                       # until v1.44.0, not a decision.
    player_load: str = "standard"      # how much your jet carries: "light" |
                                       # "standard" | "heavy". Not a per-pylon
                                       # picker — that already exists and it is
                                       # called the Mission Editor.
    formation: object = None           # formation-flying stage; see formation.py.
                                       # When set, the player flies as DASH 2 on
                                       # an AI lead flying a scripted profile —
                                       # the one thing `slots` cannot express,
                                       # since it makes every seat a client.
    ramp_heavies: str = "auto"         # how much of each ramp is HELD for tankers,
                                       # AWACS and transports. Without a reservation
                                       # the fighter pool wins every big stand and no
                                       # tanker ever parks — measured at Nellis, zero
                                       # parked tankers or AWACS across eight seeds.
                                       # "none" | "light" | "auto" | "surge"
                                       # (see dressing.RAMP_HEAVIES).

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
                                       # | mixed | guns (AAA clusters, ZERO SAM
                                       # sites — see threats.TIER_AAA). Era-gated.
    bb_tanker: bool = True             # BB-11
    bb_awacs: bool = True              # BB-12
    bb_comms: bool = True              # BB-18 comms card in briefing
    bb_briefing: bool = True           # BB-21
    bb_kneeboard: bool = True          # BB-19 nav chart kneeboard pages
    bb_carrier: bool = False           # BB-9 carrier strike group (blue, coastal maps)
    bb_ambient: bool = True            # BB-13 ambient AI traffic between friendly fields
    bb_pattern: bool = False           # BB-23 aircraft in the pattern at YOUR field
    tanker_type: Optional[str] = None  # see RECIPE_ENUMS["tanker_type"]
    pattern_mode: str = "landing"      # landing | takeoff | both
    pattern_kind: str = "fighter"      # fighter | cargo | helicopter | mixed
    pattern_count: int = 2             # how many aircraft in the pattern
                                       # (1..pattern.MAX_COUNT — one bound,
                                       # owned by the module that flies them)

    bb_navpoints: bool = True          # BB-22 named geo reference points (F10 map + kneeboard)
    bb_alignment: bool = True          # Theater Identity P1: dress each base with its real owning nation (country + liveries). No-op where no theater_identity data.
    bb_historical_airspace: bool = False  # Theater Identity P3: real corridors/no-fly zones (F10 + brief). Default off = determinism-safe for existing share links.
    corridors: List[str] = field(default_factory=list)  # selected Air Corridor names: orient the threat axis + concentrate enemy AD/CAP down the lane. Empty = open theater.
    bb_branding: bool = True             # sponsor/brand splash at mission start (cosmetic only). NOT a user option — always on; governed globally by the admin/sponsor setting, not exposed in the builder UI.
    bb_dtc: Optional[bool] = None      # F-14B(U) DTC setup card (reference nav/threat/comms for the DTM). None = auto (on only for the F-14B(U)); True/False forces it.
    bb_farps: bool = False             # BB-4 functional FARPs (helo ops; not WWII)
    bb_bfm: bool = False               # E2: one era-correct adversary spawned
    # Which BFM ride (see missiongen/bfm.py). The rung is a PARAMETER of the
    # rep, not four separate cards: offensive/defensive/high_aspect are the
    # same exercise asked from three positions.
    bfm_setup: str = "neutral"
                                       # 2nm abeam the player, co-alt, fight's
                                       # on at the merge (Quick Flight BFM)
    bb_targets: bool = False           # BB-16 strike target packages in the enemy rear
    target_packages: Optional[List[str]] = None
                                       # E3/R7: WHICH packages (keys into
                                       # targets.TARGET_PACKAGES). None = the
                                       # legacy random two — the default that
                                       # keeps every existing share link
                                       # regenerating identically.
    bb_range: bool = False             # BB-17 practice range in the friendly rear
    # BB-18 auto flight plan: WP1 > IP > TARGET > home on the PLAYER's flight.
    # OFF by default and deliberately so — "we set the stage, you write the
    # play" stays the behavior nobody has to opt out of, and every share link
    # written before this field existed keeps generating what it always did.
    # Needs a target to aim at (bb_targets, or a template that places one);
    # with none it is a no-op rather than an invented destination.
    bb_route: bool = False
    # Thread that route through the map's published corridors where it has
    # them (corridors.py: Nevada, Syria, Cold War Germany). Off keeps the
    # generic WP1 > IP > TARGET plan. (Not `corridors` above - that is the
    # Air Corridor threat-axis list, a different thing with an older name.)
    published_corridors: bool = True
    # Waypoint timing on that route (missiongen/timing.py). The card always
    # carries ETAs once there is a route; these choose what the clock is
    # anchored on and whether the mission grades you against it.
    timing_anchor: str = "takeoff"     # takeoff | push (WP1 clock) | tot (TARGET clock)
    timing_at: Optional[str] = None    # "HH:MM[:SS]" the anchor must be crossed at;
                                       # the mission clock is solved backwards from it
    timing_hold_min: int = 0           # minutes held at WP1 before pushing (0-15)
    timing_coach: bool = False         # grade wheels-up / WP1 / IP / TARGET in-mission
    timing_package: bool = False       # an AI flight flies the same route on LOCKED
                                       # ETAs ahead of you (the package to fit behind)
    check_ride: bool = False           # the coach goes SILENT and the card grades
                                       # U/F/G/E per item, Q/Q-/U overall (checkride.py
                                       # framework). Honored by the timing coach; the
                                       # formation check is its own profile.

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

    # What KIND of sortie this is. The Builder asks for it second, right after
    # era and map, because it is the decision every later screen hangs off:
    # picking one stamps sensible defaults onto the building blocks below, so
    # the rest of the wizard confirms a mission instead of assembling one.
    # Purely declarative — the engine reads it for the brief and the review
    # card; the bb_* flags it stamped remain the single source of truth for
    # what actually gets built, so a hand-edited recipe still wins.
    # "open" is the default, so every pre-v1.45 share link decodes unchanged.
    mission_kind: str = "open"         # see RECIPE_ENUMS["mission_kind"]

    # template packs
    template: Optional[str] = None     # None | backseat_izlid | backseat_intercept | rio_fleet_defense
    crew_difficulty: str = "qualified" # trainee (hints) | qualified (clean)

    # The comm table (missiongen/commplan.py): {plan row: MHz} overrides on
    # the standard ladder — {"tanker": 271.5} moves Texaco and everything that
    # prints or programs Texaco follows. None/{} = the standard ladder, byte
    # for byte, so every existing share link is untouched. Guard is refused.
    comms: Optional[dict] = None
    callsign: Optional[str] = None     # flight radio callsign ("Gypsy" -> the
                                       # flight is "Gypsy 1"). None = authentic
                                       # default per airframe (callsigns.json:
                                       # VF-32 Gypsy, Jolly Rogers Victory,
                                       # Misty for the Hun...). User-editable.

    seed: int = 1

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict, validate: bool = True) -> "Recipe":
        # A template's own `recipe` block is applied HERE, as defaults, before
        # anything else looks at the fields.
        #
        # It used to be merged only in the browser (qfRecipe()), which meant
        # POST /api/generate with {"template": "qf_bfm"} produced a RAMP START
        # — the air start that defines the card silently did not happen. Any
        # caller that is not our own frontend (an API user, a hand-built share
        # link, a future client) got a different mission from the one the UI
        # promises for the same template. The merge belongs on the server; the
        # frontend merging it too is harmless because explicit values win.
        d = cls._with_template_defaults(d)
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

    @staticmethod
    def _with_template_defaults(d: dict) -> dict:
        """Template `recipe` block as DEFAULTS under the caller's own values.

        Explicit wins, always: a recipe that says `start: "warm"` keeps it even
        if the template prefers an air start, because the user (or a share
        link) asked for that specifically. Only keys the caller did not supply
        are filled in. An unknown template is left alone — from_dict's unknown-
        field check and the builder's era gate report that properly.
        """
        tpl = d.get("template")
        if not tpl:
            return d
        try:
            from .resolver import load_json
            block = (load_json("mission_templates").get(tpl) or {}).get("recipe")
        except Exception:
            block = None
        if not isinstance(block, dict) or not block:
            return d
        merged = dict(block)
        merged.update({k: v for k, v in d.items()})
        return merged

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
                    f"{', '.join(repr(a) if a is None else str(a) for a in allowed)}.")
        # map/era are keys into the data packs. Validate here with a clear
        # message; otherwise a bad key KeyErrors deep in the builder, which
        # (now that KeyError is no longer treated as a user error) would surface
        # as an opaque 500 instead of "unknown theater".
        from .resolver import load_json
        if self.map not in load_json("maps"):
            raise RecipeError(f"map={self.map!r} is not a known theater.")
        if self.era not in load_json("eras"):
            raise RecipeError(f"era={self.era!r} is not a known era.")
        if self.lineup:
            ups = (load_json("maps")[self.map].get("lineups") or {})
            if self.lineup not in ups:
                raise RecipeError(
                    f"lineup={self.lineup!r} is not an order of battle on "
                    f"{self.map!r}. Known: {', '.join(sorted(ups)) or '(none)'}.")
            eras = ups[self.lineup].get("eras")
            # A lineup is a DATED order of battle. Proud Phantom is June 1980;
            # asking for it in a modern mission is not a preference, it is a
            # question with no answer, and answering it silently is how the
            # 1973 preset came to serve a 1980 exercise.
            if eras and self.era not in eras:
                raise RecipeError(
                    f"lineup={self.lineup!r} is a {'/'.join(eras)} order of "
                    f"battle; era={self.era!r} was asked for.")
        if self.cq_ride:
            from . import cq as _cq
            if not _cq.is_cq_ride(self.cq_ride):
                raise RecipeError(
                    f"cq_ride={self.cq_ride!r} is not a Case III ride. "
                    f"Known: {', '.join(_cq.RIDE_ORDER)}.")
            # A Case III recovery without a boat is not a degraded mission, it
            # is a contradiction: every fix in it is a radial and a DME from a
            # ship. Refuse rather than generate a recovery to nothing.
            if self.home_airbase != "CARRIER":
                raise RecipeError(
                    f"cq_ride={self.cq_ride!r} requires home_airbase='CARRIER' "
                    f"— every fix in a Case III is a bearing and range from "
                    f"the ship.")
            if not _cq.cockpit_for(self.aircraft):
                raise RecipeError(
                    f"cq_ride={self.cq_ride!r} has no cockpit procedure for "
                    f"aircraft={self.aircraft!r}. The syllabus is written for "
                    f"the F-14 and the F/A-18C, whose ICLS and ACLS setups it "
                    f"teaches by name.")
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise RecipeError(f"seed must be an integer, got {self.seed!r}.")
        if not (1 <= self.slots <= 4):
            raise RecipeError(f"slots must be 1-4, got {self.slots!r}.")
        if self.dress_fill is not None and not (0 <= self.dress_fill <= 100):
            raise RecipeError(f"dress_fill must be 0-100, got {self.dress_fill!r}.")
        from .pattern import MAX_COUNT as _PATTERN_MAX
        if not (1 <= self.pattern_count <= _PATTERN_MAX):
            raise RecipeError(
                f"pattern_count must be 1-{_PATTERN_MAX}, got {self.pattern_count!r}.")
        if not (1 <= self.threat_intensity <= 5):
            raise RecipeError(
                f"threat_intensity must be 1-5, got {self.threat_intensity!r}.")
        if self.target_packages is not None:
            from .targets import TARGET_PACKAGES
            bad = [p for p in self.target_packages if p not in TARGET_PACKAGES]
            if bad:
                raise RecipeError(
                    f"target_packages contains unknown package(s): "
                    f"{', '.join(bad)}. Known: {', '.join(TARGET_PACKAGES)}.")
            if not (1 <= len(self.target_packages) <= 3):
                raise RecipeError("target_packages must list 1-3 packages.")
        if self.timing_at is not None:
            from . import timing as _tm
            if _tm.parse_hhmm(self.timing_at) is None:
                raise RecipeError(
                    f"timing_at={self.timing_at!r} is not a clock time; expected "
                    f"HH:MM or HH:MM:SS.")
            if self.timing_anchor == "takeoff":
                raise RecipeError(
                    "timing_at needs timing_anchor='push' or 'tot' — with a "
                    "takeoff anchor the clock is the mission start, not a time "
                    "you pick.")
        if not (0 <= int(self.timing_hold_min or 0) <= 15):
            raise RecipeError(
                f"timing_hold_min must be 0-15, got {self.timing_hold_min!r}.")
        if self.callsign is not None:
            cs = str(self.callsign).strip()
            if not (1 <= len(cs) <= 20):
                raise RecipeError("callsign must be 1-20 characters.")
            self.callsign = cs
        if self.comms is not None:
            # Refuse a bad comm table BEFORE the engine runs, with the row
            # named — and keep only real changes, so a table full of defaults
            # is the same recipe as no table (share links stay canonical).
            from . import commplan as _cp
            v = _cp.validate(self.comms, _cp.unit_type_for(self.aircraft))
            if v["errors"]:
                raise RecipeError("comms: " + " ".join(e["msg"] for e in v["errors"]))
            self.comms = v["clean"] or None
        return self
