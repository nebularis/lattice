// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import java.util.List;
import java.util.Objects;

public record Section(String sectionKey, List<Element> elements) {
    public Section {
        Objects.requireNonNull(sectionKey, "sectionKey");
        elements = List.copyOf(elements);
    }
}
