// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.List;
import java.util.Map;

/** The result of {@link Audit#run}: the outcome, the rows the audit returned and the receipt count, null where it was not counted. */
public record AuditResult(AuditOutcome outcome, List<Map<String, Object>> rows, Long examined) {
    public AuditResult {
        rows = List.copyOf(rows);
    }
}
