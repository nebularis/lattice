"""The surface compile job's projections and the projection step, a run of its own (contracts/config-studio/README.md, "A projection step"), over the files of
the facility sample. The compile of the sample and its run over `facility-surface-step-projection.trig` are pinned here. The frames are held to
`run-frame.schema.json`, and what a scheme wrote after the edit to the compiled form run by `mork_rdf`'s driver over the world after, which the test computes
with rdflib and not with the worker's own code."""

from __future__ import annotations

import json
import random
import threading
import time
from datetime import datetime, timedelta, timezone

import pyoxigraph as ox
import pytest
from rdflib import Dataset, Graph, Literal, URIRef
from rdflib.namespace import RDF, SH

from lattice_workers import config_studio_jobs as jobs
from lattice_workers import config_studio_projection_step as step
from lattice_workers import config_studio_projections as projections
from lattice_workers import config_studio_run_frames as run_frames
from lattice_workers import config_studio_runs as runs
from lattice_workers.config_studio_jobs import CST
from lattice_workers.config_studio_runs import Message, Outcome, RdfRunWorker
from test_config_studio_facility_sample import BASELINE_FILES, JOB, PARTS, ROOT, SAMPLES, SUBMITTED, load, sample_part
from test_config_studio_runs import NOW, RUN, Sink, headers, parts, validate_run
from test_config_studio_worker import artefacts as job_artefacts, results

STEP_FILE = SAMPLES / "facility-surface-step-projection.trig"
KEYS = ["borrower-exposure", "drawdown-schedule", "facility-branch", "facility-covenant-test", "facility-margin", "facility-refinancing"]


def sample_config() -> Graph:
    config = Graph()
    for part in PARTS:
        config += sample_part(part)
    return config


@pytest.fixture(scope="module")
def compiled_job() -> Graph:
    """The compile job of the facility sample's surface part, finished, as the worker writes it."""
    graph = jobs.run_job(JOB, "compile", "surface", sample_config(), load(*BASELINE_FILES), ROOT, SUBMITTED)
    for triple in ((JOB, CST.kind, CST.Compile), (JOB, CST.target, CST.Surface), (JOB, CST.status, CST.Succeeded)):
        graph.add(triple)
    return graph


# ---- the compile job holds each projection ------------------------------------------------------------------------------------------


def test_the_compile_job_holds_a_compiled_form_for_each_projection_and_a_manifest_that_names_them(compiled_job):
    held = job_artefacts(compiled_job, JOB)
    entries = json.loads(held[projections.MANIFEST][1])
    assert [e["key"] for e in entries] == sorted((e["key"] for e in entries), key=lambda k: next(x["scheme"] for x in entries if x["key"] == k)), "ordered by scheme"
    assert sorted(e["key"] for e in entries) == KEYS
    assert held[projections.MANIFEST][0::2] == ("application/json", projections.PROJECTIONS)
    for entry in entries:
        media, text, group = held[entry["path"]]
        assert (media, group) == ("text/turtle", projections.PROJECTIONS) and entry["path"].endswith(".compiled.ttl")
        assert entry["path"] == f"projections/{projections.artefact_name(entry['scheme'])}.compiled.ttl"
        from mork_rdf import from_rdf

        assert from_rdf(Graph().parse(data=text, format="turtle")).scheme == entry["scheme"]
    assert {path for path in held if path.startswith("projections/")} == {e["path"] for e in entries} | {e["mork"] for e in entries} | {projections.MANIFEST}


def test_the_manifest_names_each_lowered_scheme_and_the_file_is_the_graph_the_lowering_produced(compiled_job):
    """Beside each compiled form the job holds the scheme the lowering made, before compilation, which the read only mapping canvas draws its terms
    from. The test lowers each contract itself and compares the graphs, and reads the scheme back from the file."""
    from rdflib.compare import isomorphic
    from surface.lowering import lower_projection
    from surface.model import read_projection_contracts

    held = job_artefacts(compiled_job, JOB)
    entries = json.loads(held[projections.MANIFEST][1])
    contracts = {str(c.iri): c for c in read_projection_contracts(sample_config() + load(*BASELINE_FILES))}
    for entry in entries:
        assert entry["mork"] == f"projections/{projections.artefact_name(entry['scheme'])}.mork.ttl"
        media, text, group = held[entry["mork"]]
        assert (media, group) == ("text/turtle", projections.PROJECTIONS)
        file = Graph().parse(data=text, format="turtle")
        assert isomorphic(file, lower_projection(contracts[entry["contract"]]))
        assert (URIRef(entry["scheme"]), RDF.type, URIRef("http://www.nebularis.org/ontologies/Mork#MappingScheme")) in file


def test_the_review_findings_are_warnings_on_the_contract_each_kind_asks(compiled_job):
    config = sample_config()
    from surface.model import read_projection_contracts

    keys = {c.iri: c.key for c in read_projection_contracts(config)}
    got: dict[str, list[tuple[str, str]]] = {k: [] for k in KEYS}
    for severity in (SH.Violation, SH.Warning, SH.Info):
        for result in results(compiled_job, JOB, severity):
            focus = compiled_job.value(result, SH.focusNode)
            if focus in keys:
                got[keys[focus]].append((str(compiled_job.value(result, CST.code)), str(severity).rsplit("#", 1)[-1]))
    assert {k: sorted(v) for k, v in got.items()} == {
        "borrower-exposure": [("MappingReview", "Warning")],
        "drawdown-schedule": [],
        "facility-branch": [("MappingReview", "Warning")],
        "facility-covenant-test": [("ExpansionReview", "Warning"), ("MappingReview", "Warning")],
        "facility-margin": [("DerivationReview", "Warning")],
        "facility-refinancing": [("ExpansionReview", "Warning")],
    }
    assert compiled_job.value(JOB, CST.conforms) == Literal(True)


def test_a_job_with_no_projection_is_what_it_was_and_holds_nothing_of_a_projection(monkeypatch):
    """The job of a configuration with no projection is the graph the promotions and indexes give, so a run of the projection step over it is refused."""
    config = Graph().parse(jobs.catalogue().module("surface").directory("examples") / "clinical-trial-crosswalk.ttl", format="turtle")
    baseline = Graph()
    with_step = jobs.run_job(JOB, "compile", "surface", config, baseline, ROOT, SUBMITTED)
    monkeypatch.setattr(jobs, "_compile_projections", lambda *args: False)
    without = jobs.run_job(JOB, "compile", "surface", config, baseline, ROOT, SUBMITTED)
    assert not any(path.startswith("projections/") for path in job_artefacts(with_step, JOB))
    assert sorted(with_step.serialize(format="nt").splitlines()) == sorted(without.serialize(format="nt").splitlines())


def test_a_projection_that_cannot_be_compiled_is_a_violation_that_names_the_contract(monkeypatch):
    """Whatever refuses the lowering or the compile, the job fails and the violation names the projection's contract."""
    import mork_rdf

    def refuse(*args, **kwargs):
        raise mork_rdf.CompileError("the scheme was refused", ())

    monkeypatch.setattr(mork_rdf, "compile_scheme", refuse)
    job = jobs.run_job(JOB, "compile", "surface", sample_config(), load(*BASELINE_FILES), ROOT, SUBMITTED)
    assert job.value(JOB, CST.conforms) == Literal(False)
    violations = results(job, JOB, SH.Violation)
    assert {str(job.value(r, CST.code)) for r in violations} == {"ProjectionRefused"}
    focus = {str(job.value(r, SH.focusNode)).rsplit("#", 1)[-1] for r in violations}
    assert focus == {f"{k}-projection" for k in KEYS}
    assert not any(path.startswith("projections/") for path in job_artefacts(job, JOB))


def test_the_compile_is_a_function_of_the_configuration_so_a_repeat_gives_the_same_forms(compiled_job):
    again = jobs.run_job(JOB, "compile", "surface", sample_config(), load(*BASELINE_FILES), ROOT, SUBMITTED)
    held, now = job_artefacts(compiled_job, JOB), job_artefacts(again, JOB)
    assert {p: v for p, v in held.items() if p.startswith("projections/")} == {p: v for p, v in now.items() if p.startswith("projections/")}


# ---- the step ----------------------------------------------------------------------------------------------------------------


def world_after(trig: str) -> Graph:
    """The world after the edit, merged, as rdflib reads it, which is how the test computes what the driver is given and never the worker's code."""
    dataset = Dataset()
    dataset.parse(data=trig, format="trig")
    world, added, removed = Graph(), [], []
    for graph in dataset.graphs():
        name = str(graph.identifier)
        if name.startswith("urn:lattice:studio:step/added"):
            added.append(graph)
        elif name.startswith("urn:lattice:studio:step/removed"):
            removed.append(graph)
        elif name != "urn:lattice:studio:step" and not name.startswith("urn:lattice:studio:promoted:"):
            world += graph
    for graph in removed:
        for triple in graph:
            world.remove(triple)
    for graph in added:
        world += graph
    return world


def expected_rows(compiled_job: Graph, key: str, world: Graph) -> list[str]:
    """What the scheme's compiled form, read back from the job, writes over `world` when `mork_rdf`'s driver runs it, as lines in byte order."""
    from mork_rdf import GraphSink, from_rdf, run

    entry = next(e for e in json.loads(job_artefacts(compiled_job, JOB)[projections.MANIFEST][1]) if e["key"] == key)
    compiled = from_rdf(Graph().parse(data=job_artefacts(compiled_job, JOB)[entry["path"]][1], format="turtle"))
    sink = GraphSink()
    run(compiled, world, sink=sink)
    lines = {line for g in (sink.graph, sink.tbox) for line in g.serialize(format="nt").splitlines() if line}
    return sorted(lines, key=lambda line: line.encode("utf-8"))


def run_step(compiled_job: Graph, trig: str, **changes) -> tuple[Outcome, Sink]:
    sink = Sink()
    worker = RdfRunWorker(lambda iri: compiled_job, lambda: NOW)
    h = headers(job=str(JOB), kind="simulate", target="projection", deadline=NOW + timedelta(seconds=15))
    h.update(changes)
    msg = Message(1, False, h, "application/trig", trig.encode("utf-8"))
    return worker.handle(msg, sink), sink


@pytest.fixture(scope="module")
def sample_step(compiled_job):
    trig = STEP_FILE.read_text(encoding="utf-8")
    outcome, sink = run_step(compiled_job, trig)
    assert outcome is Outcome.ACK
    return trig, sink.frames()


def test_a_step_over_the_sample_gives_the_parts_in_the_contract_s_order(sample_step):
    _, frames = sample_step
    validate_run(frames)
    assert frames[-1]["status"] == "succeeded" and "conforms" not in frames[-1]
    got = [(p["role"], p.get("path"), p.get("group"), p["mediaType"]) for p, _ in parts(frames)]
    # Each scheme in the order of its IRI, before and then after, and then the report, the delta and the outcome.
    schemes = sorted(((f"scheme_{k}", k) for k in KEYS))
    want = [("artefact", f"{k}/rows-{when}.trig", k, "application/trig") for _, k in schemes for when in ("before", "after")]
    assert got == want + [("report", None, None, "text/turtle"), ("delta", None, None, "application/json"), ("outcome", None, None, "application/json")]


def test_the_rows_after_are_the_compiled_form_run_by_the_driver_over_the_world_after(sample_step, compiled_job):
    trig, frames = sample_step
    after, before = world_after(trig), None
    by_path = {p["path"]: text for p, text in parts(frames) if p["role"] == "artefact"}
    for key in KEYS:
        assert by_path[f"{key}/rows-after.trig"].splitlines() == expected_rows(compiled_job, key, after), key
        assert by_path[f"{key}/rows-after.trig"].encode("utf-8") == "".join(f"{line}\n" for line in sorted(by_path[f"{key}/rows-after.trig"].splitlines(), key=lambda l: l.encode("utf-8"))).encode("utf-8")
    before = Graph()
    dataset = Dataset()
    dataset.parse(data=trig, format="trig")
    for graph in dataset.graphs():
        name = str(graph.identifier)
        if not name.startswith("urn:lattice:studio:step"):
            before += graph
    for key in KEYS:
        assert by_path[f"{key}/rows-before.trig"].splitlines() == expected_rows(compiled_job, key, before), key


def test_the_edit_changes_what_at_least_three_projections_write(sample_step):
    _, frames = sample_step
    delta = json.loads(next(text for p, text in parts(frames) if p["role"] == "delta"))
    changed = [c["key"] for c in delta["contracts"] if c["graphs"]]
    assert len(changed) >= 3 and changed == ["borrower-exposure", "drawdown-schedule", "facility-branch", "facility-margin", "facility-refinancing"]
    outcome = json.loads(next(text for p, text in parts(frames) if p["role"] == "outcome"))
    assert list(outcome) == ["engine", "sources", "contracts"] and outcome["sources"] == ["urn:g:facilities"]
    assert outcome["engine"] == runs.engine() and "mork_rdf" in outcome["engine"] and "Oxigraph" in outcome["engine"]
    assert [(c["key"], c["asserted"], c["retracted"]) for c in outcome["contracts"] if c["key"] == "facility-margin"] == [("facility-margin", 1, 1)]
    for entry in delta["contracts"]:
        assert list(entry) == ["contract", "key", "graphs"]
        for graph in entry["graphs"]:
            assert list(graph) == ["graph", "asserted", "retracted"] and graph["graph"] is None
            assert graph["asserted"] == sorted(graph["asserted"], key=lambda l: l.encode("utf-8"))


def test_the_report_holds_the_findings_of_the_driver_over_the_world_after(sample_step):
    _, frames = sample_step
    text = next(text for p, text in parts(frames) if p["role"] == "report")
    report = Graph().parse(data=text, format="turtle")
    codes = sorted((str(report.value(r, CST.code)), str(report.value(r, SH.resultSeverity)).rsplit("#", 1)[-1]) for r in report.subjects(RDF.type, SH.ValidationResult))
    assert ("JoinUnmatched", "Warning") in codes and ("InstanceExcluded", "Warning") in codes


def test_a_repeat_and_the_quads_of_the_world_in_another_order_give_the_same_frames(compiled_job, sample_step):
    trig, frames = sample_step
    assert run_step(compiled_job, trig)[1].frames() == frames
    quads = list(ox.parse(trig.encode("utf-8"), format=ox.RdfFormat.TRIG))
    for seed in (1, 2, 3):
        shuffled = quads[:]
        random.Random(seed).shuffle(shuffled)
        body = ox.serialize(shuffled, format=ox.RdfFormat.TRIG).decode("utf-8")
        assert run_step(compiled_job, body)[1].frames() == frames, seed


def test_the_frames_are_the_same_as_a_surface_step_s_in_shape_and_hold_to_the_schema(sample_step):
    _, frames = sample_step
    for frame in frames:
        if "part" in frame and frame["part"]["role"] == "artefact":
            assert frame["part"]["step"] == 0


# ---- a step that cannot be run, a job that cannot run it, and a run that went to the wrong worker ----------------------------------------


def one_failure(sink: Sink) -> str:
    (frame,) = sink.frames()
    validate_run([frame])
    assert frame["seq"] == 0 and frame["last"] and frame["status"] == "failed"
    return frame["message"]


STEP = STEP_FILE.read_text(encoding="utf-8")


@pytest.mark.parametrize("body, said", [
    ("", "step is empty"),
    ("this is not trig {", "not valid TriG"),
    ("<urn:g:a> { <urn:s> <urn:p> <urn:o> . }", "holds no cst:SimulationStepRequest"),
    (STEP.replace("cst:forPart cst:Surface ;", "cst:forClass <urn:c> ;"), "persistence step"),
    (STEP.replace("cst:forPart cst:Surface ;", ""), "does not say cst:forPart"),
    (STEP.replace("cst:forPart cst:Surface ;", "cst:forPart cst:Persistence ;"), "simulates the surface part"),
    (STEP.replace('cst:transactionTime "2026-04-02T09:30:00Z"^^xsd:dateTime', 'cst:transactionTime "tomorrow"'), "transactionTime once"),
    (STEP.replace("cst:transactionTime", "# no time"), "does not say cst:transactionTime"),
    (STEP + "\n<urn:lattice:studio:step/other> { <urn:s> <urn:p> <urn:o> . }\n", "reserved for the step"),
    (STEP + "\n<urn:lattice:studio:step/added/urn%3Alattice%3Astudio%3Apromoted%3Aurn%3Ag%3Afacilities> { <urn:s> <urn:p> <urn:o> . }\n", "derived rows"),
    (STEP + "\n<urn:lattice:studio:step/added/urn%3Alattice%3Astudio%3Astep> { <urn:s> <urn:p> <urn:o> . }\n", "reserved for the step"),
    (STEP + "\n<urn:lattice:studio:step/added/urn%ZZg> { <urn:s> <urn:p> <urn:o> . }\n", "not valid TriG"),
    (STEP + "\n<urn:lattice:studio:step/added> { <urn:s> <urn:p> <urn:o> . }\n<urn:lattice:studio:step/removed> { <urn:s> <urn:p> <urn:o> . }\n", "both adds and removes"),
])
def test_a_malformed_step_is_one_failed_frame_that_says_which_part(compiled_job, body, said):
    outcome, sink = run_step(compiled_job, body)
    assert outcome is Outcome.ACK
    message = one_failure(sink)
    assert said in message
    if said != "both adds and removes":  # which names the quad it is told once, as a surface step does
        assert "<urn:s>" not in message


def test_a_job_without_compiled_projections_is_one_failed_frame(compiled_job):
    held_manifest = [a for a in compiled_job.objects(JOB, CST.artefact) if str(compiled_job.value(a, CST.path)) == projections.MANIFEST]
    bare = Graph() + compiled_job
    for node in held_manifest:
        bare.remove((JOB, CST.artefact, node))
    assert "holds no compiled projection" in one_failure(run_step(bare, STEP)[1])
    empty = Graph() + bare
    node = URIRef(str(JOB) + "#manifest")
    for triple in ((JOB, CST.artefact, node), (node, CST.path, Literal(projections.MANIFEST)), (node, CST.content, Literal("[]"))):
        empty.add(triple)
    assert "lists no projection" in one_failure(run_step(empty, STEP)[1])


def test_a_job_that_is_not_a_finished_compilation_of_the_surface_part_is_one_failed_frame(compiled_job):
    other = Graph() + compiled_job
    other.remove((JOB, CST.target, CST.Surface))
    other.add((JOB, CST.target, CST.Mapping))
    assert "not a finished compilation of the surface part" in one_failure(run_step(other, STEP)[1])
    unfinished = Graph() + compiled_job
    unfinished.remove((JOB, CST.status, CST.Succeeded))
    assert "not a finished compilation" in one_failure(run_step(unfinished, STEP)[1])


def test_a_compiled_form_whose_queries_were_changed_is_refused_by_the_step(compiled_job):
    tampered = Graph() + compiled_job
    for node in tampered.objects(JOB, CST.artefact):
        path = str(tampered.value(node, CST.path))
        if path.endswith("scheme_facility-margin.compiled.ttl"):
            content = str(tampered.value(node, CST.content))
            tampered.set((node, CST.content, Literal(content.replace("DISTINCT", "REDUCED", 1) if "DISTINCT" in content else content.replace("SELECT", "SELECT ", 1))))
    message = one_failure(run_step(tampered, STEP)[1])
    assert "facility-margin" in message and "could not be read" in message


@pytest.mark.parametrize("target", ["surface", "persistence"])
def test_a_surface_or_persistence_step_that_reaches_this_worker_is_failed_as_a_run_that_went_to_the_wrong_worker(compiled_job, target):
    outcome, sink = run_step(compiled_job, STEP, target=target)
    assert outcome is Outcome.ACK
    message = one_failure(sink)
    assert "wrong worker" in message and "not started" in message


@pytest.mark.parametrize("media", ["text/turtle", "application/json", None])
def test_a_projection_step_not_sent_as_trig_is_failed(compiled_job, media):
    sink = Sink()
    worker = RdfRunWorker(lambda iri: compiled_job, lambda: NOW)
    h = headers(kind="simulate", target="projection", deadline=NOW + timedelta(seconds=15))
    outcome = worker.handle(Message(1, False, h, media, STEP.encode("utf-8")), sink)
    assert outcome is Outcome.ACK and "application/trig" in one_failure(sink)


def test_a_step_that_passes_its_deadline_is_stopped_and_publishes_nothing(compiled_job, monkeypatch):
    started = threading.Event()
    stopped = threading.Event()

    def slow(job, request, trig, stop):  # the engine does not return until the run is stopped
        started.set()
        while not stop.is_set():
            time.sleep(0.01)
        stopped.set()
        raise runs.RunStopped()

    monkeypatch.setattr(runs, "projection_step", slow)
    sink = Sink()
    h = headers(kind="simulate", target="projection", deadline=NOW + timedelta(milliseconds=300))
    outcome = RdfRunWorker(lambda iri: compiled_job, lambda: NOW).handle(Message(1, False, h, "application/trig", STEP.encode("utf-8")), sink)
    assert started.is_set() and outcome is Outcome.ACK and sink.published == []
    assert stopped.wait(5), "the run was told to stop"


def test_a_stopped_step_ends_at_the_next_query_it_would_write(compiled_job):
    stop = threading.Event()
    stop.set()
    with pytest.raises(runs.RunStopped):
        step.execute(compiled_job, str(JOB), STEP, RUN, runs.engine(), lambda: runs._StoppableRecorder(stop))


def test_a_run_past_its_deadline_is_acknowledged_and_gets_no_frame(compiled_job):
    sink = Sink()
    h = headers(kind="simulate", target="projection", deadline=NOW + timedelta(seconds=15))
    outcome = RdfRunWorker(lambda iri: compiled_job, lambda: NOW + timedelta(seconds=15)).handle(Message(1, False, h, "application/trig", STEP.encode("utf-8")), sink)
    assert outcome is Outcome.ACK and sink.published == []


def test_a_redelivered_step_is_never_run_and_gets_the_failed_frame_a_worker_stopped_says(compiled_job):
    sink = Sink()
    h = headers(kind="simulate", target="projection", deadline=NOW + timedelta(seconds=15))
    outcome = RdfRunWorker(lambda iri: compiled_job, lambda: NOW).handle(Message(1, True, h, "application/trig", STEP.encode("utf-8")), sink)
    assert outcome is Outcome.ACK and "stopped" in one_failure(sink)


def test_a_step_over_5_mib_is_one_failed_frame(compiled_job):
    big = STEP + "# " + "x" * (5 * 1024 * 1024) + "\n"
    assert "5 MiB" in one_failure(run_step(compiled_job, big)[1])


def test_a_part_list_over_128_frames_is_one_failed_frame_that_says_so():
    parts_ = [run_frames.Part("artefact", "application/trig", "x" * run_frames.MAX_TEXT_BYTES, "k", "k/rows-before.trig") for _ in range(130)]
    (frame,) = run_frames.of_step(RUN, parts_)
    validate_run([frame])
    assert frame["status"] == "failed" and "too large" in frame["message"]


def test_a_compiled_query_that_reads_the_clock_is_refused(compiled_job, monkeypatch):
    import dataclasses

    import mork_rdf

    real = mork_rdf.from_rdf

    def reading_the_clock(graph):
        compiled = real(graph)
        first = compiled.queries[0]
        return dataclasses.replace(compiled, queries=(dataclasses.replace(first, text=first.text + "\n# BIND (NOW() AS ?now)"), *compiled.queries[1:]))

    monkeypatch.setattr(mork_rdf, "from_rdf", reading_the_clock)
    assert "reads the clock" in one_failure(run_step(compiled_job, STEP)[1])
