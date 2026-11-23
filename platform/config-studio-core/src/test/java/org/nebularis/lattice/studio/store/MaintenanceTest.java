// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.store;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/** The updates a write sends to keep the rows of its source, as a caller that holds the operations' texts asks for them. */
class MaintenanceTest {
    private static final String CLEAR = "DELETE { GRAPH $derived { ?s ?p ?o } } WHERE { GRAPH $derived { ?s ?p ?o } }";
    private static final String FILL = "INSERT { GRAPH $derived { ?c <urn:p:row> ?v } } WHERE { GRAPH $source { ?c <urn:p:read> ?v } }";

    @Test
    void theOperationsAreTheClearThenEachFillInOrderAndNameTheContractEachWrites() {
        Maintenance m = Maintenance.of(CLEAR, Map.of("f", List.of(new Maintenance.Fill("a", FILL), new Maintenance.Fill("b", FILL.replace("row", "other")))));
        List<Maintenance.Operation> operations = m.operations("f", "urn:g:one");
        assertEquals(3, operations.size());
        assertNull(operations.get(0).contract());
        assertEquals(List.of("a", "b"), operations.subList(1, 3).stream().map(Maintenance.Operation::contract).toList());
        assertTrue(text(operations.get(1)).contains("<" + Graphs.promoted("urn:g:one") + ">"), "the rows go to the source's own partition");
        assertTrue(text(operations.get(1)).contains("<urn:g:one>"));
        assertEquals(operations.stream().map(MaintenanceTest::text).toList(), m.keep("f", "urn:g:one").stream().map(u -> new org.apache.jena.update.UpdateRequest(u).toString()).toList(),
            "keep is the same updates without their names");
    }

    private static String text(Maintenance.Operation operation) {
        return new org.apache.jena.update.UpdateRequest(operation.update()).toString();
    }

    @Test
    void aFamilyThatKeepsNothingKeepsNothing() {
        Maintenance m = Maintenance.of(CLEAR, Map.of("f", List.of(new Maintenance.Fill("a", FILL))));
        assertEquals(List.of(), m.operations("other", "urn:g:one"));
        assertEquals(List.of(), Maintenance.none().keep("f", "urn:g:one"));
        assertEquals(List.of(), Maintenance.of(null, Map.of("f", List.of(new Maintenance.Fill("a", FILL)))).keep("f", "urn:g:one"));
    }
}
