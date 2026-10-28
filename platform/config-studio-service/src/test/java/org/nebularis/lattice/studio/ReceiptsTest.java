// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Proxy;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdfconnection.RDFConnection;
import org.apache.jena.vocabulary.RDF;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.StudioStore;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Reply;
import org.nebularis.lattice.studio.writes.Writer;

/** Receipts, a redelivered command, a batch, and the revision guard inside the update. */
class ReceiptsTest {
    private static final String WS = Fixture.id(1);
    private static final Instant AT = Instant.parse("2026-10-28T09:00:00Z");
    private static final Clock CLOCK = Clock.fixed(Instant.parse("2026-10-28T09:00:01Z"), ZoneOffset.UTC);

    /** Runs {@code before} against the store just before each update request the writer sends, as another writer might. */
    private static StudioStore interfered(RDFConnection real, AtomicReference<Runnable> before) {
        RDFConnection proxy = (RDFConnection) Proxy.newProxyInstance(RDFConnection.class.getClassLoader(),
            new Class<?>[] {RDFConnection.class}, (self, method, args) -> {
                if (method.getName().equals("update") && before.get() != null) {
                    Runnable r = before.getAndSet(null);
                    r.run();
                }
                try {
                    return method.invoke(real, args);
                } catch (InvocationTargetException e) {
                    throw e.getCause();
                }
            });
        return Fixture.textual(proxy);
    }

    private static Model surface(String value) {
        return Fixture.model(Fixture.PREFIXES + "ex:cfg <https://www.nebularis.org/neuro-semantic/lattice/surface#label> \"" + value + "\" .");
    }

    private static long revision(StudioStore store) {
        return store.graph(Graphs.workspace(WS)).createResource(Graphs.workspace(WS)).getProperty(Cst.revision("surface")).getLong();
    }

    private static Writer created(StudioStore store) {
        Writer writer = new Writer(store, CLOCK);
        assertEquals(200, writer.apply(Command.create(WS, "Plan", AT, null, ModelFactory.createDefaultModel())).status());
        return writer;
    }

    @Test
    void everyWriteLeavesAReceiptWithItsCauseSenderAndTimes() {
        StudioStore store = Fixture.textual(RDFConnection.connect(DatasetFactory.createTxnMem()));
        Writer writer = created(store);
        Command save = Command.save(WS, "surface", 0, AT, surface("one"));
        assertEquals(Reply.ok(1), writer.apply(save));
        Model receipts = store.graph(Graphs.receipts(WS));
        Resource r = receipts.createResource(Graphs.receipt(save.id()));
        assertTrue(receipts.contains(r, RDF.type, Cst.Receipt));
        assertEquals("save", r.getProperty(Cst.command).getString());
        assertEquals("service", r.getProperty(Cst.sender).getString());
        assertEquals(AT.toString(), r.getProperty(Cst.requestedAt).getString());
        assertEquals("2026-10-28T09:00:01Z", r.getProperty(Cst.committedAt).getString());
        assertEquals(1, r.getProperty(Cst.receiptRevision).getLong());
        assertTrue(receipts.contains(r, Cst.wrote, receipts.createResource(Graphs.config(WS, "surface"))));
        assertEquals(2, receipts.listSubjectsWithProperty(RDF.type, Cst.Receipt).toList().size(), "the creation's and the save's");
    }

    @Test
    void aRedeliveredCommandIsAnsweredFromItsReceiptAndAppliedOnce() {
        StudioStore store = Fixture.textual(RDFConnection.connect(DatasetFactory.createTxnMem()));
        Writer writer = created(store);
        Command save = Command.save(WS, "surface", 0, AT, surface("one"));
        assertEquals(Reply.ok(1), writer.apply(save));
        assertEquals(Reply.ok(1), writer.apply(save), "the same command again, as after a lost acknowledgement");
        assertEquals(1, revision(store));
    }

    @Test
    void aBatchAppliesInOrderInOneRequest() {
        StudioStore store = Fixture.textual(RDFConnection.connect(DatasetFactory.createTxnMem()));
        Writer writer = created(store);
        List<Reply> replies = writer.apply(List.of(
            Command.save(WS, "surface", 0, AT, surface("one")),
            Command.save(WS, "surface", 1, AT, surface("two")),
            Command.save(WS, "surface", 0, AT, surface("stale")),
            Command.save("not-an-id", "surface", 0, AT, surface("bad"))));
        assertEquals(List.of(Reply.ok(1), Reply.ok(2), Reply.stale(2), replies.get(3)), replies);
        assertEquals(400, replies.get(3).status());
        assertEquals(2, revision(store));
        assertTrue(surface("two").isIsomorphicWith(store.graph(Graphs.config(WS, "surface"))));
    }

    @Test
    void theRevisionGuardInsideTheUpdateStopsAWriteAnotherWriterOvertook() {
        RDFConnection real = RDFConnection.connect(DatasetFactory.createTxnMem());
        AtomicReference<Runnable> before = new AtomicReference<>();
        StudioStore store = interfered(real, before);
        Writer writer = created(store);
        Writer other = new Writer(Fixture.textual(real), CLOCK);
        // Between this writer's read of the revision and its update, another writer saves revision 1.
        before.set(() -> assertEquals(Reply.ok(1), other.apply(Command.save(WS, "surface", 0, AT, surface("theirs")))));
        Reply mine = writer.apply(Command.save(WS, "surface", 0, AT, surface("mine")));
        assertEquals(Reply.stale(1), mine);
        assertEquals(1, revision(store));
        assertTrue(surface("theirs").isIsomorphicWith(store.graph(Graphs.config(WS, "surface"))), "nothing of the overtaken write");
        assertEquals(2, store.graph(Graphs.receipts(WS)).listSubjectsWithProperty(RDF.type, Cst.Receipt).toList().size(),
            "the creation's and the other writer's, none for the overtaken write");
    }

    @Test
    void deletingAWorkspaceKeepsTheReceiptOfTheDeletion() {
        StudioStore store = Fixture.textual(RDFConnection.connect(DatasetFactory.createTxnMem()));
        Writer writer = created(store);
        Command delete = Command.deleteWorkspace(WS);
        assertEquals(Reply.ok(), writer.apply(delete));
        assertTrue(store.graph(Graphs.receipts(WS)).isEmpty());
        assertTrue(store.graph(Graphs.workspace(WS)).isEmpty());
        Model kept = store.graph(Graphs.STORE_RECEIPTS);
        assertEquals("delete-workspace", kept.createResource(Graphs.receipt(delete.id())).getProperty(Cst.command).getString());
    }
}
