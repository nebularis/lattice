// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import java.util.Objects;

public record VariableDeclaration(String variableKey, String label, ValueType valueType) {
    public VariableDeclaration {
        Objects.requireNonNull(variableKey, "variableKey");
        Objects.requireNonNull(label, "label");
        Objects.requireNonNull(valueType, "valueType");
    }
}
