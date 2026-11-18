// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Proxy;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicReference;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdfconnection.RDFConnection;
import org.apache.jena.update.Update;
import org.apache.jena.update.UpdateRequest;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.model.Workspace;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.Skolem;
import org.nebularis.lattice.studio.store.StudioOperations.Family;
import org.nebularis.lattice.studio.store.StudioStore;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Reply;
import org.nebularis.lattice.studio.writes.Writer;

/**
 * A command that writes several aggregates orders its operations so that a guard failing part way leaves nothing a
 * reader acts on (ADR-A149 decision 13). Each test makes the later operation's guard fail with a write that runs just
 * before the writer's one update, and reads the store as a reader does.
 */
class MultiAggregateCommandsTest {
    private static final String WS = Fixture.id(1);
    private static final String DOC = Fixture.id(3);
    private static final Instant AT = Instant.parse("2026-10-28T09:00:00Z");
    private static final Clock CLOCK = Clock.fixed(Instant.parse("2026-10-28T09:00:01Z"), ZoneOffset.UTC);
    private static final String UNIT = "https://example.org/unit/scheme";
    private static final String D1 = "0123456789abcdef";
    private static final String D2 = "fedcba9876543210";
    private static final String D3 = "00ff00ff00ff00ff";

    /** A store whose first update is preceded by {@code before}, which writes through the real connection. */
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

    private static Writer writer(StudioStore store) {
        return new Writer(store, Fixture.OPS, Fixture.MAINTENANCE, CLOCK);
    }

    /** An aggregate's generated operations, applied as they are, which no command makes alone. */
    private static void write(RDFConnection real, List<Update> operations) {
        UpdateRequest request = new UpdateRequest();
        operations.forEach(request::add);
        Fixture.textual(real).update(request);
    }

    private static Model baseline(String value) {
        return Fixture.model(Fixture.PREFIXES + "ex:a ex:p \"" + value + "\" .");
    }

    private static Model surface(String value) {
        return Fixture.model(Fixture.PREFIXES + "ex:cfg <https://www.nebularis.org/neuro-semantic/lattice/surface#label> \"" + value + "\" .");
    }

    /** A document's graph as the writer accepts one, the node holding its markup once. */
    private static Model docGraph(String markup) {
        Model m = ModelFactory.createDefaultModel();
        m.createResource(Graphs.documentNode(DOC)).addProperty(Cst.markup, "<document>" + markup + "</document>");
        return m;
    }

    private static String version(String digest) {
        return UNIT + "/rev/1-" + digest;
    }

    private static Model content(String digest) {
        Model m = ModelFactory.createDefaultModel();
        Resource v = m.createResource(version(digest));
        v.addProperty(Cst.Fnd.hasIdentity, m.createResource(UNIT));
        v.addProperty(m.createProperty("https://example.org/p"), digest);
        return m;
    }

    private static void created(Writer writer) {
        assertEquals(Reply.ok(1), writer.apply(Command.create(WS, "Plan", AT, null, baseline("baseline"))));
    }

    /** The description of a workspace another creator made, with the generated operation that creates it. */
    private static List<Update> otherDescription() {
        return Fixture.OPS.create(Family.DESCRIPTION, Graphs.workspace(WS),
            Skolem.skolemise(Workspace.created(WS, "Other", AT, null).stored()), "urn:txn:interference/1");
    }

    /**
     * {@code create}: the parts before the description. The later operation, the description's create-if-absent, finds
     * the description another creator wrote, so the receipt is not written.
     */
    @Test
    void createWhoseDescriptionGuardFailsLeavesItsBaselineUnderTheOtherDescriptionAndIsRefusedOnResend() {
        RDFConnection real = RDFConnection.connect(DatasetFactory.createTxnMem());
        AtomicReference<Runnable> before = new AtomicReference<>();
        StudioStore store = interfered(real, before);
        Writer writer = writer(store);
        Command create = Command.create(WS, "Plan", AT, null, baseline("baseline"));
        before.set(() -> write(real, otherDescription()));

        Reply mine = writer.apply(create);

        assertEquals(Reply.refused("the workspace exists"), mine);
        assertFalse(store.graph(Graphs.receipts(WS)).contains(null, Cst.commandId, create.id()), "no receipt names the command");
        // The earlier operation applied: the baseline part is written, with its version row.
        assertEquals(Optional.of(1L), Fixture.OPS.seq(store, Family.PART, Graphs.partRoot(WS, "baseline")));
        assertTrue(baseline("baseline").isIsomorphicWith(store.graph(Graphs.baseline(WS))));
        // What a reader acts on is the workspace the description names, which is the other creator's.
        Workspace seen = Fixture.OPS.workspace(store, WS);
        assertNotNull(seen);
        assertEquals("Other", seen.label(), "the command's label is nowhere");
        assertTrue(seen.documents().isEmpty());
        assertTrue(seen.imports().isEmpty());
        assertEquals(1L, seen.revision("baseline"), "the baseline the command wrote is read as the other workspace's");

        assertEquals(Reply.refused("the workspace exists"), writer.apply(create));
        assertEquals("Other", Fixture.OPS.workspace(store, WS).label());
    }

    /**
     * {@code importing}: the parts and the documents before the description. The later operation, the description's
     * create-if-absent, finds the description another creator wrote.
     */
    @Test
    void importingWhoseDescriptionGuardFailsLeavesItsPartsAndDocumentsUnderTheOtherDescriptionAndIsRefusedOnResend() {
        RDFConnection real = RDFConnection.connect(DatasetFactory.createTxnMem());
        AtomicReference<Runnable> before = new AtomicReference<>();
        StudioStore store = interfered(real, before);
        Writer writer = writer(store);
        Workspace described = Workspace.created(WS, "Imported", AT, null)
            .withDocument(DOC, new Workspace.Document("Licence", "software-licence", 0L, AT), AT);
        Dataset body = DatasetFactory.create();
        body.addNamedModel(Graphs.workspace(WS), described.stored());
        body.addNamedModel(Graphs.partRoot(WS, "baseline"), baseline("imported"));
        body.addNamedModel(Graphs.partRoot(WS, "surface"), surface("imported"));
        body.addNamedModel(Graphs.document(WS, DOC), docGraph("imported"));
        Command importing = Command.importing(WS, AT, "Imported", body);
        before.set(() -> write(real, otherDescription()));

        Reply mine = writer.apply(importing);

        assertEquals(Reply.refused("the workspace exists"), mine);
        assertFalse(store.graph(Graphs.receipts(WS)).contains(null, Cst.commandId, importing.id()), "no receipt names the command");
        // The earlier operations applied: the parts and the document are written, with their rows.
        assertEquals(Optional.of(1L), Fixture.OPS.seq(store, Family.PART, Graphs.partRoot(WS, "baseline")));
        assertEquals(Optional.of(1L), Fixture.OPS.seq(store, Family.PART, Graphs.partRoot(WS, "surface")));
        assertEquals(Optional.of(1L), Fixture.OPS.seq(store, Family.DOCUMENT, Graphs.document(WS, DOC)));
        assertTrue(surface("imported").isIsomorphicWith(store.graph(Graphs.config(WS, "surface"))));
        assertTrue(docGraph("imported").isIsomorphicWith(store.graph(Graphs.documentGraph(WS, DOC))));
        // What a reader acts on: the other creator's workspace, which lists no document and no import.
        Workspace seen = Fixture.OPS.workspace(store, WS);
        assertNotNull(seen);
        assertEquals("Other", seen.label());
        assertTrue(seen.documents().isEmpty(), "the imported document is listed nowhere");
        assertTrue(seen.imports().isEmpty());
        assertEquals(1L, seen.revision("surface"), "the imported part is read as the other workspace's");

        assertEquals(Reply.refused("the workspace exists"), writer.apply(importing));
    }

    /**
     * {@code saveDocument} of a new document: the document before the description. The later operation, the
     * description's replace, is guarded on the description's revision, which another command moved.
     */
    @Test
    void savingANewDocumentWhoseDescriptionGuardFailsLeavesAnOrphanDocumentGraphAndAResendCompletesIt() {
        RDFConnection real = RDFConnection.connect(DatasetFactory.createTxnMem());
        AtomicReference<Runnable> before = new AtomicReference<>();
        StudioStore store = interfered(real, before);
        Writer writer = writer(store);
        created(writer);
        Writer other = writer(Fixture.textual(real));
        Command save = Command.saveDocument(WS, DOC, 0, AT, "Licence", "software-licence", docGraph("one"));
        long descriptionBefore = Fixture.OPS.seq(store, Family.DESCRIPTION, Graphs.workspace(WS)).orElseThrow();
        before.set(() -> assertEquals(Reply.ok(), other.apply(Command.setAccess(WS, "shared", null))));

        Reply mine = writer.apply(save);

        assertNotEquals(200, mine.status(), mine.toString());
        assertEquals(Reply.refused("the document was deleted, so its id cannot be used again"), mine);
        assertNotEquals(descriptionBefore, Fixture.OPS.seq(store, Family.DESCRIPTION, Graphs.workspace(WS)).orElseThrow(),
            "the other command did move the description the save was guarded on");
        // The earlier operation applied: the document graph and its row are there.
        assertEquals(Optional.of(1L), Fixture.OPS.seq(store, Family.DOCUMENT, Graphs.document(WS, DOC)));
        assertTrue(docGraph("one").isIsomorphicWith(store.graph(Graphs.documentGraph(WS, DOC))));
        // What a reader acts on shows no document, since the description lists none.
        Workspace seen = Fixture.OPS.workspace(store, WS);
        assertTrue(seen.documents().isEmpty());
        assertEquals(0L, seen.documentRevision(DOC));
        assertFalse(store.graph(Graphs.receipts(WS)).contains(null, Cst.commandId, save.id()), "no receipt names the command");

        // The same command again completes it, as if applied once.
        assertEquals(Reply.ok(1), writer.apply(save));
        Workspace done = Fixture.OPS.workspace(store, WS);
        assertEquals(1L, done.documentRevision(DOC));
        assertEquals("Licence", done.documents().get(DOC).title());
        assertTrue(docGraph("one").isIsomorphicWith(store.graph(Graphs.documentGraph(WS, DOC))));
        assertEquals(Optional.of(1L), Fixture.OPS.seq(store, Family.DOCUMENT, Graphs.document(WS, DOC)));
    }

    /**
     * {@code deleteDocument}: the description first, then the document's tombstone. The later operation, the
     * tombstone, is guarded on the document's revision, which a save moved.
     */
    @Test
    void deletingADocumentWhoseTombstoneGuardFailsReadsAsDeletedAndLeavesTheGraphAndAResendIsNotFound() {
        RDFConnection real = RDFConnection.connect(DatasetFactory.createTxnMem());
        AtomicReference<Runnable> before = new AtomicReference<>();
        StudioStore store = interfered(real, before);
        Writer writer = writer(store);
        created(writer);
        assertEquals(Reply.ok(1), writer.apply(Command.saveDocument(WS, DOC, 0, AT, "Licence", "software-licence", docGraph("one"))));
        Writer other = writer(Fixture.textual(real));
        Command delete = Command.deleteDocument(WS, DOC);
        before.set(() -> assertEquals(Reply.ok(2),
            other.apply(Command.saveDocument(WS, DOC, 1, AT, "Licence", "software-licence", docGraph("two")))));

        Reply mine = writer.apply(delete);

        assertNotEquals(200, mine.status(), mine.toString());
        assertEquals(Reply.refused("the workspace changed while the command was applied, so send it again"), mine);
        // The earlier operation applied: the description no longer lists the document, so a reader finds none.
        Workspace seen = Fixture.OPS.workspace(store, WS);
        assertNotNull(seen);
        assertFalse(seen.documents().containsKey(DOC), "the description was replaced first");
        assertEquals(0L, seen.documentRevision(DOC));
        // The later operation did not: the document is not tombstoned, and its graph, saved last by the other command, stays.
        assertEquals(Optional.of(2L), Fixture.OPS.seq(store, Family.DOCUMENT, Graphs.document(WS, DOC)));
        assertTrue(docGraph("two").isIsomorphicWith(store.graph(Graphs.documentGraph(WS, DOC))));

        // The same command again is not completed: the description no longer lists the document.
        assertEquals(Reply.notFound(), writer.apply(delete));
        assertEquals(Optional.of(2L), Fixture.OPS.seq(store, Family.DOCUMENT, Graphs.document(WS, DOC)));
        assertTrue(docGraph("two").isIsomorphicWith(store.graph(Graphs.documentGraph(WS, DOC))));
    }

    /**
     * {@code publish} of a new version onto an existing lineage: the version before the lineage. The later
     * operation, the lineage's replace, is guarded on the lineage's revision, which another publication moved.
     */
    @Test
    void publishingWhoseLineageGuardFailsLeavesAnUnnamedVersionGraphAndAResendCompletesIt() {
        RDFConnection real = RDFConnection.connect(DatasetFactory.createTxnMem());
        AtomicReference<Runnable> before = new AtomicReference<>();
        StudioStore store = interfered(real, before);
        Writer writer = writer(store);
        created(writer);
        assertEquals(Reply.ok(1), writer.apply(Command.publish(WS, UNIT, version(D1), content(D1))));
        Writer other = writer(Fixture.textual(real));
        Command publish = Command.publish(WS, UNIT, version(D2), content(D2));
        before.set(() -> assertEquals(Reply.ok(2), other.apply(Command.publish(WS, UNIT, version(D3), content(D3)))));

        Reply mine = writer.apply(publish);

        assertEquals(Reply.refused("the lineage was published meanwhile, so publish again"), mine);
        // The earlier operation applied: the version's graph is written.
        assertTrue(content(D2).isIsomorphicWith(store.graph(Graphs.version(UNIT, D2))));
        // What a reader acts on is the lineage, which names the other version current and the command's nowhere.
        Model lineage = store.graph(Graphs.lineage(UNIT));
        Resource unit = lineage.createResource(UNIT);
        Resource second = lineage.createResource(version(D2));
        assertTrue(lineage.contains(unit, Cst.current, lineage.createResource(version(D3))));
        assertFalse(lineage.contains(unit, Cst.Fnd.hasVersion, second));
        assertFalse(lineage.contains(null, Cst.Prov.generated, second));
        assertFalse(lineage.contains(null, null, second), "the lineage names the version nowhere");
        assertFalse(store.registry().contains(null, null, second));

        // The same command again completes it, as if applied once.
        Reply again = writer.apply(publish);
        assertEquals(Reply.ok(3), again);
        Model now = store.graph(Graphs.lineage(UNIT));
        assertTrue(now.contains(unit, Cst.current, second));
        assertTrue(now.contains(unit, Cst.Fnd.hasVersion, second));
        assertEquals(1, now.listSubjectsWithProperty(Cst.Prov.generated, second).toList().size(), "one event generated it");
        assertTrue(content(D2).isIsomorphicWith(store.graph(Graphs.version(UNIT, D2))));
        assertEquals(Reply.ok(3), writer.apply(publish), "and a third send is answered from the receipt");
    }

    /**
     * {@code deleteWorkspace}: the description's tombstone first, then each part's. The later operation, a part's
     * tombstone, is guarded on the part's revision, which a save moved.
     */
    @Test
    void deletingAWorkspaceWhosePartTombstoneGuardFailsReadsAsGoneAndLeavesThePartAndAResendDoesNotRemoveIt() {
        RDFConnection real = RDFConnection.connect(DatasetFactory.createTxnMem());
        AtomicReference<Runnable> before = new AtomicReference<>();
        StudioStore store = interfered(real, before);
        Writer writer = writer(store);
        created(writer);
        assertEquals(Reply.ok(1), writer.apply(Command.save(WS, "surface", 0, AT, surface("one"))));
        Writer other = writer(Fixture.textual(real));
        Command delete = Command.deleteWorkspace(WS);
        before.set(() -> assertEquals(Reply.ok(2), other.apply(Command.save(WS, "surface", 1, AT, surface("two")))));

        Reply mine = writer.apply(delete);

        // The command is answered as done, since its receipt rides on the description's tombstone.
        assertEquals(Reply.ok(), mine);
        // The earlier operations applied: the description and the baseline part are tombstoned, so a reader finds no workspace.
        assertNull(Fixture.OPS.workspace(store, WS));
        assertEquals(Optional.empty(), Fixture.OPS.seq(store, Family.DESCRIPTION, Graphs.workspace(WS)));
        assertEquals(Optional.empty(), Fixture.OPS.seq(store, Family.PART, Graphs.partRoot(WS, "baseline")));
        assertTrue(store.rawGraph(Fixture.OPS.graph(Family.PART, Graphs.partRoot(WS, "baseline"))).isEmpty());
        // The later operation did not: the surface part, saved last by the other command, is neither tombstoned nor dropped.
        assertEquals(Optional.of(2L), Fixture.OPS.seq(store, Family.PART, Graphs.partRoot(WS, "surface")));
        assertTrue(surface("two").isIsomorphicWith(store.graph(Graphs.config(WS, "surface"))));

        // The same command again is answered from its receipt, and does not remove the part.
        assertEquals(Reply.ok(), writer.apply(delete));
        assertEquals(Optional.of(2L), Fixture.OPS.seq(store, Family.PART, Graphs.partRoot(WS, "surface")));
        assertTrue(surface("two").isIsomorphicWith(store.graph(Graphs.config(WS, "surface"))));
    }
}
