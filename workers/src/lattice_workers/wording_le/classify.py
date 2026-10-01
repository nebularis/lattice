"""Keyword classification, used when no sentence form matches (plan WA6 section "Keyword rules")."""

from __future__ import annotations

from typing import Optional

from .tokens import Token

_PHRASE_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("shall", "be", "deemed"), "Deeming"),
    (("is", "deemed"), "Deeming"),
    (("are", "deemed"), "Deeming"),
    (("does", "not", "cover"), "Exclusion"),
    (("is", "not", "liable"), "Exclusion"),
    (("are", "not", "liable"), "Exclusion"),
    (("excluded",), "Exclusion"),
    (("shall", "not"), "Prohibition"),
    (("must", "not"), "Prohibition"),
    (("may", "not"), "Prohibition"),
    (("may", "terminate"), "Power"),
    (("may", "declare"), "Power"),
    (("shall",), "Obligation"),
    (("must",), "Obligation"),
    (("may",), "Permission"),
)


def keyword_class(tokens: list[Token], element_kind: str) -> Optional[str]:
    norms = [token.norm for token in tokens if token.kind == "word"]

    if element_kind == "definition" and ("means" in norms or "includes" in norms):
        return "Definition"

    for phrase, relation_class in _PHRASE_RULES:
        if _contains_phrase(norms, phrase):
            return relation_class

    return None


def _contains_phrase(norms: list[str], phrase: tuple[str, ...]) -> bool:
    n = len(phrase)
    return any(tuple(norms[i : i + n]) == phrase for i in range(len(norms) - n + 1))
