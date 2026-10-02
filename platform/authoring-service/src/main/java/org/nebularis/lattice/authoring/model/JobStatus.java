// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import com.fasterxml.jackson.annotation.JsonValue;
import java.util.Locale;

public enum JobStatus {
    QUEUED, COMPLETED, FAILED;

    public static JobStatus fromJson(String value) {
        try {
            return valueOf(value.toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalArgumentException("unknown JobStatus: " + value, e);
        }
    }

    @JsonValue
    public String toJson() {
        return name().toLowerCase(Locale.ROOT);
    }
}
