// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.auth;

/** Who made a request, as an {@link Authenticator} found them: a name the provider vouches for, and whether they administer the studio. */
public record Principal(String name, boolean admin) {
    public Principal {
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("a principal has a name");
        }
    }
}
