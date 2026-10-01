// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.template;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.nebularis.lattice.authoring.model.Severity;
import org.nebularis.lattice.authoring.model.TermKind;

/**
 * Checks a worker's analysis against the template: a clause that reads as a term kind its section
 * does not allow, or that reads as nothing where its section expects a term. Elements in sections
 * the template does not name are left to {@link TemplateFindings}.
 */
public final class ConformanceChecker {
    private ConformanceChecker() {
    }

    public static List<Finding> check(JsonNode analysis, AuthoringTemplate template) {
        List<Finding> findings = new ArrayList<>();
        for (JsonNode element : analysis.get("elements")) {
            String sectionKey = element.get("sectionKey").asText();
            Optional<TemplateSection> found = template.section(sectionKey);
            if (found.isEmpty()) {
                continue;
            }
            TemplateSection section = found.get();
            String elementId = element.get("elementId").asText();
            String objectId = element.get("objectId").asText();
            JsonNode relationClass = element.get("relationClass");
            if (relationClass == null || relationClass.isNull()) {
                if (!section.allowedTermKinds().isEmpty()) {
                    findings.add(new Finding("no-term-kind", Severity.INFO, sectionKey, elementId,
                        "Element " + objectId + " does not read as a term, but the section '" + section.heading()
                            + "' expects one."));
                }
                continue;
            }
            TermKind kind = TermKind.fromJson(relationClass.asText());
            if (!section.allowedTermKinds().contains(kind)) {
                findings.add(new Finding("term-kind-not-allowed", Severity.WARNING, sectionKey, elementId,
                    "Element " + objectId + " reads as a " + kind.jsonValue() + ", which the section '"
                        + section.heading() + "' does not allow."));
            }
        }
        return findings;
    }
}
