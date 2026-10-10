#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Run the same scenarios on rdflib and on Oxigraph and compare the results.

The project's own tests use rdflib. This shows that a second, independent engine reaches the
same answers. Run from the repository root:

    python spikes/persistence-oxigraph/rdflib_comparison.py
"""

from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rdflib import Dataset, Literal, URIRef, Variable  # noqa: E402
from rdflib.namespace import XSD  # noqa: E402

from persistence import witness  # noqa: E402
from scenarios import EX, PAT, append_event_runs, composite_sweep, generated_update  # noqa: E402


def rdflib_composite_sweep(bound_property: str, with_payment: bool) -> list[str]:
    update = generated_update(witness.EXAMPLES_DIR / "composite-property-boundary-shacl.ttl", "cas-replace-composite-property")
    meta = re.search(r"GRAPH <(urn:g:meta/\d+)>", update).group(1)
    root = URIRef("urn:order:1")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ds = Dataset()
        ds.graph(URIRef(meta)).add((root, URIRef(PAT + "epoch"), Literal(1)))
        ds.graph(URIRef(meta)).add((root, URIRef(PAT + "seq"), Literal(1, datatype=XSD.long)))
        rows = [(root, "status", Literal("open")), (root, "lineItem", URIRef("urn:li:1")), (URIRef("urn:li:1"), "sku", Literal("ABC"))]
        if with_payment:
            rows += [(root, "payment", URIRef("urn:pay:1")), (URIRef("urn:pay:1"), "amount", Literal("10"))]
        for s, p, o in rows:
            ds.default_context.add((s, URIRef(EX + p), o))
        values = {
            "root": root, "epoch": Literal(1), "expectedSeq": Literal(1, datatype=XSD.long),
            "nextSeq": Literal(2, datatype=XSD.long), "newRev": URIRef("urn:rev:2"),
            "txnId": URIRef("urn:txn:a"), "requestDigest": Literal("d"),
        }
        ds.update(update.replace(f"<{EX}lineItem>", f"<{EX}{bound_property}>"), initBindings={Variable(k): v for k, v in values.items()})
        return sorted({str(s) for s, _, _ in ds.default_context})


def rdflib_append_event_runs() -> list[tuple[list[str], int]]:
    """For each of the three runs, (the sequence counter, the number of revision records)."""
    update = generated_update(witness.WITNESS_DIR / "template-append-event.ttl", "append-event")
    meta = re.search(r"DELETE \{ GRAPH <([^>]+)>", update).group(1)
    stream = URIRef("urn:stream:1")
    full = {
        "stream": stream, "epoch": Literal(1), "txnId": URIRef("urn:txn:a"), "requestDigest": Literal("abc"),
        "event": URIRef("urn:event:1"), "eventType": URIRef("urn:type:E"), "opSeq": Literal(1),
        "occurredAt": Literal("2026-10-09T00:00:00Z"), "revBase": Literal("urn:rev:orders/1/e0000000000000000001/"),
    }
    without = {k: v for k, v in full.items() if k != "revBase"}

    def fresh() -> Dataset:
        ds = Dataset()
        ds.graph(URIRef(meta)).add((stream, URIRef(PAT + "epoch"), Literal(1)))
        ds.graph(URIRef(meta)).add((stream, URIRef(PAT + "seq"), Literal(0, datatype=XSD.long)))
        return ds

    def state(ds: Dataset) -> tuple[list[str], int]:
        seq = [str(o) for o in ds.graph(URIRef(meta)).objects(stream, URIRef(PAT + "seq"))]
        # count across every graph: a revision record lives in a log graph, not the default graph
        return seq, len(list(ds.quads((None, URIRef(PAT + "target"), None, None))))

    def run(ds: Dataset, values: dict) -> None:
        ds.update(update, initBindings={Variable(k): v for k, v in values.items()})

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        out = []
        ds = fresh()
        run(ds, full)
        out.append(state(ds))
        ds = fresh()
        run(ds, without)
        out.append(state(ds))
        run(ds, full)
        out.append(state(ds))
        return out


def compare() -> list[tuple[str, object, object]]:
    """(scenario, rdflib result, Oxigraph result) for every scenario."""
    rows = []
    for label, bound, payment in (("composite, one node property", "lineItem", False),
                                   ("composite, two, bound to lineItem", "lineItem", True),
                                   ("composite, two, bound to payment", "payment", True)):
        rows.append((label, rdflib_composite_sweep(bound, payment), composite_sweep(bound, payment)))
    ox_runs = [(s.sequence, s.revision_records) for s in append_event_runs()]
    for label, a, b in zip(("append-event A, all parameters", "append-event B, no $revBase", "append-event C, retry"),
                           rdflib_append_event_runs(), ox_runs):
        rows.append((label, a, b))
    return rows


def main() -> int:
    agree = True
    print(f"{'scenario':38} {'agree':6} rdflib / Oxigraph")
    for label, a, b in compare():
        agree &= a == b
        print(f"{label:38} {'yes' if a == b else 'NO':6} {a} / {b}")
    return 0 if agree else 1


if __name__ == "__main__":
    raise SystemExit(main())
