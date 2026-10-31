// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/** A compiled profile that does not say what a caller needs (ADR-A132 decision 3). */
public class ProfileException extends IllegalArgumentException {
    private static final long serialVersionUID = 1L;

    public ProfileException(String message) {
        super(message);
    }

    public ProfileException(String message, Throwable cause) {
        super(message, cause);
    }
}
