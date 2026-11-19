# SPDX-License-Identifier: MPL-2.0
"""The confirmation read and its classification, against contracts/persistence/vectors.json (ADR-A132, STD-312)."""

from __future__ import annotations

import pytest
from rdflib import Dataset, Literal as RdfLiteral, URIRef

from lattice_persistence import (
    Classification, ConfirmationError, Iri, Lit, Outcome, OperationKind, ProfileOperation, classify, confirm, confirm_query, confirms,
)
from lattice_persistence.contract import ParameterContract
from test_vectors import rdflib_term

GRAPHS = ("txnGraph", "datasetGraph", "datasetNode", "metaGraphPrefix", "dataGraph", "keysGraph")


class DatasetClient:
    """The adopter's client over an in-memory rdflib dataset, which holds the quads of a vector."""

    def __init__(self, quads: list) -> None:
        self.dataset = Dataset()
        for q in quads:
            self.dataset.graph(URIRef(q["graph"])).add((rdflib_term(q["s"]), rdflib_term(q["p"]), rdflib_term(q["o"])))
        self.queries: list = []

    def select(self, query: str):
        self.queries.append(query)
        return [{"fact": str(r["fact"]), "value": r["value"]} for r in self.dataset.query(query)]


def operation(v: dict) -> ProfileOperation:
    o = v["operation"]
    kind = OperationKind(o["kind"])
    claiming = kind not in (OperationKind.KEY_CLAIM_WRITE, OperationKind.KEY_CLAIM_WRITE_DUAL)
    parameters = (ParameterContract("txnId", "Iri", True), ParameterContract("requestDigest", "Digest", True)) if claiming else ()
    return ProfileOperation(None, o["templateId"], kind, 1, parameters, None, None, tuple(sorted((k, f"<{x}>") for k, x in o["bindings"].items())))


def values(v: dict) -> dict:
    out = {}
    for name, form in v["values"].items():
        if "iri" in form:
            out[name] = Iri.encode(form["iri"])
        elif "int" in form:
            out[name] = Lit(str(form["int"]), "http://www.w3.org/2001/XMLSchema#long")
        else:
            out[name] = form["string"]
    return out


def test_every_confirmation_vector_through_a_store(vectors):
    for v in vectors["confirmationChecks"]:
        got = confirm(DatasetClient(v["quads"]), operation(v), values(v))
        assert (got.outcome.value, got.classification.value, got.revision) == (v["outcome"], v["classification"], v["revision"]), v["id"]
        assert got.reason, v["id"]


def test_the_vectors_cover_every_outcome_and_every_cause(vectors):
    assert {v["outcome"] for v in vectors["confirmationChecks"]} == {o.value for o in Outcome}
    assert {v["classification"] for v in vectors["confirmationChecks"]} == {c.value for c in Classification}


def test_each_outcome_is_that_of_its_classification():
    assert {c: c.outcome for c in Classification} == {
        Classification.APPLIED: Outcome.APPLIED, Classification.IDEMPOTENCY_KEY_REUSE: Outcome.REFUSED,
        **{c: Outcome.LOST_RACE for c in Classification if c not in (Classification.APPLIED, Classification.IDEMPOTENCY_KEY_REUSE)},
    }


def test_the_read_asks_only_what_the_operations_guards_test(vectors):
    by_id = {v["id"]: v for v in vectors["confirmationChecks"]}
    replace = by_id["cf-epoch-changed"]
    query = confirm_query(operation(replace), values(replace))
    assert query.startswith("SELECT ?fact ?value WHERE")
    assert all(f'"{f}"' in query for f in ("claimRev", "claimDigest", "datasetEpoch", "rowSeq", "rowEpoch", "rowDeleted"))
    assert "dataPresent" not in query
    row_level = by_id["cf-the-dataset-epoch-is-not-read-when-the-guard-is-the-row's"]
    assert "datasetEpoch" not in confirm_query(operation(row_level), values(row_level))
    create = by_id["cf-already-exists-by-the-row"]
    assert "rowEpoch" not in confirm_query(operation(create), values(create))
    composite = by_id["cf-already-exists-by-data-with-no-row"]
    assert "dataPresent" in confirm_query(operation(composite), values(composite))


def test_the_read_holds_nothing_of_the_request_but_typed_iris(vectors):
    v = next(v for v in vectors["confirmationChecks"] if v["id"] == "cf-reused-key")
    query = confirm_query(operation(v), values(v))
    assert v["values"]["requestDigest"]["string"] not in query
    hostile = values(v) | {"root": "urn:x> } } DROP ALL #"}
    with pytest.raises(ConfirmationError):
        confirm_query(operation(v), hostile)


def test_an_operation_that_records_no_claim_is_not_confirmed(vectors):
    v = next(v for v in vectors["confirmationChecks"] if v["id"] == "cf-applied-replace")
    op = ProfileOperation(None, "bootstrap-version-row", OperationKind.BOOTSTRAP, 1, (), None, None, operation(v).bindings)
    assert not confirms(op) and confirms(operation(v))
    with pytest.raises(ConfirmationError):
        confirm_query(op, values(v))
    with pytest.raises(ConfirmationError):
        classify(op, values(v), [])


def test_a_request_without_what_the_read_needs_is_refused(vectors):
    v = next(v for v in vectors["confirmationChecks"] if v["id"] == "cf-applied-replace")
    with pytest.raises(ConfirmationError):
        confirm_query(operation(v), {k: x for k, x in values(v).items() if k != "txnId"})
    stripped = ProfileOperation(None, "cas-replace-named-graph", OperationKind.REPLACE, 1, operation(v).parameters, None, None, ())
    with pytest.raises(ConfirmationError):
        confirm_query(stripped, values(v))


def test_the_reasons_say_what_was_found(vectors):
    by_id = {v["id"]: v for v in vectors["confirmationChecks"]}

    def reason(id_: str) -> str:
        v = by_id[id_]
        return classify(operation(v), values(v), DatasetClient(v["quads"]).select(confirm_query(operation(v), values(v)))).reason

    assert "position 6, not 4" in reason("cf-precondition-failed")
    assert "epoch is 4, not 3" in reason("cf-epoch-changed")
    assert "earlier attempt" in reason("cf-applied-replace")
    assert "tombstoned" in reason("cf-gone")


def test_the_rows_of_a_client_may_hold_numbers_and_plain_text(vectors):
    v = next(v for v in vectors["confirmationChecks"] if v["id"] == "cf-precondition-failed")
    rows = [{"fact": "rowSeq", "value": 6}, {"fact": "rowEpoch", "value": "3"}, {"fact": "datasetEpoch", "value": RdfLiteral(3)}]
    assert classify(operation(v), values(v), rows).classification is Classification.PRECONDITION_FAILED
