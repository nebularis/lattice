# SPDX-License-Identifier: MPL-2.0
"""The translation table, MTP's data/translations.yaml: words a source vocabulary uses for legal relations and the parts
of a contract, and the LATTICE terms each may mean, with when each reading holds. It is a card in the teaching pack, and
gives the candidate ranking aliases, so a source term called "Right" finds ins:Permission and ins:Power, which share no
word with it."""

from __future__ import annotations

import functools

import yaml


@functools.lru_cache(maxsize=1)
def table() -> tuple:
    from .server import _mtp

    return tuple(yaml.safe_load((_mtp() / "data" / "translations.yaml").read_text(encoding="utf-8")))


def card() -> str:
    """One line for each reading of each word."""
    lines = ["# What LATTICE says for a source's legal words (Instrument README §4.4 to §4.6)", "# word, and other words for it | LATTICE term | when"]
    for entry in table():
        words = ", ".join([entry["word"], *entry.get("also", [])])
        lines += [f"{words} | {m['term']} | {m['when']}" for m in entry["means"]]
    return "\n".join(lines) + "\n"


def aliases() -> dict[str, list[str]]:
    """The words under which each term is indexed, by its CURIE."""
    out: dict[str, list[str]] = {}
    for entry in table():
        for m in entry["means"]:
            out.setdefault(m["term"], []).extend([entry["word"], *entry.get("also", [])])
    return out
