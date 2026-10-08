// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Locale;

public enum ValueType {
    MONEY, PERCENTAGE, DATE, DURATION, NUMBER, TEXT, PARTY;

    public static ValueType fromJson(String value) {
        try {
            return valueOf(value.toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("unknown ValueType: " + value, e);
        }
    }

    @JsonValue
    public String toJson() {
        return name().toLowerCase(Locale.ROOT);
    }

    /** {@code wap:} + this value type, capitalised: MONEY -> "Money". */
    public String capitalizedName() {
        String lower = toJson();
        return Character.toUpperCase(lower.charAt(0)) + lower.substring(1);
    }
}
