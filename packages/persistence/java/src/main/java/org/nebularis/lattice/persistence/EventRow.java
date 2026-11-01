// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.Set;

/** One row of an append: the event, its type, its position in the batch and when it occurred (ADR-A132 decision 2, ADR-A123 fifth addendum). */
public record EventRow(Iri event, Iri eventType, long opSeq, Lit occurredAt) {
    public EventRow {
        if (event == null || eventType == null) throw new PayloadException("an event and its type must be Iri values");
        if (occurredAt == null || occurredAt.datatype() == null) throw new PayloadException("occurredAt must be a typed literal");
    }

    /** {@code opSeq} as an xsd:long literal. */
    public Lit opSeqLiteral() { return new Lit(Long.toString(opSeq), Namespaces.XSD_LONG, null); }

    /** What the row asserts, and what the event part of the digest covers: the type, {@code pat:opSeq} and {@code pat:occurredAt}. */
    public Set<Triple> triples() {
        return Set.of(
            new Triple(event, Iri.of(Namespaces.RDF_TYPE), eventType),
            new Triple(event, Iri.of(Namespaces.PAT + "opSeq"), opSeqLiteral()),
            new Triple(event, Iri.of(Namespaces.PAT + "occurredAt"), occurredAt));
    }

    /** The {@code VALUES} row. */
    public String sparql() {
        return "(" + event + " " + eventType + " " + opSeqLiteral().sparql() + " " + occurredAt.sparql() + ")";
    }
}
