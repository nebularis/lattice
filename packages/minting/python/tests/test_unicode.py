# SPDX-License-Identifier: MPL-2.0
"""The pinned Unicode 16.0.0 tables and pipeline steps
(identity-minting-specification.md §3), cross-checked over every code point
against CPython's own Unicode 16.0.0 data. The tables themselves are checked
against the UCD files by ``mise run check:minting-tables``."""

from __future__ import annotations

import unicodedata

import pytest

from conftest import MINTING, RECIPE_FILES, load
from lattice_minting import ucd

pytestmark = pytest.mark.skipif(unicodedata.unidata_version != ucd.VERSION,
                                reason="cross-checks need a Python whose Unicode data is exactly 16.0.0")

CODE_POINTS = range(0x110000)
PYTHON_TABLES = MINTING / "python" / "src" / "lattice_minting" / "ucd" / ucd.VERSION
JAVA_TABLES = MINTING / "java" / "src" / "main" / "resources" / "org" / "nebularis" / "lattice" / "minting" / "ucd" / ucd.VERSION


def _assigned_chars():
    return [chr(cp) for cp in CODE_POINTS if cp in ucd.ASSIGNED and unicodedata.category(chr(cp)) != "Cs"]


# The three pipelines of specification §3.2.
PIPELINES = {
    "NfkcTrimCasefold": ["reject_unassigned", "nfkc_casefold", "trim_white_space"],
    "NfkcTrimUppercase": ["reject_unassigned", "nfkc", "trim_white_space", "uppercase_full", "nfkc"],
    "NfkcTrimLowercase": ["reject_unassigned", "nfkc", "trim_white_space", "lowercase_full", "nfkc"],
}


def test_recipes_use_the_pipelines_of_the_specification():
    for path in RECIPE_FILES:
        r = load(path)
        for key in [r.get("key")] + [c["key"] for c in r.get("claims", [])]:
            if key:
                assert key["pipeline"]["steps"] == PIPELINES[key["pipeline"]["id"]], path.name


def _run(steps: list[str], s: str) -> str:
    for step in steps:
        s = ucd.STEPS[step](s)
    return s


def test_both_libraries_carry_identical_tables():
    names = sorted(p.name for p in PYTHON_TABLES.iterdir())
    assert names == sorted(p.name for p in JAVA_TABLES.iterdir())
    for name in names:
        assert (PYTHON_TABLES / name).read_bytes() == (JAVA_TABLES / name).read_bytes(), name


def test_assigned_matches_general_category():
    for cp in CODE_POINTS:
        assert (cp in ucd.ASSIGNED) == (unicodedata.category(chr(cp)) != "Cn"), f"U+{cp:04X}"


def test_full_case_mappings_match_python():
    for ch in _assigned_chars():
        assert ucd.uppercase_full(ch) == ch.upper(), f"U+{ord(ch):04X}"
        assert ucd.lowercase_full(ch) == ch.lower(), f"U+{ord(ch):04X}"


@pytest.mark.parametrize("text", ["ΟΔΟΣ", "ΟΔΟΣ ΟΔΟΣ", "Σ", "ΑΣ.", "Α'Σ", "ΑΣΑ", "Α\u0301Σ"])
def test_final_sigma_matches_python(text):
    assert ucd.lowercase_full(text) == text.lower()


def test_nfkc_casefold_agrees_with_the_casefold_composition():
    """Where NFKC_Casefold keeps a character, it equals NFKC applied around
    Python's full case folding. Where it removes one, the character is a
    default-ignorable code point, which that composition does not remove."""
    def composed(s):
        s = unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", unicodedata.normalize("NFD", s).casefold()).casefold())
        return unicodedata.normalize("NFKC", s)
    for ch in _assigned_chars():
        got = ucd.nfkc_casefold(ch)
        if got:
            assert got == composed(ch), f"U+{ord(ch):04X}"
        else:
            assert unicodedata.category(ch) in {"Cf", "Mn", "Lo", "Cc"}, f"U+{ord(ch):04X}"


def test_white_space_differs_from_isspace_only_at_the_information_separators():
    differ = [cp for cp in CODE_POINTS if (cp in ucd.WHITE_SPACE) != chr(cp).isspace()]
    assert differ == [0x1C, 0x1D, 0x1E, 0x1F]


def test_every_pipeline_is_idempotent():
    corpus = _assigned_chars()
    for pid, steps in PIPELINES.items():
        for ch in corpus:
            once = _run(steps, ch)
            assert _run(steps, once) == once, f"{pid} U+{ord(ch):04X}"
