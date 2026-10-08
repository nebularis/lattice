// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.validation;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.vocabulary.RDF;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.nebularis.lattice.authoring.TestSamples;
import org.nebularis.lattice.authoring.model.DocumentSnapshot;
import org.nebularis.lattice.authoring.rdf.Vocab;
import org.nebularis.lattice.authoring.rdf.WordingMapper;

class WordingValidatorTest {
    private static final String BASE = "https://example.org/lattice/authoring/";
    private static final String DOC = "https://example.org/lattice/authoring/doc/00000009-0000-4000-8000-000000000000/";

    private final WordingValidator validator = new WordingValidator();

    // --- S2-08 ----------------------------------------------------------------------------------

    @ParameterizedTest
    @ValueSource(strings = {TestSamples.FACILITY_AGREEMENT, TestSamples.SOFTWARE_LICENCE})
    void the_facility_and_licence_samples_have_no_result(String sampleId) {
        ValidationReportView report = validate(sampleId);
        assertTrue(report.conforms(), report.results().toString());
        assertEquals(List.of(), report.results());
    }

    @Test
    void the_property_policy_sample_has_exactly_one_ws10_warning_on_period_start() {
        ValidationReportView report = validate(TestSamples.PROPERTY_POLICY);
        assertTrue(report.conforms(), "a warning does not break conformance");
        assertEquals(1, report.results().size());
        ValidationResult result = report.results().get(0);
        assertEquals("WS10", result.shapeId());
        assertEquals("warning", result.severity());
        assertTrue(result.focusNode().endsWith("/variable/period-start"), result.focusNode());
    }

    private static ValidationReportView validate(String sampleId) {
        DocumentSnapshot snapshot = TestSamples.read(sampleId);
        Model model = new WordingMapper(BASE).map(snapshot, 1);
        return new WordingValidator().validate(model);
    }

    // --- S2-09 ------------------------------------------------------------------------------------

    @Test
    void a_part_with_both_text_and_a_variable_reference_is_one_ws2_violation() {
        Model model = ModelFactory.createDefaultModel();
        Resource wording = model.createResource(DOC + "wording");
        Resource section = baseSection(model, wording);
        Resource variable = variable(model, "amount");
        wording.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, variable);

        Resource text = model.createResource(DOC + "element/text-1");
        text.addProperty(RDF.type, Vocab.WRD_TEXT);
        section.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, text);

        Resource okPart = part(text, model, "part-0", 0);
        okPart.addProperty(Vocab.WRD_REFERS_TO_VARIABLE, variable);
        okPart.addProperty(Vocab.WAP_DISPLAY_TEXT, "amount");

        Resource badPart = part(text, model, "part-1", 1);
        badPart.addProperty(Vocab.WRD_PART_TEXT, "hello");
        badPart.addProperty(Vocab.WRD_REFERS_TO_VARIABLE, variable);

        assertOnlyShape(model, "WS2");
    }

    // --- S2-10 --------------------------------------------------------------------------------

    @Test
    void duplicate_and_gapped_part_indices_are_one_ws3_violation_each() {
        Model model = ModelFactory.createDefaultModel();
        Resource wording = model.createResource(DOC + "wording");
        Resource section = baseSection(model, wording);

        Resource duplicateIndices = model.createResource(DOC + "element/text-duplicate");
        duplicateIndices.addProperty(RDF.type, Vocab.WRD_TEXT);
        section.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, duplicateIndices);
        part(duplicateIndices, model, "dup-0", 0).addProperty(Vocab.WRD_PART_TEXT, "a");
        part(duplicateIndices, model, "dup-1", 0).addProperty(Vocab.WRD_PART_TEXT, "b");

        Resource gappedIndices = model.createResource(DOC + "element/text-gapped");
        gappedIndices.addProperty(RDF.type, Vocab.WRD_TEXT);
        section.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, gappedIndices);
        part(gappedIndices, model, "gap-0", 0).addProperty(Vocab.WRD_PART_TEXT, "a");
        part(gappedIndices, model, "gap-2", 2).addProperty(Vocab.WRD_PART_TEXT, "b");

        ValidationReportView report = new WordingValidator().validate(model);
        long ws3Count = report.results().stream().filter(r -> r.shapeId().equals("WS3")).count();
        assertEquals(2, ws3Count, report.results().toString());
        assertTrue(report.results().stream().anyMatch(r -> r.focusNode().endsWith("text-duplicate")));
        assertTrue(report.results().stream().anyMatch(r -> r.focusNode().endsWith("text-gapped")));
    }

    // --- S2-11 ----------------------------------------------------------------------------------

    @Test
    void a_text_with_zero_parts_is_one_ws4_violation_and_no_ws3_result() {
        Model model = ModelFactory.createDefaultModel();
        Resource wording = model.createResource(DOC + "wording");
        Resource section = baseSection(model, wording);

        Resource empty = model.createResource(DOC + "element/text-empty");
        empty.addProperty(RDF.type, Vocab.WRD_TEXT);
        section.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, empty);

        assertOnlyShape(model, "WS4");
    }

    // --- S2-12 ----------------------------------------------------------------------------------

    @Test
    void zero_parents_and_two_parents_are_one_ws5_violation_each() {
        Model model = ModelFactory.createDefaultModel();
        Resource wording = model.createResource(DOC + "wording");
        Resource otherWording = model.createResource(DOC + "other-wording");

        Resource orphan = model.createResource(DOC + "element/orphan");
        orphan.addProperty(RDF.type, Vocab.WRD_ELEMENT);
        // no parent

        Resource doublyParented = model.createResource(DOC + "element/doubly-parented");
        doublyParented.addProperty(RDF.type, Vocab.WRD_ELEMENT);
        wording.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, doublyParented);
        otherWording.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, doublyParented);

        ValidationReportView report = new WordingValidator().validate(model);
        long ws5Count = report.results().stream().filter(r -> r.shapeId().equals("WS5")).count();
        assertEquals(2, ws5Count, report.results().toString());
        assertTrue(report.results().stream().anyMatch(r -> r.focusNode().endsWith("orphan")));
        assertTrue(report.results().stream().anyMatch(r -> r.focusNode().endsWith("doubly-parented")));
    }

    // --- S2-13 ----------------------------------------------------------------------------------

    @Test
    void a_reference_to_a_clause_and_one_to_an_absent_element_are_one_ws7_violation_each() {
        Model model = ModelFactory.createDefaultModel();
        Resource wording = model.createResource(DOC + "wording");
        Resource section = baseSection(model, wording);

        Resource clause = model.createResource(DOC + "element/clause-not-a-definition");
        clause.addProperty(RDF.type, Vocab.WRD_TEXT);
        section.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, clause);
        part(clause, model, "part-0", 0).addProperty(Vocab.WRD_PART_TEXT, "hello");

        Resource referrer = model.createResource(DOC + "element/text-with-references");
        referrer.addProperty(RDF.type, Vocab.WRD_TEXT);
        section.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, referrer);
        Resource toClause = part(referrer, model, "ref-clause", 0);
        toClause.addProperty(Vocab.WRD_REFERS_TO_OBJECT, clause);
        toClause.addProperty(Vocab.WAP_DISPLAY_TEXT, "the clause");
        Resource toAbsent = part(referrer, model, "ref-absent", 1);
        toAbsent.addProperty(Vocab.WRD_REFERS_TO_OBJECT, model.createResource(DOC + "element/does-not-exist"));
        toAbsent.addProperty(Vocab.WAP_DISPLAY_TEXT, "a ghost");

        ValidationReportView report = new WordingValidator().validate(model);
        long ws7Count = report.results().stream().filter(r -> r.shapeId().equals("WS7")).count();
        assertEquals(2, ws7Count, report.results().toString());
    }

    // --- S2-14 ----------------------------------------------------------------------------------

    @Test
    void two_definitions_of_the_same_term_are_ws9_violations() {
        Model model = ModelFactory.createDefaultModel();
        Resource wording = model.createResource(DOC + "wording");
        Resource section = baseSection(model, wording);

        Resource first = definition(model, section, "definition-1", "Loan");
        Resource second = definition(model, section, "definition-2", "Loan");

        ValidationReportView report = new WordingValidator().validate(model);
        long ws9Count = report.results().stream().filter(r -> r.shapeId().equals("WS9")).count();
        assertEquals(2, ws9Count, report.results().toString());
    }

    @Test
    void an_unreferenced_variable_is_a_ws10_warning_and_conforms_stays_true() {
        Model model = ModelFactory.createDefaultModel();
        Resource wording = model.createResource(DOC + "wording");
        Resource unreferenced = variable(model, "unused");
        wording.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, unreferenced);

        assertOnlyShape(model, "WS10");
        ValidationReportView report = new WordingValidator().validate(model);
        assertTrue(report.conforms());
        assertEquals("warning", report.results().get(0).severity());
    }

    // --- helpers ----------------------------------------------------------------------------------

    private static Resource baseSection(Model model, Resource wording) {
        Resource section = model.createResource(DOC + "section/test");
        section.addProperty(RDF.type, Vocab.WRD_ELEMENT);
        wording.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, section);
        return section;
    }

    private static Resource variable(Model model, String key) {
        Resource variable = model.createResource(DOC + "variable/" + key);
        variable.addProperty(RDF.type, Vocab.WRD_EMBEDDED_VARIABLE);
        variable.addProperty(Vocab.WRD_VARIABLE_KEY, key);
        return variable;
    }

    private static Resource part(Resource text, Model model, String suffix, int index) {
        Resource part = model.createResource(DOC + "part/" + suffix);
        part.addProperty(RDF.type, Vocab.WRD_TEXT_PART);
        part.addProperty(Vocab.WRD_PART_INDEX, model.createTypedLiteral(Integer.toString(index), XSDDatatype.XSDinteger));
        text.addProperty(Vocab.WAP_HAS_PART, part);
        return part;
    }

    private static Resource definition(Model model, Resource section, String suffix, String term) {
        Resource definition = model.createResource(DOC + "element/" + suffix);
        definition.addProperty(RDF.type, Vocab.WRD_TEXT);
        definition.addProperty(RDF.type, Vocab.WAP_DEFINITION_TEXT);
        definition.addProperty(Vocab.WAP_DEFINED_TERM, term);
        section.addProperty(Vocab.WRD_DIRECTLY_COMPRISES, definition);
        part(definition, model, suffix + "-part-0", 0).addProperty(Vocab.WRD_PART_TEXT, "\u201c" + term + "\u201d means something.");
        return definition;
    }

    private static void assertOnlyShape(Model model, String expectedShapeId) {
        ValidationReportView report = new WordingValidator().validate(model);
        assertTrue(report.results().stream().anyMatch(r -> r.shapeId().equals(expectedShapeId)),
            "expected a " + expectedShapeId + " result, got " + report.results());
        assertTrue(report.results().stream().allMatch(r -> r.shapeId().equals(expectedShapeId)),
            "expected only " + expectedShapeId + " results, got " + report.results());
    }
}
