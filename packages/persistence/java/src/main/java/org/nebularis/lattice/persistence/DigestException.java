// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/** A digest that cannot be computed from the values given (ADR-A132 decision 2). */
public class DigestException extends IllegalArgumentException {
    private static final long serialVersionUID = 1L;

    public DigestException(String message) {
        super(message);
    }

    public DigestException(String message, Throwable cause) {
        super(message, cause);
    }
}
