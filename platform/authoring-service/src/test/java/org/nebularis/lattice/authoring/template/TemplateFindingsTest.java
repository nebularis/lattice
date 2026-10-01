// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.template;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.authoring.TestSamples;
import org.nebularis.lattice.authoring.json.ContractSchemas;
import org.nebularis.lattice.authoring.model.DocumentSnapshot;
import org.nebularis.lattice.authoring.model.Element;
import org.nebularis.lattice.authoring.model.ElementKind;
import org.nebularis.lattice.authoring.model.LiteralPart;
import org.nebularis.lattice.authoring.model.Section;
import org.nebularis.lattice.authoring.model.Severity;

class TemplateFindingsTest {
    private static final TemplateCatalog CATALOG = new TemplateCatalog(new ContractSchemas());
    private static final AuthoringTemplate LICENCE = CATALOG.get("software-licence").orElseThrow();

    /** S3-09: a missing section, an empty one, an unknown one and an element of the wrong kind. */
    @Test
    void reportsEachKindOfTemplateMismatch() {
        DocumentSnapshot snapshot = snapshot(
            new Section("definitions", List.of(element("01", ElementKind.DEFINITION, "Software"))),
            new Section("grant", List.of(element("02", ElementKind.DEFINITION, "Licensee"))),
            new Section("fees", List.of()),
            new Section("misc", List.of(element("03", ElementKind.CLAUSE, null))),
            new Section("termination", List.of(element("04", ElementKind.CLAUSE, null)))
        );

        List<Finding> findings = TemplateFindings.check(snapshot, LICENCE);

        assertEquals(List.of("element-kind-not-allowed", "required-section-empty", "required-section-empty",
            "unknown-section"), findings.stream().map(Finding::kind).sorted().toList(), findings.toString());
        assertEquals(List.of("fees", "restrictions"), findings.stream()
            .filter(f -> f.kind().equals("required-section-empty")).map(Finding::sectionKey).sorted().toList());
        Finding wrongKind = single(findings, "element-kind-not-allowed");
        assertEquals("grant", wrongKind.sectionKey());
        assertEquals(Severity.WARNING, wrongKind.severity());
        assertTrue(wrongKind.message().contains("Element 2.1"), wrongKind.message());
        assertTrue(wrongKind.message().contains("'Grant'"), wrongKind.message());
        assertTrue(single(findings, "unknown-section").message().contains("'misc'"));
    }

    /** S3-10: the zero case, one finding per required template section. */
    @Test
    void reportsEveryRequiredSectionWhenThereAreNone() {
        List<Finding> findings = TemplateFindings.check(snapshot(), LICENCE);

        List<String> required = LICENCE.sections().stream()
            .filter(TemplateSection::required).map(TemplateSection::sectionKey).toList();
        assertEquals(required, findings.stream().map(Finding::sectionKey).toList());
        assertTrue(findings.stream().allMatch(f -> f.kind().equals("required-section-empty")), findings.toString());
    }

    /** S3-13: the licence sample is clean apart from its one piece of unmarked text. */
    @Test
    void reportsOnlyUnmarkedTextForTheLicenceSample() {
        List<Finding> findings = TemplateFindings.check(TestSamples.read(TestSamples.SOFTWARE_LICENCE), LICENCE);

        assertEquals(1, findings.size(), findings.toString());
        assertEquals("unmarked-text", findings.get(0).kind());
        assertEquals(Severity.INFO, findings.get(0).severity());
        assertEquals("fees", findings.get(0).sectionKey());
        assertTrue(findings.get(0).message().contains("'Fees'"), findings.get(0).message());
    }

    private static DocumentSnapshot snapshot(Section... sections) {
        return new DocumentSnapshot("0.1.0", "00000009-0000-4000-8000-000000000000", "software-licence",
            "Ad hoc", List.of(sections), List.of(), List.of());
    }

    private static Element element(String number, ElementKind kind, String definedTerm) {
        return new Element("00000009-0000-4000-8000-0000000000" + number, kind, definedTerm,
            List.of(new LiteralPart("Text.")));
    }

    private static Finding single(List<Finding> findings, String kind) {
        List<Finding> matching = findings.stream().filter(f -> f.kind().equals(kind)).toList();
        assertEquals(1, matching.size(), "expected one " + kind + " in " + findings);
        return matching.get(0);
    }
}
