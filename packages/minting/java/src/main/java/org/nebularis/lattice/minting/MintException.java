// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

/** A named refusal. Compare on {@link #kind()}, never on the message. */
public final class MintException extends RuntimeException {
    private static final long serialVersionUID = 1L;

    private final MintError kind;

    public MintException(MintError kind, String message) {
        super(kind + ": " + message);
        this.kind = kind;
    }

    public MintError kind() {
        return kind;
    }
}
