// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/** A ground RDF term of a payload, an IRI or a literal. A blank node has no type here, so none can be built (ADR-A132 decision 2). */
public sealed interface Term permits Iri, Lit {
    /** The canonical N-Triples form, the text the request digest is taken over. */
    String nt();

    /** The encoded SPARQL form, the text that fills a request-time slot. */
    String sparql();
}
