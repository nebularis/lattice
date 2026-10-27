"""Pure job logic of the Configuration Studio worker (ADR-A136). No AMQP and no HTTP.

Given a job's kind, target, configuration graph and baseline graph, `run_job` returns the result
triples the contract in `contracts/config-studio` describes. Ontology files are found through the
repository catalogue reader, never by a path written here (STD-273).
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple

import pyshacl
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

CST = Namespace("https://www.nebularis.org/neuro-semantic/lattice/poc/config-studio#")
SH = Namespace("http://www.w3.org/ns/shacl#")

_JOB_PREFIX = "urn:lattice:studio:job:"
_SPARQL_UPDATE = "application/sparql-update"
_SPARQL_QUERY = "application/sparql-query"
_WHOLE_GRAPH_PREFIX = "urn:x-persistence:"


def catalogue(root: Optional[Path | str] = None) -> Any:
    """The repository catalogue, loaded from `root` or found from `LATTICE_ROOT` or the working
    directory. The reader lives under `tools/`, which is not on the path of an installed worker."""
    try:
        import lattice_repo_catalogue as reader
    except ImportError:
        base = Path(root).resolve() if root is not None else _bootstrap_root()
        sys.path.insert(0, str(base / "tools"))
        import lattice_repo_catalogue as reader
    return reader.load(root)


def _bootstrap_root() -> Path:
    import os

    if os.environ.get("LATTICE_ROOT"):
        return Path(os.environ["LATTICE_ROOT"]).resolve()
    here = Path.cwd().resolve()
    for candidate in (here, *here.parents):
        if (candidate / "tools" / "lattice_repo_catalogue.py").is_file():
            return candidate
    raise RuntimeError("no repository found at or above the working directory: set LATTICE_ROOT")


def find_root(root: Optional[Path | str] = None) -> Path:
    """The repository root: `root`, else `LATTICE_ROOT`, else found from the working directory."""
    return Path(root).resolve() if root is not None else _bootstrap_root()


@functools.lru_cache(maxsize=None)
def _module_dir(root: str, module: str, role: str) -> Path:
    return catalogue(root).module(module).directory(role)


def _parse(*paths: Path) -> Graph:
    graph = Graph()
    for path in paths:
        graph.parse(path, format="turtle")
    return graph


@functools.lru_cache(maxsize=None)
def _spec(root: str, target: str) -> Graph:
    """The target's specification graph. Cached, so never modified."""
    module = "persistence" if target == "persistence" else "surface"
    return _parse(*sorted(_module_dir(root, module, "spec").glob(f"{module}.ttl")))


@functools.lru_cache(maxsize=None)
def _shapes(root: str, target: str) -> Graph:
    """The shapes graph to validate against. Cached, so never modified. Surface's constraints.ttl is
    left out because pySHACL refuses it (TD-11), and the surface compiler checks those laws."""
    if target == "persistence":
        return _merge(_spec(root, target), _parse(_module_dir(root, "persistence", "shapes") / "constraints.ttl"))
    shapes = _module_dir(root, "surface", "shapes")
    return _merge(_spec(root, target), _parse(shapes / "structural.ttl"))


def _merge(*graphs: Graph) -> Graph:
    merged = Graph()
    for graph in graphs:
        for prefix, namespace in graph.namespaces():
            merged.bind(prefix, namespace, override=False)
        merged += graph
    return merged


class _Result:
    """The triples a job adds to its graph, with deterministic minted IRIs."""

    def __init__(self, job: URIRef) -> None:
        self.job = job
        self.graph = Graph()
        self.report = URIRef(f"{job}#report")
        self._count = 0
        self.graph.add((job, CST.report, self.report))
        self.graph.add((self.report, RDF.type, SH.ValidationReport))

    def _mint(self, kind: str) -> URIRef:
        self._count += 1
        return URIRef(f"{self.job}#{kind}-{self._count}")

    def finding(self, severity: URIRef, message: str, code: Optional[str] = None, focus: Any = None) -> None:
        node = self._mint("result")
        add = self.graph.add
        add((self.report, SH.result, node))
        add((node, RDF.type, SH.ValidationResult))
        add((node, SH.resultSeverity, severity))
        add((node, SH.resultMessage, Literal(message)))
        if code is not None:
            add((node, CST.code, Literal(code)))
        if isinstance(focus, URIRef):
            add((node, SH.focusNode, focus))

    def conforms(self, value: bool) -> None:
        literal = Literal(value, datatype=XSD.boolean)
        self.graph.add((self.job, CST.conforms, literal))
        self.graph.add((self.report, SH.conforms, literal))

    def artefact(self, path: str, media_type: str, content: str, group: str) -> None:
        node = self._mint("artefact")
        add = self.graph.add
        add((self.job, CST.artefact, node))
        add((node, RDF.type, CST.Artefact))
        add((node, CST.path, Literal(path)))
        add((node, CST.mediaType, Literal(media_type)))
        add((node, CST.content, Literal(content)))
        add((node, CST.group, Literal(group)))

    def gap(self, group: str, obligation: str, message: str) -> None:
        node = self._mint("gap")
        add = self.graph.add
        add((self.job, CST.gap, node))
        add((node, RDF.type, CST.Gap))
        add((node, CST.group, Literal(group)))
        add((node, CST.obligation, Literal(obligation)))
        add((node, CST.message, Literal(message)))


def _copy_shacl_report(result: _Result, report: Graph) -> None:
    """Copies pySHACL's results, sorted, with minted IRIs. Blank-node shape and path references are
    dropped, since their identifiers differ between processes."""
    rows = []
    for node in report.subjects(RDF.type, SH.ValidationResult):
        def one(predicate: URIRef) -> Any:
            value = report.value(node, predicate)
            return None if isinstance(value, BNode) else value

        messages = sorted(str(m) for m in report.objects(node, SH.resultMessage))
        rows.append((
            str(one(SH.resultSeverity)), str(one(SH.focusNode)), str(one(SH.resultPath)),
            str(one(SH.sourceConstraintComponent)), messages, one(SH.focusNode), one(SH.resultPath),
            one(SH.resultSeverity), one(SH.sourceConstraintComponent), one(SH.value),
        ))
    rows.sort(key=lambda row: row[:5])
    for row in rows:
        _, _, _, _, messages, focus, path, severity, component, value = row
        node = result._mint("result")
        add = result.graph.add
        add((result.report, SH.result, node))
        add((node, RDF.type, SH.ValidationResult))
        for predicate, obj in ((SH.focusNode, focus), (SH.resultPath, path), (SH.resultSeverity, severity),
                               (SH.sourceConstraintComponent, component), (SH.value, value)):
            if obj is not None:
                add((node, predicate, obj))
        for message in messages:
            add((node, SH.resultMessage, Literal(message)))


def _validate(result: _Result, target: str, config: Graph, baseline: Graph, root: str) -> None:
    data = _merge(_spec(root, target) if target == "persistence" else Graph(), baseline, config)
    conforms, report, _ = pyshacl.validate(
        data, shacl_graph=_shapes(root, target), inference="none", advanced=True, allow_warnings=True
    )
    _copy_shacl_report(result, report)
    # The dal: shapes target the dimension classes, so a dal:DataAccessProfile that declares several
    # dimensions at once is checked only by the compiler. Its refusal and warnings join the report.
    compiled = target != "persistence" or _persistence_findings(result, config, baseline, root) is not None
    result.conforms(bool(conforms) and compiled)
    if target == "surface":
        result.finding(
            SH.Warning, "Surface constraints.ttl was not run, since pySHACL refuses it. Compile to check those laws.",
            "ConstraintsNotRun",
        )


def _persistence_findings(result: _Result, config: Graph, baseline: Graph, root: str) -> Optional[Tuple[Graph, Any]]:
    """Compiles the configuration and records the compiler's refusal, or each of its warnings.
    Returns the compiled profile and targets, or None when the compiler refused."""
    from persistence.compiler import CompileError, compile_to_graph

    try:
        profile, compiled = compile_to_graph(_merge(_spec(root, "persistence"), baseline, config))
    except CompileError as error:
        focus = error.target.cls
        named = focus if not str(focus).startswith(_WHOLE_GRAPH_PREFIX) else None
        result.finding(SH.Violation, str(error.cause), type(error.cause).__name__, named)
        return None
    seen = sorted({
        (d.kind, d.message, str(ct.target.cls))
        for ct in compiled for d in ct.diagnostics if d.severity == "WARNING"
    })
    for kind, message, cls in seen:
        result.finding(SH.Warning, message, kind, URIRef(cls))
    return profile, compiled


def _compile_persistence(result: _Result, config: Graph, baseline: Graph, root: str) -> None:
    from persistence.gaps import find_gaps
    from persistence.instantiate import instantiate_by_target

    found = _persistence_findings(result, config, baseline, root)
    result.conforms(found is not None)
    if found is None:
        return
    profile, compiled = found
    result.artefact("compiled-profile.ttl", "text/turtle", profile.serialize(format="turtle"), "profile")
    for group, operations in sorted(instantiate_by_target(profile).items()):
        for operation, text in sorted(operations.items()):
            name = operation.replace(":", "_").replace("/", "_") + ".rq"
            media = _SPARQL_UPDATE if name.endswith(".ru") else _SPARQL_QUERY
            result.artefact(f"{group}/{name}", media, text, group)
    for gap in find_gaps(compiled):
        result.gap(gap.target, gap.obligation, f"[{gap.gap}] {gap.message}")


def _compile_surface(result: _Result, config: Graph, baseline: Graph, now: str) -> None:
    from surface.compile import CompileError, SurfaceCompiler, render
    from surface.model import ContractError, read_contracts

    source = _merge(config, baseline)
    try:
        contracts = read_contracts(config)
    except ContractError as error:
        result.finding(SH.Violation, str(error), type(error).__name__)
        result.conforms(False)
        return
    failed = False
    for contract in sorted(contracts, key=lambda c: c.key):
        try:
            compiled = SurfaceCompiler(contract, source, now).compile()
            files = render(compiled)
        except (CompileError, ContractError, ValueError) as error:
            result.finding(SH.Violation, str(error), type(error).__name__, contract.iri)
            failed = True
            continue
        for warning in compiled.warnings:
            result.finding(SH.Warning, str(warning), "SurfaceWarning", contract.iri)
        for name, text in sorted(files.items()):
            result.artefact(f"{contract.key}/{name}.ttl", "text/turtle", text, contract.key)
    result.conforms(not failed)


def run_job(
    job: URIRef, kind: str, target: str, config: Graph, baseline: Graph, root: Path | str, submitted_at: str
) -> Graph:
    """The triples a finished job adds. `kind` is `validate` or `compile`, `target` is `persistence`
    or `surface`. `submitted_at` is the compile time of a surface, so two runs give the same files."""
    if kind not in ("validate", "compile") or target not in ("persistence", "surface"):
        raise ValueError(f"unknown job kind {kind!r} or target {target!r}")
    base = str(Path(root).resolve())
    result = _Result(job)
    if kind == "validate":
        _validate(result, target, config, baseline, base)
    elif target == "persistence":
        _compile_persistence(result, config, baseline, base)
    else:
        _compile_surface(result, config, baseline, submitted_at)
    return result.graph
