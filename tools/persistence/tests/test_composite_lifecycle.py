# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""HO7: a composite aggregate can be created and deleted as a whole (formal-methods track H, slice HO7,
ADR-A122 decision 3, technical debt TD-04).
Validation Pack: docs/developer/validation/FMH-HO7.md. Test IDs are HO7-Tn.

The generated updates run on rdflib's in-memory ``Dataset`` with the project fixture. Nothing in them
touches the default graph, and no test puts data there except HO7-T4's guard check."""

from __future__ import annotations

import re
import warnings
from functools import lru_cache
from pathlib import Path

import pytest
from rdflib import RDF, Dataset, Graph, Literal, URIRef, Variable
from rdflib.graph import DATASET_DEFAULT_GRAPH_ID
from rdflib.namespace import XSD

from persistence import templatecheck, witness
from persistence.compiler import compile_targets, compile_to_graph

from conftest import EXAMPLES_DIR

PAT = "https://example.org/lattice/patterns#"
PX = "https://example.org/projects#"
PROJECT_EXAMPLE = EXAMPLES_DIR / "composite-project-ownership.ttl"
PROJECT_DATA = Path(__file__).resolve().parent / "fixtures" / "project-data.ttl"
DATASET_GUARD_FIXTURE = witness.WITNESS_DIR / "template-cas-replace-composite-property-dataset-guard.ttl"
DATA_GRAPH = URIRef("urn:g:projects")
ROOT = URIRef(PX + "p1")
MEMBERS = {"m1", "m2", "plan1", "t1", "t2", "t3", "docOwned", "c1"}
CREATE, TOMBSTONE, REPLACE = "create-if-absent-composite", "tombstone-delete-composite", "cas-replace-composite-property"


@lru_cache(maxsize=None)
def _text(template: str) -> str:
    compiled, _ = compile_to_graph(witness._load_fixture(PROJECT_EXAMPLE))
    return next(o for o in templatecheck.operations(compiled) if o.template == template).text


def _meta(template: str) -> URIRef:
    return URIRef(re.search(r"GRAPH <(urn:g:meta/\d+)>", _text(template)).group(1))


def _data() -> Graph:
    return Graph().parse(PROJECT_DATA, format="turtle")


def _px(name: str) -> URIRef:
    return URIRef(PX + name)


def _delete_set(data: Graph) -> set:
    subjects = {ROOT, *(_px(m) for m in MEMBERS)}
    return {t for t in data if t[0] in subjects}


def _nt(triples) -> str:
    return "".join(f"{s.n3()} {p.n3()} {o.n3()} . " for s, p, o in triples)


def _dataset(template: str, *, data: Graph | None, row_seq: int | None = 1, default_copy: Graph | None = None) -> Dataset:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ds = Dataset()
        if row_seq is not None:
            ds.graph(_meta(template)).add((ROOT, URIRef(PAT + "epoch"), Literal(1)))
            ds.graph(_meta(template)).add((ROOT, URIRef(PAT + "seq"), Literal(row_seq, datatype=XSD.long)))
        if data is not None:
            graph = ds.graph(DATA_GRAPH)
            for triple in data:
                graph.add(triple)
        if default_copy is not None:
            for triple in default_copy:
                ds.default_context.add(triple)
    return ds


def _quads(ds: Dataset) -> set:
    return {(s, p, o, str(getattr(g, "identifier", g))) for s, p, o, g in ds.quads((None, None, None, None))}


def _run(ds: Dataset, template: str, *, txn: str = "a", expected_seq: int = 1, payload=()) -> None:
    text = _text(template).replace(templatecheck._SLOT_STAND_INS["payloadTriples"], _nt(payload))
    values = {
        "root": ROOT, "epoch": Literal(1), "expectedSeq": Literal(expected_seq, datatype=XSD.long),
        "nextSeq": Literal(expected_seq + 1, datatype=XSD.long), "newRev": URIRef(f"urn:rev:{txn}"),
        "txnId": URIRef(f"urn:txn:{txn}"), "requestDigest": Literal("d"),
        "cause": URIRef("urn:decision:1"), "actor": URIRef("urn:actor:1"),
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ds.update(text, initBindings={Variable(k): v for k, v in values.items()})


def _data_graph(ds: Dataset) -> set:
    return {(s, p, o) for s, p, o, g in _quads(ds) if g == str(DATA_GRAPH)}


def _revisions(ds: Dataset) -> list:
    return [q for q in _quads(ds) if q[1] == RDF.type and q[2] == URIRef(PAT + "Revision")]


# ---- what is generated


def test_ho7_t1_a_composite_family_with_an_absent_row_gets_both_create_templates_and_a_tombstone():
    for fixture, suffix in ((PROJECT_EXAMPLE, ""), (DATASET_GUARD_FIXTURE, "-dataset-guard")):
        (compiled,) = compile_targets(witness._load_fixture(fixture))
        templates = {o.operation: o.template_id for o in compiled.operations}
        assert templates["create-if-absent"] == f"create-if-absent-composite{suffix}.mustache"
        assert templates["tombstone-delete"] == f"tombstone-delete-composite{suffix}.mustache"
        assert templates["cas-replace"].startswith("cas-replace-composite-property")


def test_ho7_t1b_a_pre_created_row_gets_no_create_and_still_a_tombstone():
    graph = witness._load_fixture(PROJECT_EXAMPLE)
    graph.parse(
        data="@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> . "
             "@prefix px: <https://example.org/projects#> . px:ProjectBoundaryProfile dal:firstWrite dal:PreCreatedRow .",
        format="turtle",
    )
    (compiled,) = compile_targets(graph)
    operations = {o.operation for o in compiled.operations}
    assert "create-if-absent" not in operations and "bootstrap-version-row" in operations and "tombstone-delete" in operations


# ---- create


def test_ho7_t2_a_create_writes_the_payload_to_the_data_graph_a_version_row_and_one_revision():
    data = _data()
    payload = _delete_set(data)
    ds = _dataset(CREATE, data=None, row_seq=None)
    _run(ds, CREATE, payload=payload)
    assert _data_graph(ds) == payload
    quads = _quads(ds)
    assert (ROOT, URIRef(PAT + "seq"), Literal(1, datatype=XSD.long), str(_meta(CREATE))) in quads
    assert len(_revisions(ds)) == 1
    assert not any(g == str(DATASET_DEFAULT_GRAPH_ID) for *_, g in quads)


def test_ho7_t3_a_second_create_with_another_transaction_changes_nothing():
    ds = _dataset(CREATE, data=None, row_seq=None)
    _run(ds, CREATE, txn="a", payload=_delete_set(_data()))
    before = _quads(ds)
    _run(ds, CREATE, txn="b", payload=_delete_set(_data()))
    assert _quads(ds) == before


def test_ho7_t4_a_create_over_a_root_that_already_has_triples_changes_nothing():
    data = _data()
    ds = _dataset(CREATE, data=data, row_seq=None)  # the aggregate is there, the version row is not
    before = _quads(ds)
    _run(ds, CREATE, payload={(ROOT, _px("name"), Literal("Other"))})
    assert _quads(ds) == before


# ---- tombstone delete


def test_ho7_t5_a_tombstone_delete_removes_the_delete_set_and_tombstones_the_row():
    data = _data()
    ds = _dataset(TOMBSTONE, data=data)
    _run(ds, TOMBSTONE)
    assert _data_graph(ds) == set(data) - _delete_set(data)
    quads = _quads(ds)
    meta = str(_meta(TOMBSTONE))
    assert (ROOT, URIRef(PAT + "deleted"), Literal(True), meta) in quads
    assert (ROOT, URIRef(PAT + "seq"), Literal(2, datatype=XSD.long), meta) in quads
    deletions = [q for q in quads if q[1] == RDF.type and q[2] == URIRef(PAT + "Deletion")]
    assert len(deletions) == 1


def test_ho7_t6_a_stale_sequence_changes_nothing():
    ds = _dataset(TOMBSTONE, data=_data())
    before = _quads(ds)
    _run(ds, TOMBSTONE, expected_seq=7)
    assert _quads(ds) == before


def test_ho7_t7_after_a_tombstone_a_replace_is_refused_by_the_tombstone_guard():
    data = _data()
    ds = _dataset(TOMBSTONE, data=data)
    _run(ds, TOMBSTONE, txn="a")
    before = _quads(ds)
    _run(ds, REPLACE, txn="b", expected_seq=2, payload={(ROOT, _px("name"), Literal("Back"))})
    assert _quads(ds) == before


def test_ho7_t7b_a_tombstone_leaves_a_copy_of_the_data_in_the_default_graph_alone():
    data = _data()
    ds = _dataset(TOMBSTONE, data=data, default_copy=data)
    _run(ds, TOMBSTONE)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        assert set(ds.default_context) == set(data)


# ---- the new templates meet the static checks


@pytest.mark.parametrize("fixture", [PROJECT_EXAMPLE, DATASET_GUARD_FIXTURE])
def test_ho7_t8_the_new_templates_pass_the_static_checks(fixture):
    compiled, _ = compile_to_graph(witness._load_fixture(fixture))
    assert templatecheck.check_compiled(compiled) == []
