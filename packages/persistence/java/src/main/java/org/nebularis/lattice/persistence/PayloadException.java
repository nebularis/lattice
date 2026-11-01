// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/** A payload, or a row, that cannot be built. It holds a blank node, a term that is not typed, or a value out of range (ADR-A132 decision 2). */
public class PayloadException extends IllegalArgumentException {
    private static final long serialVersionUID = 1L;

    public PayloadException(String message) {
        super(message);
    }

    public PayloadException(String message, Throwable cause) {
        super(message, cause);
    }
}
