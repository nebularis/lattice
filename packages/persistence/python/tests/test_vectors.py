# SPDX-License-Identifier: MPL-2.0
"""The library against contracts/persistence/vectors.json, which verify-vectors.py checks without this library."""

from __future__ import annotations

import json

import jsonschema
import pytest
from rdflib import BNode, Literal as RdfLiteral, URIRef

from conftest import CONTRACTS

from lattice_persistence import DigestSpec, EventRow, Iri, Lit, OperationKind, Payload, PayloadError, ProfileOperation, Rows, Triple
from lattice_persistence.contract import DigestPart
from lattice_persistence.digest import request_digest, request_input

SLOT = {"PayloadPart": "payloadTriples", "AddPart": "assertTriples", "DelPart": "retractTriples"}


def typed(t: dict):
    if "literal" in t:
        return Lit(t["literal"], t.get("datatype"), t.get("language"))
    return Iri.encode(t["iri"])


def payload(triples: list) -> Payload:
    return Payload.of(*(Triple(typed(t["s"]), typed(t["p"]), typed(t["o"])) for t in triples))


def rdflib_term(t: dict):
    if "bnode" in t:
        return BNode(t["bnode"])
    if "literal" in t:
        return RdfLiteral(t["literal"], datatype=URIRef(t["datatype"]) if t.get("datatype") else None, lang=t.get("language"))
    return URIRef(t["iri"])


def operation(v: dict) -> tuple:
    """A synthetic operation for a vector, and the values of its request."""
    parts = [DigestPart(1, "OperationKindPart"), DigestPart(2, "TargetPart", ("root",) if v["target"] else ()),
             DigestPart(3, "ExpectedSeqPart", ("expectedSeq",) if v["expected"] is not None else ())]
    values: dict = {"root": v["target"], "expectedSeq": v["expected"]}
    for order, p in enumerate(v["parts"], 4):
        if p["role"] == "EventPart":
            parts.append(DigestPart(order, "EventPart", ("eventRows", "eventTriples")))
            values["eventRows"] = Rows(tuple(
                EventRow(Iri.encode(r["event"]), Iri.encode(r["type"]), r["opSeq"], typed(r["occurredAt"])) for r in p["rows"]))
            values["eventTriples"] = payload(p.get("triples", []))
        else:
            parts.append(DigestPart(order, p["role"], (SLOT[p["role"]],)))
            values[SLOT[p["role"]]] = payload(p.get("triples", []))
    op = ProfileOperation(None, v["id"], OperationKind(v["operationKind"]), 1, (), None, DigestSpec("SHA-256", tuple(parts)))
    return op, values


def test_vectors_conform_to_their_schema(vectors):
    jsonschema.validate(vectors, json.loads((CONTRACTS / "vectors.schema.json").read_text(encoding="utf-8")))


def test_every_ntriples_vector(vectors):
    for v in vectors["ntriples"]:
        assert list(payload(v["triples"]).lines()) == v["canonical"], v["id"]


def test_every_refusal_vector(vectors):
    for v in vectors["refusals"]:
        with pytest.raises(PayloadError):
            Payload.from_rdflib((rdflib_term(t["s"]), rdflib_term(t["p"]), rdflib_term(t["o"])) for t in v["triples"])


def test_every_digest_vector(vectors):
    for v in vectors["digests"]:
        op, values = operation(v)
        assert request_input(op, values).hex() == v["encodedHex"], v["id"]
        assert request_digest(op, values) == v["sha256"], v["id"]


def test_digest_vectors_cover_the_operation_kinds_and_parts(vectors):
    assert {v["operationKind"] for v in vectors["digests"]} >= {"Create", "Replace", "Tombstone", "Append", "AppendVersion"}
    roles = {p["role"] for v in vectors["digests"] for p in v["parts"]}
    assert roles == {"PayloadPart", "EventPart", "AddPart", "DelPart"}


def test_part_order_is_hashed(vectors):
    """Swapping two parts of the contract changes the digest, so the vector for a replace fails. This is the probe of the Pack."""
    v = next(v for v in vectors["digests"] if v["id"] == "digest-replace-patch-log")
    op, values = operation(v)
    parts = list(op.digest.parts)
    parts[3], parts[5] = (DigestPart(4, "PayloadPart", ("retractTriples",)), DigestPart(6, "DelPart", ("payloadTriples",)))
    swapped = ProfileOperation(None, "x", op.kind, 1, (), None, DigestSpec("SHA-256", tuple(parts)))
    assert request_digest(swapped, values) != v["sha256"]
