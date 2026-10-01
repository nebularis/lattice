// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.template;

import java.util.ArrayList;
import java.util.List;
import org.nebularis.lattice.authoring.model.DocumentSnapshot;
import org.nebularis.lattice.authoring.model.Element;
import org.nebularis.lattice.authoring.model.Section;
import org.nebularis.lattice.authoring.model.Severity;
import org.nebularis.lattice.authoring.model.Unmarked;

/**
 * Checks a snapshot against its template: missing required sections, sections the template does not
 * name, elements of a kind a section does not allow, and text left outside every element. Findings
 * come in template section order, then in snapshot order.
 */
public final class TemplateFindings {

    public List<Finding> check(DocumentSnapshot snapshot, AuthoringTemplate template) {
        List<Finding> findings = new ArrayList<>();
        List<Section> sections = snapshot.sections();

        for (TemplateSection templateSection : template.sections()) {
            int index = indexOf(sections, templateSection.sectionKey());
            Section section = index < 0 ? null : sections.get(index);
            if (templateSection.required() && (section == null || section.elements().isEmpty())) {
                findings.add(new Finding("required-section-empty", Severity.WARNING, templateSection.sectionKey(),
                    null, "The required section '" + templateSection.heading() + "' has no content."));
            }
            if (section == null) {
                continue;
            }
            List<Element> elements = section.elements();
            for (int e = 0; e < elements.size(); e++) {
                Element element = elements.get(e);
                if (!templateSection.elementKinds().contains(element.kind())) {
                    findings.add(new Finding("element-kind-not-allowed", Severity.WARNING,
                        templateSection.sectionKey(), element.elementId(),
                        "Element " + (index + 1) + "." + (e + 1) + " is a " + element.kind().toJson()
                            + ", which the section '" + templateSection.heading() + "' does not allow."));
                }
            }
        }

        for (Section section : sections) {
            if (template.section(section.sectionKey()).isEmpty()) {
                findings.add(new Finding("unknown-section", Severity.WARNING, section.sectionKey(), null,
                    "The section '" + section.sectionKey() + "' is not in the " + template.title() + " template."));
            }
        }

        for (Unmarked unmarked : snapshot.unmarked()) {
            findings.add(new Finding("unmarked-text", Severity.INFO, unmarked.sectionKey(), null,
                "Text in " + where(unmarked.sectionKey(), template) + " is not inside a marked element."));
        }
        return findings;
    }

    private static int indexOf(List<Section> sections, String sectionKey) {
        for (int i = 0; i < sections.size(); i++) {
            if (sections.get(i).sectionKey().equals(sectionKey)) {
                return i;
            }
        }
        return -1;
    }

    private static String where(String sectionKey, AuthoringTemplate template) {
        if (sectionKey == null) {
            return "the document, outside every section,";
        }
        String heading = template.section(sectionKey).map(TemplateSection::heading).orElse(sectionKey);
        return "the section '" + heading + "'";
    }
}
