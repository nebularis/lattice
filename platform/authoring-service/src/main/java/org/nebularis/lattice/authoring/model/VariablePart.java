// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import java.util.Objects;

public record VariablePart(String variableKey, String text) implements Part {
    public VariablePart {
        Objects.requireNonNull(variableKey, "variableKey");
        Objects.requireNonNull(text, "text");
    }

    @Override
    public String displayText() {
        return text;
    }
}
