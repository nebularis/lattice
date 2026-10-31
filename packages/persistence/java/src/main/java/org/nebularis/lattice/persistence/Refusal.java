// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.Comparator;

/** One reason a request is refused (ADR-A132 decision 2). {@code code} is a stable name and {@code where} the parameter or part it is about. */
public record Refusal(String code, String where, String reason) implements Comparable<Refusal> {
    private static final Comparator<Refusal> ORDER = Comparator.comparing(Refusal::code, Text.ORDER)
        .thenComparing(Refusal::where, Text.ORDER).thenComparing(Refusal::reason, Text.ORDER);

    @Override public int compareTo(Refusal o) { return ORDER.compare(this, o); }

    @Override public String toString() { return code + " (" + where + "): " + reason; }
}
