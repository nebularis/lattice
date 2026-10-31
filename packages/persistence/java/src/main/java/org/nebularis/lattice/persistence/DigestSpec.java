// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.List;

/** The digest contract of one operation as a profile declares it: the algorithm and the parts, sorted by order (ADR-A123 fifth addendum). */
public record DigestSpec(String algorithm, List<DigestPart> parts) {
    public DigestSpec {
        parts = List.copyOf(parts);
    }
}
