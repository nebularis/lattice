// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import java.util.List;
import java.util.Objects;

public record Element(String elementId, ElementKind kind, String definedTerm, List<Part> parts) {
    public Element {
        Objects.requireNonNull(elementId, "elementId");
        Objects.requireNonNull(kind, "kind");
        parts = List.copyOf(parts);
    }

    /** The element's text: its parts' display text, concatenated in part order (plan §2.5). */
    public String text() {
        StringBuilder builder = new StringBuilder();
        for (Part part : parts) {
            builder.append(part.displayText());
        }
        return builder.toString();
    }
}
