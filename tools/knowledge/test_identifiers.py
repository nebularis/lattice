# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Tests for the identifier table and the referential-integrity check."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import identifiers  # noqa: E402

DECISION = next(f for f in identifiers.FAMILIES if f.name == "decision")


def test_normalise_unifies_the_spellings_one_decision_is_written_in():
    """The clean-room decision was the file ADR-AC2 while it was written ADR-A-C2 in 125 places, and
    a heading wrote "ADR A-07" where prose writes ADR-A07. Each pair has to resolve to one key. The
    variants are written as escapes, so a rewrite of the corpus's spellings cannot flatten them."""
    assert identifiers.normalise("ADR-A-C2") == identifiers.normalise("ADR-AC2")
    assert identifiers.normalise("ADR\x20A-07") == identifiers.normalise("ADR-A07")
    # U+2011, the non-breaking hyphen, appears in four decisions' references.
    assert identifiers.normalise("ADR\u2011A82") == identifiers.normalise("ADR-A82")


def test_normalise_keeps_distinct_decisions_apart():
    assert identifiers.normalise("ADR-A07") != identifiers.normalise("ADR-A07b")
    assert identifiers.normalise("ADR-A-CAP1") != identifiers.normalise("ADR-AC1")
    assert identifiers.normalise("ADR-A1") != identifiers.normalise("ADR-A11")


def test_the_decision_pattern_matches_every_spelling_the_corpus_uses():
    for spelling in (
        "ADR-A01",
        "ADR-A131",
        "ADR-A07b",
        "ADR-AC2",
        "ADR-A-C2",
        "ADR-A-FM2",
        "ADR-A-CAP1",
        "ADR\x20A-07",
        "ADR\x20A127",
        "ADR\u2011A68",
    ):
        assert DECISION.mention.fullmatch(spelling), spelling


def test_the_decision_pattern_does_not_match_ordinary_prose():
    for text in ("ADR", "an ADR for", "ADRs", "ADR-", "PDD-01", "TD-34"):
        assert not DECISION.mention.fullmatch(text), text


def test_every_family_with_a_definition_rule_names_where_it_defines():
    for family in identifiers.FAMILIES:
        if family.resolvable:
            assert family.defines, family.name
            assert family.definition in {"filename", "table-row", "heading"}, family.name


def test_a_removable_family_is_never_failed():
    """A register entry is removed once a plan takes it on, so an unresolved mention there is a
    rehoming, not a break. Were that classified as unresolved the check would fail on normal work."""
    found = identifiers.mentions(identifiers.scannable(identifiers.tracked_markdown()))
    findings = identifiers.examine(found)
    removable = {f.name for f in identifiers.FAMILIES if f.removable}
    assert removable, "the registers are the reason this distinction exists"
    assert not [f.name for f, _ in findings.unresolved if f.name in removable]


def test_the_corpus_has_no_unresolved_identifier_outside_the_baseline():
    """The check itself, over the real tree. This fails when a decision a document cites stops
    existing, which is the rot the check is for."""
    found = identifiers.mentions(identifiers.scannable(identifiers.tracked_markdown()))
    findings = identifiers.examine(found)
    unresolved = [sorted(m.spellings)[0] for _, m in findings.unresolved]
    assert not unresolved, (
        f"mentioned but defined nowhere: {unresolved}. Define each, correct the mention, or add it "
        f"to tools/knowledge/identifier-exceptions.txt with a reason."
    )


def test_the_scan_skips_a_generated_copy_and_keeps_an_original():
    """A generated copy repeats its source's identifiers, so counting it would double every
    identifier the site publishes. A copy is recognised by the marker its generator writes, not by
    its directory: most files under docs/_includes are originals that live there."""
    tracked = identifiers.tracked_markdown()
    kept = set(identifiers.scannable(tracked))

    copies = [
        path
        for path in tracked
        if path.is_file()
        and identifiers.GENERATED_COPY.match(
            path.read_text(encoding="utf-8", errors="replace")[:200]
        )
    ]
    assert copies, "the site's generated copies are part of the tree"
    assert not [path for path in copies if path in kept]

    originals = [p for p in tracked if "_includes" in p.parts and p not in copies and p.is_file()]
    assert originals, "docs/_includes also holds originals, which must still be scanned"
    assert all(path in kept for path in originals)


def test_a_known_decision_resolves_to_its_canonical_filename_spelling():
    defined = identifiers.definitions(DECISION)
    assert defined[identifiers.normalise("ADR-A131")] == "ADR-A131"
    assert defined[identifiers.normalise("ADR-AC2")] == "ADR-A-C2"
