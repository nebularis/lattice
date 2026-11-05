# SPDX-License-Identifier: MPL-2.0

"""Tests for `tools/validation_replay.py`, the recorder and replayer of the suite's SHACL
validations (docs/architecture/efficient-queries-and-shapes.md, rule R7)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from pyshacl import validate
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import RDF

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validation_replay as vr  # noqa: E402

EX = Namespace("https://example.org/lattice/test-validation-replay/")

SHAPES = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <https://example.org/lattice/test-validation-replay/> .
ex:NeedsName a sh:NodeShape ; sh:targetClass ex:Thing ;
  sh:property [ sh:path ex:name ; sh:minCount {minimum} ; sh:message "needs a name" ] .
"""


def _shapes(tmp_path: Path, minimum: int = 1) -> Path:
    path = tmp_path / "shapes.ttl"
    path.write_text(SHAPES.format(minimum=minimum))
    return path


def _data(named: bool) -> Graph:
    graph = Graph()
    graph.bind("ex", EX)
    graph.add((EX.a, RDF.type, EX.Thing))
    if named:
        graph.add((EX.a, EX.name, Literal("a")))
    return graph


def _recorded(tmp_path: Path, shapes: Path, data: Graph) -> dict:
    """One call recorded as the suite's validation cache would, then read back."""
    recorder = vr.Recorder(tmp_path / "rec")
    shapes_graph = Graph().parse(shapes)
    conforms, report, _ = validate(data, shacl_graph=shapes_graph)
    recorder.record([shapes], data.serialize(format="nt"), {"ex": str(EX)}, {"advanced": True}, conforms, vr.result_rows(report))
    return vr.load_calls(tmp_path / "rec")[0]


def test_a_recording_replays_to_the_same_report(tmp_path: Path) -> None:
    call = _recorded(tmp_path, _shapes(tmp_path), _data(named=False))
    conforms, rows, _ = vr.replay_call(call, tmp_path / "rec")
    assert call["conforms"] is False and conforms is False
    assert not vr.differs(call, conforms, rows)


def test_a_changed_shape_is_reported_as_a_difference(tmp_path: Path) -> None:
    shapes = _shapes(tmp_path)
    call = _recorded(tmp_path, shapes, _data(named=True))
    assert call["conforms"] is True
    _shapes(tmp_path, minimum=2)
    conforms, rows, _ = vr.replay_call(call, tmp_path / "rec")
    assert vr.differs(call, conforms, rows)
    assert "DIFFERENT" in vr.describe_difference(call, conforms, rows)


def test_blank_node_labels_do_not_count_as_a_difference() -> None:
    assert vr.masked([["a", "_:b1", "N0123456789abcdef0123456789abcdef", "m", ""]]) == vr.masked([["a", "_:other", "N" + "f" * 32, "m", ""]])


def test_the_same_call_is_loaded_once(tmp_path: Path) -> None:
    call = _recorded(tmp_path, _shapes(tmp_path), _data(named=False))
    line = json.dumps(call)
    (tmp_path / "rec" / "calls-2.jsonl").write_text(line + "\n" + line + "\n")
    assert len(vr.load_calls(tmp_path / "rec")) == 1


def test_a_path_under_the_repository_is_recorded_relative_to_it() -> None:
    assert vr.describe_sources([vr.ROOT / "ontology" / "foundation" / "spec" / "foundation.ttl"]) == [{"path": "ontology/foundation/spec/foundation.ttl"}]
    assert vr.describe_sources(["@prefix ex: <urn:x#> ."]) == [{"turtle": "@prefix ex: <urn:x#> ."}]


def test_a_data_graph_that_cannot_be_read_back_is_counted_not_compared(tmp_path: Path) -> None:
    call = _recorded(tmp_path, _shapes(tmp_path), _data(named=False))
    (tmp_path / "rec" / "data" / f"{call['data']}.nt.gz").write_bytes(b"not gzip")
    assert vr.replay_call(call, tmp_path / "rec")[0] is None


def test_replay_counts_a_known_difference_separately(tmp_path: Path) -> None:
    shapes = _shapes(tmp_path)
    call = _recorded(tmp_path, shapes, _data(named=True))
    _shapes(tmp_path, minimum=2)
    messages: list[str] = []
    summary = vr.replay(tmp_path / "rec", 1, out=messages.append)
    assert summary["differing"] == [vr.call_identity(call)]
    again = vr.replay(tmp_path / "rec", 1, baseline=set(summary["differing"]), out=messages.append)
    assert again["differing"] == [] and again["known"] == 1


def _stub_conftest(shapes_graph: Graph | None):
    """A stand-in for `tools/conftest.py` whose cache validates with pySHACL as it is."""
    class Cache:
        def __call__(self, data_graph, *args, shacl_graph, **options):
            return validate(data_graph, shacl_graph=shacl_graph, **options)

    graphs = {} if shapes_graph is None else {("shapes",): shapes_graph}
    return SimpleNamespace(ValidationCache=Cache, _GRAPH_CACHE=SimpleNamespace(_by_key=graphs))


def test_install_records_a_validation_without_changing_its_result(tmp_path: Path) -> None:
    shapes_graph = Graph().parse(_shapes(tmp_path))
    stub = _stub_conftest(shapes_graph)
    plain = stub.ValidationCache()(_data(named=False), shacl_graph=shapes_graph)
    vr.install(stub, vr.Recorder(tmp_path / "rec"))
    result = stub.ValidationCache()(_data(named=False), shacl_graph=shapes_graph)
    assert result[0] == plain[0] is False
    [call] = vr.load_calls(tmp_path / "rec")
    assert call["conforms"] is False and len(call["results"]) == 1


def test_install_skips_shapes_that_did_not_come_from_the_graph_cache(tmp_path: Path) -> None:
    shapes_graph = Graph().parse(_shapes(tmp_path))
    stub = _stub_conftest(None)
    vr.install(stub, vr.Recorder(tmp_path / "rec"))
    stub.ValidationCache()(_data(named=False), shacl_graph=shapes_graph)
    assert vr.load_calls(tmp_path / "rec") == []


def test_a_literal_subject_is_recorded_and_counted_as_unreadable_on_replay(tmp_path: Path) -> None:
    shapes_graph = Graph().parse(_shapes(tmp_path))
    stub = _stub_conftest(shapes_graph)
    vr.install(stub, vr.Recorder(tmp_path / "rec"))
    data = _data(named=False)
    data.add((Literal("subject"), EX.name, Literal("x")))
    stub.ValidationCache()(data, shacl_graph=shapes_graph)
    [call] = vr.load_calls(tmp_path / "rec")
    assert vr.replay_call(call, tmp_path / "rec")[0] is None   # N-Triples cannot be parsed back with a literal subject


def test_the_record_command_is_the_task_s_own_with_the_plugin() -> None:
    command = vr.record_command(None)
    assert command[1:3] == ["-m", "pytest"] and "validation_replay" in command
    assert "tools/test_wording.py" in command and "--dist" in command
    workers = vr.record_command("3")
    assert workers[workers.index("-n") + 1] == "3" and workers.count("-n") == 1
