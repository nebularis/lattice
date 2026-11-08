# SPDX-License-Identifier: MPL-2.0
"""`python -m v_rig --rig <path> [--out <path>]`. Reads the rig, writes the representation, the blind view, the findings,
the run record and the deny list, and prints the run's identifying lines first. Logs name ids and locators, never text."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from rdflib import OWL, Graph, URIRef

from . import canon
from . import p1 as p1_module
from . import p1_checks
from . import p2 as p2_module
from . import p3 as p3_module
from .cases import input_bindings
from . import readcase
from .lift import RunInfo, lift, mark_readings
from .out import OutError, counts, repository_root, resolve_out, write_outputs
from .rig import RigError, read_rig

VECTOR_SCHEMA_VERSION = p3_module.VECTOR_SCHEMA_VERSION


def _commit(root: Path) -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, encoding="utf-8")
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def run_info(root: Path | None = None) -> RunInfo:
    import lattice_repo_catalogue as reader
    catalogue = reader.load(root)
    module = catalogue.module("v-rig")
    spec = Graph()
    for path in module.files("spec"):
        spec.parse(path, format="turtle")
    version = next((str(v).rsplit("/", 1)[-1] for v in spec.objects(None, OWL.versionIRI)), "unknown")
    return RunInfo(_commit(catalogue.root), catalogue.release_version or "unknown", version, VECTOR_SCHEMA_VERSION)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="v_rig", description=__doc__)
    parser.add_argument("--rig", required=True, help="the rig's directory, read in place and never written")
    parser.add_argument("--out", help="the output directory, default .local/v-rig/<rig digest>/ in the checkout")
    parser.add_argument("--extension", action="append", default=[], metavar="TTL",
                        help="a rig's extension graph, its reference data and its own mapping schemes, run after the tracked scheme. Repeatable")
    parser.add_argument("--case", action="append", default=[], metavar="TTL",
                        help="a read case, a Turtle graph in the vrig vocabulary written outside the repository, validated and compared with the declared view. Repeatable")
    parser.add_argument("--no-reasoner", action="store_true", help="skip the consistency check, which is then a reasoner-unavailable finding")
    parser.add_argument("--build-theory", action="store_true", help="build the generated P2 session with Isabelle, one build on HOL alone")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s", stream=sys.stderr)
    try:
        root = repository_root()
        rig = read_rig(args.rig)
        out = resolve_out(rig, args.out, root)
        info = run_info(root)
        graph = lift(rig, info)
        projection = p1_module.project(graph, [Path(e) for e in args.extension])
        mark_readings(graph, projection.reading_keys)
        checks = p1_checks.check_all(graph, projection.layers, reasoner=not args.no_reasoner)
        disagreements = []
        module_graphs = readcase.module_graphs() if args.case else None
        for path in args.case:
            case = readcase.load(Path(path), module_graphs)
            disagreements += readcase.compare(graph, case)
            readcase.add_read_case(graph, case)
        p1_module.add_findings(graph, URIRef(canon.run_iri(rig.digest)), projection.findings + checks.findings + disagreements)
        bindings = input_bindings([Path(e) for e in args.extension])
        found_vectors = p3_module.vectors(graph, rig.digest, projection.reading_keys, bindings, rig.file_digests)
        p3_module.validate_vectors(found_vectors)
        theory_text = p2_module.theory(graph, rig.digest, projection.reading_keys, bindings, rig.file_digests)
        record = {
            "rig_digest": rig.digest, "format_version": rig.format_version, "checkout_commit": info.checkout_commit,
            "substrate_release": info.substrate_release, "vocabulary_version": info.vocabulary_version,
            "vector_schema_version": info.vector_schema_version, "canonicalisation": canon.VERSION,
            "documents": [d.id for d in rig.documents], "programmes": [p.id for p in rig.programmes],
            "events": len(rig.events.events) if rig.events else 0, "counts": counts(graph),
            "p1": {"reading_keys": list(projection.reading_keys), "mapped_keys": sorted(projection.mapped_keys),
                   "compile_findings": projection.compile_findings, "layer_triples": len(projection.layers),
                   "consistent": checks.consistent, "competency": checks.competency},
            "p2": {"session": p2_module.SESSION, "built": None},
            "p3": {"vectors": sorted(found_vectors), "input_bindings": bindings},
            "read_cases": {"files": [str(Path(p).name) for p in args.case], "disagreements": len(disagreements)},
        }
        if args.build_theory:
            p2_module.write_theory(theory_text, out)
            built, output = p2_module.build(out)
            record["p2"]["built"] = built
            (out / "p2" / "build.log").write_text(output, encoding="utf-8", newline="\n")
            if not built:
                print(f"v_rig: the P2 build failed, see {out / 'p2' / 'build.log'}", file=sys.stderr)
        written = write_outputs(rig, graph, out, record, projection=projection, checks=checks)
        for path in p2_module.write_theory(theory_text, out) + p3_module.write_vectors(found_vectors, out):
            written[str(path.relative_to(out))] = path
    except (RigError, OutError, readcase.ReadCaseError) as error:
        print(f"v_rig: {error}", file=sys.stderr)
        return 2
    print(f"rig digest        {rig.digest}")
    print(f"format version    {rig.format_version}")
    print(f"checkout commit   {info.checkout_commit}")
    print(f"substrate release {info.substrate_release}")
    print(f"vocabulary        v-rig {info.vocabulary_version}, canonicalisation {canon.VERSION}")
    print(f"vector schema     {info.vector_schema_version or 'none yet'}")
    print(f"output            {out}")
    for name, path in written.items():
        print(f"  {name:<12} {path.name}")
    return 0
