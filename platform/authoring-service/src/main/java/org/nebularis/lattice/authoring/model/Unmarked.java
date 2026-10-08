// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import java.util.Objects;

public record Unmarked(String sectionKey, String text) {
    public Unmarked {
        Objects.requireNonNull(text, "text");
    }
}
