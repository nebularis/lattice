// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import java.util.Objects;

public record ReferencePart(String targetElementId, String text) implements Part {
    public ReferencePart {
        Objects.requireNonNull(targetElementId, "targetElementId");
        Objects.requireNonNull(text, "text");
    }

    @Override
    public String displayText() {
        return text;
    }
}
