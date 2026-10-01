// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Locale;

/** Not produced by WA2. {@link org.nebularis.lattice.authoring.validation.ValidationResult} keeps
 *  its own severity string, computed from Jena's SHACL severity node. Used directly from WA3's
 *  {@code template.Finding} onward, including in HTTP response bodies (WA4). */
public enum Severity {
    VIOLATION, WARNING, INFO;

    public static Severity fromJson(String value) {
        return valueOf(value.toUpperCase(Locale.ROOT));
    }

    @JsonValue
    public String toJson() {
        return name().toLowerCase(Locale.ROOT);
    }
}
