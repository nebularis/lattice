// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import java.util.Locale;

/** Not produced by WA2. {@link org.nebularis.lattice.authoring.validation.ValidationResult} keeps
 *  its own severity string, computed from Jena's SHACL severity node. */
public enum Severity {
    VIOLATION, WARNING, INFO;

    public static Severity fromJson(String value) {
        return valueOf(value.toUpperCase(Locale.ROOT));
    }

    public String toJson() {
        return name().toLowerCase(Locale.ROOT);
    }
}
