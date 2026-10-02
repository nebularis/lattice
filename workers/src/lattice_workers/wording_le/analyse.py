"""Builds the Analysis shape, without `graphView` (plan WA6 section "Element analysis fields")."""

from __future__ import annotations

import re
from typing import Any

from .classify import keyword_class
from .forms import FormProfile
from .matcher import Match, best_match
from .model import Element, Wording
from .render import le_program
from .tokens import Token, tokenise

_MODALS = {"shall", "must", "may", "not"}
_CONNECTIVES = {"if", "unless", "provided", "save", "subject", "where", "when"}


def analyse_wording(wording: Wording, profile: FormProfile) -> dict[str, Any]:
    variable_types = {variable.key: variable.value_type for variable in wording.variables}
    elements = [_analyse_element(element, profile, variable_types) for element in wording.elements]
    return {
        "formsProfile": {"profileId": profile.profile_id, "version": profile.version},
        "elements": elements,
        "leProgram": le_program(wording, elements, profile),
    }


def _analyse_element(element: Element, profile: FormProfile, variable_types: dict[str, str]) -> dict[str, Any]:
    tokens = tokenise(element)
    base = {
        "elementId": element.element_id,
        "objectId": element.object_id,
        "sectionKey": element.section_key,
        "kind": element.kind,
        "text": element.text,
    }

    if not tokens:
        return {**base, "relationClass": None, "basis": "none", "formId": None, "leTemplate": None,
                "leSentence": None, "spans": []}

    match = best_match(tokens, profile, element, variable_types)
    if match is not None:
        relation_class = match.form.relation_class
        basis = "form"
        form_id: Any = match.form.form_id
        le_template: Any = match.form.template + "."
    else:
        relation_class = keyword_class(tokens, element.kind)
        basis = "keyword" if relation_class is not None else "none"
        form_id = None
        le_template = None

    le_sentence = _le_sentence(element.text) if basis != "none" else None
    spans = _spans(tokens, match, profile.ignorable)

    return {
        **base,
        "relationClass": relation_class,
        "basis": basis,
        "formId": form_id,
        "leTemplate": le_template,
        "leSentence": le_sentence,
        "spans": spans,
    }


def _le_sentence(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if not collapsed.endswith("."):
        collapsed += "."
    return collapsed


def _spans(tokens: list[Token], match: "Match | None", ignorable: tuple[str, ...]) -> list[dict[str, Any]]:
    fixed_tokens = set(match.fixed_tokens) if match is not None else set()
    text_slot_tokens: set[Token] = set()
    if match is not None:
        for slot, slot_tokens in match.slots.values():
            if slot.type in ("text", "term"):
                text_slot_tokens.update(slot_tokens)

    roles: list[str] = []
    for token in tokens:
        if token.kind == "variable":
            role = "slot-variable"
        elif token.kind == "constant":
            role = "slot-constant"
        elif token.norm in ignorable:
            role = "ignorable"
        elif token in fixed_tokens:
            role = "fixed"
        elif token in text_slot_tokens:
            role = "slot-text"
        else:
            role = "unmatched"

        if role in ("fixed", "unmatched") and token.kind == "word":
            if token.norm in _MODALS:
                role = "modal"
            elif token.norm in _CONNECTIVES:
                role = "connective"
        roles.append(role)

    return _merge_spans(tokens, roles)


def _merge_spans(tokens: list[Token], roles: list[str]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    index = 0
    while index < len(tokens):
        role = roles[index]
        part_index = tokens[index].part_index
        start = tokens[index].start
        end = tokens[index].end
        next_index = index + 1
        while (
            next_index < len(tokens)
            and roles[next_index] == role
            and tokens[next_index].part_index == part_index
        ):
            end = tokens[next_index].end
            next_index += 1
        spans.append({"start": start, "end": end, "role": role, "partIndex": part_index})
        index = next_index
    return spans
