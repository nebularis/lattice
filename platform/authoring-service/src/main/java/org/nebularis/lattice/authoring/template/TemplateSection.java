// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.template;

import java.util.List;
import org.nebularis.lattice.authoring.model.ElementKind;
import org.nebularis.lattice.authoring.model.TermKind;

public record TemplateSection(
    String sectionKey,
    String heading,
    List<ElementKind> elementKinds,
    List<TermKind> allowedTermKinds,
    boolean required,
    String guidance
) {
    public TemplateSection {
        elementKinds = List.copyOf(elementKinds);
        allowedTermKinds = List.copyOf(allowedTermKinds);
    }
}
