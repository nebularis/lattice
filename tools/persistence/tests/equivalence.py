# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The equivalence harness of the typed IR sketch §7.1 (slice H2.2). It holds a builder to its Mustache template:
"a port changes nothing, and a change ports nothing".

Both sides are parsed and translated to SPARQL algebra by rdflib, so comments, whitespace and prefix spelling
vanish. Then only what SPARQL does not order is put in a fixed order, the triples of a basic graph pattern and
the conjuncts of a filter. Nothing else is reordered, and variable names must match exactly. The harness is
deleted with the templates in H2.9."""

from __future__ import annotations

import pprint
import re
from collections import defaultdict

from rdflib import RDF
from rdflib.plugins.sparql.algebra import translateQuery, translateUpdate
from rdflib.plugins.sparql.parser import parseQuery, parseUpdate
from rdflib.plugins.sparql.parserutils import CompValue

from persistence.builders import BUILDERS, build_recording
from persistence.instantiate import BUILDER_ONLY
from persistence.instantiate import operation_context
from persistence.ir_render import render
from persistence.namespaces import DAL
from persistence.render import REQUEST_TIME_SLOTS, load_template, render as mustache_render

from request_slots import fill_request_slots

_BGP_LISTS = {("BGP", "triples"), ("TriplesBlock", "triples")}


def _canonical(node, parent: str = "", key: str = ""):
    """``node`` as nested tuples, with unordered parts sorted."""
    if isinstance(node, CompValue):
        name = node.name
        if name == "ConditionalAndExpression":
            conjuncts = [node["expr"], *node.get("other", [])]
            return ("and", tuple(sorted((_canonical(c) for c in conjuncts), key=repr)))
        return (name, tuple(sorted(((k, _canonical(v, name, k)) for k, v in node.items()), key=lambda kv: kv[0])))
    if isinstance(node, (list, tuple)):
        items = tuple(_canonical(i, parent, key) for i in node)
        return tuple(sorted(items, key=repr)) if (parent, key) in _BGP_LISTS else items
    if isinstance(node, (dict, defaultdict)):
        return tuple(sorted(((repr(k), _canonical(v)) for k, v in node.items()), key=lambda kv: kv[0]))
    return node


def normal_form(text: str):
    """The canonical algebra of an update or a query."""
    stripped = re.sub(r"^(\s*PREFIX[^\n]*\n)+", "", text).lstrip()
    if stripped.startswith(("SELECT", "ASK", "CONSTRUCT")):
        return _canonical(translateQuery(parseQuery(text)).algebra)
    return _canonical(translateUpdate(parseUpdate(text)).algebra)


class Mismatch(AssertionError):
    pass


def compare(mustache_text: str, builder_text: str, label: str = "") -> None:
    left, right = normal_form(mustache_text), normal_form(builder_text)
    if left != right:
        raise Mismatch(f"{label}: the template and the builder differ at {first_difference(left, right)}\n--- template\n{pprint.pformat(left, width=140)}\n--- builder\n{pprint.pformat(right, width=140)}")


# ---- the corpus: every operation of every compiling fixture that a builder ports

_TAG = re.compile(r"\{\{\{?\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}?\}\}")
_COMMENT = re.compile(r"\{\{!.*?\}\}", re.S)


def template_tags(template_text: str) -> set[str]:
    """The compile-time names a template reads (its Mustache tags, less the request-time slots)."""
    return {m.group(1) for m in _TAG.finditer(_COMMENT.sub("", template_text))} - set(REQUEST_TIME_SLOTS)


def templated(operations):
    """The operations that have a Mustache template to be compared with. A builder with none (H2.8b) is held by its own tests."""
    return [op for op in operations if op[2] not in BUILDER_ONLY]


def ported_operations(compiled_corpus):
    """(fixture, operation name, template stem, context) for every generated operation a builder ports."""
    out = []
    for fixture, compiled in compiled_corpus:
        for profile in sorted(compiled.subjects(RDF.type, DAL.CompiledProfile), key=str):
            for node in sorted(compiled.objects(profile, DAL.generatedOperation), key=str):
                path = str(compiled.value(compiled.value(node, DAL.usesTemplate), DAL.templateId))
                stem = path.removesuffix(".mustache")  # a templateId has no suffix since H2.7
                if stem in BUILDERS:
                    out.append((fixture, str(compiled.value(node, DAL.forOperation)), stem, operation_context(compiled, node)))
    return out


def require_compared(compared: int, ported: int) -> None:
    """The harness must have compared every operation that was ported, and at least one."""
    if compared < max(ported, 1):
        raise Mismatch(f"the harness compared {compared} operations and {ported} were ported")


def compare_all(operations) -> int:
    """Compare the template and the builder (guards off) of each operation. Returns how many were compared."""
    compared = 0
    for fixture, name, stem, context in templated(operations):
        template_text = load_template(stem + ".mustache")
        mustache = fill_request_slots(mustache_render(template_text, context))
        built, read = build_recording(stem, context, guards=False)
        compare(mustache, fill_request_slots(render(built)), f"{fixture} {name}")
        if read != template_tags(template_text):
            raise Mismatch(f"{fixture} {name}: the builder reads {sorted(read)} and the template {sorted(template_tags(template_text))}")
        compared += 1
    return compared


def first_difference(left, right, path: str = "") -> str | None:
    """The path to the first place two normal forms differ, for the failure message."""
    if type(left) is not type(right):
        return f"{path}: {left!r} vs {right!r}"
    if isinstance(left, tuple):
        if len(left) != len(right):
            return f"{path}: {len(left)} items vs {len(right)}: {left!r} vs {right!r}"
        for i, (a, b) in enumerate(zip(left, right)):
            found = first_difference(a, b, f"{path}/{i}")
            if found:
                return found
        return None
    return None if left == right else f"{path}: {left!r} vs {right!r}"
