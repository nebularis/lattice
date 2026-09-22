# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Command line for the persistence compiler.

``compile``
    Load ontology/persistence graphs plus an adopter's applied ontology,
    resolve every target, validate, select operations, and emit a
    ``dal:CompiledProfile`` graph (Turtle). Never produces SPARQL text and
    never touches a live backend (ADR-A79).

``instantiate``
    Read a compiled profile and the checked-in template library, and
    write one ``.rq`` file per generated operation. Entirely optional.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rdflib import Graph

from .capability import load_capability_spec
from .compiler import CompileError, compile_to_graph
from .instantiate import instantiate_to_directory
from .namespaces import DAL


def _load_graph(config_paths: list[str], capability_spec: str | None) -> Graph:
    graph = Graph()
    graph.bind("dal", DAL)
    for path in config_paths:
        p = Path(path)
        if p.is_dir():
            for ttl_file in sorted(p.glob("*.ttl")):
                graph.parse(ttl_file, format="turtle")
        else:
            graph.parse(p, format="turtle")
    if capability_spec:
        graph.parse(capability_spec, format="turtle")
    return graph


def cmd_compile(args: argparse.Namespace) -> int:
    graph = _load_graph(args.config, args.capability_spec)
    try:
        out, compiled = compile_to_graph(graph, fail_on_capability_mismatch=not args.no_fail_on_capability)
    except CompileError as e:
        print(f"compile failed: {e}", file=sys.stderr)
        return 1

    if not compiled:
        print("no targets discovered (no dal:targetClass found; pass --target-class explicitly?)", file=sys.stderr)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.serialize(destination=str(out_path), format="turtle")
    print(f"compiled {len(compiled)} target(s) -> {out_path}", file=sys.stderr)
    return 0


def cmd_instantiate(args: argparse.Namespace) -> int:
    profile = Graph()
    profile.parse(args.compiled_profile, format="turtle")
    template_dir = Path(args.template_dir) if args.template_dir else None
    written = instantiate_to_directory(profile, Path(args.out), template_dir)
    for path in written:
        print(f"wrote {path}", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="persistence")
    sub = parser.add_subparsers(dest="command", required=True)

    p_compile = sub.add_parser("compile", help="resolve and validate a configuration, emit a dal:CompiledProfile")
    p_compile.add_argument("config", nargs="+", help="ontology/persistence graph file(s) or directory(ies)")
    p_compile.add_argument("--capability-spec", help="an optional dal:CapabilitySpec Turtle file")
    p_compile.add_argument("--out", required=True, help="output path for the compiled profile (Turtle)")
    p_compile.add_argument(
        "--no-fail-on-capability",
        action="store_true",
        help="do not fail the compile when a supplied CapabilitySpec's check fails (report only)",
    )
    p_compile.set_defaults(func=cmd_compile)

    p_instantiate = sub.add_parser("instantiate", help="render a compiled profile's operations to SPARQL text")
    p_instantiate.add_argument("compiled_profile", help="a dal:CompiledProfile Turtle file")
    p_instantiate.add_argument("--template-dir", help="override the built-in template library directory")
    p_instantiate.add_argument("--out", required=True, help="output directory for generated .rq files")
    p_instantiate.set_defaults(func=cmd_instantiate)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


__all__ = ["main", "build_parser"]
