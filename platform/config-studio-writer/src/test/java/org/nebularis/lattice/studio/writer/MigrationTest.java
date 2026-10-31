// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.SortedSet;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.vocabulary.RDF;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.model.Workspace;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.StudioOperations;
import org.nebularis.lattice.studio.store.StudioOperations.Family;
import org.nebularis.lattice.studio.store.StudioStore;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.DirectWrites;
import org.nebularis.lattice.studio.writes.Writer;

class MigrationTest {
    private static final String WS = "00000000-0000-4000-8000-000000000001";
    private static final String WS2 = "00000000-0000-4000-8000-000000000002";
    private static final String DOC = "00000000-0000-4000-8000-0000000000d1";
    private static final String JOB = "00000000-0000-4000-8000-0000000000a1";
    private static final String HELD = "a".repeat(64);
    private static final String LOOSE = "b".repeat(64);
    private static final String LINEAGE = "https://example.org/unit";
    private static final String V1 = LINEAGE + "/rev/1-aaaaaaaaaaaaaaaa";
    private static final String V2 = LINEAGE + "/rev/1-bbbbbbbbbbbbbbbb";
    private static final Instant AT = Instant.parse("2026-10-27T10:00:00Z");
    private static final Clock CLOCK = Clock.fixed(AT, ZoneOffset.UTC);
    private static final StudioOperations OPS = StudioOperations.load(Path.of(System.getProperty("studio.assets"), "persistence"), 1L);
    private static final Property P = ResourceFactoryHolder.p("urn:xx:p");
    private static final Property Q = ResourceFactoryHolder.p("urn:xx:q");

    private final StudioStore store = StudioStore.inMemory();
    private final Model[] baselines = new Model[3];
    private Workspace workspace;
    private Model library;
    private Model surface;
    private Model document;
    private Model held;
    private Model loose;
    private Model version1;
    private Model version2;

    @TempDir
    Path assets;

    /** A graph with a node that has a blank node, whose content is named by {@code text}. */
    private static Model withBlank(String text) {
        Model m = ModelFactory.createDefaultModel();
        Resource b = m.createResource();
        m.createResource("urn:xx:a").addProperty(P, b);
        b.addProperty(Q, text);
        return m;
    }

    private void put(String graph, Model m) {
        store.write(List.of(), Map.of(graph, m));
    }

    @BeforeEach
    void oldLayout() {
        String root = Graphs.workspace(WS);
        workspace = Workspace.created(WS, "Plan", AT, null, "alice").withAccess("alice", Workspace.READ_ONLY)
            .withDependencies(Set.of(LINEAGE)).withImport(Graphs.importGraph(HELD), "Held")
            .withDocument(DOC, new Workspace.Document("Doc", "template", 2, AT), AT).revised("baseline", 3);
        Model description = workspace.toModel();
        description.removeAll(description.createResource(root), Cst.baselineGraph, null);
        description.add(description.createResource(root), Cst.baselineGraph, description.createResource(root + ":baseline:3"));
        put(root, description);
        for (int k = 1; k <= 3; k++) {
            baselines[k - 1] = withBlank("revision " + k);
            if (k > 1) {
                baselines[k - 1].createResource("urn:xx:kept").addProperty(P, "same");
            }
            put(root + ":baseline:" + k, baselines[k - 1]);
        }
        library = withBlank("library");
        surface = withBlank("surface");
        document = withBlank("document");
        put(root + ":library", library);
        put(root + ":surface", surface);
        put(Graphs.document(WS, DOC), document);
        held = withBlank("held");
        loose = withBlank("loose");
        put(Graphs.importGraph(HELD), held);
        put(Graphs.importGraph(LOOSE), loose);
        put(Graphs.receipts(WS), withBlank("receipt"));
        Model job = ModelFactory.createDefaultModel();
        job.createResource(Graphs.job(JOB)).addProperty(RDF.type, Cst.Job).addProperty(Cst.workspace, job.createResource(root));
        put(Graphs.job(JOB), job);
        put(Graphs.jobInput(JOB), withBlank("input"));
        put(Graphs.jobReceipts(JOB), withBlank("job receipt"));
        put(Graphs.workspace(WS2), Workspace.created(WS2, "Two", AT, null).toModel());
        put(Graphs.workspace(WS2) + ":baseline:1", withBlank("two"));
        put(Graphs.receipts(WS2), withBlank("two receipt"));
        String pub = "urn:lattice:studio:pub:" + "0".repeat(32);
        Model lineage = ModelFactory.createDefaultModel();
        Resource l = lineage.createResource(LINEAGE);
        l.addProperty(RDF.type, Cst.Fnd.PersistentIdentity).addProperty(Cst.Fnd.hasVersion, lineage.createResource(V1))
            .addProperty(Cst.Fnd.hasVersion, lineage.createResource(V2)).addProperty(Cst.current, lineage.createResource(V2));
        lineage.createResource(V1).addProperty(Cst.Fnd.supersededBy, lineage.createResource(V2));
        put(pub, lineage);
        version1 = version(V1, "one");
        version2 = version(V2, "two");
        put(pub + ":rev:aaaaaaaaaaaaaaaa", version1);
        put(pub + ":rev:bbbbbbbbbbbbbbbb", version2);
    }

    private static Model version(String iri, String text) {
        Model m = withBlank(text);
        m.createResource(iri).addProperty(Cst.Fnd.hasIdentity, m.createResource(LINEAGE));
        return m;
    }

    private Migration.Summary migrate(boolean dryRun) {
        return new Migration(store, OPS, assets, CLOCK, new PrintStream(new ByteArrayOutputStream())).run(dryRun);
    }

    private static void sameDataset(Dataset a, Dataset b) {
        SortedSet<String> names = new java.util.TreeSet<>();
        a.listNames().forEachRemaining(names::add);
        SortedSet<String> others = new java.util.TreeSet<>();
        b.listNames().forEachRemaining(others::add);
        assertEquals(names, others);
        names.forEach(n -> assertTrue(a.getNamedModel(n).isIsomorphicWith(b.getNamedModel(n)), n));
    }

    @Test
    void workspacesReadBackWithTheirHistory() {
        Migration.Summary s = migrate(false);
        assertEquals(2, s.workspaces());
        assertEquals(3 + 1, s.revisions());
        assertEquals(2, s.parts());
        assertEquals(1, s.documents());
        assertEquals(2, s.imports());
        assertEquals(1, s.lineages());
        assertEquals(2, s.versions());
        Workspace ws = OPS.workspace(store, WS);
        assertNotNull(ws);
        assertEquals("Plan", ws.label());
        assertEquals("alice", ws.owner());
        assertEquals(Workspace.READ_ONLY, ws.mode());
        assertEquals(Set.of(LINEAGE), ws.dependencies());
        assertEquals(Map.of(Graphs.importGraph(HELD), "Held"), ws.imports());
        assertEquals("Doc", ws.documents().get(DOC).title());
        assertEquals(3, ws.revision("baseline"));
        assertEquals(1, ws.revision("library"));
        assertEquals(0, ws.revision("persistence"));
        assertEquals(1, ws.documentRevision(DOC));
        assertEquals(1, OPS.workspace(store, WS2).revision("baseline"));
        String baseline = Graphs.partRoot(WS, "baseline");
        for (int k = 1; k <= 3; k++) {
            assertTrue(baselines[k - 1].isIsomorphicWith(OPS.asOf(store, Family.PART, baseline, 3, k)), "revision " + k);
        }
    }

    @Test
    void partsDocumentsImportsAndTheRegistryReadBackIsomorphic() {
        migrate(false);
        assertTrue(library.isIsomorphicWith(store.graph(Graphs.config(WS, "library"))));
        assertTrue(surface.isIsomorphicWith(store.graph(Graphs.config(WS, "surface"))));
        assertTrue(document.isIsomorphicWith(store.graph(Graphs.documentGraph(WS, DOC))));
        assertTrue(OPS.seq(store, Family.PART, Graphs.partRoot(WS, "persistence")).isEmpty());
        assertTrue(held.isIsomorphicWith(store.graph(Graphs.importedGraph(HELD))));
        assertTrue(loose.isIsomorphicWith(store.graph(Graphs.importedGraph(LOOSE))));
        Model registry = store.registry();
        assertTrue(registry.contains(registry.createResource(LINEAGE), Cst.current, registry.createResource(V2)));
        assertTrue(version1.isIsomorphicWith(store.graph(Graphs.version(LINEAGE, "aaaaaaaaaaaaaaaa"))));
        assertTrue(version2.isIsomorphicWith(store.graph(Graphs.version(LINEAGE, "bbbbbbbbbbbbbbbb"))));
    }

    @Test
    void noOldGraphRemainsButTheReceipts() {
        migrate(false);
        for (String g : store.graphNames()) {
            boolean old = g.startsWith("urn:lattice:studio:ws:") || g.startsWith("urn:lattice:studio:pub:")
                || g.startsWith("urn:lattice:studio:job:") || g.startsWith("urn:lattice:studio:import:");
            assertFalse(old && !g.equals(Graphs.receipts(WS)) && !g.equals(Graphs.receipts(WS2)), g);
        }
        assertTrue(store.graphNames().contains(Graphs.receipts(WS)));
        assertTrue(store.graphNames().contains(Graphs.receipts(WS2)));
    }

    @Test
    void runningAgainChangesNothing() {
        migrate(false);
        Dataset once = store.snapshot();
        Migration.Summary again = migrate(false);
        assertEquals(0, again.workspaces() + again.lineages() + again.versions() + again.imports() + again.graphsDropped());
        assertEquals(null, again.backup());
        sameDataset(once, store.snapshot());
    }

    @Test
    void aDryRunWritesNothingAndReports() {
        Dataset before = store.snapshot();
        Migration.Summary s = migrate(true);
        assertEquals(2, s.workspaces());
        assertEquals(1, s.lineages());
        assertEquals(2, s.imports());
        assertTrue(s.graphsDropped() > 0);
        sameDataset(before, store.snapshot());
        assertFalse(Files.exists(s.backup()));
    }

    @Test
    void aSaveAppliesAfterwards() {
        migrate(false);
        DirectWrites writes = new DirectWrites(new Writer(store, OPS, CLOCK));
        Model wording = ModelFactory.createDefaultModel();
        wording.createResource("urn:xx:a").addProperty(ResourceFactoryHolder.p("https://www.nebularis.org/neuro-semantic/lattice/wording#label"), "saved");
        assertEquals(200, writes.send(Command.save(WS, "library", 1, AT, wording)).status());
        Model next = ModelFactory.createDefaultModel();
        next.createResource("urn:xx:a").addProperty(P, "saved");
        assertEquals(2, OPS.workspace(store, WS).revision("library"));
        assertEquals(200, writes.send(Command.save(WS, "baseline", 3, AT, next)).status());
        assertEquals(4, OPS.workspace(store, WS).revision("baseline"));
    }

    @Test
    void theBackupHoldsEveryGraphThatWasThere() throws Exception {
        Dataset before = store.snapshot();
        Path file = migrate(false).backup();
        Dataset backed = DatasetFactory.create();
        RDFDataMgr.read(backed, file.toUri().toString(), Lang.TRIG);
        sameDataset(before, backed);
    }

    /** {@code Property} factory kept out of the fields' way. */
    private static final class ResourceFactoryHolder {
        static Property p(String iri) {
            return org.apache.jena.rdf.model.ResourceFactory.createProperty(iri);
        }
    }
}
