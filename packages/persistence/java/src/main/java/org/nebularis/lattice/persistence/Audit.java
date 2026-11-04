// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * The outcome of an audit (ADR-A132 decisions 2 and 3, ADR-A123 addendum of 2026-10-20). An audit's query returns the rows that violate an
 * invariant, so a clean dataset returns none, and so does a query that read nothing. {@link #outcome} tells them apart with three values.
 */
public final class Audit {
    private Audit() {}

    /** The marker of the {@code logGraphs} slot in an instantiated audit. */
    public static final String LOG_GRAPHS_SLOT = "{{{logGraphs}}}";

    /**
     * The outcome of an audit that returned {@code rows}. It is FAILED if it returned a row. It is NOTHING_EXAMINED if it returned none and
     * {@code logGraphs} is an empty list, or {@code examined} is zero. Otherwise CLEAN. {@code logGraphs} is null for an audit that lists
     * none, and {@code examined} is null where the caller did not count.
     */
    public static AuditOutcome outcome(Collection<?> rows, Collection<?> logGraphs, Long examined) {
        if (!rows.isEmpty()) return AuditOutcome.FAILED;
        if ((logGraphs != null && logGraphs.isEmpty()) || (examined != null && examined == 0)) return AuditOutcome.NOTHING_EXAMINED;
        return AuditOutcome.CLEAN;
    }

    /** The text of the {@code logGraphs} slot, from typed IRIs only. A plain string is validated as an IRI. */
    public static String registryText(Collection<?> logGraphs) {
        return logGraphs.stream().map(g -> g instanceof Iri i ? i.toString() : Iri.of((String) g).toString()).collect(Collectors.joining(" "));
    }

    /** The query that counts the receipts an audit over {@code logGraphs} can read. A count of zero means the audit examined nothing. */
    public static String examinedQuery(OperationContract operation, Collection<?> logGraphs) {
        String graphs = java.util.stream.Stream.concat(operation.binding("pinnedGraph").stream(), java.util.stream.Stream.of(registryText(logGraphs)))
            .filter(s -> !s.isEmpty()).collect(Collectors.joining(" "));
        return "SELECT (COUNT(?r) AS ?n) WHERE { VALUES ?log { " + graphs + " } GRAPH ?log { ?r a <" + Namespaces.PAT + "Revision> } }";
    }

    /**
     * Run {@code query}, the instantiated text of the audit {@code operation}, and report its outcome. {@code logGraphs} fills the slot of
     * an audit that has one and may be null for an audit that has none. It is counted so that an audit that read no receipt is not reported clean.
     */
    public static AuditResult run(SelectClient client, OperationContract operation, String query, Collection<?> logGraphs) {
        if (operation.kind() != OperationKind.AUDIT) throw new IllegalArgumentException(operation.templateId() + " is not an audit");
        if (operation.examines() != null) {
            if (logGraphs == null) {
                throw new IllegalArgumentException(operation.templateId() + " examines " + operation.examines() + ", which must be given, empty if it lists none");
            }
            query = query.replace(LOG_GRAPHS_SLOT, registryText(logGraphs));
        }
        List<Map<String, Object>> rows = List.copyOf(client.select(query));
        Long examined = null;
        if (operation.examines() != null && logGraphs != null && !logGraphs.isEmpty() && rows.isEmpty()) {
            List<Map<String, Object>> counted = client.select(examinedQuery(operation, logGraphs));
            examined = counted.isEmpty() ? 0L : Long.parseLong(String.valueOf(counted.get(0).values().iterator().next()));
        }
        boolean lists = operation.examines() != null && !operation.examines().isEmpty();
        return new AuditResult(outcome(rows, lists ? logGraphs : null, examined), rows, examined);
    }
}
