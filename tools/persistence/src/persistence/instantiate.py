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

from rdflib import RDF, Graph

from .builders import BUILDERS, build
from .ir_render import render as render_operation
from .namespaces import DAL
from .render import load_template, render
from .terms import Iri, Literal, PropertyPath

BUILDER_ONLY = frozenset({"payload-check"})
"""The builders that never had a Mustache template (H2.8b), so the equivalence harness has nothing to compare them with and a template
directory cannot supply them."""

TEMPLATE_SUFFIX = ".mustache"
"""What `dal:templateId` no longer carries (H2.7). Until H2.9 retires the templates, the file of a template is its id and this suffix."""


# The term type each declared dal:paramType is re-wrapped as. Wrapping by the declared type, not by the text's
# first character, keeps a property path from being read as an IRI.
_PARAM_TYPES = {"Iri": Iri, "Literal": Literal, "String": Literal, "PropertyPath": PropertyPath}


def operation_context(compiled_profile: Graph, op_node) -> dict:
    """The parameter bindings of one generated operation, as the values a template (or a builder) takes. Each
    value is already encoded term text, re-wrapped as the term type its ``dal:paramType`` declares and never
    encoded again (see the module docstring). An unknown type is refused."""
    context: dict = {}
    for binding_node in compiled_profile.objects(op_node, DAL.hasParameterBinding):
        name = str(compiled_profile.value(binding_node, DAL.paramName))
        raw_value = str(compiled_profile.value(binding_node, DAL.paramValue))
        param_type = str(compiled_profile.value(binding_node, DAL.paramType))
        if param_type == "Integer":
            context[name] = int(raw_value)
        elif param_type in _PARAM_TYPES:
            context[name] = _PARAM_TYPES[param_type](raw_value)
        else:
            raise ValueError(f"parameter binding {name!r} has an unknown dal:paramType {param_type!r}")
    return context


def run_choices(compiled_profile: Graph, op_node) -> tuple[bool, str]:
    """What the run that compiled the profile chose for one operation: whether its required-parameter guard is on, and who names its
    graph. They are the operation's ``dal:guardStatus`` (guards are on unless it is ``dal:GuardsOff``) and ``dal:graphNaming``
    (``dal:CallerNamed``, or the query names it). ``instantiate`` follows them, so a rendering cannot disagree with its profile
    (H2.7-Q2). A profile that records neither is rendered with the guards on and the query naming its graphs."""
    guards = compiled_profile.value(op_node, DAL.guardStatus) != DAL.GuardsOff
    graph_names = "caller" if compiled_profile.value(op_node, DAL.graphNaming) == DAL.CallerNamed else "query"
    return guards, graph_names


def _render_operation(compiled_profile: Graph, op_node, template_dir: Path | None) -> tuple[str, str]:
    """An operation's name and SPARQL text, found by its ``dal:templateId``, which is the builder's identity. An operation
    with a builder (:mod:`persistence.builders`) is rendered from its typed value, with the guard and the graph naming
    its contract records. Any operation under an overriding template library is rendered by Mustache as before,
    from the file named by its id and the ``.mustache`` suffix, until H2.9 retires the templates."""
    operation_name = str(compiled_profile.value(op_node, DAL.forOperation))
    template_node = compiled_profile.value(op_node, DAL.usesTemplate)
    stem = str(compiled_profile.value(template_node, DAL.templateId)).removesuffix(TEMPLATE_SUFFIX)
    context = operation_context(compiled_profile, op_node)
    if (template_dir is None or stem in BUILDER_ONLY) and stem in BUILDERS:
        guards, graph_names = run_choices(compiled_profile, op_node)
        return operation_name, render_operation(build(stem, context, guards=guards, graph_names=graph_names))
    return operation_name, render(load_template(stem + TEMPLATE_SUFFIX, template_dir), context)


def _local(iri) -> str:
    return str(iri).rstrip("/#").rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def instantiate_by_target(compiled_profile: Graph, template_dir: Path | None = None) -> dict[str, dict[str, str]]:
    """Returns ``{target_name: {operation_name: rendered_sparql_text}}``, one
    entry per ``dal:CompiledProfile``. A target's name is its class's local
    name, followed by its deployment's local name where it has one
    (``Behaviour.LendingBehaviourGraphs``), since operations repeat per
    target (every target has its own audits) and differ in their bindings."""
    out: dict[str, dict[str, str]] = {}
    for profile in compiled_profile.subjects(RDF.type, DAL.CompiledProfile):
        name = _local(compiled_profile.value(profile, DAL.forTarget))
        deployment = compiled_profile.value(profile, DAL.forDeployment)
        if deployment is not None:
            name = f"{name}.{_local(deployment)}"
        if name in out:
            raise ValueError(f"two compiled targets share the name {name!r}")
        out[name] = dict(
            _render_operation(compiled_profile, op_node, template_dir)
            for op_node in compiled_profile.objects(profile, DAL.generatedOperation)
        )
    return out


def instantiate_profile(compiled_profile: Graph, template_dir: Path | None = None) -> dict[str, str]:
    """Returns ``{operation_name: rendered_sparql_text}`` for a compiled
    profile with one target. Refuses a profile with several, whose
    operations share names: use :func:`instantiate_by_target`."""
    by_target = instantiate_by_target(compiled_profile, template_dir)
    if len(by_target) > 1:
        raise ValueError(f"{len(by_target)} targets: operation names repeat per target, use instantiate_by_target")
    return next(iter(by_target.values()), {})


def instantiate_to_directory(compiled_profile: Graph, out_dir: Path, template_dir: Path | None = None) -> list[Path]:
    """Writes ``<out_dir>/<target_name>/<operation_name>.rq`` for every
    generated operation of every target."""
    written: list[Path] = []
    for target_name, rendered in instantiate_by_target(compiled_profile, template_dir).items():
        target_dir = out_dir / target_name
        target_dir.mkdir(parents=True, exist_ok=True)
        for operation_name, text in rendered.items():
            path = target_dir / f"{operation_name.replace(':', '_').replace('/', '_')}.rq"
            path.write_text(text, encoding="utf-8")
            written.append(path)
    return written


__all__ = ["run_choices", "instantiate_by_target", "instantiate_profile", "instantiate_to_directory"]
