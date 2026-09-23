# SPDX-License-Identifier: MPL-2.0
"""Unicode 16.0.0 behaviour from the pinned tables (identity-minting-
specification.md §3). Every step except NFC and NFKC reads the tables
generated from the Unicode Character Database, never Python's own case or
whitespace handling, so this library and the Java library agree byte for
byte. NFC and NFKC use ``unicodedata``, which is safe only on Unicode 16.0.0
or later data and only for assigned code points: see ``check_runtime`` and
``reject_unassigned``."""

from __future__ import annotations

import bisect
import unicodedata
from importlib.resources import files

from .errors import MintError

VERSION = "16.0.0"
_DATA = files(__package__) / "ucd" / VERSION


def _rows(name: str):
    for raw in (_DATA / name).read_text(encoding="utf-8").splitlines():
        if raw and not raw.startswith("#"):
            yield raw


def _span(field: str) -> tuple[int, int]:
    a, _, b = field.partition("..")
    return int(a, 16), int(b or a, 16)


class _Ranges:
    def __init__(self, name: str):
        spans = sorted(_span(r) for r in _rows(name))
        self._starts = [a for a, _ in spans]
        self._ends = [b for _, b in spans]

    def __contains__(self, cp: int) -> bool:
        i = bisect.bisect_right(self._starts, cp) - 1
        return i >= 0 and cp <= self._ends[i]


def _mapping(name: str) -> dict[int, str]:
    out: dict[int, str] = {}
    for row in _rows(name):
        src, _, dst = row.partition(";")
        target = "".join(chr(int(x, 16)) for x in dst.split())
        a, b = _span(src)
        for cp in range(a, b + 1):
            out[cp] = target
    return out


ASSIGNED = _Ranges("assigned.txt")
WHITE_SPACE = _Ranges("white_space.txt")
CASED = _Ranges("cased.txt")
CASE_IGNORABLE = _Ranges("case_ignorable.txt")
NFKC_CF = _mapping("nfkc_cf.txt")
UPPER = _mapping("upper.txt")
LOWER = _mapping("lower.txt")


def check_runtime() -> None:
    have = tuple(int(x) for x in unicodedata.unidata_version.split("."))
    need = tuple(int(x) for x in VERSION.split("."))
    if have < need:
        raise MintError("RuntimeUnicodeTooOld",
                        f"this Python has Unicode {unicodedata.unidata_version}; minting needs {VERSION} or later")


def reject_unassigned(s: str) -> str:
    for ch in s:
        if ord(ch) not in ASSIGNED:
            raise MintError("UnassignedCodePoint", f"U+{ord(ch):04X} is unassigned in Unicode {VERSION}")
    return s


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s)


def nfkc_casefold(s: str) -> str:
    """toNFKC_Casefold: map each code point through NFKC_CF, then NFC."""
    return nfc("".join(NFKC_CF.get(ord(ch), ch) for ch in s))


def trim_white_space(s: str) -> str:
    i, j = 0, len(s)
    while i < j and ord(s[i]) in WHITE_SPACE:
        i += 1
    while j > i and ord(s[j - 1]) in WHITE_SPACE:
        j -= 1
    return s[i:j]


def uppercase_full(s: str) -> str:
    return "".join(UPPER.get(ord(ch), ch) for ch in s)


def _final_sigma(s: str, i: int) -> bool:
    # Unicode §3.13 Final_Sigma: preceded by a cased letter (skipping
    # case-ignorable characters) and not followed by one.
    j = i - 1
    while j >= 0 and ord(s[j]) in CASE_IGNORABLE:
        j -= 1
    if j < 0 or ord(s[j]) not in CASED:
        return False
    j = i + 1
    while j < len(s) and ord(s[j]) in CASE_IGNORABLE:
        j += 1
    return j == len(s) or ord(s[j]) not in CASED


CAPITAL_SIGMA = chr(0x03A3)
FINAL_SIGMA = chr(0x03C2)


def lowercase_full(s: str) -> str:
    out = []
    for i, ch in enumerate(s):
        if ch == CAPITAL_SIGMA and _final_sigma(s, i):
            out.append(FINAL_SIGMA)
        else:
            out.append(LOWER.get(ord(ch), ch))
    return "".join(out)


STEPS = {
    "reject_unassigned": reject_unassigned,
    "nfc": nfc,
    "nfkc": nfkc,
    "nfkc_casefold": nfkc_casefold,
    "trim_white_space": trim_white_space,
    "uppercase_full": uppercase_full,
    "lowercase_full": lowercase_full,
}
