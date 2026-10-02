// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import java.util.Objects;

public record LiteralPart(String text) implements Part {
    public LiteralPart {
        Objects.requireNonNull(text, "text");
    }

    @Override
    public String displayText() {
        return text;
    }
}
