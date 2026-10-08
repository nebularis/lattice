// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.validation;

import java.util.List;

/** {@code conforms} is true when no result has severity {@code violation} (plan \u00a72.3, WA2 Shapes). */
public record ValidationReportView(boolean conforms, List<ValidationResult> results) {
    public ValidationReportView {
        results = List.copyOf(results);
    }
}
