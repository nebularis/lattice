"""The compilations and the Turtle runs of the studio's browser journeys (SVA-M3b). The journeys' fake service cannot compile or run anything, so it
answers from `apps/config-studio/e2e/fixtures/sample-runs.json`, which holds, for each workspace of the journeys, the body the browser submits to
compile its mapping part and what the compiler gave for it, and for each run the sample the author gives and the frames a worker gave for it. This
test keeps the compilations and the frames of the runs the Python worker answers equal to what the worker gives now, so a change to the compiler, the
worker or the contract fails here until the fixture is written again. The browser's own test (`sample.journey.test.ts`) keeps the bodies and the
samples current, and the Java run worker's (`SampleRunsTest`) the frames of the XML and JSON runs.

    LATTICE_WRITE_SAMPLE_RUNS=1 mise exec -- python -m pytest workers/tests/test_config_studio_sample_runs.py -q

Frames are never written by hand."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from rdflib import Graph, URIRef
from rdflib.compare import isomorphic

from lattice_workers import config_studio_jobs as jobs
from lattice_workers.config_studio_jobs import CST
from lattice_workers.config_studio_runs import Message, Outcome, RdfRunWorker

ROOT = jobs.find_root()
FIXTURE = ROOT / "apps" / "config-studio" / "e2e" / "fixtures" / "sample-runs.json"
SCHEMA = json.loads((ROOT / "contracts" / "config-studio" / "run-frame.schema.json").read_text(encoding="utf-8"))
WRITE = os.environ.get("LATTICE_WRITE_SAMPLE_RUNS") == "1"
JOB = "urn:lattice:studio:job:00000000-0000-4000-8000-000000000001"
RUN = "urn:lattice:studio:run:3f2b8c1e-5a47-4d0e-9b1a-6c7d8e9f0a1b"
SUBMITTED = "2026-11-20T10:00:00Z"
NOW = datetime(2026, 11, 20, 10, 5, tzinfo=timezone.utc)


def load() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def save(data: dict[str, Any]) -> None:
    FIXTURE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def compile_job(workspace: dict[str, Any]) -> Graph:
    """The compile job a worker writes for what the browser submits, with the workspace's baseline and other parts read beside it."""
    job = URIRef(JOB)
    graph = jobs.run_job(
        job, "compile", "mapping", Graph().parse(data=workspace["compileBody"], format="turtle"),
        Graph().parse(data=workspace["baseline"], format="turtle"), ROOT, SUBMITTED,
        Graph().parse(data=workspace["context"], format="turtle"),
    )
    graph.add((job, CST.kind, CST.Compile))
    graph.add((job, CST.target, CST.Mapping))
    graph.add((job, CST.status, CST.Succeeded))
    return graph


def written(graph: Graph) -> list[dict[str, str]]:
    """The artefacts of a job as the fixture holds them, by group and then by path."""
    rows = [
        {"path": str(graph.value(a, CST.path)), "mediaType": str(graph.value(a, CST.mediaType)), "group": str(graph.value(a, CST.group)), "content": str(graph.value(a, CST.content))}
        for a in graph.objects(URIRef(JOB), CST.artefact)
    ]
    return sorted(rows, key=lambda r: (r["group"], r["path"]))


class Sink:
    def __init__(self) -> None:
        self.frames: list[dict[str, Any]] = []

    def publish(self, run: str, frames: list[str]) -> None:
        self.frames += [json.loads(f) for f in frames]


def frames_of(job: Graph, media: str, sample: str) -> list[dict[str, Any]]:
    headers = {"run": RUN, "job": JOB, "kind": "sample", "target": "mapping", "deadline": (NOW + timedelta(seconds=120)).isoformat().replace("+00:00", "Z")}
    sink = Sink()
    outcome = RdfRunWorker(lambda iri: job, lambda: NOW).handle(Message(1, False, headers, media, sample.encode("utf-8")), sink)
    assert outcome is Outcome.ACK
    return sink.frames


def same_artefacts(kept: list[dict[str, str]], now: list[dict[str, str]]) -> bool:
    """The same artefacts at the same paths, with equal text. A Turtle artefact is compared as a graph, since the RML file of a workspace with two
    formats is written with its blank nodes in an order that changes from one process to the next (TD-151 records that one file serves both formats)."""
    if [(r["group"], r["path"], r["mediaType"]) for r in kept] != [(r["group"], r["path"], r["mediaType"]) for r in now]:
        return False
    for a, b in zip(kept, now):
        if a["mediaType"] == "text/turtle":
            if not isomorphic(Graph().parse(data=a["content"], format="turtle"), Graph().parse(data=b["content"], format="turtle")):
                return False
        elif a["content"] != b["content"]:
            return False
    return True


def test_each_workspace_s_compilation_is_what_the_compiler_gives_for_the_body_the_browser_submits():
    data = load()
    assert data["workspaces"], "the fixture holds the journeys' workspaces. Run sample.journey.test.ts with UPDATE_SAMPLE_RUNS=1 to write their bodies"
    for workspace in data["workspaces"]:
        job = compile_job(workspace)
        conforms = str(job.value(URIRef(JOB), CST.conforms)) == "true"
        if WRITE:
            workspace["compiled"] = written(job)
            workspace["conforms"] = conforms
            save(data)
        assert same_artefacts(workspace["compiled"], written(job)), f"the compilation of {workspace['id']} is not what the compiler gives. Write it with LATTICE_WRITE_SAMPLE_RUNS=1"
        assert workspace["conforms"] == conforms


def test_each_turtle_run_s_frames_are_what_the_python_worker_gives_for_its_sample_over_the_compilation():
    data = load()
    by_id = {w["id"]: w for w in data["workspaces"]}
    mine = [r for r in data["runs"] if r["worker"] == "python"]
    assert mine, "the fixture holds a run for the Python worker"
    for run in mine:
        assert run["mediaType"] in ("text/turtle", "application/n-triples")
        frames = frames_of(compile_job(by_id[run["workspace"]]), run["mediaType"], run["sample"])
        for frame in frames:
            jsonschema.validate(frame, SCHEMA, format_checker=jsonschema.FormatChecker())
        assert frames[-1]["status"] == "succeeded", frames[-1]
        if WRITE:
            run["frames"] = frames
            save(data)
        assert run["frames"] == frames, f"the frames of {run['id']} are not what the worker gives. Write them with LATTICE_WRITE_SAMPLE_RUNS=1"


def test_the_fixture_gives_the_xml_and_json_runs_to_the_java_run_worker_and_the_rest_to_the_python_worker():
    for run in load()["runs"]:
        rdf = run["mediaType"] in ("text/turtle", "application/n-triples")
        assert run["worker"] == ("python" if rdf else "java"), run["id"]
