// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/** One ground triple of a payload. The subject and predicate are IRIs and the object an IRI or a literal (ADR-A132 decision 2). */
public record Triple(Iri subject, Iri predicate, Term object) {
    public Triple {
        if (subject == null) throw new PayloadException("the subject of a payload triple must be an Iri");
        if (predicate == null) throw new PayloadException("the predicate of a payload triple must be an Iri");
        if (object == null) throw new PayloadException("the object of a payload triple must be an Iri or a Lit");
    }

    /** The canonical N-Triples line. */
    public String nt() { return subject + " " + predicate + " " + object.nt() + " ."; }

    /** The encoded SPARQL form of the triple. */
    public String sparql() { return subject + " " + predicate + " " + object.sparql() + " ."; }
}
