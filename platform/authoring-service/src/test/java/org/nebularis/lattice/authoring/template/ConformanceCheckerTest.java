// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.template;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.authoring.json.ContractSchemas;
import org.nebularis.lattice.authoring.json.Json;
import org.nebularis.lattice.authoring.model.Severity;

class ConformanceCheckerTest {
    private static final TemplateCatalog CATALOG = new TemplateCatalog(new ContractSchemas());
    private static final ConformanceChecker CHECKER = new ConformanceChecker();

    /** S3-11: a term kind the section does not allow, beside one it does. */
    @Test
    void reportsOnlyTheTermKindTheSectionDoesNotAllow() {
        JsonNode analysis = analysis(
            element("01", "1.1", "grant", "\"Prohibition\""),
            element("02", "1.2", "grant", "\"Permission\""));

        List<Finding> findings = CHECKER.check(analysis, CATALOG.get("software-licence").orElseThrow());

        assertEquals(1, findings.size(), findings.toString());
        assertEquals("term-kind-not-allowed", findings.get(0).kind());
        assertEquals(Severity.WARNING, findings.get(0).severity());
        assertEquals("00000009-0000-4000-8000-0000000000" + "01", findings.get(0).elementId());
        assertTrue(findings.get(0).message().contains("Element 1.1"), findings.get(0).message());
        assertTrue(findings.get(0).message().contains("'Grant'"), findings.get(0).message());
    }

    /** S3-12: no reading where one is expected, and nothing at all for an unknown section. */
    @Test
    void reportsAMissingTermKindButIgnoresUnknownSections() {
        JsonNode analysis = analysis(
            element("01", "3.1", "interest", "null"),
            element("02", "7.1", "miscellaneous", "null"));

        List<Finding> findings = CHECKER.check(analysis, CATALOG.get("facility-agreement").orElseThrow());

        assertEquals(1, findings.size(), findings.toString());
        assertEquals("no-term-kind", findings.get(0).kind());
        assertEquals(Severity.INFO, findings.get(0).severity());
        assertEquals("interest", findings.get(0).sectionKey());
        assertTrue(findings.get(0).message().contains("'Interest'"), findings.get(0).message());
    }

    private static String element(String number, String objectId, String sectionKey, String relationClass) {
        return """
            {"elementId": "00000009-0000-4000-8000-0000000000%s", "objectId": "%s", "sectionKey": "%s",
             "relationClass": %s}""".formatted(number, objectId, sectionKey, relationClass);
    }

    private static JsonNode analysis(String... elements) {
        try {
            return Json.MAPPER.readTree("{\"elements\": [" + String.join(",", elements) + "]}");
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
