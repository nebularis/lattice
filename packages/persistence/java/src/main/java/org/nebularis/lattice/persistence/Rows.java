// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

/** The rows of an append's events. The text fills the {@code eventRows} slot, which sits in the update's {@code WHERE} (ADR-A132 decision 2). */
public record Rows(List<EventRow> rows) {
    public Rows {
        rows = new LinkedHashSet<>(rows).stream().sorted(
            Comparator.comparingLong(EventRow::opSeq)
                .thenComparing((EventRow r) -> r.event().toString(), Text.ORDER)
                .thenComparing((EventRow r) -> r.eventType().toString(), Text.ORDER)).toList();
    }

    /** Rows of these events. */
    public static Rows of(EventRow... rows) { return new Rows(List.of(rows)); }

    /** The {@code VALUES} rows, one per line. */
    public String sparql() { return rows.stream().map(EventRow::sparql).collect(Collectors.joining("\n")); }

    /** The triples the rows assert, as a payload. */
    public Payload payload() {
        Set<Triple> all = new HashSet<>();
        for (EventRow r : rows) all.addAll(r.triples());
        return new Payload(all);
    }

    public int size() { return rows.size(); }
}
