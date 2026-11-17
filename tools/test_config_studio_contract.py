# SPDX-License-Identifier: MPL-2.0
"""Tests the Configuration Studio's contract for runs, `contracts/config-studio` (ADR-A154, slice SVA-R1).

A frame of a run is one wire type, used both as the body of a `run.frame` event and as an element of a `wait=true`
response, so one schema holds both. The two queues of runs are in the topology beside the transforms queue.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lattice_repo_catalogue  # noqa: E402

ROOT = lattice_repo_catalogue.find_root()
CONTRACT = ROOT / lattice_repo_catalogue.load(ROOT).area("contracts") / "config-studio"
CST = Namespace("https://www.nebularis.org/neuro-semantic/lattice/config-studio#")
MAX_TEXT_BYTES = 49152
MAX_FRAMES = 128
EXAMPLES = ["run-frames.example.json", "run-frames-failed.example.json"]

SCHEMA = json.loads((CONTRACT / "run-frame.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)
RUN = "urn:lattice:studio:run:3f2b8c1e-5a47-4d0e-9b1a-6c7d8e9f0a1b"


def example(name: str) -> list[dict]:
    return json.loads((CONTRACT / "samples" / name).read_text(encoding="utf-8"))


def test_the_schema_is_a_valid_2020_12_schema() -> None:
    Draft202012Validator.check_schema(SCHEMA)
    assert SCHEMA["properties"]["text"]["maxLength"] == MAX_TEXT_BYTES


@pytest.mark.parametrize("name", EXAMPLES)
def test_each_example_frame_validates_against_the_schema(name: str) -> None:
    frames = example(name)
    assert frames
    for frame in frames:
        assert list(VALIDATOR.iter_errors(frame)) == [], frame


def test_the_deadline_example_validates_and_has_a_gap_before_the_services_failed_frame() -> None:
    frames = example("run-frames-deadline.example.json")
    for frame in frames:
        assert list(VALIDATOR.iter_errors(frame)) == [], frame
    assert [f["seq"] for f in frames] == [0, 1, 3, 4]
    assert [f["last"] for f in frames] == [False, False, False, True]
    assert frames[-1]["status"] == "failed"
    assert {f["run"] for f in frames} == {frames[0]["run"]}


@pytest.mark.parametrize("name", EXAMPLES)
def test_an_example_is_a_whole_run(name: str) -> None:
    frames = example(name)
    assert len(frames) <= MAX_FRAMES
    assert [f["seq"] for f in frames] == list(range(len(frames)))
    assert {f["run"] for f in frames} == {frames[0]["run"]}
    assert [f["last"] for f in frames] == [False] * (len(frames) - 1) + [True]
    assert [f["part"]["index"] for f in frames if "part" in f] == list(range(sum("part" in f for f in frames)))
    for f in frames:
        assert len(f.get("text", "").encode("utf-8")) <= MAX_TEXT_BYTES


def test_the_parts_of_the_sample_run_read_back_as_rdf() -> None:
    parts: dict[int, dict] = {}
    current = -1
    for f in example("run-frames.example.json"):
        if "part" in f:
            current = f["part"]["index"]
            parts[current] = {"part": f["part"], "text": ""}
        parts[current]["text"] += f.get("text", "")
    assert [p["part"]["role"] for p in parts.values()] == ["report", "artefact"]
    report = Graph().parse(data=parts[0]["text"], format="turtle")
    assert len(report) == 2
    artefact = Graph().parse(data=parts[1]["text"], format="nt")
    assert len(artefact) == 2


def last(**changes) -> dict:
    """A last frame that is good, with `changes` applied, and a key set to None removed."""
    frame = {"run": RUN, "seq": 3, "last": True, "status": "succeeded"}
    frame.update(changes)
    return {k: v for k, v in frame.items() if v is not None}


def middle(**changes) -> dict:
    """A frame that is not last and is good, with `changes` applied, and a key set to None removed."""
    frame = {"run": RUN, "seq": 1, "last": False, "text": "x"}
    frame.update(changes)
    return {k: v for k, v in frame.items() if v is not None}


PART = {"index": 0, "role": "report", "mediaType": "text/turtle"}

BAD = {
    "a last frame with no status": last(status=None),
    "a failed frame with no message": last(status="failed"),
    "a succeeded frame with a message": last(message="why"),
    "a failed frame with conforms": last(status="failed", message="why", conforms=True),
    "a frame that is not last, with a status": middle(status="succeeded"),
    "a last frame that says the part continues": last(more=True),
    "an unknown status": last(status="done"),
    "a negative seq": last(seq=-1),
    "a seq that is not a whole number": last(seq=1.5),
    "an extra property": last(extra=1),
    "no run": last(run=None),
    "a run that is not a run IRI": last(run="urn:lattice:studio:job:3f2b8c1e-5a47-4d0e-9b1a-6c7d8e9f0a1b"),
    "an unknown role": middle(part={**PART, "role": "summary"}),
    "a part with no media type": middle(part={"index": 0, "role": "report"}),
    "a part with no role": middle(part={"index": 0, "mediaType": "text/turtle"}),
    "a part with no index": middle(part={"role": "report", "mediaType": "text/turtle"}),
    "a part with a negative index": middle(part={**PART, "index": -1}),
    "a part with an extra property": middle(part={**PART, "x": 1}),
    "a part with a negative step": middle(part={**PART, "role": "artefact", "step": -1}),
    "text over 49,152 characters": middle(text="x" * (MAX_TEXT_BYTES + 1)),
}


@pytest.mark.parametrize("name", sorted(BAD))
def test_a_bad_frame_is_refused(name: str) -> None:
    assert list(VALIDATOR.iter_errors(BAD[name])), name


def test_text_of_exactly_the_limit_is_accepted() -> None:
    assert list(VALIDATOR.iter_errors(middle(text="x" * MAX_TEXT_BYTES))) == []


def test_each_role_of_a_part_is_accepted() -> None:
    for role in ("check", "request", "report", "artefact", "delta", "outcome"):
        assert list(VALIDATOR.iter_errors(middle(part={**PART, "role": role}))) == [], role


def test_the_two_run_queues_sit_in_the_topology_with_the_transforms_queues_settings() -> None:
    queues = {q["name"]: q for q in json.loads((CONTRACT / "amqp-topology.json").read_text(encoding="utf-8"))["queues"]}
    transforms = queues["lattice.studio.transforms"]
    for name in ("lattice.studio.runs.interactive", "lattice.studio.runs"):
        assert queues[name] == {"name": name, "routingKey": name, "deadLetter": transforms["deadLetter"], "bindTo": transforms["bindTo"]}
    assert transforms["deadLetter"] is False


def test_the_vocabulary_declares_a_run_and_its_two_kinds() -> None:
    g = Graph().parse(CONTRACT / "studio-vocabulary.ttl")
    assert (CST.Run, RDF.type, OWL.Class) in g
    assert (CST.Run, RDFS.subClassOf, CST.Job) in g
    for kind in (CST.SampleRun, CST.SimulationStep):
        assert (kind, RDF.type, CST.JobKind) in g
        assert g.value(kind, RDFS.comment) is not None
    assert (CST.deadline, RDFS.domain, CST.Run) in g
    assert CST.Sample != CST.SampleRun


def test_the_contract_states_the_limits_the_schema_holds() -> None:
    readme = (CONTRACT / "README.md").read_text(encoding="utf-8")
    assert "run-frame.schema.json" in readme
    for text in ("49,152", "128 frames", "lattice.studio.runs.interactive", "lattice.studio.runs"):
        assert text in readme, text
