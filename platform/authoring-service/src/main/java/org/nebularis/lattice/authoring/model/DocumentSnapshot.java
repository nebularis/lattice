// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

import java.util.List;
import java.util.Objects;

public record DocumentSnapshot(
    String schemaVersion,
    String documentId,
    String templateId,
    String title,
    List<Section> sections,
    List<VariableDeclaration> variables,
    List<Unmarked> unmarked
) {
    public DocumentSnapshot {
        Objects.requireNonNull(schemaVersion, "schemaVersion");
        Objects.requireNonNull(documentId, "documentId");
        Objects.requireNonNull(templateId, "templateId");
        Objects.requireNonNull(title, "title");
        sections = List.copyOf(sections);
        variables = List.copyOf(variables);
        unmarked = List.copyOf(unmarked);
    }
}
