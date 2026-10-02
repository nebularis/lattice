"""Tokenises an element's text, keeping its parts whole (plan WA6 section "Matching rules" 3)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import offsets
from .model import Element

WORD_PATTERN = re.compile(r"[\w\u2019'-]+|[,;:]")
_PUNCT = {",", ";", ":"}


@dataclass(frozen=True)
class Token:
    text: str
    norm: str
    start: int
    end: int
    part_index: int
    kind: str  # "word" | "punct" | "variable" | "constant"


def tokenise(element: Element) -> list[Token]:
    tokens: list[Token] = []
    base = 0
    for part in element.parts:
        text = part.text
        if part.kind == "variable":
            tokens.append(Token(text, normalise(text), base, base + offsets.utf16_len(text), part.index, "variable"))
        elif part.kind == "reference":
            tokens.append(Token(text, normalise(text), base, base + offsets.utf16_len(text), part.index, "constant"))
        else:
            for match in WORD_PATTERN.finditer(text):
                word = match.group(0)
                start = base + offsets.utf16_index(text, match.start())
                end = base + offsets.utf16_index(text, match.end())
                kind = "punct" if word in _PUNCT else "word"
                tokens.append(Token(word, normalise(word), start, end, part.index, kind))
        base += offsets.utf16_len(text)
    return tokens


def normalise(text: str) -> str:
    return text.lower().replace("\u2019", "'")
