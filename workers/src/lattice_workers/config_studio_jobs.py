"""Pure job logic of the Configuration Studio worker (ADR-A136). No AMQP and no HTTP.

Given a job's kind, target, configuration graph and baseline graph, `run_job` returns the result
triples the contract in `contracts/config-studio` describes. Ontology files are found through the
repository catalogue reader, never by a path written here (STD-273).
"""

from __future__ import annotations

import functools
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple

import pyshacl
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

from . import config_studio_layers as layers

CST = Namespace("https://www.nebularis.org/neuro-semantic/lattice/config-studio#")
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


# The ontology files each target is validated with: (module, role, file pattern) for its data, and
# (module, file) for its shapes. Surface's constraints.ttl is left out because pySHACL refuses it
# (TD-11), and the surface compiler checks those laws. No layer's rules.ttl is run.
_SPECS = {
    "persistence": [("persistence", "spec", "persistence.ttl")],
    "surface": [("surface", "spec", "surface.ttl")],
    "vocabulary": [("foundation", "spec", "*.ttl"), ("foundation", "vocab", "*.ttl"), ("vocabulary", "spec", "*.ttl")],
    "quantification": [("quantification", "spec", "*.ttl"), ("quantification", "vocab", "*.ttl")],
    "eligibility": [
        ("vocabulary", "spec", "*.ttl"), ("quantification", "spec", "*.ttl"), ("quantification", "vocab", "*.ttl"),
        ("eligibility", "spec", "*.ttl"), ("eligibility", "vocab", "*.ttl"),
    ],
    # Stated meaning, checked with the layers Instrument imports, the library's forms coming in with the input.
    "meaning": [("vocabulary", "spec", "*.ttl")] + [
        (module, role, "*.ttl")
        for module in ("foundation", "quantification", "party", "eligibility", "wording", "behaviour", "instrument")
        for role in ("spec", "vocab")
    ],
    # A mapping's target terms, which compiling it checks: the layers stated meaning is written in.
    "mapping": [("vocabulary", "spec", "*.ttl")] + [
        (module, role, "*.ttl")
        for module in ("foundation", "quantification", "party", "eligibility", "wording", "behaviour", "instrument")
        for role in ("spec", "vocab")
    ],
}
_SHAPES = {
    "persistence": [("persistence", "constraints.ttl")],
    "surface": [("surface", "structural.ttl")],
    "vocabulary": [("vocabulary", "structural.ttl"), ("vocabulary", "constraints.ttl")],
    "quantification": [("quantification", "constraints.ttl")],
    "eligibility": [("eligibility", "structural.ttl"), ("eligibility", "constraints.ttl")],
    "meaning": [("instrument", "structural.ttl"), ("instrument", "constraints.ttl")],
}
TARGETS = tuple(_SPECS)


@functools.lru_cache(maxsize=None)
def _spec(root: str, target: str) -> Graph:
    """The target's specification graph. Cached, so never modified."""
    return _parse(*(path for module, role, pattern in _SPECS[target] for path in sorted(_module_dir(root, module, role).glob(pattern))))


@functools.lru_cache(maxsize=None)
def _shapes(root: str, target: str) -> Graph:
    """The shapes graph to validate against. Cached, so never modified."""
    return _merge(_spec(root, target), _parse(*(_module_dir(root, module, "shapes") / name for module, name in _SHAPES[target])))


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

    def artefact(self, path: str, media_type: str, content: str, group: str, stratum: Optional[int] = None) -> None:
        node = self._mint("artefact")
        add = self.graph.add
        add((self.job, CST.artefact, node))
        add((node, RDF.type, CST.Artefact))
        if stratum is not None:
            add((node, CST.stratum, Literal(stratum, datatype=XSD.nonNegativeInteger)))
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


def _validate(result: _Result, target: str, config: Graph, baseline: Graph, root: str, now: datetime) -> None:
    if target == "mapping":
        result.conforms(_mapping_findings(result, config, baseline, root, now))
        return
    data = _merge(Graph() if target == "surface" else _spec(root, target), baseline, config)
    conforms, report, _ = pyshacl.validate(
        data, shacl_graph=_shapes(root, target), inference="none", advanced=True, allow_warnings=True
    )
    _copy_shacl_report(result, report)
    # The dal: shapes target the dimension classes, so a dal:DataAccessProfile that declares several
    # dimensions at once is checked only by the compiler. Its refusal and warnings join the report.
    compiled = True
    if target == "persistence":
        compiled = _persistence_findings(result, config, baseline, root) is not None
    elif target == "vocabulary":
        layers.resolution_table(result, _merge(baseline, config), now)
    elif target == "eligibility":
        compiled = layers.eligibility(result, data, now)
    result.conforms(bool(conforms) and compiled)
    if target == "surface":
        result.finding(
            SH.Warning, "Surface constraints.ttl was not run, since pySHACL refuses it. Compile to check those laws.",
            "ConstraintsNotRun",
        )


# The namespace a mapping's compiled queries mint under. The studio never runs them on its own data, so it is a placeholder.
_MAPPING_BASE = "urn:lattice:studio:mapping/"
_MAPPING_SEVERITY = {"error": SH.Violation, "warning": SH.Warning}


def _mapping_findings(result: _Result, config: Graph, baseline: Graph, root: str, now: datetime, compiled: Optional[list] = None) -> bool:
    """Compiles every mapping scheme with mork_rdf, which validates it against MORK's shapes first and checks its target
    terms against the layers, and records each finding on the mapping it concerns. A finding that asks for review, such
    as an uncertain mapping, is information. Returns whether nothing is an error."""
    from mork_propose.check import check_graph

    checked = check_graph(_merge(baseline, config), base=_MAPPING_BASE, at=now, target_vocabulary=_spec(root, "mapping"), compiled_out=compiled)
    for _, severity, code, about, message in checked.findings:
        result.finding(_MAPPING_SEVERITY.get(severity, SH.Info), message, code, URIRef(str(about)) if about else None)
    return not any(f[1] == "error" for f in checked.findings)


def _compile_mapping(result: _Result, config: Graph, baseline: Graph, root: str, now: datetime) -> None:
    """Each scheme's compiled form as RDF, and its queries in the order a run takes them, grouped by scheme. A scheme whose
    source is JSON, XML or CSV, which mork_rdf leaves to another backend, is compiled to RML as well, with mork2rml, under
    its scheme's namespace."""
    from mork_rdf import to_rdf

    _compile_rml(result, _merge(baseline, config))

    compiled: list = []
    result.conforms(_mapping_findings(result, config, baseline, root, now, compiled))
    for c in compiled:
        name = re.sub(r"[^A-Za-z0-9_-]+", "-", c.scheme.rsplit("#", 1)[-1].rsplit("/", 1)[-1]).strip("-") or "scheme"
        result.artefact(f"{name}.compiled.ttl", "text/turtle", to_rdf(c).serialize(format="turtle"), c.scheme)
        queries = sorted(c.queries, key=lambda q: (q.stratum, q.box != "tbox", q.mapping, q.kind))
        text = "\n\n".join(f"# {q.kind} for {q.mapping}, stratum {q.stratum}, {q.box}\n{q.text}" for q in queries)
        result.artefact(f"{name}.rq", "application/sparql-query", text + "\n", c.scheme)


# The media types a sample source may be given in. JSON-LD is left out, since a context it names would be fetched.
_SAMPLE_FORMATS = {"text/turtle": "turtle", "application/n-triples": "nt"}


def run_mapping(job: URIRef, config: Graph, baseline: Graph, root: str, submitted_at: str) -> Graph:
    """A dry run of the mapping part over the sample source its one cst:ImportDocument carries: every scheme compiled,
    then run stratum by stratum, with what each mapping wrote at each stratum as an N-Triples artefact grouped by the
    mapping and marked with its stratum. Nothing is written but the job."""
    import pyoxigraph as ox
    from mork_rdf import run

    now = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
    result = _Result(job)
    documents = list(config.subjects(RDF.type, CST.ImportDocument))
    if len(documents) != 1:
        raise ValueError("a mapping's dry run needs exactly one cst:ImportDocument, its sample source")
    content, media = config.value(documents[0], CST.documentContent), config.value(documents[0], CST.documentMediaType)
    if str(media) not in _SAMPLE_FORMATS:
        raise ValueError(f"a sample source is Turtle or N-Triples, not {media}")
    sample = Graph().parse(data=str(content), format=_SAMPLE_FORMATS[str(media)])
    mappings = Graph()
    for t in config:
        if t[0] != documents[0]:
            mappings.add(t)

    class Recorder:
        """Keeps what each construct and closure wrote, by mapping and stratum."""

        def __init__(self) -> None:
            self.out: dict = {}

        def write(self, query, triples) -> None:
            self.out.setdefault((query.mapping, query.stratum), set()).update(triples)

        def close(self) -> None:
            pass

    compiled: list = []
    conforms = _mapping_findings(result, mappings, baseline, root, now, compiled)
    for c in compiled:
        recorder = Recorder()
        ran = run(c, sample, sink=recorder)
        for f in ran.findings:
            message = f"{f.message} ({f.value})" if f.value else f.message
            result.finding(SH.Warning, message, f.code, URIRef(f.mapping) if f.mapping else None)
        for (mapping, stratum), triples in sorted(recorder.out.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            text = ox.serialize(sorted(triples, key=str), format=ox.RdfFormat.N_TRIPLES).decode("utf-8")
            name = re.sub(r"[^A-Za-z0-9_-]+", "-", mapping.rsplit("#", 1)[-1].rsplit("/", 1)[-1]).strip("-") or "mapping"
            result.artefact(f"{stratum}/{name}.nt", "application/n-triples", text, mapping, stratum)
    result.conforms(conforms)
    return result.graph


_MORK = "http://www.nebularis.org/ontologies/Mork#"
_RML_FORMATS = {URIRef(_MORK + f) for f in ("JSON", "XML", "CSV", "YAML")}


def _compile_rml(result: _Result, g: Graph) -> None:
    import mork2rml

    representations = sorted(s for s, f in g.subject_objects(URIRef(_MORK + "format")) if f in _RML_FORMATS)
    if not representations:
        return
    schemes = sorted(g.subjects(RDF.type, URIRef(_MORK + "MappingScheme")), key=str)
    scheme = str(schemes[0]) if schemes else ""
    base = scheme[: max(scheme.rfind("#"), scheme.rfind("/")) + 1] or "urn:lattice:studio:rml/"
    source = g.value(representations[0], URIRef(_MORK + "identifier"))
    if len(schemes) > 1:
        result.finding(SH.Info, f"the schemes are compiled to RML together, under {base}", "RmlTogether")
    rml = mork2rml.MorkToRmlCompiler(g, base_iri=base, default_source=str(source) if source else None).compile()
    result.artefact("mapping.rml.ttl", "text/turtle", rml.serialize(format="turtle"), scheme or "rml")


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


def _compile_surface(result: _Result, config: Graph, baseline: Graph, root: str, now: str) -> None:
    from surface.compile import CompileError, SurfaceCompiler, render
    from surface.model import ContractError, read_contracts

    # A promotion onto a LATTICE term, such as fnd:externalKey, finds it declared in the substrate's specifications.
    source = _merge(config, baseline, _spec(root, "vocabulary"))
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
    if kind not in ("validate", "compile") or target not in TARGETS:
        raise ValueError(f"unknown job kind {kind!r} or target {target!r}")
    if kind == "compile" and target in ("vocabulary", "quantification"):
        raise ValueError(f"{target} configuration has nothing to compile")
    base = str(Path(root).resolve())
    now = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
    result = _Result(job)
    if kind == "validate":
        _validate(result, target, config, baseline, base, now)
    elif target == "persistence":
        _compile_persistence(result, config, baseline, base)
    elif target == "mapping":
        _compile_mapping(result, config, baseline, base, now)
    elif target == "eligibility":
        result.conforms(layers.eligibility_artefacts(result, _merge(_spec(base, target), baseline, config), now))
    else:
        _compile_surface(result, config, baseline, str(root), submitted_at)
    return result.graph
