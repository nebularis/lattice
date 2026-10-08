// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Locale;

public enum ElementKind {
    CLAUSE, DEFINITION;

    public static ElementKind fromJson(String value) {
        return switch (value) {
            case "clause" -> CLAUSE;
            case "definition" -> DEFINITION;
            default -> throw new IllegalArgumentException("unknown ElementKind: " + value);
        };
    }

    @JsonValue
    public String toJson() {
        return name().toLowerCase(Locale.ROOT);
    }
}
