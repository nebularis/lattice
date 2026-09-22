# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The ``instantiate`` stage's template renderer (sketch §5.2, §5.3).

Mixes a :class:`~persistence.model.GeneratedOperation`'s parameter bindings
into its named Mustache template to produce generic, portable SPARQL text.
Needs no live backend and performs no backend-specific dialect rewriting
(that is Query Execution, explicitly deferred, ADR-A79 point 6).
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence, Union

import chevron

from .terms import SparqlTerm

ContextValue = Union[SparqlTerm, int, Sequence[SparqlTerm]]


def _template_dir_default() -> Path:
    return Path(__file__).resolve().parent / "templates"


def load_template(template_path: str, template_dir: Path | None = None) -> str:
    """Read a template file's raw Mustache text.

    ``template_path`` is the value of a ``dal:Template``'s ``dal:templatePath``,
    a path relative to the template library, never a literal query body
    (ADR-A79 point 2).
    """
    base = template_dir or _template_dir_default()
    path = (base / template_path).resolve()
    if base.resolve() not in path.parents and path != base.resolve():
        raise ValueError(f"template path {template_path!r} escapes the template directory")
    if not path.is_file():
        raise FileNotFoundError(f"no such template: {path}")
    return path.read_text(encoding="utf-8")


def render(template_text: str, context: Mapping[str, ContextValue]) -> str:
    """Render ``template_text`` against ``context``.

    Every value in ``context`` must already be a :class:`SparqlTerm` (or a
    plain ``int``, or a sequence of these). A bare ``str`` reaching this
    function is a programming error: the value skipped
    :mod:`persistence.terms`'s encoders, and this function refuses to guess
    what it should have been encoded as (ADR-A79 point 4).
    """
    for key, value in context.items():
        _check_value(key, value)
    return chevron.render(template_text, dict(context))


def _check_value(key: str, value: ContextValue) -> None:
    if isinstance(value, SparqlTerm):
        return
    if isinstance(value, bool):
        raise TypeError(f"context key {key!r} is a bool, not a supported SPARQL term type")
    if isinstance(value, int):
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _check_value(key, item)
        return
    if isinstance(value, str):
        raise TypeError(
            f"context key {key!r} reached the renderer as a bare str, not an "
            "encoded SparqlTerm (see persistence.terms)"
        )
    raise TypeError(f"context key {key!r} has unsupported type {type(value)!r}")


__all__ = ["render", "load_template"]
