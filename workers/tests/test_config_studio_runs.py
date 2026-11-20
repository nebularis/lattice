"""The studio worker's sample run over an RDF source (ADR-A154, addendum of 2026-11-20), against a store that is in memory and a sink that is
scripted. The frames are held to `run-frame.schema.json` and to the shape of the contract's example frames, and the run's artefacts to what the
studio's dry run of the same mapping writes. A real broker is driven by `test/studio-integration/test_runs.py`."""

from __future__ import annotations

import json
import random
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import RDF, SH

from lattice_workers import config_studio_jobs as jobs
from lattice_workers import config_studio_run_frames as run_frames
from lattice_workers import config_studio_runs as runs
from lattice_workers.config_studio_jobs import CST
from lattice_workers.config_studio_runs import Message, Outcome, RdfRunWorker
from lattice_workers.fuseki_gsp import GraphNotFound

ROOT = jobs.find_root()
CONTRACT = ROOT / "contracts" / "config-studio"
ODRL = CONTRACT / "odrl"
SCHEMA = json.loads((CONTRACT / "run-frame.schema.json").read_text(encoding="utf-8"))
RUN = "urn:lattice:studio:run:3f2b8c1e-5a47-4d0e-9b1a-6c7d8e9f0a1b"
RUN_2 = "urn:lattice:studio:run:aaaaaaaa-5a47-4d0e-9b1a-6c7d8e9f0a1b"
JOB = "urn:lattice:studio:job:00000000-0000-4000-8000-000000000001"
SUBMITTED = "2026-11-20T10:00:00Z"
NOW = datetime(2026, 11, 20, 10, 5, tzinfo=timezone.utc)
SAMPLE = (ODRL / "trial" / "software-licence.ttl").read_text(encoding="utf-8")


def validate(frame: dict[str, Any]) -> None:
    jsonschema.validate(frame, SCHEMA, format_checker=jsonschema.FormatChecker())


def validate_run(frames: list[dict[str, Any]]) -> None:
    """Each frame holds against the schema, and the run is whole: `seq` counts from 0 with no gap, `last` is on the final frame only, the
    parts are numbered from 0 with no gap, and a frame with no part continues one."""
    for frame in frames:
        validate(frame)
    assert [f["seq"] for f in frames] == list(range(len(frames)))
    assert [f["last"] for f in frames] == [False] * (len(frames) - 1) + [True]
    assert [f["part"]["index"] for f in frames if "part" in f] == list(range(sum("part" in f for f in frames)))
    if len(frames) > 1:
        assert "part" in frames[0]


def parts(frames: list[dict[str, Any]]) -> list[tuple[dict[str, Any], str]]:
    """Each part with its text, the text of its frames joined in sequence order."""
    out: list[tuple[dict[str, Any], str]] = []
    for frame in frames:
        if "part" in frame:
            out.append((frame["part"], ""))
        if "text" in frame:
            part, text = out[-1]
            out[-1] = (part, text + frame["text"])
    return out


class Sink:
    def __init__(self) -> None:
        self.published: list[tuple[str, list[dict[str, Any]]]] = []
        self.fail = False
        self.log: list[str] = []

    def publish(self, run: str, frames: list[str]) -> None:
        if self.fail:
            raise OSError("the broker did not confirm")
        self.log.append(f"publish:{run}")
        self.published.append((run, [json.loads(f) for f in frames]))

    def frames(self, run: str = RUN) -> list[dict[str, Any]]:
        return [f for r, fs in self.published for f in fs if r == run]


def headers(run: str = RUN, job: str = JOB, kind: str = "sample", target: str = "mapping", deadline: datetime = NOW + timedelta(seconds=120)) -> dict:
    return {"run": run, "job": job, "kind": kind, "target": target, "deadline": deadline.isoformat().replace("+00:00", "Z")}


def message(body: str | bytes = SAMPLE, media: str | None = "text/turtle", tag: int = 1, redelivered: bool = False, **changes: Any) -> Message:
    h = headers()
    for name, value in changes.items():
        if value is None:
            h.pop(name, None)
        else:
            h[name] = value
    return Message(tag, redelivered, h, media, body if isinstance(body, bytes) else body.encode("utf-8"))


# ---- a compile job of the ODRL instrument, as the worker compiles and writes it -------------------------------------------------

def _configuration() -> Graph:
    return Graph().parse(ODRL / "odrl-instrument.mork.ttl")


def _compile_job(config: Graph, iri: str = JOB, finished: bool = True, kind=CST.Compile, target=CST.Mapping) -> Graph:
    job = URIRef(iri)
    graph = jobs.run_job(job, "compile", "mapping", config, Graph(), ROOT, SUBMITTED)
    graph.add((job, CST.kind, kind))
    graph.add((job, CST.target, target))
    if finished:
        graph.add((job, CST.status, CST.Succeeded))
    return graph


@pytest.fixture(scope="module")
def compile_job() -> Graph:
    return _compile_job(_configuration())


@pytest.fixture(scope="module")
def dry_run() -> Graph:
    """The studio's dry run of the same mapping over the same sample, which the sample run is held to."""
    config = _configuration()
    document = URIRef("urn:lattice:studio:ws:00000000-0000-0000-0000-000000000001:import/1")
    config.add((document, RDF.type, CST.ImportDocument))
    config.add((document, CST.documentContent, Literal(SAMPLE)))
    config.add((document, CST.documentMediaType, Literal("text/turtle")))
    return jobs.run_mapping(URIRef("urn:lattice:studio:job:00000000-0000-4000-8000-000000000002"), config, Graph(), str(ROOT), SUBMITTED)


def worker(job: Graph | None, reads: list[str] | None = None, now: datetime = NOW) -> RdfRunWorker:
    def read(iri: str) -> Graph:
        if reads is not None:
            reads.append(iri)
        if job is None:
            raise GraphNotFound(iri)
        return job

    return RdfRunWorker(read, lambda: now)


def run(job: Graph | None, msg: Message | None = None, **kwargs: Any) -> tuple[Outcome, Sink]:
    sink = Sink()
    return worker(job, **kwargs).handle(msg or message(), sink), sink


def artefacts(frames: list[dict[str, Any]]) -> dict[tuple[str, int], tuple[str, str]]:
    """What the run wrote, by mapping and stratum, with the path and the text."""
    return {(p["group"], p["step"]): (p["path"], text) for p, text in parts(frames) if p["role"] == "artefact"}


def dry_artefacts(job: Graph) -> dict[tuple[str, int], tuple[str, str]]:
    return {(str(job.value(a, CST.group)), int(job.value(a, CST.stratum))): (str(job.value(a, CST.path)), str(job.value(a, CST.content)))
            for a in job.subjects(RDF.type, CST.Artefact)}


# ---- equality with the dry run ----------------------------------------------------------------------------------------------------

def test_a_sample_run_writes_what_the_dry_run_of_the_same_mapping_writes(compile_job, dry_run):
    outcome, sink = run(compile_job)
    assert outcome is Outcome.ACK
    frames = sink.frames()
    validate_run(frames)
    assert frames[-1]["status"] == "succeeded"
    ran, dry = artefacts(frames), dry_artefacts(dry_run)
    assert dry, "the dry run wrote something"
    assert ran.keys() == dry.keys(), "the same mappings at the same strata"
    for key in dry:
        # Paths and lines are the dry run's. A blank node is named by its graph's canonical label here, so such an artefact is compared as a graph.
        assert ran[key][0] == dry[key][0], key
        if "_:" not in dry[key][1]:
            assert ran[key][1] == dry[key][1], key
        else:
            assert isomorphic(Graph().parse(data=ran[key][1], format="nt"), Graph().parse(data=dry[key][1], format="nt")), key
    assert len(ran) == len(list(dry_run.subjects(RDF.type, CST.Artefact))), "and no artefact more"


def test_the_artefacts_are_the_dry_run_s_triples_stratum_by_stratum(compile_job, dry_run):
    _, sink = run(compile_job)
    ran = artefacts(sink.frames())
    strata = sorted({step for _, step in ran})
    assert strata == sorted({step for _, step in dry_artefacts(dry_run)})
    for (group, step), (path, text) in ran.items():
        assert path == jobs.mapping_artefact_path(group, step)
        assert text == "".join(sorted(text.splitlines(keepends=True))) or "_:" in text, "N-Triples lines in code point order"


def test_the_report_names_no_violation_and_conforms_where_the_dry_run_does(compile_job, dry_run):
    _, sink = run(compile_job)
    frames = sink.frames()
    (part, text), *_ = parts(frames)
    assert part == {"index": 0, "role": "report", "mediaType": "text/turtle"}
    report = Graph().parse(data=text, format="turtle")
    (node,) = report.subjects(RDF.type, SH.ValidationReport)
    assert node == URIRef(f"{RUN}#report")
    conforms = report.value(node, SH.conforms) == Literal(True)
    assert conforms == (frames[-1]["conforms"] is True)
    assert conforms == (next(dry_run.objects(None, CST.conforms)) == Literal(True))


def test_the_report_names_mork_rdf_on_oxigraph_as_the_engine(compile_job):
    _, sink = run(compile_job)
    (_, text), *_ = parts(sink.frames())
    report = Graph().parse(data=text, format="turtle")
    engine = report.value(URIRef(f"{RUN}#report"), CST.engine)
    assert str(engine).startswith("mork_rdf ") and " on Oxigraph " in str(engine)
    assert str(engine) == runs.engine()


# ---- the shape of the contract's example frames --------------------------------------------------------------------------------

def test_the_frames_match_the_shape_of_the_contract_s_example_run(compile_job):
    example = json.loads((CONTRACT / "samples" / "run-frames.example.json").read_text(encoding="utf-8"))
    for frame in example:
        validate(frame)
    _, sink = run(compile_job)
    frames = sink.frames()

    def shape(fs: list[dict[str, Any]]) -> list[tuple]:
        return [(tuple(sorted(f)), tuple(sorted(f.get("part", {})))) for f in fs]

    # The first frame is a report part and the last a succeeded frame with conforms, as the example's are.
    assert shape(frames)[0] == shape(example)[0] == (("last", "part", "run", "seq", "text"), ("index", "mediaType", "role"))
    assert shape(frames)[-1] == shape(example)[-1]
    artefact = next(f for f in frames if f.get("part", {}).get("role") == "artefact")
    assert tuple(sorted(artefact["part"])) == tuple(sorted(example[1]["part"]))


def test_a_run_that_cannot_start_is_one_failed_frame_as_the_contract_s_example_is(compile_job):
    example = json.loads((CONTRACT / "samples" / "run-frames-failed.example.json").read_text(encoding="utf-8"))
    for case in (None, Graph()):
        outcome, sink = run(case)
        assert outcome is Outcome.ACK
        (frame,) = sink.frames()
        validate_run([frame])
        assert sorted(frame) == sorted(example[0]) and frame["seq"] == 0 and frame["last"] and frame["status"] == "failed"
    assert "could not be read" in run(None)[1].frames()[0]["message"]
    assert "not a finished compilation" in run(Graph())[1].frames()[0]["message"]


# ---- every rule of a run ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("change", [
    {"run": None}, {"job": None}, {"kind": None}, {"target": None}, {"deadline": None},
    {"run": "urn:lattice:studio:run:not-a-uuid"}, {"job": "urn:lattice:studio:job:not-a-uuid"}, {"job": "urn:lattice:studio:ws:" + "0" * 8 + "-0000-4000-8000-000000000001"},
    {"deadline": "tomorrow"}, {"deadline": "2026-11-20T10:07:00"}, {"kind": "simulate", "target": "persistence"},
    {"kind": "sample", "target": "persistence"}, {"kind": "other", "target": "mapping"}, {"run": ""},
])
def test_a_message_that_fails_the_checks_is_refused_without_requeuing_and_nothing_is_published_or_read(compile_job, change):
    reads: list[str] = []
    outcome, sink = run(compile_job, message(**change), reads=reads)
    assert outcome is Outcome.REJECT
    assert sink.published == [] and reads == []


def test_a_redelivered_run_gets_the_failed_frame_a_worker_stopped_says_and_is_acknowledged_and_never_run(compile_job):
    reads: list[str] = []
    outcome, sink = run(compile_job, message(redelivered=True), reads=reads)
    assert outcome is Outcome.ACK
    (frame,) = sink.frames()
    validate_run([frame])
    assert frame["status"] == "failed" and "worker stopped" in frame["message"] and "run it again" in frame["message"]
    assert reads == [], "a redelivered run is never run"


def test_a_redelivered_run_gets_the_same_failed_frame_the_java_run_worker_sends():
    java = (ROOT / "platform" / "config-studio-transforms" / "src" / "main" / "java" / "org" / "nebularis" / "lattice" / "studio" / "transforms" / "RunWorker.java").read_text(encoding="utf-8")
    _, sink = run(None, message(redelivered=True))
    assert f'"{sink.frames()[0]["message"]}"' in java


def test_a_run_past_its_deadline_is_acknowledged_and_gets_no_frame_and_is_not_run(compile_job):
    reads: list[str] = []
    for now in (NOW + timedelta(seconds=120), NOW + timedelta(seconds=500)):
        sink = Sink()
        outcome = worker(compile_job, reads, now).handle(message(), sink)
        assert outcome is Outcome.ACK and sink.published == []
    assert reads == []


def test_a_run_that_passes_its_deadline_is_stopped_and_publishes_nothing(compile_job, monkeypatch):
    started = threading.Event()
    stopped = threading.Event()

    def slow(job, job_iri, media, sample, stop=None):  # the engine does not return until the run is stopped
        started.set()
        while not stop.is_set():
            time.sleep(0.01)
        stopped.set()
        raise runs.RunStopped()

    monkeypatch.setattr(runs, "execute", slow)
    now = [NOW]
    clock = lambda: now[0]
    sink = Sink()
    w = RdfRunWorker(lambda iri: compile_job, clock)
    # The clock is fixed, so the budget is the 0.3 seconds between it and the deadline.
    msg = Message(1, False, headers(deadline=NOW + timedelta(milliseconds=300)), "text/turtle", SAMPLE.encode("utf-8"))
    outcome = w.handle(msg, sink)
    assert started.is_set() and outcome is Outcome.ACK and sink.published == []
    assert stopped.wait(5), "the run was told to stop"


def test_a_stopped_run_ends_at_the_next_query_it_would_write(compile_job):
    stop = threading.Event()
    stop.set()
    with pytest.raises(runs.RunStopped):
        runs.execute(compile_job, JOB, "text/turtle", SAMPLE, stop)


def test_frames_are_published_before_the_message_is_acknowledged(compile_job):
    sink = Sink()
    outcome = worker(compile_job).handle(message(), sink)
    assert sink.log == [f"publish:{RUN}"] and outcome is Outcome.ACK, "the outcome, which the consumer acts on, comes after the publish"


def test_a_publish_the_broker_did_not_confirm_leaves_the_message_unacknowledged_for_redelivery(compile_job):
    sink = Sink()
    sink.fail = True
    assert worker(compile_job).handle(message(), sink) is Outcome.REQUEUE


@pytest.mark.parametrize("media", ["application/xml", "text/xml", "application/json", "application/trig", None, ""])
def test_a_sample_that_is_not_rdf_is_failed_as_a_run_that_went_to_the_wrong_worker(compile_job, media):
    outcome, sink = run(compile_job, message(media=media))
    assert outcome is Outcome.ACK
    (frame,) = sink.frames()
    validate_run([frame])
    assert frame["status"] == "failed" and "wrong worker" in frame["message"]


def test_media_types_with_parameters_and_case_are_read_as_the_service_reads_them(compile_job):
    for media in ("Text/Turtle; charset=utf-8", "application/n-triples;charset=UTF-8"):
        body = SAMPLE if "turtle" in media.lower() else "<urn:a> <urn:b> <urn:c> .\n"
        _, sink = run(compile_job, message(body=body, media=media))
        assert sink.frames()[-1]["status"] == "succeeded", media


def test_a_sample_over_5_mib_is_one_failed_frame_and_the_job_is_not_read(compile_job):
    reads: list[str] = []
    _, sink = run(compile_job, message(body=b"#" * (5 * 1024 * 1024 + 1)), reads=reads)
    (frame,) = sink.frames()
    assert frame["status"] == "failed" and "5 MiB" in frame["message"] and reads == []


@pytest.mark.parametrize("body, media, said", [
    ("this is not turtle {", "text/turtle", "could not be read as Turtle"),
    ("<urn:a> <urn:b> .", "application/n-triples", "could not be read as N-Triples"),
    (b"\xff\xfe\x00", "text/turtle", "not UTF-8"),
])
def test_a_sample_that_cannot_be_parsed_is_one_failed_frame_that_does_not_quote_it(compile_job, body, media, said):
    _, sink = run(compile_job, message(body=body, media=media))
    (frame,) = sink.frames()
    validate_run([frame])
    assert frame["status"] == "failed" and said in frame["message"]


@pytest.mark.parametrize("kind, target, status", [
    (CST.Compile, CST.Persistence, True), (CST.Validate, CST.Mapping, True), (CST.Compile, CST.Mapping, False),
])
def test_a_job_that_is_not_a_finished_compilation_of_the_mapping_part_fails_the_run(kind, target, status):
    job = _compile_job(_configuration(), finished=status, kind=kind, target=target)
    _, sink = run(job)
    (frame,) = sink.frames()
    assert frame["status"] == "failed" and "not a finished compilation of the mapping part" in frame["message"]


def test_a_compiled_form_whose_queries_were_changed_is_refused_and_the_run_fails(compile_job):
    changed = Graph() + compile_job
    for artefact in list(changed.objects(URIRef(JOB), CST.artefact)):
        if str(changed.value(artefact, CST.path)).endswith(".compiled.ttl"):
            text = str(changed.value(artefact, CST.content)).replace("CONSTRUCT", "CONSTRUCT ", 1)
            changed.set((artefact, CST.content, Literal(text)))
    _, sink = run(changed)
    (frame,) = sink.frames()
    assert frame["status"] == "failed" and "compiled form could not be read" in frame["message"]


def test_a_scheme_with_no_compiled_form_is_reported_as_not_run_and_a_job_with_none_runs_nothing():
    job = Graph() + _compile_job(_configuration())
    for artefact in list(job.objects(URIRef(JOB), CST.artefact)):
        if str(job.value(artefact, CST.path)).endswith(".compiled.ttl"):
            job.remove((URIRef(JOB), CST.artefact, artefact))
            job.remove((artefact, None, None))
    _, sink = run(job)
    frames = sink.frames()
    validate_run(frames)
    assert frames[-1]["status"] == "succeeded" and not artefacts(frames)
    (_, text), = parts(frames)
    assert "NotRun" in text and "reads no RDF source" in text


# ---- determinism (PRI-58) -----------------------------------------------------------------------------------------------------

def test_a_repeat_gives_the_same_frames(compile_job):
    assert run(compile_job)[1].frames() == run(compile_job)[1].frames()


def test_the_triples_of_the_sample_in_another_order_give_the_same_frames(compile_job):
    lines = [line for line in Graph().parse(data=SAMPLE, format="turtle").serialize(format="nt").splitlines() if line.strip()]
    first = run(compile_job, message(body="\n".join(lines) + "\n", media="application/n-triples"))[1].frames()
    random.Random(7).shuffle(lines)
    second = run(compile_job, message(body="\n".join(lines) + "\n", media="application/n-triples"))[1].frames()
    other = list(reversed(lines))
    third = run(compile_job, message(body="\n".join(other) + "\n", media="application/n-triples"))[1].frames()
    assert first == second == third
    assert first == run(compile_job)[1].frames(), "and the same as the Turtle the lines came from"


def test_blank_nodes_a_closure_writes_are_named_by_the_graph_and_not_by_chance():
    import pyoxigraph as ox

    def members() -> list:
        first, rest, nil = (ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#" + n) for n in ("first", "rest", "nil"))
        a, b = ox.BlankNode(), ox.BlankNode()
        return [ox.Triple(ox.NamedNode("urn:p"), ox.NamedNode("urn:axiom"), a), ox.Triple(a, first, ox.NamedNode("urn:m1")), ox.Triple(a, rest, b),
                ox.Triple(b, first, ox.NamedNode("urn:m2")), ox.Triple(b, rest, nil)]

    one, two = runs.ntriples(members()), runs.ntriples(reversed(members()))
    assert one == two and "_:" in one
    assert isomorphic(Graph().parse(data=one, format="nt"), Graph().parse(data=ox.serialize(members(), format=ox.RdfFormat.N_TRIPLES).decode(), format="nt"))


# ---- the frames' own rules, alone --------------------------------------------------------------------------------------------------

def result_of(*texts: str, findings: tuple = ()) -> run_frames.Result:
    outputs = tuple(run_frames.Output(f"urn:m{i}", 0, f"0/m{i}.nt", t) for i, t in enumerate(texts))
    return run_frames.Result(findings=findings, outputs=outputs)


def test_a_part_is_cut_at_the_frame_bound_never_inside_a_character_and_the_pieces_join_to_the_text():
    text = "é" * 30_000 + "x" + "𝄞" * 20_000
    pieces = run_frames.cut(text)
    assert "".join(pieces) == text and len(pieces) == 3
    assert all(len(p.encode("utf-8")) <= run_frames.MAX_TEXT_BYTES for p in pieces)
    assert run_frames.cut("") == [""]
    frames = run_frames.of(RUN, result_of(text))
    validate_run(frames)
    assert parts(frames)[1][1] == text
    assert [f.get("more") for f in frames if "part" not in f or f["part"]["role"] == "artefact"][:3] == [True, True, None]


def test_the_frame_texts_are_at_most_49152_bytes_whatever_the_result():
    frames = run_frames.of(RUN, result_of("<urn:a> <urn:b> <urn:c> .\n" * 5_000))
    validate_run(frames)
    assert all(len(f.get("text", "").encode("utf-8")) <= 49_152 for f in frames)


def test_a_result_that_needs_more_than_128_frames_is_one_failed_frame_that_says_so():
    over = result_of("x" * (run_frames.MAX_TEXT_BYTES * 130))
    (frame,) = run_frames.of(RUN, over)
    validate_run([frame])
    assert frame["status"] == "failed" and frame["seq"] == 0 and frame["last"] and "too large" in frame["message"] and "narrow" in frame["message"]


def test_a_result_of_exactly_128_frames_is_sent_and_one_of_129_fails():
    # The report is one frame and the last another, so 126 frames of an artefact fill the run.
    fits = run_frames.of(RUN, result_of("x" * (run_frames.MAX_TEXT_BYTES * 126)))
    assert len(fits) == 128 and fits[-1]["seq"] == 127 and fits[-1]["status"] == "succeeded"
    validate_run(fits)
    (fails,) = run_frames.of(RUN, result_of("x" * (run_frames.MAX_TEXT_BYTES * 126 + 1)))
    assert fails["status"] == "failed"


def test_a_failure_of_the_result_is_one_failed_frame():
    (frame,) = run_frames.of(RUN, run_frames.Result(failure="the sample could not be read"))
    validate_run([frame])
    assert frame == {"run": RUN, "seq": 0, "last": True, "status": "failed", "message": "the sample could not be read"}


def test_the_report_is_valid_turtle_in_a_fixed_order_and_says_what_each_finding_is():
    findings = (
        run_frames.Finding(run_frames.Severity.WARNING, 'a "quoted"\nvalue \\ here', "UnmappedValue", "https://example.org/m#a"),
        run_frames.Finding(run_frames.Severity.INFO, "nothing was lost", "NotRun"),
        run_frames.Finding(run_frames.Severity.VIOLATION, "it failed", "Failed", "https://example.org/m#b"),
    )
    result = run_frames.Result(findings=findings)
    text = run_frames.report_turtle(RUN, result)
    assert text == run_frames.report_turtle(RUN, result)
    g = Graph().parse(data=text, format="turtle")
    assert len(list(g.subjects(RDF.type, SH.ValidationResult))) == 3
    assert (URIRef(f"{RUN}#report"), SH.conforms, Literal(False)) in g
    assert (URIRef(f"{RUN}#result-1"), SH.resultMessage, Literal('a "quoted"\nvalue \\ here')) in g
    assert (URIRef(f"{RUN}#result-1"), SH.resultSeverity, SH.Warning) in g
    assert (URIRef(f"{RUN}#result-2"), SH.focusNode, None) not in g
    assert run_frames.of(RUN, result)[-1]["conforms"] is False


def test_outputs_are_sent_in_the_order_of_their_mapping_step_and_path_whatever_order_they_are_given():
    a = run_frames.Output("urn:a", 1, "1/a.nt", "<urn:s> <urn:p> <urn:o> .\n")
    b = run_frames.Output("urn:a", 0, "0/a.nt", "<urn:s> <urn:p> <urn:o> .\n")
    c = run_frames.Output("urn:b", 0, "0/b.nt", "<urn:s> <urn:p> <urn:o> .\n")
    one = run_frames.of(RUN, run_frames.Result(outputs=(a, b, c)))
    two = run_frames.of(RUN, run_frames.Result(outputs=(c, a, b)))
    assert one == two
    assert [(p["group"], p["step"]) for p, _ in parts(one)[1:]] == [("urn:a", 0), ("urn:a", 1), ("urn:b", 0)]


def test_frames_encode_as_compact_json_that_reads_back():
    frame = run_frames.failed(RUN, "naïve")[0]
    assert json.loads(run_frames.encode(frame)) == frame and "\n" not in run_frames.encode(frame) and "naïve" in run_frames.encode(frame)


# ---- a mapping with strata and a closure, held to the driver the dry run uses ----------------------------------------------------

_MM, _SRC, _TGT, _REC, _BASE = ("http://example.org/mapping#", "http://example.org/src#", "http://example.org/tgt#", "http://example.org/records/", "http://example.org/out/")
_STRATIFIED = f"""@prefix mork: <http://www.nebularis.org/ontologies/Mork#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> . @prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix mm: <{_MM}> . @prefix src: <{_SRC}> . @prefix tgt: <{_TGT}> .
mm:S a mork:MappingScheme ; sh:declare [ sh:prefix "src" ; sh:namespace "{_SRC}"^^xsd:anyURI ] .
src:Thing a mork:Entity . mm:C a mork:DataConcept ; mork:representedAs src:Thing .
mm:Root a mork:Datum ; mork:mappingScheme mm:S ; mork:mappingFor mm:C ; mork:exactTBoxMatch tgt:Thing .
src:Species a mork:Entity . mm:SC a mork:DataConcept ; mork:representedAs src:Species .
src:Animal a mork:Entity . mm:AC a mork:DataConcept ; mork:representedAs src:Animal .
mm:GenSpecies a mork:DataMapping ; mork:mappingScheme mm:S ; mork:mappingFor mm:SC ; mork:broadTBoxCategoryMatch tgt:Animal ;
    mork:conceptNameTemplate "${{src:name}}" .
mm:Yield_Species a mork:DeferredContext ; mork:mappingScheme mm:S ; mork:yieldConcept mm:GenSpecies .
mm:Animal a mork:Datum ; mork:mappingScheme mm:S ; mork:mappingFor mm:AC ; mork:conceptName "animal" ;
    mork:exactTBoxMatch tgt:Animal ; mork:referenceDataMapping mm:AnimalSpecies .
mm:AnimalSpecies a mork:Lookup ; mork:mappingScheme mm:S ; mork:exactRBoxMatch rdf:type ;
    mork:exactTBoxMatch mm:Yield_Species ; mork:dataRef "src:species" ; mork:dataInline "" .
mm:Knows a mork:DataMapping ; mork:mappingScheme mm:S ; mork:broadRBoxCategoryMatch owl:topObjectProperty ;
    mork:conceptName "#knows" ; mork:assertsPropertyDomains mm:Yield_Species , tgt:A .
"""
_STRATIFIED_SOURCE = f"""<{_REC}s1> a <{_SRC}Species> ; <{_SRC}name> "Falcon" . <{_REC}s2> a <{_SRC}Species> ; <{_SRC}name> "Owl" .
<{_REC}a7> a <{_SRC}Animal> ; <{_SRC}species> "Falcon" . <{_REC}a8> a <{_SRC}Animal> ; <{_SRC}species> "Dodo" .
<{_REC}t> a <{_SRC}Thing> ."""


def test_a_mapping_with_strata_and_a_closure_writes_what_the_driver_the_dry_run_uses_writes_stratum_by_stratum():
    from mork_rdf import compile_scheme, run as drive, to_rdf

    compiled = compile_scheme(Graph().parse(data=_STRATIFIED, format="turtle"), _MM + "S", base=_BASE, at=datetime(2026, 10, 29, tzinfo=timezone.utc))
    assert compiled.strata == 2 and compiled.closures
    job = Graph()
    node = URIRef(JOB)
    for triple in ((node, CST.kind, CST.Compile), (node, CST.target, CST.Mapping), (node, CST.status, CST.Succeeded)):
        job.add(triple)
    artefact = URIRef(JOB + "#artefact-1")
    for triple in ((node, CST.artefact, artefact), (artefact, CST.path, Literal("S.compiled.ttl")), (artefact, CST.mediaType, Literal("text/turtle")),
                   (artefact, CST.group, Literal(compiled.scheme)), (artefact, CST.content, Literal(to_rdf(compiled).serialize(format="turtle")))):
        job.add(triple)
    # What the dry run does with a compiled scheme, as its own code does it.
    recorder = jobs.Recorder()
    ran = drive(compiled, Graph().parse(data=_STRATIFIED_SOURCE, format="turtle"), sink=recorder)
    result = runs.execute(job, JOB, "text/turtle", _STRATIFIED_SOURCE)
    assert result.failure is None
    assert {(o.group, o.step) for o in result.outputs} == set(recorder.out), "the same mappings at the same strata"
    assert {step for _, step in recorder.out} == {0, 1}
    blank = False
    for output in result.outputs:
        expected = recorder.out[(output.group, output.step)]
        assert output.path == jobs.mapping_artefact_path(output.group, output.step)
        mine = Graph().parse(data=output.ntriples, format="nt")
        import pyoxigraph as ox

        theirs = Graph().parse(data=ox.serialize(sorted(expected, key=str), format=ox.RdfFormat.N_TRIPLES).decode("utf-8"), format="nt")
        assert isomorphic(mine, theirs), (output.group, output.step)
        blank = blank or "_:" in output.ntriples
    assert blank, "a closure of two classes wrote an OWL list of blank nodes"
    # The report holds the compiler's findings, as a dry run's does, and then the run's checks.
    from collections import Counter

    reported = Counter((f.code, f.focus or "") for f in result.findings)
    compiler = Counter((f.code, f.mapping or "") for f in compiled.findings)
    assert compiler and reported - compiler == Counter((f.code, f.mapping or "") for f in ran.findings)
    assert [f.code for f in result.findings][:len(compiled.findings)] == [f.code for f in compiled.findings], "the compiler's first"
    # And the frames are the same again, blank nodes included (PRI-58).
    again = runs.execute(job, JOB, "text/turtle", _STRATIFIED_SOURCE)
    assert run_frames.of(RUN, result) == run_frames.of(RUN, again)


def test_a_deadline_with_the_nanoseconds_java_writes_an_instant_with_is_read(compile_job):
    stamp = (NOW + timedelta(seconds=60)).strftime("%Y-%m-%dT%H:%M:%S") + ".123456789Z"
    outcome, sink = run(compile_job, message(deadline=stamp))
    assert outcome is Outcome.ACK and sink.frames()[-1]["status"] == "succeeded"
