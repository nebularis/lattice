// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.template;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.function.Function;
import org.nebularis.lattice.authoring.model.ElementKind;
import org.nebularis.lattice.authoring.model.TermKind;

/**
 * A document template: which sections a document of this kind has, what may go in each, and which
 * term kinds each is expected to read as. The template's variable declarations are not parsed; the
 * add-in reads them from {@link TemplateCatalog#raw(String)}.
 */
public record AuthoringTemplate(
    String templateId,
    String version,
    String title,
    String domain,
    List<TemplateSection> sections
) {
    public AuthoringTemplate {
        sections = List.copyOf(sections);
    }

    /** Reads an already schema-validated {@code authoring-template} node. */
    public static AuthoringTemplate from(JsonNode node) {
        List<TemplateSection> sections = new ArrayList<>();
        for (JsonNode section : node.get("sections")) {
            sections.add(new TemplateSection(
                section.get("sectionKey").asText(),
                section.get("heading").asText(),
                values(section.get("elementKinds"), ElementKind::fromJson),
                values(section.get("allowedTermKinds"), TermKind::fromJson),
                section.get("required").asBoolean(),
                section.get("guidance").asText()
            ));
        }
        return new AuthoringTemplate(
            node.get("templateId").asText(),
            node.get("version").asText(),
            node.get("title").asText(),
            node.get("domain").asText(),
            sections
        );
    }

    public Optional<TemplateSection> section(String sectionKey) {
        return sections.stream().filter(section -> section.sectionKey().equals(sectionKey)).findFirst();
    }

    public TemplateSummary summary() {
        return new TemplateSummary(templateId, title, domain, version);
    }

    private static <T> List<T> values(JsonNode array, Function<String, T> parse) {
        List<T> values = new ArrayList<>();
        for (JsonNode value : array) {
            values.add(parse.apply(value.asText()));
        }
        return values;
    }
}
