"""The pack format, against `docs/PACK_FORMAT.md`.

THE SPEC SAYS THE COMPATIBILITY RULES ARE "TESTED, NOT MERELY STATED". This is
where that is made true. The format is PUBLIC — a `.sspack` may arrive from
somebody who has never seen this repository — so the promises in §3 are
promises to strangers, and a promise nobody checks is a lie with good manners.

Section references match the specification. When one of these fails, read the
spec first: the document is normative and the code is the implementation.
"""
import io
import json
import zipfile

import pytest

from missiongen import packfmt as F

MIZ = b"PK\x05\x06" + b"\0" * 18          # an empty but structurally valid zip


def zipit(d: dict, wrap: str = "") -> bytes:
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for k, v in d.items():
            z.writestr(f"{wrap}/{k}" if wrap else k,
                       v if isinstance(v, bytes) else json.dumps(v))
    return b.getvalue()


# --------------------------------------------------------------------------- #
# §1.1 — what a reader must refuse before extracting
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("evil", [
    "../../etc/passwd",
    "/etc/passwd",
    "a/../../b.miz",
    "C:/windows/system32/x.miz",
])
def test_a_hostile_path_is_dropped_not_cleaned_up(evil):
    """A path with `..` in it is not a typo to be sanitised, it is an archive
    trying to write outside its own directory."""
    files = F.read_archive(zipit({evil: MIZ, "ok.miz": MIZ}))
    assert list(files) == ["ok.miz"], list(files)


def test_a_symlink_member_is_dropped():
    """A symlink whose target is /etc/passwd is the whole reason §1.1 lists
    non-regular entries."""
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("ok.miz", MIZ)
        info = zipfile.ZipInfo("link")
        info.external_attr = (0o120777 << 16)
        z.writestr(info, "/etc/passwd")
    assert list(F.read_archive(b.getvalue())) == ["ok.miz"]


def test_mac_resource_forks_are_ignored():
    files = F.read_archive(zipit(
        {"a.miz": MIZ, "__MACOSX/._a.miz": b"junk", "._b.miz": b"junk"}))
    assert list(files) == ["a.miz"], list(files)


def test_a_single_wrapper_directory_is_stripped():
    """Renaming a pack, or zipping the folder rather than its contents, must
    not change how it reads."""
    assert sorted(F.read_archive(zipit({"a.miz": MIZ, "pack.json": {"id": "x"}},
                                       wrap="my-pack"))) == ["a.miz",
                                                             "pack.json"]


def test_a_file_that_is_not_a_zip_says_so_in_words():
    with pytest.raises(F.PackError) as e:
        F.read_archive(b"this is not a zip")
    assert "readable" in str(e.value).lower()


# --------------------------------------------------------------------------- #
# §3 — the compatibility promises
# --------------------------------------------------------------------------- #
def test_an_unknown_field_survives_a_round_trip():
    """§3 rule 1. A pack that passes through an older reader must not lose a
    newer reader's data — otherwise every reader in the world is a lossy
    filter and nobody can extend the format."""
    raw = {"id": "x", "format": 2, "label": "X",
           "x_vendor": {"deep": ["structure", 1, True]},
           "some_field_from_2027": "keep me"}
    man = F.normalize(raw, "x", {"a.miz": MIZ})
    assert man["x_vendor"] == {"deep": ["structure", 1, True]}
    assert man["some_field_from_2027"] == "keep me"


def test_a_future_format_fails_with_a_sentence_not_a_stack_trace():
    """§3 rule 2. The person holding the file needs to know what to do about
    it, and "KeyError: 'syllabus'" does not tell them."""
    with pytest.raises(F.PackError) as e:
        F.upgrade({"id": "x", "format": F.FORMAT + 1})
    msg = str(e.value)
    assert str(F.FORMAT + 1) in msg, msg
    assert "newer Sortie Starter" in msg, msg
    assert str(F.FORMAT) in msg, msg


def test_only_three_fields_are_ever_required():
    """§2.1 + §3 rule 4. A future version may add fields; it may not make an
    existing optional field required. The guard is that a manifest of exactly
    the required three still produces a usable pack."""
    man = F.normalize({"format": 2, "id": "x", "label": "X"}, "x",
                      {"a.miz": MIZ})
    assert man["syllabus"] and man["files"] and man["digest"]
    assert man["library"]["role"] == "training"


def test_an_unknown_role_degrades_and_does_not_reject():
    """§2.5. A role this version has never heard of is a card that renders in
    the wrong tab, not a pack somebody cannot install."""
    man = F.normalize({"id": "x", "library": {"role": "spaceflight"}}, "x",
                      {"a.miz": MIZ})
    assert man["library"]["role"] == "training"


# --------------------------------------------------------------------------- #
# §5 — derivation, the property that keeps the format usable
# --------------------------------------------------------------------------- #
def test_a_bare_folder_of_missions_becomes_a_working_pack():
    """THE PROPERTY WORTH PROTECTING ABOVE ALL OTHERS. Somebody who has never
    read the specification drops a folder in and it works. The day that stops
    being true the format has become a barrier instead of a container."""
    man = F.normalize(None, "awi", {
        "AWI_01.miz": MIZ, "AWI_02.miz": MIZ,
        "Brief_01.pdf": b"%PDF", "Brief_02.pdf": b"%PDF",
        "AWI Guide.pdf": b"%PDF", "card.png": b"\x89PNG"})
    assert man["derived"] is True
    assert [e["n"] for e in man["syllabus"]] == [1, 2]
    assert man["syllabus"][0]["files"]["brief"] == "Brief_01.pdf"
    assert man["docs"]["guide"] == "AWI Guide.pdf"
    assert man["library"]["image"] == "card.png"


def test_a_brief_is_paired_by_its_number_even_at_the_end_of_the_name():
    """`Brief_01` has no trailing non-digit, so a `\\D` anchor can never match
    it. Lookarounds, and a regression guard because this was a real bug."""
    man = F.normalize(None, "x", {"M_07.miz": MIZ, "Brief_07.pdf": b"%PDF"})
    assert man["syllabus"][0]["files"]["brief"] == "Brief_07.pdf"


def test_derivation_never_overwrites_the_author():
    """§5. Derivation fills gaps; the author always wins."""
    man = F.normalize({"id": "x", "label": "Author's Title",
                       "library": {"premise": "mine", "threat": 5}},
                      "x", {"a.miz": MIZ})
    assert man["label"] == "Author's Title"
    assert man["library"]["premise"] == "mine"
    assert man["library"]["threat"] == 5
    assert man["derived"] is False


def test_an_entry_pointing_at_a_missing_mission_is_dropped_not_served():
    """§2.6. Serving a card whose Download button 404s is worse than not
    showing the card."""
    man = F.normalize({"id": "x", "syllabus": [
        {"n": 1, "files": {"mission": "here.miz"}},
        {"n": 2, "files": {"mission": "gone.miz"}}]}, "x", {"here.miz": MIZ})
    assert [e["files"]["mission"] for e in man["syllabus"]] == ["here.miz"]


# --------------------------------------------------------------------------- #
# §2.8 — integrity
# --------------------------------------------------------------------------- #
def test_the_digest_does_not_depend_on_how_the_zip_was_made():
    """§2.8. A digest that changed when you re-zipped an unchanged folder is a
    digest nobody can use — not for signing, not for caching, not for saying
    'this is the same pack'."""
    files = {"b.miz": MIZ, "a.miz": b"different", "z/c.pdf": b"%PDF"}
    d1 = F.digest_of(F.file_list(files))
    d2 = F.digest_of(F.file_list(dict(reversed(list(files.items())))))
    assert d1 == d2
    # ...and it DOES change when the content does, or it is not a digest
    files["a.miz"] = b"changed"
    assert F.digest_of(F.file_list(files)) != d1


def test_a_wrong_checksum_is_refused():
    """§6 rule 3. Serving a .miz that DCS silently fails to open is the worst
    outcome available to this system."""
    with pytest.raises(F.PackError) as e:
        F.verify({"files": [{"path": "a.miz", "sha256": "0" * 64}]},
                 {"a.miz": MIZ})
    assert "corrupt" in str(e.value).lower()


def test_a_listed_file_that_is_not_there_is_refused():
    with pytest.raises(F.PackError) as e:
        F.verify({"files": [{"path": "gone.miz", "sha256": "0" * 64}]},
                 {"a.miz": MIZ})
    assert "incomplete" in str(e.value).lower()


def test_a_tampered_digest_is_refused():
    fl = F.file_list({"a.miz": MIZ})
    with pytest.raises(F.PackError) as e:
        F.verify({"files": fl, "digest": "sha256:" + "0" * 64}, {"a.miz": MIZ})
    assert "modified" in str(e.value).lower()


def test_a_file_not_listed_in_the_manifest_is_still_allowed():
    """§2.8. Additive manifests must not be made impossible by strict readers
    — an author who lists only his missions has not made a broken pack."""
    fl = F.file_list({"a.miz": MIZ})
    F.verify({"files": fl}, {"a.miz": MIZ, "extra.txt": b"hello"})


def test_the_stored_manifest_always_describes_what_is_actually_there():
    """An author's stale hash list is verified and then REPLACED, so a pack
    can never be stored describing files it does not have."""
    man = F.normalize({"id": "x"}, "x", {"a.miz": MIZ, "b.pdf": b"%PDF"})
    assert {e["path"] for e in man["files"]} == {"a.miz", "b.pdf"}
    assert man["digest"] == F.digest_of(man["files"])


# --------------------------------------------------------------------------- #
# §2.9 — signatures
# --------------------------------------------------------------------------- #
def test_no_signature_means_unsigned_and_installs_fine():
    F.verify({"files": F.file_list({"a.miz": MIZ})}, {"a.miz": MIZ})


def test_a_malformed_signature_is_a_hard_failure():
    """§2.9. A reader that shrugs at a field it does not understand is exactly
    how a signature becomes decorative."""
    with pytest.raises(F.PackError):
        F.verify({"signature": {"alg": "ed25519"}}, {"a.miz": MIZ})
    with pytest.raises(F.PackError) as e:
        F.verify({"signature": {"alg": "moon-runes", "sig": "x"}},
                 {"a.miz": MIZ})
    assert "cannot check" in str(e.value)


# --------------------------------------------------------------------------- #
# §4 — reading format 1
# --------------------------------------------------------------------------- #
def test_a_format_1_manifest_installs_unchanged():
    """The AWI pack is live on the server right now. It must not need a
    re-upload to survive this change."""
    v1 = {"id": "awi_basics", "label": "AWI Basics", "role": "a2a",
          "threat": 4, "players": "SP", "module": "F-14B(U)",
          "maps": ["nevada"], "eras": ["modern"], "premise": "…",
          "docs": {"guide": "g.pdf"},
          "events": [{"n": 1, "label": "One", "miz": "a.miz",
                      "brief_pdf": "b.pdf"}]}
    man = F.normalize(v1, "awi_basics", {"a.miz": MIZ, "b.pdf": b"%PDF",
                                         "g.pdf": b"%PDF"})
    assert man["format"] == 2
    assert man["syllabus"][0]["files"] == {"mission": "a.miz",
                                           "brief": "b.pdf"}
    assert man["library"]["role"] == "a2a" and man["library"]["threat"] == 4
    # the display-string `module` is PROMOTED, not dropped: this is the field
    # that tells a pilot he cannot fly the pack before he downloads it
    assert man["requires"]["modules"] == ["F-14B(U)"]
    assert man["requires"]["terrains"] == ["nevada"]


def test_both_spellings_are_accepted_in_one_manifest():
    """§4. A hand-edited hybrid is what a real migration looks like."""
    man = F.normalize({"id": "x", "role": "strike",
                       "events": [{"n": 1, "miz": "a.miz"}]},
                      "x", {"a.miz": MIZ})
    assert man["library"]["role"] == "strike"
    assert man["syllabus"][0]["files"]["mission"] == "a.miz"


# --------------------------------------------------------------------------- #
# §6 — and nothing else is refused
# --------------------------------------------------------------------------- #
def test_an_archive_with_nothing_to_publish_is_refused():
    with pytest.raises(F.PackError) as e:
        F.normalize(None, "x", {"notes.rtf": b"hello"})
    assert "nothing to publish" in str(e.value)


def test_an_odd_but_harmless_pack_installs():
    """§6's closing line. Odd is not invalid: no manifest, no artwork, paths
    that follow no convention — it installs."""
    man = F.normalize(None, "x", {"weird name!.miz": MIZ})
    assert len(man["syllabus"]) == 1
    assert man["library"]["image"] is None


# --------------------------------------------------------------------------- #
# the one-direction rule
# --------------------------------------------------------------------------- #
def test_the_card_view_is_derived_and_never_round_trips():
    """Two shapes on disk is the twin-source problem that has already cost
    this codebase two live defects. The projection must be one-directional:
    normalising a card view back must not produce a second stored shape."""
    man = F.normalize({"id": "x", "library": {"role": "sead", "threat": 2}},
                      "x", {"a.miz": MIZ})
    card = F.card_view(man)
    assert card["role"] == "sead" and card["events"][0]["miz"] == "a.miz"
    # the card view carries the flat keys, the STORED manifest does not gain
    # them — normalize is the only thing that writes, and it writes format 2
    assert "role" not in man and "events" not in man
    again = F.normalize(man, "x", {"a.miz": MIZ})
    assert again["library"]["role"] == "sead"
    assert "role" not in again and "events" not in again
