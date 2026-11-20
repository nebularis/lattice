# SPDX-License-Identifier: MPL-2.0
"""A mapping's sample run over an RDF source, answered by the studio's Python worker (ADR-A154, addendum of 2026-11-20).

The run worker of the contract is two workers with one protocol. This is the one that runs `mork_rdf`'s driver, for a sample in Turtle or
N-Triples, from a queue of its own. `RdfRunWorker.handle` keeps every rule of a run the Java run worker keeps, in the same order:

1. the headers and the request are checked before anything is done (PRI-75), and a message that fails is refused without requeuing
2. a message the broker marks as redelivered is never run, and gets the failed frame saying a worker stopped, and is acknowledged
3. a run past its deadline is acknowledged and gets no frame, since the service sends the failed frame of a run that passed it
4. the run is stopped when it passes its deadline, and nothing more is published for it
5. the frames are published, confirmed, before the message is acknowledged
6. the store is read and never written

The compile job is read from the store and its compiled forms are run, `{scheme}.compiled.ttl`, which `mork_rdf.from_rdf` reads back as the
mapping they were made from, refusing one whose queries no longer give its digest. A run is a function of the compile job, as ADR-A154
decision 1 states, and needs neither the layers the compilation read nor a recompilation that could differ in what it reads or when.
The queries run with `mork_rdf.run` and the `Recorder` of the studio's dry run of a mapping, so a sample run and a dry run of the same
scheme over the same source write the same triples. The clock is an input (PRI-56), and the frames are built by `config_studio_run_frames`."""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Mapping, Optional, Protocol

import pyoxigraph as ox
from rdflib import Graph, URIRef
from rdflib.compare import to_canonical_graph

from . import config_studio_run_frames as frames
from .config_studio_jobs import CST, Recorder, mapping_artefact_path

LOG = logging.getLogger("lattice_workers.runs")

MAX_INPUT_BYTES = 5 * 1024 * 1024
RDF_SAMPLES = {"text/turtle": "turtle", "application/n-triples": "nt"}
_LABEL = {"turtle": "Turtle", "nt": "N-Triples"}
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_RUN_IRI = re.compile(rf"urn:lattice:studio:run:{_UUID}")
_JOB_IRI = re.compile(rf"urn:lattice:studio:job:{_UUID}")
# The pairs a run takes, as the service accepts them. This queue carries one of them.
_TARGETS = {"sample": {"mapping"}, "simulate": {"persistence", "surface"}}
_SEVERITY = {"error": frames.Severity.VIOLATION, "warning": frames.Severity.WARNING}


class Outcome(Enum):
    """What the queue's consumer does with a message once the handler has published what it publishes."""

    ACK = "ack"
    REJECT = "reject"
    REQUEUE = "requeue"


@dataclass(frozen=True)
class Message:
    """A delivery as the worker reads it, apart from the broker's types."""

    tag: int
    redelivered: bool
    headers: Mapping[str, Any]
    content_type: Optional[str]
    body: bytes

    def header(self, name: str) -> Optional[str]:
        """A header as text, or None when it is absent."""
        value = self.headers.get(name)
        if value is None:
            return None
        return value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value)


class FrameSink(Protocol):
    def publish(self, run: str, frames: list[str]) -> None:
        """Publishes the frames of one run, as JSON text, in order. Returns once the broker has confirmed them, and raises when it did not."""


class RunStopped(Exception):
    """A run passed its deadline and is abandoned at the next query it would write."""


class _StoppableRecorder(Recorder):
    """The dry run's `Recorder`, which also stops the run between two queries once the deadline has passed. Oxigraph cannot be interrupted
    in the middle of a query, so a query in hand finishes, and the run ends at the next write."""

    def __init__(self, stop: threading.Event) -> None:
        super().__init__()
        self._stop = stop

    def write(self, query, triples) -> None:  # type: ignore[no-untyped-def]
        if self._stop.is_set():
            raise RunStopped()
        super().write(query, triples)


@dataclass(frozen=True)
class _Request:
    run: str
    job: str
    deadline: datetime


class RdfRunWorker:
    """Handles the messages of the queue of RDF sample runs. `jobs` reads a job's graph from the store and raises when it cannot. `clock` gives
    the time as an aware `datetime`."""

    def __init__(self, jobs: Callable[[str], Graph], clock: Callable[[], datetime]) -> None:
        self._jobs = jobs
        self._clock = clock

    def handle(self, message: Message, sink: FrameSink) -> Outcome:
        try:
            request = self._read(message)
        except ValueError as error:
            # The reason names a header, never a value or the body.
            LOG.warning("rejected a run request: %s", error)
            return Outcome.REJECT
        if message.redelivered:
            return _publish(sink, request.run, frames.failed(request.run, "A worker stopped during the run, so run it again."))
        now = self._clock()
        if now >= request.deadline:
            # The service sends the failed frame of a run that passed its deadline.
            return Outcome.ACK
        media = (message.content_type or "").split(";", 1)[0].strip().lower()
        if media not in RDF_SAMPLES:
            return _publish(sink, request.run, frames.failed(
                request.run, "A sample that is not Turtle or N-Triples is run by the run worker, so this run went to the wrong worker and was not started."))
        if len(message.body) > MAX_INPUT_BYTES:
            return _publish(sink, request.run, frames.failed(request.run, "The sample is over 5 MiB, so this run was not started."))
        budget = (request.deadline - now).total_seconds()
        done = threading.Event()
        stop = threading.Event()
        held: dict[str, Any] = {}

        def execute() -> None:
            try:
                held["frames"] = self._execute(request, media, message.body, stop)
            except RunStopped:
                pass
            except BaseException as error:  # the run failed, which the author reads as a failed frame
                held["error"] = error
            finally:
                done.set()

        threading.Thread(target=execute, name="rdf-run-execution", daemon=True).start()
        if not done.wait(max(budget, 0.0)):
            stop.set()
            LOG.warning("a run passed its deadline and was stopped")
            return Outcome.ACK
        if "error" in held:
            LOG.error("a run failed", exc_info=held["error"])
            return _publish(sink, request.run, frames.failed(request.run, "The run failed, so run it again."))
        return _publish(sink, request.run, held["frames"])

    def _execute(self, request: _Request, media: str, body: bytes, stop: threading.Event) -> list[dict[str, Any]]:
        try:
            job = self._jobs(request.job)
        except Exception:
            LOG.warning("the compile job of a run could not be read", exc_info=True)
            return frames.failed(request.run, "The compile job could not be read, so this run was not started.")
        try:
            sample = body.decode("utf-8")
        except UnicodeDecodeError:
            return frames.failed(request.run, "The sample is not UTF-8 text, so this run was not started.")
        return frames.of(request.run, execute(job, request.job, media, sample, stop))

    @staticmethod
    def _read(message: Message) -> _Request:
        """Checks the headers as the service did. Raises a reason that names a header, never its value."""
        values = {name: message.header(name) for name in ("run", "job", "kind", "target", "deadline")}
        for name, value in values.items():
            if not value:
                raise ValueError(f"header {name} is missing")
        run, job, kind, target, deadline = (values[n] for n in ("run", "job", "kind", "target", "deadline"))
        assert run and job and kind and target and deadline
        if not _RUN_IRI.fullmatch(run):
            raise ValueError("header run is not a run IRI")
        if not _JOB_IRI.fullmatch(job):
            raise ValueError("header job is not a job IRI")
        if target not in _TARGETS.get(kind, set()):
            raise ValueError("headers kind and target are not a pair a run takes")
        if kind != "sample":
            raise ValueError("header kind is not one this queue carries")
        try:
            at = datetime.fromisoformat(deadline)
        except ValueError:
            raise ValueError("header deadline is not a dateTime with a time zone") from None
        if at.tzinfo is None:
            raise ValueError("header deadline is not a dateTime with a time zone")
        return _Request(run, job, at)


def _publish(sink: FrameSink, run: str, run_frames: list[dict[str, Any]]) -> Outcome:
    try:
        sink.publish(run, [frames.encode(f) for f in run_frames])
        return Outcome.ACK
    except Exception:
        # Not acknowledged, so the broker redelivers it and a worker then says the run was lost.
        LOG.warning("publishing the frames of a run failed", exc_info=True)
        return Outcome.REQUEUE


def execute(job: Graph, job_iri: str, media: str, sample: str, stop: Optional[threading.Event] = None) -> frames.Result:
    """Runs the compiled forms of the compile job `job_iri` over `sample`, and says what happened without telling it as frames. A scheme the job
    holds no compiled form of, since it reads another kind of source, is reported as information. `stop`, once set, ends the run at the next
    query it would write."""
    stop = stop if stop is not None else threading.Event()
    from mork_rdf import from_rdf, run

    syntax = RDF_SAMPLES.get(media.split(";", 1)[0].strip().lower())
    if syntax is None:
        return frames.Result(failure=f"a sample source is Turtle or N-Triples, not {media}")
    node = URIRef(job_iri)
    if not ((node, CST.kind, CST.Compile) in job and (node, CST.target, CST.Mapping) in job and (node, CST.status, CST.Succeeded) in job):
        return frames.Result(failure="the job is not a finished compilation of the mapping part")
    schemes: dict[str, dict[str, list[tuple[str, str]]]] = {}
    for artefact in job.objects(node, CST.artefact):
        group, path = job.value(artefact, CST.group), job.value(artefact, CST.path)
        if group is not None and path is not None:
            schemes.setdefault(str(group), {}).setdefault(str(path), []).append((str(job.value(artefact, CST.mediaType)), str(job.value(artefact, CST.content))))
    findings: list[frames.Finding] = []
    outputs: list[frames.Output] = []
    runnable = {scheme: forms for scheme, forms in sorted(schemes.items()) if any(p.endswith(".compiled.ttl") for p in forms)}
    for scheme in sorted(schemes):
        if scheme not in runnable:
            findings.append(frames.Finding(frames.Severity.INFO, f"{scheme} was not run, since it reads no RDF source", "NotRun", scheme))
    if not runnable:
        findings.append(frames.Finding(frames.Severity.INFO, "no scheme of the mapping part reads an RDF source", "NotRun"))
        return frames.Result(findings=tuple(findings), engine=engine())
    try:
        source = Graph().parse(data=sample, format=syntax)
    except Exception as error:
        reason = (str(error).strip().splitlines() or [type(error).__name__])[0][:200]
        return frames.Result(failure=f"the sample could not be read as {_LABEL[syntax]}: {reason}")
    for scheme, forms in runnable.items():
        path = sorted(p for p in forms if p.endswith(".compiled.ttl"))[0]
        _, text = sorted(forms[path])[0]
        try:
            compiled = from_rdf(Graph().parse(data=text, format="turtle"))
        except Exception as error:
            reason = (str(error).strip().splitlines() or [type(error).__name__])[0][:200]
            return frames.Result(failure=f"{scheme}: the compiled form could not be read: {reason}", findings=tuple(findings), outputs=tuple(outputs))
        for f in compiled.findings:
            findings.append(frames.Finding(_SEVERITY.get(f.severity.value, frames.Severity.INFO), f.message, f.code, f.mapping))
        recorder = _StoppableRecorder(stop)
        ran = run(compiled, source, sink=recorder)
        for f in ran.findings:
            findings.append(frames.Finding(frames.Severity.WARNING, f"{f.message} ({f.value})" if f.value else f.message, f.code, f.mapping))
        for (mapping, stratum), triples in sorted(recorder.out.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            outputs.append(frames.Output(mapping, stratum, mapping_artefact_path(mapping, stratum), ntriples(triples)))
    return frames.Result(findings=tuple(findings), outputs=tuple(outputs), engine=engine())


def engine() -> str:
    """What a sample run says evaluated the mapping: the driver and the store it runs on."""
    from importlib.metadata import version

    from mork_rdf import COMPILER

    return f"mork_rdf {COMPILER.rsplit(' ', 1)[-1]} on Oxigraph {version('pyoxigraph')}, in memory"


def ntriples(triples: Any) -> str:
    """What a mapping wrote as N-Triples, the lines in the order of their text, as the studio's dry run writes it. A closure writes the blank
    nodes of an OWL list under labels Oxigraph draws at random, so a run with one gives its blank nodes the canonical labels of the graph
    they are in, which a repeat gives again (PRI-58). The triples are the same up to those labels."""
    triples = list(triples)
    if any(isinstance(t.subject, ox.BlankNode) or isinstance(t.object, ox.BlankNode) for t in triples):
        graph = Graph().parse(data=ox.serialize(triples, format=ox.RdfFormat.N_TRIPLES).decode("utf-8"), format="nt")
        canonical = to_canonical_graph(graph).serialize(format="nt")
        triples = list(ox.parse(canonical.encode("utf-8"), format=ox.RdfFormat.N_TRIPLES))
    return ox.serialize(sorted(triples, key=str), format=ox.RdfFormat.N_TRIPLES).decode("utf-8")
