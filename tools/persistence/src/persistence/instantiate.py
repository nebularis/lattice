# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The ``instantiate`` stage (sketch §5.2, §5.3): reads a ``dal:CompiledProfile``
graph and the checked-in template library, and mixes each
``dal:GeneratedOperation``'s parameter bindings into its named template to
produce generic, portable SPARQL text. Entirely optional, and still needs
no live backend (ADR-A79 point 1).

A ``dal:ParameterBinding``'s ``dal:paramValue`` already holds fully-encoded
SPARQL term text (an ``Iri``, ``Literal``, ``Integer``, or ``Var`` produced
by :mod:`persistence.terms` during ``compile``), never a raw, unencoded
value: this stage re-wraps it as a trusted :class:`~persistence.terms.SparqlTerm`
rather than re-running an encoder, because it was already encoded once, by
this same compiler, and encoding it twice would corrupt it (double-quoting,
double-escaping). The only new encoding this stage ever performs is the
injection corpus's own adversarial-input tests (see ``tests/test_injection.py``),
never real compiled-profile data.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import RDF, Graph, URIRef

from .namespaces import DAL
from .render import load_template, render
from .terms import SparqlTerm


def instantiate_profile(compiled_profile: Graph, template_dir: Path | None = None) -> dict[str, str]:
    """Returns ``{operation_name: rendered_sparql_text}`` for every
    ``dal:GeneratedOperation`` in ``compiled_profile``."""
    out: dict[str, str] = {}
    for op_node in compiled_profile.subjects(RDF.type, DAL.GeneratedOperation):
        operation_name = str(compiled_profile.value(op_node, DAL.forOperation))
        template_node = compiled_profile.value(op_node, DAL.usesTemplate)
        template_path = str(compiled_profile.value(template_node, DAL.templatePath))

        context: dict[str, SparqlTerm] = {}
        for binding_node in compiled_profile.objects(op_node, DAL.hasParameterBinding):
            name = str(compiled_profile.value(binding_node, DAL.paramName))
            raw_value = str(compiled_profile.value(binding_node, DAL.paramValue))
            param_type = str(compiled_profile.value(binding_node, DAL.paramType))
            if param_type == "Integer":
                context[name] = int(raw_value)  # type: ignore[assignment]
            else:
                # already fully-encoded SPARQL term text (Iri/Literal/Var),
                # re-wrapped, never re-encoded (see module docstring)
                context[name] = SparqlTerm(raw_value)

        template_text = load_template(template_path, template_dir)
        out[operation_name] = render(template_text, context)
    return out


def instantiate_to_directory(compiled_profile: Graph, out_dir: Path, template_dir: Path | None = None) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for operation_name, text in instantiate_profile(compiled_profile, template_dir).items():
        safe_name = operation_name.replace(":", "_").replace("/", "_")
        path = out_dir / f"{safe_name}.rq"
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


__all__ = ["instantiate_profile", "instantiate_to_directory"]
