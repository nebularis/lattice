// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Iterator;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdfconnection.RDFConnection;
import org.apache.jena.sparql.core.DatasetGraph;
import org.apache.jena.sparql.core.Quad;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.persistence.Namespaces;
import org.nebularis.lattice.studio.model.Workspace;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.StudioOperations.Family;
import org.nebularis.lattice.studio.store.StudioStore;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Reply;
import org.nebularis.lattice.studio.writes.Writer;

/** The writer's workspace commands on the generated operations, in batches, against the layout of the profile. */
class WorkspaceCommandsTest {
    private static final String WS = Fixture.id(1);
    private static final String OTHER = Fixture.id(2);
    private static final String DOC = Fixture.id(3);
    private static final String DIGEST = "c".repeat(64);
    private static final Instant AT = Instant.parse("2026-10-28T09:00:00Z");
    private static final Clock CLOCK = Clock.fixed(Instant.parse("2026-10-28T09:00:01Z"), ZoneOffset.UTC);

    private DatasetGraph dataset;
    private StudioStore store;
    private Writer writer;

    @BeforeEach
    void setUp() {
        dataset = DatasetFactory.createTxnMem().asDatasetGraph();
        store = Fixture.textual(RDFConnection.connect(DatasetFactory.wrap(dataset)));
        writer = new Writer(store, Fixture.OPS, CLOCK);
        assertEquals(Reply.ok(1), writer.apply(Command.create(WS, "Plan", AT, null, model("baseline"))));
    }

    private static Model model(String value) {
        return Fixture.model(Fixture.PREFIXES + "ex:a ex:p \"" + value + "\" .");
    }

    /** A document's graph as the writer accepts one, the node holding its markup once. */
    private static Model docGraph(String markup) {
        Model m = ModelFactory.createDefaultModel();
        m.createResource(Graphs.documentNode(DOC)).addProperty(Cst.markup, "<document>" + markup + "</document>");
        return m;
    }

    private static Model surface(String value) {
        return Fixture.model(Fixture.PREFIXES + "ex:cfg <https://www.nebularis.org/neuro-semantic/lattice/surface#label> \"" + value + "\" .");
    }

    private static Model persistence(String value) {
        return Fixture.model(Fixture.PREFIXES + "ex:profile <https://www.nebularis.org/neuro-semantic/lattice/persistence#label> \"" + value + "\" .");
    }

    private Set<String> quads(String graph) {
        Set<String> out = new TreeSet<>();
        for (Iterator<Quad> it = dataset.find(NodeFactory.createURI(graph), null, null, null); it.hasNext(); ) {
            Quad q = it.next();
            out.add(q.getSubject() + " " + q.getPredicate() + " " + q.getObject());
        }
        return out;
    }

    private Set<String> everyQuad() {
        Set<String> out = new TreeSet<>();
        for (Iterator<Quad> it = dataset.find(); it.hasNext(); ) {
            out.add(it.next().toString());
        }
        return out;
    }

    private long descriptionSeq() {
        return Fixture.OPS.seq(store, Family.DESCRIPTION, Graphs.workspace(WS)).orElseThrow();
    }

    @Test
    void twoSavesOfOnePartWithOneExpectationInOneBatchLoseTheSecondAndTheFirstStays() {
        List<Reply> replies = writer.apply(List.of(
            Command.save(WS, "surface", 0, AT, surface("first")),
            Command.save(WS, "surface", 0, AT, surface("second"))));
        assertEquals(List.of(Reply.ok(1), Reply.stale(1)), replies);
        assertTrue(surface("first").isIsomorphicWith(store.graph(Graphs.config(WS, "surface"))));
        assertEquals(1, Fixture.OPS.workspace(store, WS).revision("surface"));
        // The same part again, with the right expectation, replaces it, and the delta is from what the first left.
        assertEquals(List.of(Reply.ok(2), Reply.ok(3)), writer.apply(List.of(
            Command.save(WS, "surface", 1, AT, surface("second")), Command.save(WS, "surface", 2, AT, surface("third")))));
        assertTrue(surface("third").isIsomorphicWith(store.graph(Graphs.config(WS, "surface"))));
    }

    @Test
    void twoPartsSavedWithTheirOwnExpectationsInOneBatchBothApplyAndTheDescriptionIsUntouched() {
        Set<String> description = quads(Graphs.description(WS));
        long seq = descriptionSeq();
        List<Reply> replies = writer.apply(List.of(
            Command.save(WS, "surface", 0, AT, surface("one")),
            Command.save(WS, "persistence", 0, AT, persistence("two")),
            Command.save(WS, "baseline", 1, AT, model("again"))));
        assertEquals(List.of(Reply.ok(1), Reply.ok(1), Reply.ok(2)), replies);
        assertTrue(surface("one").isIsomorphicWith(store.graph(Graphs.config(WS, "surface"))));
        assertTrue(persistence("two").isIsomorphicWith(store.graph(Graphs.config(WS, "persistence"))));
        assertTrue(model("again").isIsomorphicWith(store.graph(Graphs.baseline(WS))));
        assertEquals(description, quads(Graphs.description(WS)), "the description holds no revision, and saving a part leaves it");
        assertEquals(seq, descriptionSeq());
        Workspace ws = Fixture.OPS.workspace(store, WS);
        assertEquals(Instant.parse("2026-10-28T09:00:00Z"), ws.modifiedAt(), "modifiedAt moves only when the description is written");
        assertEquals(1, ws.revision("surface"));
        assertEquals(1, ws.revision("persistence"));
        assertEquals(2, ws.revision("baseline"));
    }

    @Test
    void deletingAWorkspaceLeavesNoGraphOfItsPartsDocumentsLogsOrDescriptionAndTombstonesItsRows() {
        assertEquals(Reply.ok(1), writer.apply(Command.save(WS, "surface", 0, AT, surface("one"))));
        assertEquals(Reply.ok(2), writer.apply(Command.save(WS, "surface", 1, AT, surface("two"))));
        assertEquals(Reply.ok(2), writer.apply(Command.save(WS, "baseline", 1, AT, model("two"))));
        assertEquals(Reply.ok(1), writer.apply(Command.saveDocument(WS, DOC, 0, AT, "Licence", "software-licence", docGraph("one"))));
        assertEquals(Reply.ok(2), writer.apply(Command.saveDocument(WS, DOC, 1, AT, "Licence", "software-licence", docGraph("two"))));
        Command delete = Command.deleteWorkspace(WS);
        assertEquals(Reply.ok(), writer.apply(delete));

        List<String> roots = List.of(Graphs.workspace(WS), Graphs.partRoot(WS, "baseline"), Graphs.partRoot(WS, "surface"), Graphs.document(WS, DOC));
        List<Family> families = List.of(Family.DESCRIPTION, Family.PART, Family.PART, Family.DOCUMENT);
        List<Long> sequences = List.of(2L, 2L, 2L, 2L);
        for (int i = 0; i < roots.size(); i++) {
            assertTrue(store.rawGraph(Fixture.OPS.graph(families.get(i), roots.get(i))).isEmpty(), roots.get(i));
            for (long k = 1; k <= sequences.get(i) + 1; k++) {
                String rev = Fixture.OPS.revision(families.get(i), roots.get(i), k);
                assertTrue(store.rawGraph(rev + "/add").isEmpty() && store.rawGraph(rev + "/del").isEmpty(), rev);
            }
            assertEquals(Optional.empty(), Fixture.OPS.seq(store, families.get(i), roots.get(i)), "the row is tombstoned");
            assertTrue(dataset.find(null, NodeFactory.createURI(roots.get(i)), NodeFactory.createURI(Namespaces.PAT + "deleted"), null).hasNext(),
                "the row of " + roots.get(i) + " says it is deleted");
        }
        assertEquals(null, Fixture.OPS.workspace(store, WS));
        assertTrue(store.graph(Graphs.receipts(WS)).isEmpty());
        assertFalse(store.graph(Graphs.STORE_RECEIPTS).isEmpty(), "the store keeps the receipt of the deletion");
        assertEquals(Reply.ok(), writer.apply(delete), "a retried deletion is answered from its receipt");
    }

    @Test
    void aFencedImportTwoWorkspacesHoldIsOneGraphAndAReleaseLeavesIt() {
        assertEquals(Reply.ok(1), writer.apply(Command.create(OTHER, "Other", AT, null, model("other"))));
        Model content = Fixture.model(Fixture.PREFIXES + "ex:term a ex:Term ; ex:label \"t\" .");
        assertEquals(Reply.ok(), writer.apply(Command.fence(WS, DIGEST, "Reference", content)));
        assertEquals(Reply.ok(), writer.apply(Command.fence(OTHER, DIGEST, "Same", content)));
        String graph = Graphs.importedGraph(DIGEST);
        assertEquals(2, quads(graph).size());
        assertTrue(content.isIsomorphicWith(store.graph(graph)));
        assertEquals(Optional.of(1L), Fixture.OPS.seq(store, Family.IMPORT, Graphs.importGraph(DIGEST)), "created once, by the first fence");
        assertEquals(Set.of(Graphs.importGraph(DIGEST)), Fixture.OPS.workspace(store, WS).imports().keySet());
        assertEquals(Set.of(Graphs.importGraph(DIGEST)), Fixture.OPS.workspace(store, OTHER).imports().keySet());
        assertEquals(Reply.ok(), writer.apply(Command.release(WS, DIGEST)));
        assertTrue(Fixture.OPS.workspace(store, WS).imports().isEmpty());
        assertTrue(content.isIsomorphicWith(store.graph(graph)), "the other workspace still holds it");
        assertEquals(Reply.ok(), writer.apply(Command.release(OTHER, DIGEST)));
        assertTrue(content.isIsomorphicWith(store.graph(graph)), "an import is never tombstoned");
        assertEquals(Reply.ok(), writer.apply(Command.fence(WS, DIGEST, "Again", content)), "and can be held again");
    }

    @Test
    void aRetriedCommandOfSeveralOperationsWritesNothing() {
        Command save = Command.saveDocument(WS, DOC, 0, AT, "Licence", "software-licence", docGraph("one"));
        assertEquals(Reply.ok(1), writer.apply(save));
        Set<String> before = everyQuad();
        assertEquals(Reply.ok(1), writer.apply(save));
        assertEquals(Reply.ok(1), writer.apply(List.of(save)).get(0));
        assertEquals(before, everyQuad());
        Command access = Command.setAccess(WS, "shared", null);
        assertEquals(Reply.ok(), writer.apply(access));
        before = everyQuad();
        assertEquals(Reply.ok(), writer.apply(access));
        assertEquals(before, everyQuad());
    }
}
