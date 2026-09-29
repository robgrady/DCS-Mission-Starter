"""A brief may only promise what the mission contains.

We already have a rule that a number in a briefing card must be measured or
cited, because a confidently wrong number is worse than no number. This is its
sibling, and it came out of building all 41 Library cards and reading them
against their own briefs.

Four cards were describing missions the file did not contain. `bc_cas1` told the
pilot **"THE 9-LINE IS THE SORTIE. Read it back."** — with no controller in the
mission to read it back to. `af_tic_cas` and `f100_fulda_cas` briefed terminal
control that was not there. `f100_victor_alert` mentioned a tanker and an AWACS
it did not have.

That is the same failure as an invented number, wearing different clothes: the
pilot believes the brief, flies looking for something that was never generated,
and concludes the tool is broken. It is also invisible to every other test we
have, because the mission builds perfectly — it just is not the mission the
brief describes.

So: for every card, for every promise we can detect, the thing must be in the
file. The checks are deliberately narrow — a promise has to be unambiguous
before it is worth asserting on — and each one is anchored to a phrase a pilot
would actually act on.
"""
import re
import zipfile

import pytest

import dcs.lua as lua

from missiongen import Recipe, generate
from missiongen.resolver import load_json
from missiongen.templates import effective_recipe

TEMPLATES = load_json("mission_templates")
CARDS = sorted(k for k, v in TEMPLATES.items()
               if isinstance(v, dict) and not k.startswith("_"))


def _contents(path):
    with zipfile.ZipFile(path) as z:
        m = lua.loads(z.read("mission").decode("utf-8"))["mission"]
    c = dict(red_air=0, friendly_air=0, red_ground=0, moving=0, tanker=0,
             awacs=0, shootable=0, client_slots=0)
    for side in ("blue", "red"):
        for co in m["coalition"][side].get("country", {}).values():
            for kind in ("plane", "helicopter"):
                for g in co.get(kind, {}).get("group", {}).values():
                    nm = (g.get("name") or "").upper()
                    units = list(g["units"].values())
                    clients = sum(1 for u in units
                                  if u.get("skill") in ("Player", "Client"))
                    if clients:
                        c["client_slots"] += clients
                    elif side == "red":
                        c["red_air"] += 1
                    else:
                        c["friendly_air"] += 1
                    if any(t in nm for t in ("TEXACO", "SHELL", "ARCO", "TANKER")):
                        c["tanker"] += 1
                    if any(t in nm for t in ("OVERLORD", "AWACS", "MAGIC")):
                        c["awacs"] += 1
            for g in co.get("vehicle", {}).get("group", {}).values():
                if side == "red":
                    c["red_ground"] += len(g["units"])
                    c["shootable"] += len(g["units"])
                if len(list(g.get("route", {}).get("points", {}).values())) > 1:
                    c["moving"] += 1
            for g in co.get("static", {}).get("group", {}).values():
                nm = (g.get("name") or "").upper()
                # Range furniture is shootable even though it is friendly-side.
                if side == "red" or nm.startswith(("RNG", "TGT")):
                    c["shootable"] += 1
    return c


def _built(key):
    import tempfile
    v = TEMPLATES[key]
    era = (v.get("eras") or ["modern"])[0]
    rc = effective_recipe(key, era)
    rc.setdefault("map", v.get("default_map", "caucasus"))
    rc.update(era=era, template=key, seed=7)
    path = tempfile.mktemp(suffix=".miz")
    generate(Recipe.from_dict(rc), path)
    return _contents(path)


# (label, what the brief says, what must therefore be in the file, why, how the
#  card may DISCLAIM it)
#
# Each pattern is a phrase a pilot ACTS ON. "Support" in prose is not a promise;
# "Texaco is on station" is. Keep them narrow — a false positive here teaches
# people to weaken the test, which is how guards die.
#
# THE DISCLAIMER COLUMN IS THE IMPORTANT PART, and it exists because the first
# version of this file got it wrong in exactly the way it was written to
# prevent. It accused `f100_fulda_cas` of promising a JTAC — the brief says
# "No JTAC datalink in this era — talk-on off the F10 picture and your own
# eyes" — and `f100_victor_alert` of promising an AWACS, where the brief says
# "GCI only — no AWACS". Both were being scrupulously honest. The matcher saw
# the keyword and not the negation, which is the same mistake as flagging
# escaped HTML because the payload's characters are still present.
#
# So a card is allowed to NAME a thing in order to say it is absent. Naming the
# gap is better writing than silence, and the older cards in this Library were
# already doing it before the newer ones forgot.
PROMISES = [
    ("a controller", r"9-LINE|9-line|read it back to|JTAC will|FAC\(A\) will",
     lambda c: False,
     "the brief has the pilot talking to a terminal controller, and we cannot "
     "generate one",
     r"[Nn]o JTAC|no FAC|without a controller|we cannot generate a controller|"
     r"[Tt]his mission has\s*\**\s*neither|no controller"),
    ("something that moves", r"moving target|MOVING TARGET|convoy is moving|"
     r"catch them on the move",
     lambda c: c["moving"] > 0,
     "the brief promises a target that is under way",
     r"nothing in the target\s*\n?\s*area is under way|nothing is under way|"
     r"[Tt]his mission has\s*\**\s*neither|otherwise simulate"),
    ("an airborne opponent", r"\bbandit\b|\badversary\b|enemy CAP will|"
     r"MiGs are up",
     lambda c: c["red_air"] > 0,
     "the brief promises somebody to fight",
     r"no bandit|no enemy air|nothing will contest you"),
    ("a tanker on station", r"[Tt]anker is up|Texaco|tanker is on station|"
     r"[Rr]ecovery tanker",
     lambda c: c["tanker"] > 0, "the brief sends the pilot to a tanker",
     r"no tanker|tanker is not|without a tanker"),
    ("an AWACS", r"AWACS is up|Overlord|AWACS is on station",
     lambda c: c["awacs"] > 0, "the brief tells the pilot to use the picture",
     r"[Nn]o AWACS|GCI only|without AWACS"),
    ("something to shoot", r"deliveries|box pattern|put a bomb|strafe|"
     r"weapons employment",
     lambda c: c["shootable"] > 0, "the brief has the pilot employing weapons",
     r"nothing to shoot|no targets"),
    ("a second seat", r"two client seats|fly it with someone in the other seat",
     lambda c: c["client_slots"] > 1, "the brief offers a seat for a friend",
     r"single seat only"),
]


@pytest.mark.parametrize("key", CARDS)
def test_a_card_only_promises_what_it_builds(key):
    brief = "\n".join(TEMPLATES[key].get("brief") or [])
    if not brief:
        pytest.skip("no brief")
    def claimed(pat, dis):
        return re.search(pat, brief) and not re.search(dis, brief)

    if not any(claimed(pat, dis) for _n, pat, _p, _w, dis in PROMISES):
        return
    c = _built(key)
    broken = []
    for name, pat, pred, why, dis in PROMISES:
        if claimed(pat, dis) and not pred(c):
            broken.append(f"{name} — {why}")
    assert not broken, (
        f"{key}: the brief promises what the mission does not contain:\n  "
        + "\n  ".join(broken)
        + f"\n  mission has: {c}")


def test_a_card_that_briefs_an_empty_sky_gets_one():
    """`bc_tr1` is the first card of the B-Course track and it says 'nothing is
    trying to kill you'. Trust in a track is built on its first sortie, so an
    ambient red aircraft wandering the same sky is not a small thing."""
    quiet = [k for k in CARDS
             if re.search(r"[Nn]othing is trying to kill you|no threats|"
                          r"nobody shooting back",
                          "\n".join(TEMPLATES[k].get("brief") or []))]
    assert quiet, "no card claims an empty sky — has the wording changed?"
    for key in quiet:
        c = _built(key)
        assert c["red_air"] == 0, (
            f"{key} promises an empty sky and contains {c['red_air']} enemy "
            f"aircraft")


def test_no_card_sends_the_pilot_to_the_builder_mid_brief():
    """A Library card exists so somebody can fly without configuring anything.
    A brief that says 'now open this in the Builder and change a setting' is a
    card admitting it did not finish its job — and it arrives in the middle of
    a briefing, which is the worst possible moment to be handed a config task.

    Referring to the Builder as a NEXT step is fine; instructing the pilot to
    go change a value in order to fly the sortie as briefed is not."""
    offenders = []
    for key in CARDS:
        brief = "\n".join(TEMPLATES[key].get("brief") or [])
        if re.search(r"open (this|it) in the Builder and (change|set)|"
                     r"setting the BFM setup to|change the BFM setup to", brief):
            offenders.append(key)
    assert not offenders, (
        "these cards interrupt their own brief with a configuration task: "
        f"{offenders}")


def test_the_new_badge_still_means_something():
    """68 % of the Library was flagged `new` at the time of the August audit —
    a badge on two cards in three is decoration, not information. A returning
    pilot uses it to find what changed since they last flew.

    `new` means SHIPPED IN THIS RELEASE, not "recently" — "recently" is how it
    reached 68 %. A track that shipped two releases ago has had its moment and
    should clear. The threshold is a third: generous enough for a release that
    ships a whole set at once, tight enough that nobody can leave the flag on
    forever."""
    cards = [v for k, v in TEMPLATES.items()
             if isinstance(v, dict) and not k.startswith("_")]
    flagged = [v for v in cards if (v.get("library") or {}).get("new")]
    assert len(flagged) <= len(cards) / 3, (
        f"{len(flagged)} of {len(cards)} cards are flagged NEW — the badge has "
        f"stopped meaning 'changed recently' and started meaning 'exists'")


def test_every_card_declares_its_role():
    """A card with no role gets one synthesised by the frontend, which means the
    Library's own filters sort it somewhere nobody chose."""
    missing = [k for k, v in TEMPLATES.items()
               if isinstance(v, dict) and not k.startswith("_")
               and not (v.get("library") or {}).get("role")]
    assert not missing, f"cards with no library.role: {missing}"


def test_a_card_that_points_at_another_card_points_at_a_real_one():
    """The fixed BFM and AHC briefs stop sending the pilot to the Builder and
    send them to a sibling card instead. That is only an improvement if the
    sibling exists — a brief naming a card we never shipped is a worse dead end
    than the config task it replaced."""
    labels = {v.get("label", "") for v in TEMPLATES.values()
              if isinstance(v, dict)}
    missing = []
    for key, v in TEMPLATES.items():
        if not isinstance(v, dict):
            continue
        for line in v.get("brief") or []:
            for quoted in re.findall(r"'([^']{6,60})'", line):
                if quoted.startswith(("B-Course", "BFM-", "TR-", "SA-", "CAS-")):
                    if not any(quoted in lab for lab in labels):
                        missing.append(f"{key} -> {quoted!r}")
    assert not missing, f"briefs referring to cards that do not exist: {missing}"
