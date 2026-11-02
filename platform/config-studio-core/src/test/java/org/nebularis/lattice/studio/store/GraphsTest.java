// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.store;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.model.Workspace;
import org.nebularis.lattice.studio.store.StudioOperations.Family;

/** {@link Graphs} restates the profile's naming rules, so every graph it names is the one the generated operations write. */
class GraphsTest {
    private static final String WS = "00000000-0000-0000-0000-00000000000a";
    private static final String DOC = "00000000-0000-0000-0000-00000000000b";
    private static final String UNIT = "https://example.org/unit/scheme?a=b&c=\u00e9";
    private static final String D16 = "0123456789abcdef";
    private static final String DIGEST = "d".repeat(64);
    private static final StudioOperations OPS = StudioOperations.load(Path.of(System.getProperty("studio.assets"), "persistence"), 1L);

    @Test
    void everyGraphIsTheOneTheOperationsName() {
        assertEquals(OPS.graph(Family.DESCRIPTION, Graphs.workspace(WS)), Graphs.description(WS));
        for (String name : Workspace.GRAPHS) {
            assertEquals(OPS.graph(Family.PART, Graphs.partRoot(WS, name)), Graphs.config(WS, name), name);
        }
        assertEquals(OPS.graph(Family.PART, Graphs.partRoot(WS, "baseline")), Graphs.baseline(WS));
        assertEquals(OPS.graph(Family.DOCUMENT, Graphs.document(WS, DOC)), Graphs.documentGraph(WS, DOC));
        assertEquals(OPS.graph(Family.IMPORT, Graphs.importGraph(DIGEST)), Graphs.importedGraph(DIGEST));
        assertEquals(OPS.graph(Family.LINEAGE, UNIT), Graphs.lineage(UNIT));
        assertEquals(OPS.graph(Family.VERSION, UNIT + "/rev/1-" + D16), Graphs.version(UNIT, D16));
    }

    @Test
    void aVersionGraphIsRecognisedApartFromALineageGraph() {
        assertTrue(Graphs.isVersionGraph(Graphs.version(UNIT, D16)));
        assertFalse(Graphs.isVersionGraph(Graphs.lineage(UNIT)));
        assertFalse(Graphs.isVersionGraph(Graphs.version(UNIT, D16) + "x"));
        assertFalse(Graphs.isVersionGraph(Graphs.config(WS, "surface")));
    }

    @Test
    void aRootAndItsGraphAreRecognisedApart() {
        assertEquals(DOC, Graphs.documentId(WS, Graphs.document(WS, DOC)));
        assertEquals(null, Graphs.documentId(WS, Graphs.documentGraph(WS, DOC)));
        assertTrue(Graphs.isImportGraph(Graphs.importGraph(DIGEST)));
        assertFalse(Graphs.isImportGraph(Graphs.importedGraph(DIGEST)));
        assertTrue(Graphs.isImportedGraph(Graphs.importedGraph(DIGEST)));
        assertFalse(Graphs.isImportedGraph(Graphs.importGraph(DIGEST)));
    }
}
