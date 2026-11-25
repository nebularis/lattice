# SPDX-License-Identifier: MPL-2.0
"""A surface step's projection part, run as a run of its own (contracts/config-studio/README.md, Runs, "A projection step"; ADR-A154, addendum of
2026-11-25).

The body is the TriG a surface step is, read by the rules of "A surface step": every graph is the sample world as it was before the edit, except the
reserved graphs under `urn:lattice:studio:step`, which hold the request and the edit. The worker runs each compiled projection scheme of the compile job
with `mork_rdf`'s driver over the world before the edit and over the world after it, and says what each scheme wrote in both and what changed. The
compiled forms are the job's, `projections/{scheme}.compiled.ttl`, which `mork_rdf.from_rdf` reads back and refuses where their queries no longer give
the digest they are named by, and the job's `projections/manifest.json` names them. A step is a function of the compile job and the body alone, so the same
step gives the same parts on a repeat and when the quads of the world arrive in another order, and it reads no clock (PRI-56). The parts are built here
and framed by `config_studio_run_frames`."""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Optional
from urllib.parse import unquote

import pyoxigraph as ox
from rdflib import Graph, URIRef

from . import config_studio_run_frames as frames
from .config_studio_jobs import CST, Recorder
from .config_studio_projections import MANIFEST

STEP_GRAPH = "urn:lattice:studio:step"
ADDED = STEP_GRAPH + "/added"
REMOVED = STEP_GRAPH + "/removed"
PROMOTED_PREFIX = "urn:lattice:studio:promoted:"
_CST = "https://www.nebularis.org/neuro-semantic/lattice/config-studio#"
_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
_REQUEST = ox.NamedNode(_CST + "SimulationStepRequest")
_FOR_PART = ox.NamedNode(_CST + "forPart")
_FOR_CLASS = ox.NamedNode(_CST + "forClass")
_TIME = ox.NamedNode(_CST + "transactionTime")
_SURFACE = ox.NamedNode(_CST + "Surface")
_DATETIME = "http://www.w3.org/2001/XMLSchema#dateTime"
_ZONED = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T.*(Z|[+-][0-9]{2}:[0-9]{2})")


class StepFailed(Exception):
    """A step that cannot be run. The message is for the author, so it names the part and never repeats the input."""


def _bytes(text: str) -> bytes:
    return text.encode("utf-8")


def _line(q: ox.Quad) -> str:
    return f"{q.subject} {q.predicate} {q.object} ."


def _where(graph: Any) -> str:
    return "the default graph" if isinstance(graph, ox.DefaultGraph) else f"<{graph.value}>"


@dataclass(frozen=True)
class Step:
    """A step as its TriG gives it: the time, the quads the edit adds and removes, and the world before the edit."""

    time: str
    added: frozenset
    removed: frozenset
    world: frozenset

    def after(self) -> frozenset:
        """The world once the edit is applied. A removal of a quad the world lacks and an addition of one it holds change nothing."""
        return frozenset((self.world - self.removed) | self.added)

    def sources(self) -> list[str]:
        """The named graphs the edit changes, in the order of their UTF-8 bytes."""
        named = {q.graph_name.value for q in (*self.added, *self.removed) if isinstance(q.graph_name, ox.NamedNode)}
        return sorted(named, key=_bytes)


def parse(trig: str) -> Step:
    """Reads `trig`, or raises the reason a part of it is missing or malformed."""
    if not trig.strip():
        raise StepFailed(f"The step is empty. Send TriG with the step in the graph <{STEP_GRAPH}>.")
    try:
        quads = list(ox.parse(_bytes(trig), format=ox.RdfFormat.TRIG))
    except (SyntaxError, ValueError) as error:
        reason = (str(error).strip().splitlines() or [""])[0][:200]
        raise StepFailed(f"The sample world is not valid TriG. {reason}".strip()) from None
    step = ox.NamedNode(STEP_GRAPH)
    own = [q for q in quads if q.graph_name == step]
    requests = sorted({q.subject for q in own if q.predicate == _RDF_TYPE and q.object == _REQUEST}, key=str)
    if not requests:
        raise StepFailed(f"The step graph <{STEP_GRAPH}> holds no cst:SimulationStepRequest, so there is no step to run.")
    if len(requests) > 1:
        raise StepFailed(f"The step graph <{STEP_GRAPH}> holds {len(requests)} steps, and a run takes one.")
    request = requests[0]
    _part(own, request)
    time = _time(own, request)
    added: set = set()
    removed: set = set()
    world: set = set()
    for q in quads:
        if q.graph_name == step:
            continue
        edit = _edit(q)
        if edit is None:
            world.add(q)
        elif q.graph_name.value.startswith(ADDED):
            added.add(edit)
        else:
            removed.add(edit)
    for q in sorted(added, key=lambda q: _bytes(_where(q.graph_name) + " " + _line(q))):
        if q in removed:
            raise StepFailed(f"The edit both adds and removes {_line(q)} in {_where(q.graph_name)}. Give a change once.")
    return Step(time, frozenset(added), frozenset(removed), frozenset(world))


def _part(own: list, request: Any) -> None:
    """The part the step simulates must be the surface, and a persistence step sent here is told so."""
    parts = [q.object for q in own if q.subject == request and q.predicate == _FOR_PART]
    if not parts:
        if any(q.subject == request and q.predicate == _FOR_CLASS for q in own):
            raise StepFailed(f"The step names cst:forClass, as a persistence step does, and this run simulates the surface part. Send cst:forPart cst:Surface and the edit in the graphs <{ADDED}> and <{REMOVED}>.")
        raise StepFailed("The step does not say cst:forPart, the part it simulates. Add cst:forPart cst:Surface to the step graph.")
    if len(parts) > 1 or not isinstance(parts[0], ox.NamedNode):
        raise StepFailed("The step must give cst:forPart once, as an IRI.")
    if parts[0] != _SURFACE:
        raise StepFailed(f"The step is for <{parts[0].value}>, and this run simulates the surface part, cst:Surface.")


def _time(own: list, request: Any) -> str:
    values = [q.object for q in own if q.subject == request and q.predicate == _TIME]
    if not values:
        raise StepFailed("The step does not say cst:transactionTime, the time it runs at. Add it as an xsd:dateTime with a time zone.")
    value = values[0]
    ok = len(values) == 1 and isinstance(value, ox.Literal) and value.datatype.value == _DATETIME and bool(_ZONED.fullmatch(value.value))
    if ok:
        try:
            ok = datetime.fromisoformat(value.value.replace("Z", "+00:00")).tzinfo is not None
        except ValueError:
            ok = False
    if not ok:
        raise StepFailed("The step must give cst:transactionTime once, as a valid xsd:dateTime with a time zone, for example 2026-03-31T23:59:58Z.")
    return value.value


def _edit(q: ox.Quad) -> Optional[ox.Quad]:
    """The quad a reserved graph's quad edits, or None for a quad of the sample world. A graph under `urn:lattice:studio:step/` that is not one of
    the four forms is reserved and malformed here."""
    graph = q.graph_name
    if not isinstance(graph, ox.NamedNode) or not graph.value.startswith(STEP_GRAPH + "/"):
        return None
    name = graph.value
    if name in (ADDED, REMOVED):
        target: Any = ox.DefaultGraph()
    elif name.startswith((ADDED + "/", REMOVED + "/")):
        edited = _decode(name, name[len(ADDED if name.startswith(ADDED + "/") else REMOVED) + 1:])
        if not edited or ":" not in edited[1:] or any(c.isspace() or c in '<>"' for c in edited):
            raise StepFailed(f"The graph <{name}> names the edited graph <{edited}>, which is not an IRI.")
        if edited == STEP_GRAPH or edited.startswith(STEP_GRAPH + "/"):
            raise StepFailed(f"The graph <{name}> edits a graph that is reserved for the step.")
        if edited.startswith(PROMOTED_PREFIX):
            raise StepFailed(f"The graph <{name}> edits the derived rows <{edited}>. A step edits a source, and the rows are what it maintains.")
        target = ox.NamedNode(edited)
    else:
        raise StepFailed(f"The graph <{name}> is reserved for the step and is not one a surface step reads. The edit is in <{ADDED}> and <{REMOVED}> and in a graph of each named from the edited graph, as <{ADDED}/{{graph}}>.")
    return ox.Quad(q.subject, q.predicate, q.object, target)


def _decode(name: str, encoded: str) -> str:
    """The graph an encoded name stands for, as `ENCODE_FOR_URI` wrote it, or raises."""
    if re.search(r"%(?![0-9A-Fa-f]{2})", encoded):
        raise StepFailed(f"The graph <{name}> is not percent-encoded as ENCODE_FOR_URI writes it.")
    try:
        return unquote(encoded, errors="strict")
    except UnicodeDecodeError:
        raise StepFailed(f"The graph <{name}> is not percent-encoded as ENCODE_FOR_URI writes it.") from None


# ---- the compile job


@dataclass(frozen=True)
class Scheme:
    """One compiled projection scheme the job holds, from its manifest."""

    key: str
    contract: str
    kind: str
    scheme: str
    compiled: Any


def read_job(job: Graph, job_iri: str) -> list[Scheme]:
    """The compiled schemes of the job in the order of their IRIs, or raises why the job cannot be run. The compiled forms are read back with
    `mork_rdf.from_rdf`, which refuses one whose queries no longer give its digest."""
    from mork_rdf import from_rdf

    node = URIRef(job_iri)
    if not ((node, CST.kind, CST.Compile) in job and (node, CST.target, CST.Surface) in job and (node, CST.status, CST.Succeeded) in job):
        raise StepFailed("The job is not a finished compilation of the surface part, so this step was not run.")
    held: dict[str, str] = {}
    for artefact in job.objects(node, CST.artefact):
        path, content = job.value(artefact, CST.path), job.value(artefact, CST.content)
        if path is not None and content is not None:
            held[str(path)] = str(content)
    if MANIFEST not in held:
        raise StepFailed(f"The job holds no compiled projection ({MANIFEST}), so this step was not run. Compile the surface part again, or add a projection.")
    try:
        manifest = json.loads(held[MANIFEST])
        entries = [(e["key"], e["contract"], e["kind"], e["scheme"], e["path"]) for e in manifest]
        if not all(isinstance(v, str) and v for entry in entries for v in entry):
            raise ValueError
    except (ValueError, KeyError, TypeError):
        raise StepFailed("The job's projection manifest could not be read, so this step was not run.") from None
    if not entries:
        raise StepFailed("The job's projection manifest lists no projection, so this step was not run.")
    out: dict[str, Scheme] = {}
    for key, contract, kind, scheme, path in entries:
        if path not in held:
            raise StepFailed(f"The projection manifest names the compiled form of {key}, which the job does not hold, so this step was not run.")
        if scheme in out:
            raise StepFailed(f"The projection manifest names the scheme of {key} more than once, so this step was not run.")
        try:
            compiled = from_rdf(Graph().parse(data=held[path], format="turtle"))
        except Exception as error:  # a form that cannot be read back, whatever the reason
            reason = (str(error).strip().splitlines() or [type(error).__name__])[0][:200]
            raise StepFailed(f"The compiled form of {key} could not be read: {reason}") from None
        if any(re.search(r"\bNOW\s*\(", query.text, re.IGNORECASE) for query in compiled.queries):
            raise StepFailed(f"A query of the projection {key} reads the clock, and a step reads none.")
        out[scheme] = Scheme(key, contract, kind, scheme, compiled)
    return [out[scheme] for scheme in sorted(out)]


# ---- running


def _lines(triples: Any) -> list[str]:
    """What a scheme wrote as N-Triples lines in the order of their UTF-8 bytes. A closure writes the blank nodes of an OWL list under labels
    Oxigraph draws at random, so a result with one gives its blank nodes the canonical labels of the graph they are in, which a repeat gives again
    (PRI-58). The triples are the same up to those labels."""
    from rdflib.compare import to_canonical_graph

    triples = list(triples)
    if any(isinstance(t.subject, ox.BlankNode) or isinstance(t.object, ox.BlankNode) for t in triples):
        graph = Graph().parse(data=ox.serialize(triples, format=ox.RdfFormat.N_TRIPLES).decode("utf-8"), format="nt")
        triples = list(ox.parse(to_canonical_graph(graph).serialize(format="nt").encode("utf-8"), format=ox.RdfFormat.N_TRIPLES))
    return sorted({f"{t.subject} {t.predicate} {t.object} ." for t in triples}, key=_bytes)


def _source(world: frozenset) -> ox.Dataset:
    """The triples of the world's graphs, merged, as the driver's source. The derived partitions the writer keeps are no source of a projection."""
    return ox.Dataset(q for q in world if not (isinstance(q.graph_name, ox.NamedNode) and q.graph_name.value.startswith(PROMOTED_PREFIX)))


def _severity(code: str) -> frames.Severity:
    return {"error": frames.Severity.VIOLATION, "warning": frames.Severity.WARNING}.get(code, frames.Severity.INFO)


def execute(job: Graph, job_iri: str, trig: str, run: str, engine: str, make_recorder: Callable[[], Recorder]) -> list[frames.Part]:
    """The parts of a projection step, in order, or raises why it cannot be run. For each compiled scheme ordered by its IRI, the rows before and
    after the edit as artefacts, and then the report of the driver's findings over the world after, the delta and the outcome. `make_recorder` gives
    each run of the driver the sink that collects what it writes, which stops the run at its deadline."""
    from mork_rdf import run as drive

    step = parse(trig)
    schemes = read_job(job, job_iri)
    before_world, after_world = _source(step.world), _source(step.after())
    parts: list[frames.Part] = []
    changes: list[dict[str, Any]] = []
    table: list[dict[str, Any]] = []
    findings: list[frames.Finding] = []
    for s in schemes:
        rows = []
        for world in (before_world, after_world):
            recorder = make_recorder()
            ran = drive(s.compiled, world, sink=recorder)
            written = [t for triples in recorder.out.values() for t in triples]
            rows.append((_lines(written), ran))
        (before, _), (after, ran_after) = rows
        parts.append(frames.Part("artefact", "application/trig", "".join(f"{line}\n" for line in before), s.key, f"{s.key}/rows-before.trig"))
        parts.append(frames.Part("artefact", "application/trig", "".join(f"{line}\n" for line in after), s.key, f"{s.key}/rows-after.trig"))
        asserted = sorted(set(after) - set(before), key=_bytes)
        retracted = sorted(set(before) - set(after), key=_bytes)
        changes.append({"contract": s.contract, "key": s.key, "graphs": [{"graph": None, "asserted": asserted, "retracted": retracted}] if asserted or retracted else []})
        table.append({"contract": s.contract, "key": s.key, "kind": s.kind, "scheme": s.scheme, "asserted": len(asserted), "retracted": len(retracted)})
        for f in ran_after.findings:
            message = f"{s.key}: {f.message} ({f.value})" if f.value else f"{s.key}: {f.message}"
            findings.append(frames.Finding(_severity(f.severity.value), message, f.code, f.focus))
    parts.append(frames.Part("report", "text/turtle", frames.report_turtle(run, frames.Result(findings=tuple(findings)))))
    parts.append(frames.Part("delta", "application/json", json.dumps({"contracts": changes}, indent=2, ensure_ascii=False) + "\n"))
    outcome = {"engine": engine, "sources": step.sources(), "contracts": table}
    parts.append(frames.Part("outcome", "application/json", json.dumps(outcome, indent=2, ensure_ascii=False) + "\n"))
    return parts
