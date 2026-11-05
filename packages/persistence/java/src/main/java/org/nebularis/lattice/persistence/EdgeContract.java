// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.Comparator;

/**
 * One edge of the boundary shape that leads to a node, as a caller's check reads it (ADR-A132 decision 2, ADR-A123 decision 6): where it
 * leaves, the step, its ownership, the class it leads to and its reference mode ({@code ByIdentity} or {@code Pinned}). A null target
 * class or target shape means the profile names none.
 */
public record EdgeContract(String sourceShape, String predicate, boolean inverse, String ownership, String targetClass, String referenceMode, String targetShape)
    implements Comparable<EdgeContract> {
    private static final Comparator<EdgeContract> ORDER = Comparator.comparing(EdgeContract::sourceShape, Text.ORDER)
        .thenComparing(EdgeContract::predicate, Text.ORDER).thenComparing(EdgeContract::inverse)
        .thenComparing(EdgeContract::ownership, Text.ORDER)
        .thenComparing(EdgeContract::targetClass, Comparator.nullsFirst(Text.ORDER))
        .thenComparing(EdgeContract::referenceMode, Text.ORDER)
        .thenComparing(EdgeContract::targetShape, Comparator.nullsFirst(Text.ORDER));

    @Override public int compareTo(EdgeContract o) { return ORDER.compare(this, o); }

    EdgeContract withReferenceMode(String mode) {
        return new EdgeContract(sourceShape, predicate, inverse, ownership, targetClass, mode, targetShape);
    }
}
