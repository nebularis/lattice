// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.rdf;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.ResourceFactory;
import org.apache.jena.rdf.model.Statement;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.authoring.TestSamples;
import org.nebularis.lattice.authoring.model.DocumentSnapshot;

class CanonicalHashTest {
    private static final String BASE = "https://example.org/lattice/authoring/";

    // --- S2-02 ----------------------------------------------------------------------------------

    @Test
    void the_hash_does_not_depend_on_statement_insertion_order() {
        DocumentSnapshot snapshot = TestSamples.read(TestSamples.FACILITY_AGREEMENT);
        Model model = new WordingMapper(BASE).map(snapshot, 1);
        String hash = CanonicalHash.of(model);

        Statement[] statements = model.listStatements().toList().toArray(new Statement[0]);
        Model reversed = ModelFactory.createDefaultModel();
        for (int i = statements.length - 1; i >= 0; i--) {
            reversed.add(statements[i]);
        }

        assertEquals(hash, CanonicalHash.of(reversed), "insertion order must not affect the canonical hash");
    }

    // --- S2-03 ----------------------------------------------------------------------------------

    @Test
    void changing_one_literal_character_changes_the_hash() {
        DocumentSnapshot snapshot = TestSamples.read(TestSamples.FACILITY_AGREEMENT);
        WordingMapper mapper = new WordingMapper(BASE);
        Model original = mapper.map(snapshot, 1);
        String originalHash = CanonicalHash.of(original);

        Model changed = ModelFactory.createDefaultModel();
        changed.add(original.listStatements());
        Statement target = changed.listStatements(null, Vocab.WRD_PART_TEXT, (String) null).nextStatement();
        changed.remove(target);
        changed.add(target.getSubject(), Vocab.WRD_PART_TEXT, target.getString() + "!");

        assertNotEquals(originalHash, CanonicalHash.of(changed), "a one-character change must change the hash");
    }

    @Test
    void a_blank_node_is_rejected() {
        Model model = ModelFactory.createDefaultModel();
        Resource subject = model.createResource();
        Property property = ResourceFactory.createProperty(Vocab.WAP_NS + "documentId");
        model.add(subject, property, "x");

        assertThrows(IllegalStateException.class, () -> CanonicalHash.of(model));
    }
}
