# SPDX-License-Identifier: MPL-2.0
# NB: This file has been produced using GenAI
"""H2.12: a payload written as rows for the rows replace (dal:TripleRows). The digest does not depend on the encoding, the rows are the
same terms as the N-Triples form, and `slot_text` picks the text by the contract. Validation Pack: docs/developer/validation/FMH-H2-12.md."""
from __future__ import annotations

import dataclasses

import pytest

from lattice_persistence import Iri, Lit, Payload, Rows, Triple, read_contracts, request_digest, slot_text
from lattice_persistence.payload import PayloadError

A, NAME, P = Iri.encode("urn:ex:a"), Iri.encode("urn:ex:name"), Iri.encode("urn:ex:p")


def _payload() -> Payload:
    return Payload.of(Triple(A, NAME, Lit("Ada")), Triple(A, P, Iri.encode("urn:ex:b")), Triple(A, NAME, Lit("Ada", lang="en")))


def test_h2_12_l1_a_row_holds_the_same_terms_as_the_triple_without_the_full_stop():
    for t in _payload().triples:
        assert t.row() == "(" + t.sparql().removesuffix(" .") + ")"


def test_h2_12_l2_rows_are_sorted_and_free_of_duplicates():
    p = Payload.of(*_payload().triples, Triple(A, NAME, Lit("Ada")))
    lines = p.rows().split("\n")
    assert lines == sorted(lines) and len(lines) == 3 and all(l.startswith("(") and l.endswith(")") for l in lines)


def test_h2_12_l3_an_empty_payload_gives_an_empty_block():
    assert Payload.of().rows() == ""


def _replace(profiles):
    return next(o for o in read_contracts(profiles["baseline-whole-state"]) if o.template_id == "cas-replace-named-graph-patch-log")


def test_h2_12_l4_a_template_replace_declares_ground_ntriples_and_its_slot_text_is_the_triples(profiles):
    op = _replace(profiles)
    assert op.payload.encoding == "GroundNTriples"
    assert slot_text(op, "payloadTriples", _payload()) == _payload().sparql()


def test_h2_12_l5_a_rows_contract_makes_the_slot_text_rows_and_leaves_the_digest_alone(profiles):
    op = _replace(profiles)
    rows_op = dataclasses.replace(op, payload=dataclasses.replace(op.payload, encoding="TripleRows"))
    assert slot_text(rows_op, "payloadTriples", _payload()) == _payload().rows()
    values = {"root": "urn:ex:a", "epoch": 1, "expectedSeq": 3, "nextSeq": 4, "newRev": "urn:rev:a/4", "txnId": "urn:txn:1",
              "payloadTriples": _payload(), "assertTriples": Payload.of(next(iter(_payload().triples))), "retractTriples": Payload.of()}
    assert request_digest(op, values) == request_digest(rows_op, values)


def test_h2_12_l6_event_rows_are_their_own_text_and_anything_else_is_refused(profiles):
    op = _replace(profiles)
    assert slot_text(op, "eventRows", Rows()) == ""
    with pytest.raises(PayloadError):
        slot_text(op, "payloadTriples", "<urn:x> <urn:y> <urn:z> .")
