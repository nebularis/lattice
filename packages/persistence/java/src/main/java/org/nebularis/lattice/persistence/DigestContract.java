// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * What the request digest is taken over, as the compiler derives it from an operation: the target it names, the sequence it expects and the
 * slots whose triples the request asserts (ADR-A132 decision 2). Any of {@code target}, {@code expected}, {@code payload}, {@code add} and
 * {@code delete} may be null.
 */
public record DigestContract(String target, String expected, String payload, List<String> event, String add, String delete) {
    public DigestContract {
        event = List.copyOf(event);
    }

    /** The role and sources of each part, in order. The event part replaces the payload part for an append. */
    public List<Map.Entry<String, List<String>>> parts() {
        List<Map.Entry<String, List<String>>> out = new ArrayList<>();
        out.add(Map.entry("OperationKindPart", List.of()));
        out.add(Map.entry("TargetPart", target != null ? List.of(target) : List.of()));
        out.add(Map.entry("ExpectedSeqPart", expected != null ? List.of(expected) : List.of()));
        out.add(!event.isEmpty() ? Map.entry("EventPart", event) : Map.entry("PayloadPart", payload != null ? List.of(payload) : List.<String>of()));
        if (add != null) out.add(Map.entry("AddPart", List.of(add)));
        if (delete != null) out.add(Map.entry("DelPart", List.of(delete)));
        return out;
    }
}
