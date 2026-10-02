"""Matches an element's tokens against a sentence form (plan WA6 section "Matching rules")."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Mapping, Optional

from .forms import Fixed, Form, FormProfile, Slot
from .model import Element
from .tokens import Token, WORD_PATTERN, normalise


@dataclass(frozen=True)
class Match:
    form: Form
    slots: dict[str, tuple[Slot, tuple[Token, ...]]]
    fixed_tokens: tuple[Token, ...]


def match(
    tokens: list[Token],
    form: Form,
    ignorable: tuple[str, ...],
    element: Element,
    variable_types: Mapping[str, str],
) -> Optional[Match]:
    significant = [token for token in tokens if token.norm not in ignorable]
    for slots, fixed_tokens, position in _try_match(significant, 0, form.items, 0, {}, (), element, variable_types):
        if position == len(significant):
            return Match(form, slots, fixed_tokens)
    return None


def best_match(
    tokens: list[Token], profile: FormProfile, element: Element, variable_types: Mapping[str, str]
) -> Optional[Match]:
    candidates: list[Match] = []
    for form in profile.forms:
        found = match(tokens, form, profile.ignorable, element, variable_types)
        if found is not None:
            candidates.append(found)
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda candidate: (-len(candidate.fixed_tokens), profile.forms.index(candidate.form)),
    )


def _try_match(
    tokens: list[Token],
    position: int,
    items: tuple,
    item_index: int,
    slots: dict,
    fixed_tokens: tuple,
    element: Element,
    variable_types: Mapping[str, str],
) -> Iterator[tuple[dict, tuple, int]]:
    if item_index == len(items):
        yield slots, fixed_tokens, position
        return

    item = items[item_index]

    if isinstance(item, Fixed):
        count = len(item.words)
        if position + count > len(tokens):
            return
        window = tokens[position : position + count]
        if tuple(token.norm for token in window) != item.words:
            return
        yield from _try_match(
            tokens, position + count, items, item_index + 1, slots, fixed_tokens + tuple(window), element,
            variable_types,
        )
        return

    assert isinstance(item, Slot)

    if item.type == "party":
        if position >= len(tokens) or tokens[position].kind != "constant":
            return
        yield from _try_match(
            tokens, position + 1, items, item_index + 1, {**slots, item.name: (item, (tokens[position],))},
            fixed_tokens, element, variable_types,
        )
        return

    if item.type == "variable":
        if position >= len(tokens) or tokens[position].kind != "variable":
            return
        token = tokens[position]
        if item.value_types is not None:
            part = element.parts[token.part_index]
            declared = variable_types.get(part.variable_key)
            if declared not in item.value_types:
                return
        yield from _try_match(
            tokens, position + 1, items, item_index + 1, {**slots, item.name: (item, (token,))},
            fixed_tokens, element, variable_types,
        )
        return

    if item.type == "term":
        if element.kind != "definition" or not element.defined_term:
            return
        term_words = tuple(normalise(w) for w in WORD_PATTERN.findall(element.defined_term))
        count = len(term_words)
        if count == 0 or position + count > len(tokens):
            return
        window = tokens[position : position + count]
        if tuple(token.norm for token in window) != term_words:
            return
        yield from _try_match(
            tokens, position + count, items, item_index + 1, {**slots, item.name: (item, tuple(window))},
            fixed_tokens, element, variable_types,
        )
        return

    if item.type == "text":
        remaining = len(tokens) - position
        for count in range(1, remaining + 1):
            window = tuple(tokens[position : position + count])
            yield from _try_match(
                tokens, position + count, items, item_index + 1, {**slots, item.name: (item, window)},
                fixed_tokens, element, variable_types,
            )
        return

    raise ValueError(f"unknown slot type: {item.type}")
