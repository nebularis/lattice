// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.rdf;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.rdf.model.StmtIterator;
import org.apache.jena.vocabulary.RDF;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.nebularis.lattice.authoring.RepoPaths;
import org.nebularis.lattice.authoring.TestSamples;
import org.nebularis.lattice.authoring.model.DocumentSnapshot;
import org.nebularis.lattice.authoring.model.Element;
import org.nebularis.lattice.authoring.model.ElementKind;
import org.nebularis.lattice.authoring.model.LiteralPart;
import org.nebularis.lattice.authoring.model.Section;
import org.nebularis.lattice.authoring.model.Unmarked;
import org.nebularis.lattice.authoring.model.VariableDeclaration;

class WordingMapperTest {
    private static final String BASE = "https://example.org/lattice/authoring/";

    // --- S2-01 --------------------------------------------------------------------------------

    @ParameterizedTest
    @ValueSource(strings = {TestSamples.FACILITY_AGREEMENT, TestSamples.SOFTWARE_LICENCE, TestSamples.PROPERTY_POLICY})
    void each_sample_maps_to_its_committed_fixture(String sampleId) throws Exception {
        DocumentSnapshot snapshot = TestSamples.read(sampleId);
        Model model = new WordingMapper(BASE).map(snapshot, 1);
        List<String> actual = CanonicalHash.sortedNTriplesLines(model);

        Path fixture = RepoPaths.contracts().resolve("authoring").resolve("fixtures").resolve("wording").resolve(sampleId + ".nt");
        List<String> expected = Files.readAllLines(fixture).stream().filter(line -> !line.isBlank()).sorted().toList();

        assertEquals(expected, actual, "mapped graph does not match the committed fixture for " + sampleId);
    }

    // --- S2-04 ----------------------------------------------------------------------------------

    @Test
    void inserting_an_element_shifts_object_ids_but_not_iris() {
        String documentId = "00000009-0000-4000-8000-000000000000";
        Element a = element(documentId, 1, "A");
        Element b = element(documentId, 2, "B");
        WordingMapper mapper = new WordingMapper(BASE);
        IriMinter minter = new IriMinter(BASE);
        String bIri = minter.element(documentId, b.elementId());

        Model before = mapper.map(snapshot(documentId, List.of(new Section("commitment", List.of(a, b)))), 1);
        assertEquals("1.2", before.getResource(bIri).getProperty(Vocab.WRD_OBJECT_ID).getString());

        Element c = element(documentId, 3, "C");
        Model after = mapper.map(snapshot(documentId, List.of(new Section("commitment", List.of(a, c, b)))), 1);
        assertEquals("1.3", after.getResource(bIri).getProperty(Vocab.WRD_OBJECT_ID).getString(),
            "b's object id should shift to reflect its new position");
        assertTrue(after.containsResource(after.getResource(bIri)), "b's IRI is unchanged by the insertion (law W7)");
    }

    // --- S2-05 ----------------------------------------------------------------------------------

    @Test
    void parts_carry_exactly_one_of_the_three_forms() {
        Model model = new WordingMapper(BASE).map(TestSamples.read(TestSamples.FACILITY_AGREEMENT), 1);
        var parts = model.listResourcesWithProperty(RDF.type, Vocab.WRD_TEXT_PART);
        assertTrue(parts.hasNext(), "no text parts found");
        while (parts.hasNext()) {
            Resource part = parts.next();
            boolean hasText = part.hasProperty(Vocab.WRD_PART_TEXT);
            boolean hasVariable = part.hasProperty(Vocab.WRD_REFERS_TO_VARIABLE);
            boolean hasReference = part.hasProperty(Vocab.WRD_REFERS_TO_OBJECT);
            boolean hasDisplayText = part.hasProperty(Vocab.WAP_DISPLAY_TEXT);

            int formCount = (hasText ? 1 : 0) + (hasVariable ? 1 : 0) + (hasReference ? 1 : 0);
            assertEquals(1, formCount, part + " must have exactly one form");
            if (hasText) {
                assertFalse(hasDisplayText, part + " a literal part carries no wap:displayText");
            } else {
                assertTrue(hasDisplayText, part + " a variable or reference part carries wap:displayText");
            }
        }
    }

    // --- S2-06 ----------------------------------------------------------------------------------

    @Test
    void special_characters_in_text_never_leak_into_an_iri_and_no_blank_node_is_created() {
        String documentId = "00000009-0000-4000-8000-000000000000";
        String nasty = "a > b \" c\nd { e # f";
        Element element = new Element(
            "00000009-0000-4000-8000-000000000001", ElementKind.CLAUSE, null, List.of(new LiteralPart(nasty)));
        Section section = new Section("commitment", List.of(element));
        DocumentSnapshot snapshot = new DocumentSnapshot(
            "0.1.0", documentId, "facility-agreement", "Title with > \" \n { # chars",
            List.of(section), List.of(), List.of());

        Model model = new WordingMapper(BASE).map(snapshot, 1);

        StmtIterator statements = model.listStatements();
        while (statements.hasNext()) {
            Statement statement = statements.next();
            assertFalse(statement.getSubject().isAnon(), "no blank node subject: " + statement);
            Resource subject = statement.getSubject();
            assertTrue(isDocOrVocabIri(subject.getURI()), "unexpected IRI: " + subject.getURI());

            RDFNode object = statement.getObject();
            if (object.isAnon()) {
                throw new AssertionError("no blank node object: " + statement);
            }
            if (object.isURIResource()) {
                assertTrue(isDocOrVocabIri(object.asResource().getURI()), "unexpected IRI: " + object.asResource().getURI());
            }
        }
    }

    private static boolean isDocOrVocabIri(String iri) {
        return iri.startsWith(BASE + "doc/")
            || iri.startsWith(Vocab.WRD_NS)
            || iri.startsWith(Vocab.WAP_NS)
            || iri.startsWith(Vocab.INS_NS);
    }

    private static Element element(String documentId, int suffix, String text) {
        String elementId = String.format("%s-0000-4000-8000-%012d", documentId.substring(0, 8), suffix);
        return new Element(elementId, ElementKind.CLAUSE, null, List.of(new LiteralPart(text)));
    }

    private static DocumentSnapshot snapshot(String documentId, List<Section> sections) {
        return new DocumentSnapshot("0.1.0", documentId, "facility-agreement", "Test", sections, List.<VariableDeclaration>of(), List.<Unmarked>of());
    }
}
