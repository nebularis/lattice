# SPDX-License-Identifier: MPL-2.0
"""Reading a compiled profile's contract, and the digest of requests to its operations."""

from __future__ import annotations

import pytest
from rdflib.namespace import XSD

from lattice_persistence import EventRow, Iri, Lit, OperationKind, Payload, Rows, Triple, read_contracts
from lattice_persistence.digest import DigestError, request_digest, request_input

T = lambda s, p, o: Triple(Iri.encode(s), Iri.encode(p), Iri.encode(o) if isinstance(o, str) else o)


def by_template(profile, template):
    return next(o for o in read_contracts(profile) if o.template_id == template)


def test_reads_every_operation_and_its_parameters(profiles):
    ops = read_contracts(profiles["baseline-single-class"])
    assert {o.kind for o in ops} >= {OperationKind.CREATE, OperationKind.REPLACE, OperationKind.TOMBSTONE, OperationKind.AUDIT}
    replace = by_template(profiles["baseline-single-class"], "cas-replace-named-graph-patch-log")
    assert replace.parameter("expectedSeq").kind == "Position" and replace.parameter("requestDigest").kind == "Digest"
    assert replace.payload.parameter == "payloadTriples" and replace.payload.root == "root"
    assert replace.version >= 1


def test_digest_parts_in_order(profiles):
    replace = by_template(profiles["baseline-single-class"], "cas-replace-named-graph-patch-log")
    assert [p.role for p in replace.digest.parts] == [
        "OperationKindPart", "TargetPart", "ExpectedSeqPart", "PayloadPart", "AddPart", "DelPart"]
    assert replace.digest.algorithm == "SHA-256"
    append = by_template(profiles["append-stream-dataset-guard"], "append-event-dataset-guard")
    assert append.digest.as_pairs()[-1] == ("EventPart", ("eventRows", "eventTriples"))
    assert by_template(profiles["baseline-single-class"], "key-claim-write").digest is None


def test_replace_digest_from_a_profile(profiles):
    replace = by_template(profiles["baseline-single-class"], "cas-replace-named-graph-patch-log")
    a, b = T("urn:example:r", "urn:example:p", "urn:example:a"), T("urn:example:r", "urn:example:p", "urn:example:b")
    values = {"root": Iri.encode("urn:example:r"), "expectedSeq": 3, "payloadTriples": Payload.of(a, b),
              "assertTriples": Payload.of(b), "retractTriples": Payload.of()}
    one = request_digest(replace, values)
    assert len(one) == 64 and one == request_digest(replace, dict(values))
    assert request_digest(replace, {**values, "assertTriples": Payload.of(), "retractTriples": Payload.of(b)}) != one
    assert request_digest(replace, {**values, "expectedSeq": 4}) != one
    assert request_input(replace, values).startswith(b"7:Replace13:urn:example:r1:3")


def test_append_digest_merges_rows_and_triples_into_one_part(profiles):
    append = by_template(profiles["append-stream-dataset-guard"], "append-event-dataset-guard")
    when = Lit("2026-10-20T10:00:00Z", str(XSD.dateTime))
    rows = Rows((EventRow(Iri.encode("urn:e:1"), Iri.encode("urn:T"), 1, when),))
    values = {"stream": "urn:example:s", "eventRows": rows, "eventTriples": Payload.of(T("urn:e:1", "urn:example:p", "urn:example:o"))}
    data = request_input(append, values)
    assert data.startswith(b"6:Append13:urn:example:s0:")
    # an empty expected seq and exactly one content part
    assert data.count(b"urn:e:1> <urn:example:p>") == 1
    assert request_digest(append, {**values, "eventTriples": Payload.of()}) != request_digest(append, values)


def test_a_missing_source_is_named(profiles):
    replace = by_template(profiles["baseline-single-class"], "cas-replace-named-graph-patch-log")
    with pytest.raises(DigestError, match="retractTriples"):
        request_digest(replace, {"root": "urn:example:r", "expectedSeq": 1, "payloadTriples": Payload.of(), "assertTriples": Payload.of()})


def test_a_bare_string_is_not_a_payload(profiles):
    replace = by_template(profiles["baseline-single-class"], "cas-replace-named-graph-patch-log")
    with pytest.raises(DigestError, match="Payload"):
        request_digest(replace, {"root": "urn:example:r", "expectedSeq": 1, "payloadTriples": "<urn:a> <urn:b> <urn:c> .",
                                 "assertTriples": Payload.of(), "retractTriples": Payload.of()})


def test_an_operation_without_a_digest_refuses(profiles):
    with pytest.raises(DigestError):
        request_digest(by_template(profiles["baseline-single-class"], "key-claim-write"), {})
