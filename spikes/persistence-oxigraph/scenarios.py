# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The experiments of formal-methods track H, H1.3 and H1.4a, as functions that return data.

Each takes the update the persistence compiler actually generates and runs it on
:class:`~oxigraph_backend.OxigraphBackend`. Nothing here is a test of the compiler. It shows
what a generated update does to data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from persistence import templatecheck, witness
from persistence.compiler import compile_to_graph

from oxigraph_backend import OxigraphBackend, iri, literal, XSD
import pyoxigraph as ox

EX = "https://example.org/lending#"
PAT = "https://example.org/lattice/patterns#"


def generated_update(fixture: Path, template: str) -> str:
    """The text of the first generated operation that uses ``template``, as ``instantiate``
    renders it. Only the request-time slots are left to the caller. ``_load_fixture`` is the
    witness harness's loader, which understands the ``# base:`` patch format."""
    compiled, _ = compile_to_graph(witness._load_fixture(fixture))
    return next(op.text for op in templatecheck.operations(compiled) if op.template == template)


def _meta_graph(update: str) -> str:
    return re.search(r"GRAPH <(urn:g:meta/\d+)>", update).group(1)


# ---- composite boundary: what a replace leaves behind -----------------------------------------


def composite_sweep(bound_property: str, with_payment: bool) -> list[str]:
    """Run ``cas-replace-composite-property`` on an order and return the subjects that still have
    triples afterwards. ``bound_property`` is the local name the compiler binds, ``lineItem`` or
    ``payment``. An empty list means the replace swept everything."""
    update = generated_update(witness.EXAMPLES_DIR / "composite-property-boundary-shacl.ttl", "cas-replace-composite-property")
    meta = _meta_graph(update)
    backend, order = OxigraphBackend(), iri("urn:order:1")
    backend.add(order, iri(PAT + "epoch"), literal(1), iri(meta))
    backend.add(order, iri(PAT + "seq"), literal(1, XSD + "long"), iri(meta))
    rows = [("urn:order:1", "status", literal("open")), ("urn:order:1", "lineItem", iri("urn:li:1")), ("urn:li:1", "sku", literal("ABC"))]
    if with_payment:
        rows += [("urn:order:1", "payment", iri("urn:pay:1")), ("urn:pay:1", "amount", literal("10"))]
    for subject, predicate, obj in rows:
        backend.add(iri(subject), iri(EX + predicate), obj)
    update = update.replace(f"<{EX}lineItem>", f"<{EX}{bound_property}>")
    backend.update(
        update,
        {
            "root": order, "epoch": literal(1), "expectedSeq": literal(1, XSD + "long"),
            "nextSeq": literal(2, XSD + "long"), "newRev": iri("urn:rev:2"),
            "txnId": iri("urn:txn:a"), "requestDigest": literal("d"),
        },
    )
    return sorted(q.subject.value for q in backend.quads(ox.DefaultGraph()))


# ---- append-event: what a missing parameter does ----------------------------------------------


@dataclass(frozen=True)
class StreamState:
    label: str
    quads: int
    sequence: list[str]
    revision_records: int
    head_pointers: int
    claim_predicates: list[str]

    def __str__(self) -> str:
        return (
            f"{self.label}: {self.quads} quads | seq={self.sequence} | revision records={self.revision_records}"
            f" | head pointers={self.head_pointers} | txn claim has={self.claim_predicates}"
        )


def _append_parameters() -> dict:
    return {
        "stream": iri("urn:stream:1"), "epoch": literal(1), "txnId": iri("urn:txn:a"),
        "requestDigest": literal("abc"), "event": iri("urn:event:1"), "eventType": iri("urn:type:E"),
        "opSeq": literal(1), "occurredAt": literal("2026-10-09T00:00:00Z"),
        "revBase": literal("urn:rev:orders/1/e0000000000000000001/"),
    }


def _stream_state(backend: OxigraphBackend, meta: str, label: str) -> StreamState:
    quads = backend.quads()
    return StreamState(
        label=label,
        quads=len(quads),
        sequence=[q.object.value for q in quads if q.predicate.value == PAT + "seq" and q.graph_name.value == meta],
        revision_records=backend.count(PAT + "target"),
        head_pointers=backend.count(PAT + "head"),
        claim_predicates=sorted(q.predicate.value.split("#")[-1] for q in quads if q.subject.value == "urn:txn:a"),
    )


def append_event_runs() -> list[StreamState]:
    """Three runs of the generated ``append-event`` update on one stream: every parameter supplied,
    the caller forgetting ``$revBase``, then a retry with the same transaction id and every
    parameter. No run raises an error. See TD-26."""
    update = generated_update(witness.WITNESS_DIR / "template-append-event.ttl", "append-event")
    meta = re.search(r"DELETE \{ GRAPH <([^>]+)>", update).group(1)
    full = _append_parameters()
    without = {k: v for k, v in full.items() if k != "revBase"}

    def fresh() -> OxigraphBackend:
        backend = OxigraphBackend()
        backend.add(iri("urn:stream:1"), iri(PAT + "epoch"), literal(1), iri(meta))
        backend.add(iri("urn:stream:1"), iri(PAT + "seq"), literal(0, XSD + "long"), iri(meta))
        return backend

    states = []
    backend = fresh()
    backend.update(update, full)
    states.append(_stream_state(backend, meta, "A. every parameter supplied      "))
    backend = fresh()
    backend.update(update, without)
    states.append(_stream_state(backend, meta, "B. caller forgets $revBase       "))
    backend.update(update, full)
    states.append(_stream_state(backend, meta, "C. retry, same txn id, all params"))
    return states
