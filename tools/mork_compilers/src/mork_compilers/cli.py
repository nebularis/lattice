# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Command line for the MORK backend compiler family (ADR-A23, ADR-A24).

Usage::

    python -m mork_compilers.cli compile-condition \\
        --declarations ontology/eligibility/examples/interval-containment.ttl \\
        --condition https://example.org/lattice/eligibility/minimum-credit-condition \\
        --backend sparql --out artefact.ttl

``--backend`` may be repeated; omitting it compiles the sparql, shacl and
swrl backends into one combined output graph. The owl backend compiles bound
conditions with a claimed single-valued path only (ADR-A90). A concept condition
whose scheme contract has bindings needs ``--at`` (an ISO 8601 instant) and
any number of ``--scope`` binding-scope IRIs (ADR-A89 item 2).

``check-classes`` compiles the named conditions or profiles into one OWL
module and asks the test-only reasoning harness one question about them
(ADR-A83, ADR-A90 item 6), printing the ``exe:DesignTimeCheck`` record::

    python -m mork_compilers.cli check-classes --declarations decl.ttl \
        --context applied-ontology.ttl --kind subsumption \
        --class https://example.org/revised --against https://example.org/original There is no "native"
backend — see this package's ``namespaces.py`` module docstring for why.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from datetime import datetime

from rdflib import Graph, URIRef
from rdflib.namespace import RDF

from . import owl_backend, reasoning, shacl_backend, sparql_backend, swrl_backend
from .eligibility_ir import (
    IRCompileError, ResolutionContext, compile_any_condition, compile_concept_condition, compile_condition, compile_profile,
)
from .namespaces import ELG
from .namespaces import OUTPUT_PREFIXES

BACKENDS = {
    "sparql": lambda plan: sparql_backend.compile_query_template(plan),
    "shacl": lambda plan: shacl_backend.compile_shapes(plan),
    "swrl": lambda plan: swrl_backend.compile_rules(plan),
    "owl": lambda plan: owl_backend.compile_classes(plan),
}


def _load(paths: Sequence[str]) -> Graph:
    graph = Graph()
    for path in paths:
        graph.parse(path, format="turtle")
    return graph


def _context(args: argparse.Namespace) -> Optional[ResolutionContext]:
    if not args.at:
        return None
    return ResolutionContext(at=datetime.fromisoformat(args.at), scope=frozenset(URIRef(s) for s in args.scope or ()))


def _emit(graph: Graph, out: Optional[str]) -> None:
    for prefix, namespace in OUTPUT_PREFIXES.items():
        graph.bind(prefix, namespace)
    text = graph.serialize(format="turtle")
    if out:
        Path(out).write_text(text, encoding="utf-8")
    else:
        print(text)


def command_compile_condition(args: argparse.Namespace) -> int:
    graph = _load(args.declarations)
    condition = URIRef(args.condition)
    combined = Graph()
    try:
        if (condition, RDF.type, ELG.IntervalCondition) in graph:
            plan = compile_condition(graph, condition)
        else:
            plan = compile_concept_condition(graph, condition, _context(args))
        for name in args.backend or ["sparql", "shacl", "swrl"]:
            combined += BACKENDS[name](plan)
    except IRCompileError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    _emit(combined, args.out)
    return 0


def command_check_classes(args: argparse.Namespace) -> int:
    if not reasoning.available():
        print("error: reasoning-testkit jar not built (mise run bootstrap:reasoning-testkit)", file=sys.stderr)
        return 2
    graph = _load(args.declarations)
    names = [URIRef(args.cls)] + ([URIRef(args.against)] if args.against else [])
    try:
        plans = [
            compile_profile(graph, name, _context(args)) if (name, RDF.type, ELG.AdmissionProfile) in graph
            else compile_any_condition(graph, name, _context(args))
            for name in names
        ]
        module = owl_backend.compile_classes(*plans, disjoint_siblings=args.disjoint_siblings)
    except IRCompileError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    classes = [owl_backend.owl_class(name) for name in names]
    _, record = owl_backend.check(module, args.kind, classes[0], classes[1] if args.against else None,
                                  context=[_load(args.context)] if args.context else [])
    _emit(record, args.out)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mork_compilers", description="MORK backend compiler family"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    condition = sub.add_parser("compile-condition", help="compile one interval or concept condition")
    condition.add_argument(
        "--declarations", nargs="+", required=True,
        help="Eligibility/Quantification declaration graph files",
    )
    condition.add_argument("--condition", required=True, help="the condition IRI")
    condition.add_argument("--at", default=None, help="resolution instant, ISO 8601, for contracts with bindings")
    condition.add_argument("--scope", action="append", help="repeatable voc:BindingScope IRI active at resolution")
    condition.add_argument(
        "--backend", action="append", choices=list(BACKENDS),
        help="repeatable; omit to compile all backends",
    )
    condition.add_argument("--out", default=None, help="output file (default: stdout)")
    condition.set_defaults(func=command_compile_condition)

    classes = sub.add_parser("check-classes", help="ask the reasoning harness about generated OWL classes")
    classes.add_argument("--declarations", nargs="+", required=True, help="Eligibility declaration graph files")
    classes.add_argument("--context", nargs="+", help="the applied ontology's class and property declarations")
    classes.add_argument("--kind", required=True, choices=sorted(owl_backend.CHECKS))
    classes.add_argument("--class", dest="cls", required=True, help="the condition or profile IRI checked")
    classes.add_argument("--against", help="the subsuming or overlapping condition or profile IRI")
    classes.add_argument("--disjoint-siblings", action="store_true", help="declare sibling concepts disjoint")
    classes.add_argument("--at", default=None, help="resolution instant, ISO 8601, for contracts with bindings")
    classes.add_argument("--scope", action="append", help="repeatable voc:BindingScope IRI active at resolution")
    classes.add_argument("--out", default=None, help="output file (default: stdout)")
    classes.set_defaults(func=command_check_classes)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
