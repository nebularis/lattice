// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/** A value that cannot be safely encoded as an RDF term (ADR-A132 decision 2). */
public class SparqlTermException extends IllegalArgumentException {
    private static final long serialVersionUID = 1L;

    public SparqlTermException(String message) {
        super(message);
    }

    public SparqlTermException(String message, Throwable cause) {
        super(message, cause);
    }
}
