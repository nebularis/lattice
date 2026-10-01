"""Loads the LE sentence-form profile (plan WA6 section "Sentence-form profile")."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Optional, Union


@dataclass(frozen=True)
class Fixed:
    words: tuple[str, ...]


@dataclass(frozen=True)
class Slot:
    name: str
    type: str  # "party" | "variable" | "text" | "term"
    value_types: Optional[tuple[str, ...]] = None


Item = Union[Fixed, Slot]


@dataclass(frozen=True)
class Form:
    form_id: str
    relation_class: str
    template: str
    items: tuple[Item, ...]


@dataclass(frozen=True)
class FormProfile:
    profile_id: str
    version: str
    ignorable: tuple[str, ...]
    forms: tuple[Form, ...]


def load_profile() -> FormProfile:
    raw = resources.files("lattice_workers.wording_le").joinpath("forms/sentence-forms.json").read_text(
        encoding="utf-8"
    )
    data = json.loads(raw)
    forms = tuple(_load_form(form) for form in data["forms"])
    return FormProfile(data["profileId"], data["version"], tuple(data["ignorable"]), forms)


def _load_form(data: dict) -> Form:
    items = tuple(_load_item(item) for item in data["items"])
    return Form(data["formId"], data["relationClass"], data["template"], items)


def _load_item(data: dict) -> Item:
    if data["kind"] == "fixed":
        return Fixed(tuple(data["words"]))
    value_types = tuple(data["valueTypes"]) if "valueTypes" in data else None
    return Slot(data["name"], data["type"], value_types)
