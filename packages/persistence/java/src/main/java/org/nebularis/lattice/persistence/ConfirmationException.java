// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/** A write that cannot be confirmed, because its operation records no claim to read or the request lacks what the read needs. */
public class ConfirmationException extends IllegalArgumentException {
    private static final long serialVersionUID = 1L;

    public ConfirmationException(String message) { super(message); }

    public ConfirmationException(String message, Throwable cause) { super(message, cause); }
}
