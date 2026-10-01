// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.detection;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.authoring.RepoPaths;
import org.nebularis.lattice.authoring.TestSamples;
import org.nebularis.lattice.authoring.json.Json;
import org.nebularis.lattice.authoring.model.DocumentSnapshot;
import org.nebularis.lattice.authoring.model.Element;
import org.nebularis.lattice.authoring.model.ElementKind;
import org.nebularis.lattice.authoring.model.LiteralPart;
import org.nebularis.lattice.authoring.model.Section;
import org.nebularis.lattice.authoring.model.ValueType;

class ConstructDetectorTest {
    private static final String ELEMENT_ID = "00000009-0000-4000-8000-000000000001";
    private static final DocumentSnapshot FACILITY = TestSamples.read(TestSamples.FACILITY_AGREEMENT);
    private static final String FACILITY_ELEMENT = "00000001-0000-4000-8000-0000000000";
    private static final String LOAN_DEFINITION = FACILITY_ELEMENT + "03";

    /** S3-01: a placeholder in element 13, at its offsets in the element text. */
    @Test
    void findsPlaceholderAtElementTextOffsets() {
        Element element = facilityElement("13");
        Detection detection = only(detectionsIn("13", "placeholder"));
        int start = element.text().indexOf("[Agent]");

        assertEquals(start, detection.start());
        assertEquals(start + "[Agent]".length(), detection.end());
        assertEquals("[Agent]", detection.text());
        assertEquals(1, detection.partIndex());
        assertEquals(new Suggestion(Suggestion.MARK_VARIABLE, ValueType.TEXT, "agent", null), detection.suggestion());
    }

    /** S3-02: money and duration in the samples, and every suggested-key case of the fixture. */
    @Test
    void findsMoneyAndDurationAndDerivesKeys() {
        Detection money = only(detectionsIn("11", "money"));
        assertEquals("GBP 250", money.text());
        assertEquals("gbp-250", money.suggestion().suggestedKey());
        assertEquals(ValueType.MONEY, money.suggestion().valueType());

        Detection duration = only(detectionsIn("13", "duration"));
        assertEquals("120 days", duration.text());
        assertEquals("duration-120-days", duration.suggestion().suggestedKey());

        for (JsonNode expected : readFixture()) {
            String text = expected.get("text").asText();
            ValueType valueType = ValueType.fromJson(expected.get("valueType").asText());
            assertEquals(expected.get("suggestedKey").asText(), ConstructDetector.suggestedKey(text, valueType), text);
        }
    }

    /** S3-03: the longer placeholder wins over the duration inside it, the later duration stands. */
    @Test
    void resolvesOverlapsByLength() {
        List<Detection> detections = detect("within [5 days] and 5 days");

        assertEquals(2, detections.size(), detections.toString());
        assertEquals("[5 days]", detections.get(0).text());
        assertEquals("placeholder", detections.get(0).kind());
        assertEquals("5 days", detections.get(1).text());
        assertEquals("duration", detections.get(1).kind());
        assertEquals(20, detections.get(1).start());
    }

    /** S3-04: defined terms with a plural, nothing inside a longer word, nothing for its own term. */
    @Test
    void findsDefinedTermsButNotItsOwnAndNotInsideAWord() {
        Detection plural = only(detectionsIn("14", "defined-term"));
        assertEquals("Loans", plural.text());
        assertEquals(LOAN_DEFINITION, plural.suggestion().targetElementId());
        assertEquals(Suggestion.MARK_REFERENCE, plural.suggestion().action());

        Detection singular = only(detectionsIn("15", "defined-term"));
        assertEquals("Loan", singular.text());
        assertEquals(LOAN_DEFINITION, singular.suggestion().targetElementId());

        Detection outside = only(withFacilityTerms("A Loaner is not a Loan reference."));
        assertEquals("Loan", outside.text(), "Loaner contains Loan but is a different word");

        Detection ownDefinition = only(detectionsIn("03", "defined-term"));
        assertEquals("Facility", ownDefinition.text(), "the Loan definition does not refer to itself");
    }

    /** S3-05: variable and reference parts are not scanned. */
    @Test
    void ignoresNonLiteralParts() {
        assertEquals(List.of(), detectionsIn("08", null), "element 08 has only marked-up content");
    }

    /** S3-06: offsets are UTF-16 code units, so an astral character counts 2. */
    @Test
    void countsOffsetsInUtf16CodeUnits() {
        Detection money = only(detect("\uD835\uDC65 costs GBP 5"));
        assertEquals(9, money.start());
        assertEquals("GBP 5", money.text());
    }

    /** S3-07: a cross-reference is reported with nothing to do about it. */
    @Test
    void findsCrossReferenceWithNoAction() {
        Detection detection = only(detect("subject to clause 4.1(a)"));
        assertEquals("cross-reference", detection.kind());
        assertEquals("clause 4.1(a)", detection.text());
        assertEquals(Suggestion.none(), detection.suggestion());
    }

    private static List<Detection> detect(String literal) {
        Element element = new Element(ELEMENT_ID, ElementKind.CLAUSE, null, List.of(new LiteralPart(literal)));
        DocumentSnapshot snapshot = new DocumentSnapshot("0.1.0", "00000009-0000-4000-8000-000000000000",
            "facility-agreement", "Ad hoc", List.of(new Section("body", List.of(element))), List.of(), List.of());
        return new ConstructDetector().detect(snapshot);
    }

    /** The same literal, in a document that declares the facility sample's terms. */
    private static List<Detection> withFacilityTerms(String literal) {
        Element element = new Element(ELEMENT_ID, ElementKind.CLAUSE, null, List.of(new LiteralPart(literal)));
        DocumentSnapshot snapshot = new DocumentSnapshot("0.1.0", FACILITY.documentId(), "facility-agreement",
            "Ad hoc", List.of(FACILITY.sections().get(0), new Section("body", List.of(element))),
            List.of(), List.of());
        return new ConstructDetector().detect(snapshot).stream()
            .filter(d -> d.elementId().equals(ELEMENT_ID))
            .toList();
    }

    private static List<Detection> detectionsIn(String elementNumber, String kind) {
        return new ConstructDetector().detect(FACILITY).stream()
            .filter(d -> d.elementId().equals(FACILITY_ELEMENT + elementNumber))
            .filter(d -> kind == null || d.kind().equals(kind))
            .toList();
    }

    private static Element facilityElement(String elementNumber) {
        return FACILITY.sections().stream()
            .flatMap(section -> section.elements().stream())
            .filter(element -> element.elementId().equals(FACILITY_ELEMENT + elementNumber))
            .findFirst()
            .orElseThrow();
    }

    private static Detection only(List<Detection> detections) {
        assertTrue(detections.size() == 1, "expected exactly one detection, got " + detections);
        return detections.get(0);
    }

    private static JsonNode readFixture() {
        try {
            return Json.MAPPER.readTree(
                RepoPaths.contracts().resolve("authoring/fixtures/suggested-keys.json").toFile());
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
