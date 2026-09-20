# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Command line for the MORK backend compiler family (ADR-A23, ADR-A24).

Usage::

    python -m mork_compilers.cli compile-condition \\
        --declarations ontology/eligibility/examples/interval-containment.ttl \\
        --condition https://example.org/lattice/eligibility/minimum-credit-condition \\
        --backend sparql --out artefact.ttl

``--backend`` may be repeated; omitting it compiles all three backends
(sparql, shacl, swrl) into one combined output graph. There is no "native"
backend — see this package's ``namespaces.py`` module docstring for why.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from rdflib import Graph, URIRef

from . import shacl_backend, sparql_backend, swrl_backend
from .eligibility_ir import IRCompileError, compile_condition
from .namespaces import OUTPUT_PREFIXES

BACKENDS = {
    "sparql": lambda plan: sparql_backend.compile_query_template(plan),
    "shacl": lambda plan: shacl_backend.compile_shapes(plan),
    "swrl": lambda plan: swrl_backend.compile_rules(plan),
}


def _load(paths: Sequence[str]) -> Graph:
    graph = Graph()
    for path in paths:
        graph.parse(path, format="turtle")
    return graph


def command_compile_condition(args: argparse.Namespace) -> int:
    graph = _load(args.declarations)
    try:
        plan = compile_condition(graph, URIRef(args.condition))
    except IRCompileError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    backends = args.backend or list(BACKENDS)
    combined = Graph()
    for prefix, namespace in OUTPUT_PREFIXES.items():
        combined.bind(prefix, namespace)
    for name in backends:
        for triple in BACKENDS[name](plan):
            combined.add(triple)

    text = combined.serialize(format="turtle")
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mork_compilers", description="MORK backend compiler family"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    condition = sub.add_parser("compile-condition", help="compile one elg:IntervalCondition")
    condition.add_argument(
        "--declarations", nargs="+", required=True,
        help="Eligibility/Quantification declaration graph files",
    )
    condition.add_argument("--condition", required=True, help="the elg:IntervalCondition IRI")
    condition.add_argument(
        "--backend", action="append", choices=list(BACKENDS),
        help="repeatable; omit to compile all backends",
    )
    condition.add_argument("--out", default=None, help="output file (default: stdout)")
    condition.set_defaults(func=command_compile_condition)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
