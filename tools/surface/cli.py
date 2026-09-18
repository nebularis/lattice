# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Command line for the surface compiler.

Argument and logging conventions follow ``tools/mork2rml.py``, so the two tools
behave the same way in a pipeline.

``compile``
    Generate the module package for every contract in a declaration graph.
    ``--verify-determinism`` compiles twice and compares artefact hashes,
    discharging law ``srf:R1`` on success and failing the run on mismatch.

``check``
    Recompute a recorded surface's read set against the current sources and
    report which entries have moved. This is the whole of invalidation: a
    surface is stale when any entry's current hash differs from the recorded
    one, and nothing about the change needs classifying for that to be decided.

``parity``
    Ask the surface and the source the same questions and compare the answers,
    discharging law ``srf:R2`` when they agree.

``mork``
    Lift compiled surfaces into ``mrk:ProjectionMapping`` records.

``lower``
    Lower Surface contracts into MORK mapping graphs (ADR-A18). Projection
    contracts always lower, since a projection has no direct-emit form
    (ADR-A17); ``--promotion-index`` additionally lowers Promotion and Index
    contracts, mirrored alongside their existing direct-emit path — the
    "configured" case, not the default. Unlike ``mork``, this reads no source
    graph and compiles nothing: the whole output is the mapping graph a later
    backend compiler (ADR-A23) will read, plus any ``mork:dependsOnMapping``
    edges a role binding's declared cross-reference to another contract in
    the same batch implies.
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from rdflib import Graph, Literal, URIRef

from . import mork as mork_interop
from .compile import CompileError, StackedInput, SurfaceCompiler, discharge_determinism, render
from .lowering import lower_all
from .model import ContractError, SurfaceGraphAnalyser, read_contracts, read_projection_contracts
from .namespaces import OUTPUT_PREFIXES, RDF, SRF
from .parity import check_parity, run_shared_surface_parity
from .serialise import parse_files, serialise

logger = logging.getLogger(__name__)

DETERMINISM_RUN = "surface-compiler-selfcheck"
PARITY_RUN = "surface-parity-harness"


def _now(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    return (
        _datetime.datetime.now(_datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _input_surfaces(paths: Sequence[str], declarations: Graph) -> List[StackedInput]:
    """Read generated manifests supplied as input, for stacked surfaces.

    Resolves each input's profile identity against ``declarations`` (where the
    profile individual's own properties are asserted, not the manifest), so
    the ADR-A21 composition check in ``SurfaceCompiler`` has something to
    compare rather than silently skipping every input.
    """
    if not paths:
        return []
    graph = parse_files(paths)
    analyser = SurfaceGraphAnalyser(declarations)
    found: List[StackedInput] = []
    for record in graph.subjects(RDF.type, SRF.GeneratedSurface):
        digest = graph.value(record, SRF.artefactHash)
        depth = graph.value(record, SRF.stackDepth)
        scope = graph.value(record, SRF.signatureScope)
        profile_iri = graph.value(record, SRF.generatedByProfile)
        identity: Optional[str] = None
        if profile_iri is not None:
            try:
                identity = analyser.profile(profile_iri).identity_hash()
            except ContractError:
                identity = None
        found.append(
            StackedInput(
                surface=record,
                artefact_hash=str(digest) if digest is not None else "",
                depth=int(depth) if depth is not None else 0,
                profile_identity=identity,
                signature_scope=str(scope) if scope is not None else None,
            )
        )
    return sorted(set(found), key=lambda entry: str(entry.surface))


def _load(args: argparse.Namespace, *extra: Sequence[str]) -> Graph:
    paths: List[str] = list(args.contracts)
    paths.extend(getattr(args, "sources", []) or [])
    for group in extra:
        paths.extend(group or [])
    return parse_files(paths)


def command_compile(args: argparse.Namespace) -> int:
    declarations = parse_files(args.contracts)
    source = _load(args, args.input_surface)
    stacked = _input_surfaces(args.input_surface, declarations)
    produced_at = _now(args.now)

    out_root = Path(args.out)
    failures = 0

    for contract in read_contracts(declarations, only=args.contract):
        try:
            compiled = SurfaceCompiler(contract, source, produced_at, stacked).compile()
        except (CompileError, ContractError, ValueError) as error:
            print(f"FAIL {contract.iri}\n  {error}", file=sys.stderr)
            failures += 1
            continue

        if args.verify_determinism:
            again = SurfaceCompiler(contract, source, produced_at, stacked).compile()
            if again.artefact_hash != compiled.artefact_hash:
                print(
                    f"FAIL {contract.iri}\n  regeneration is not deterministic: "
                    f"{compiled.artefact_hash} then {again.artefact_hash}",
                    file=sys.stderr,
                )
                failures += 1
                continue
            discharge_determinism(compiled, produced_at, DETERMINISM_RUN)

        if args.parity:
            report = check_parity(compiled, source)
            if not report.holds():
                print(f"FAIL {contract.iri}\n{report.describe()}", file=sys.stderr)
                failures += 1
                continue
            if report.checked:
                SurfaceCompiler(contract, Graph(), produced_at).discharge(
                    compiled.modules["manifest"], SRF.R2, PARITY_RUN
                )

        target = out_root / contract.key
        target.mkdir(parents=True, exist_ok=True)
        rendered = render(compiled)
        for name, text in sorted(rendered.items()):
            (target / f"{name}.ttl").write_text(text, encoding="utf-8")

        if args.mork_mapping:
            mapping = mork_interop.lift(compiled)
            prefixes = dict(OUTPUT_PREFIXES)
            prefixes["mork"] = mork_interop.MORK
            prefixes["exec"] = URIRef(str(contract.target_namespace))
            (target / "projection-mapping.ttl").write_text(
                serialise(
                    mapping,
                    prefixes,
                    ["# SPDX-License-Identifier: MPL-2.0", "# MORK projection mapping record.", ""],
                ),
                encoding="utf-8",
            )

        print(
            f"ok   {contract.iri}\n"
            f"     modules      {', '.join(sorted(rendered))}\n"
            f"     population   {len(compiled.population)}\n"
            f"     symbols      {len(compiled.symbols)}\n"
            f"     artefact     {compiled.artefact_hash[:16]}\n"
            f"     semantic     {compiled.semantic_hash[:16]}\n"
            f"     signature    {str(compiled.signature_scope).rsplit('#', 1)[1]}"
        )
        for warning in compiled.warnings:
            print(f"warn {contract.iri}\n     {warning}", file=sys.stderr)

    return 1 if failures else 0


def command_check(args: argparse.Namespace) -> int:
    manifests = parse_files(args.manifest)
    declarations = parse_files(args.contracts)
    source = _load(args)
    produced_at = _now(args.now)
    stale = 0

    for record in manifests.subjects(RDF.type, SRF.GeneratedSurface):
        contract_iri = manifests.value(record, SRF.coversContract)
        recorded: Dict[Tuple[str, str], str] = {}
        for entry in manifests.objects(record, SRF.hasReadSetEntry):
            kind = manifests.value(entry, SRF.readSourceKind)
            origin = manifests.value(entry, SRF.readsSource)
            digest = manifests.value(entry, SRF.readHash)
            recorded[(str(kind), str(origin))] = str(digest)

        contracts = read_contracts(declarations, only=str(contract_iri))
        compiled = SurfaceCompiler(contracts[0], source, produced_at).compile()
        current = {entry.key(): entry.digest for entry in compiled.read_set}

        moved = [key for key, digest in current.items() if recorded.get(key) != digest]
        missing = [key for key in recorded if key not in current]
        if not moved and not missing:
            print(f"fresh {record}")
            continue
        stale += 1
        print(f"STALE {record}")
        for kind, origin in sorted(moved):
            print(f"      moved   {kind.rsplit('#', 1)[1]}  {origin}")
        for kind, origin in sorted(missing):
            print(f"      dropped {kind.rsplit('#', 1)[1]}  {origin}")
    return 1 if stale else 0


def command_parity(args: argparse.Namespace) -> int:
    if args.shared_corpus:
        failures = 0
        for case, report in run_shared_surface_parity(args.shared_corpus, args.root, _now(args.now)):
            print(f"{case}\n{report.describe()}")
            if not report.holds():
                failures += 1
        return 1 if failures else 0

    declarations = parse_files(args.contracts)
    source = _load(args)
    produced_at = _now(args.now)
    failures = 0
    for contract in read_contracts(declarations, only=args.contract):
        compiled = SurfaceCompiler(contract, source, produced_at).compile()
        report = check_parity(compiled, source)
        print(report.describe())
        if not report.holds():
            failures += 1
    return 1 if failures else 0


def command_mork(args: argparse.Namespace) -> int:
    prefixes = dict(OUTPUT_PREFIXES)
    prefixes["mork"] = mork_interop.MORK
    header = ["# SPDX-License-Identifier: MPL-2.0", ""]

    declarations = parse_files(args.contracts)
    source = _load(args)
    produced_at = _now(args.now)
    combined = Graph()
    for contract in read_contracts(declarations, only=args.contract):
        compiled = SurfaceCompiler(contract, source, produced_at).compile()
        for triple in mork_interop.lift(compiled, mapping_scheme=args.mapping_scheme):
            combined.add(triple)
    text = serialise(combined, prefixes, header + ["# MORK projection mapping records.", ""])
    Path(args.out).write_text(text, encoding="utf-8") if args.out else print(text)
    return 0


def command_lower(args: argparse.Namespace) -> int:
    """Lower Surface contracts into MORK mapping graphs (ADR-A18).

    Projection contracts always lower, since they have no direct-emit form.
    Promotion and Index contracts lower only when ``--promotion-index`` is
    given: they already have a working direct-emit path, so mirroring them
    into MORK as well is the configured case, not the default (delivery-plan
    Phase 3 item 2), and running both mechanisms over disjoint contract keys
    avoids any ambiguity about which one produced a given mapping.
    """
    prefixes = dict(OUTPUT_PREFIXES)
    prefixes["mork"] = mork_interop.MORK
    header = ["# SPDX-License-Identifier: MPL-2.0", ""]

    declarations = parse_files(args.contracts)
    try:
        projections = read_projection_contracts(declarations, only=args.contract)
    except ContractError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    contracts = []
    if args.promotion_index:
        contracts = read_contracts(declarations, only=args.contract)

    combined = lower_all(contracts=contracts, projections=projections)
    text = serialise(combined, prefixes, header + ["# Lowered MORK mapping graph.", ""])
    Path(args.out).write_text(text, encoding="utf-8") if args.out else print(text)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="surface", description="LATTICE surface compiler")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable verbose logging")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("compile", help="generate surface modules from contracts")
    build.add_argument("--contracts", nargs="+", required=True, help="declaration graph files")
    build.add_argument("--sources", nargs="*", default=[], help="scheme and instance graph files")
    build.add_argument("--input-surface", nargs="*", default=[], help="generated surfaces read as input")
    build.add_argument("--out", required=True, help="output directory")
    build.add_argument("--contract", default=None, help="compile only this contract IRI")
    build.add_argument("--now", default=None, help="fix the production timestamp")
    build.add_argument("--verify-determinism", action="store_true", help="compile twice and compare")
    build.add_argument("--parity", action="store_true", help="check surface/source parity before writing")
    build.add_argument("--mork-mapping", action="store_true", help="also emit a MORK projection mapping")
    build.set_defaults(func=command_compile)

    check = sub.add_parser("check", help="report whether a recorded surface is stale")
    check.add_argument("--manifest", nargs="+", required=True, help="generated manifest files")
    check.add_argument("--contracts", nargs="+", required=True, help="declaration graph files")
    check.add_argument("--sources", nargs="*", default=[], help="scheme and instance graph files")
    check.add_argument("--now", default=None)
    check.set_defaults(func=command_check)

    parity = sub.add_parser("parity", help="compare surface answers against source answers")
    parity.add_argument("--contracts", nargs="*", default=[])
    parity.add_argument("--sources", nargs="*", default=[])
    parity.add_argument("--contract", default=None)
    parity.add_argument("--shared-corpus", default=None, help="shared conformance manifest")
    parity.add_argument("--root", default=".", help="repository root for corpus paths")
    parity.add_argument("--now", default=None)
    parity.set_defaults(func=command_parity)

    mork_cmd = sub.add_parser("mork", help="MORK projection-mapping interoperation")
    mork_cmd.add_argument("--contracts", nargs="*", default=[])
    mork_cmd.add_argument("--sources", nargs="*", default=[])
    mork_cmd.add_argument("--contract", default=None)
    mork_cmd.add_argument("--mapping-scheme", default=None, type=URIRef)
    mork_cmd.add_argument("--out", default=None, help="output file (default: stdout)")
    mork_cmd.add_argument("--now", default=None)
    mork_cmd.set_defaults(func=command_mork)

    lower_cmd = sub.add_parser("lower", help="lower Surface contracts into MORK mapping graphs")
    lower_cmd.add_argument("--contracts", nargs="+", required=True, help="declaration graph files")
    lower_cmd.add_argument("--contract", default=None, help="lower only this contract IRI")
    lower_cmd.add_argument(
        "--promotion-index",
        action="store_true",
        help="also lower Promotion/Index contracts, mirrored alongside their direct-emit path",
    )
    lower_cmd.add_argument("--out", default=None, help="output file (default: stdout)")
    lower_cmd.set_defaults(func=command_lower)

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    try:
        return args.func(args)
    except (CompileError, ContractError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
