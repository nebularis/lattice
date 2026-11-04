// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.List;

/** One part of a digest contract: its position, its role and the names of the parameters and slots it is taken from (ADR-A123 fifth addendum). */
public record DigestPart(int order, String role, List<String> sources) implements Comparable<DigestPart> {
    public DigestPart {
        sources = List.copyOf(sources);
    }

    public DigestPart(int order, String role) { this(order, role, List.of()); }

    @Override public int compareTo(DigestPart o) {
        int c = Integer.compare(order, o.order);
        if (c == 0) c = Text.compare(role, o.role);
        for (int i = 0; c == 0 && i < Math.min(sources.size(), o.sources.size()); i++) c = Text.compare(sources.get(i), o.sources.get(i));
        return c != 0 ? c : Integer.compare(sources.size(), o.sources.size());
    }
}
