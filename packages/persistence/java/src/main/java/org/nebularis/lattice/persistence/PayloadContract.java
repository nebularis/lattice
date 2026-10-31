// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.List;

/**
 * What an operation takes as the aggregate's triples (ADR-A132 decision 2). {@code root} names the parameter whose value the walk starts at,
 * and is null where the profile names none. {@code shape} is the family's boundary shape, null where it names none, and then only the form of
 * the payload is checked. {@code recordClasses} are the classes the profile names as records ({@code dal:recordClass}).
 */
public record PayloadContract(String parameter, String root, List<EdgeContract> edges, String shape, List<String> recordClasses) {
    public PayloadContract {
        edges = List.copyOf(edges);
        recordClasses = List.copyOf(recordClasses);
    }

    public PayloadContract(String parameter, String root, List<EdgeContract> edges, String shape) { this(parameter, root, edges, shape, List.of()); }

    PayloadContract withEdges(List<EdgeContract> edges) { return new PayloadContract(parameter, root, edges, shape, recordClasses); }
}
