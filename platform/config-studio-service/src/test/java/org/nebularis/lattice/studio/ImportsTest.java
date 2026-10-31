// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.Map;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Writer;

/** Fencing imported RDF into a graph stored once by its digest, held by workspaces (ADR-A149 decision 6). */
class ImportsTest {
    private static final String WS = Fixture.id(1);
    private static final String OTHER = Fixture.id(2);
    private static final String DIGEST = "0123456789abcdef".repeat(4);
    private static final String GRAPH = Graphs.importGraph(DIGEST);
    private static final String HELD = Graphs.importedGraph(DIGEST);
    private static final String IMPORTED = Fixture.PREFIXES + "ex:imported ex:p ex:o .";
    private static final String UNIT = "https://example.org/unit/imported";

    @TempDir Path dir;
    Fixture f;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir));
        assertEquals(201, f.createWorkspace("One").status());
        assertEquals(201, f.createWorkspace("Two").status());
    }

    private static String base(String ws) {
        return "/api/workspaces/" + ws;
    }

    private ApiResponse submit(String ws, String principal, String query, String body) {
        Map<String, String> headers = new HashMap<>(Map.of("content-type", Fixture.TURTLE));
        if (principal != null) {
            headers.put("x-lattice-principal", principal);
        }
        return f.send("POST", base(ws) + "/jobs", query, headers, body.getBytes(StandardCharsets.UTF_8));
    }

    private static Model imported() {
        return Fixture.model(IMPORTED);
    }

    /** A fence job as the worker leaves it when it succeeds: the digest on the job and the graph as import.nt. */
    private String finished(String ws) {
        ApiResponse r = submit(ws, null, "kind=fence&target=import", IMPORTED);
        assertEquals(202, r.status());
        String job = r.headers().get("Location").substring("/api/jobs/".length());
        String iri = Graphs.job(job);
        Model m = ModelFactory.createDefaultModel().add(f.store.graph(iri));
        Resource node = m.createResource(iri);
        m.removeAll(node, Cst.status, null);
        node.addProperty(Cst.status, Cst.Succeeded);
        node.addProperty(Cst.digest, DIGEST);
        java.io.StringWriter nt = new java.io.StringWriter();
        RDFDataMgr.write(nt, imported(), Lang.NTRIPLES);
        node.addProperty(Cst.artefact, m.createResource().addProperty(Cst.path, "import.nt")
            .addProperty(Cst.mediaType, "application/n-triples").addProperty(Cst.content, nt.toString()));
        Dataset d = DatasetFactory.create();
        d.addNamedModel(iri, m);
        assertEquals(200, f.writes.send(new Command(java.util.UUID.randomUUID().toString(), "worker", Command.Type.JOB_UPDATE, ws, job,
            null, null, null, null, null, d, null, false)).status());
        return job;
    }

    private ApiResponse fence(String ws, String job, String label) {
        return f.send("POST", base(ws) + "/imports", "job=" + job + (label == null ? "" : "&label=" + label), Map.of(), new byte[0]);
    }

    private ApiResponse held(String ws) {
        return f.get(base(ws) + "/imports/" + DIGEST);
    }

    @Test
    void aFenceJobIsQueuedWithTheBodyAsItsInputAndAReaderMayNotSubmitOne() {
        ApiResponse r = submit(WS, null, "kind=fence&target=import", IMPORTED);
        assertEquals(202, r.status());
        String job = r.headers().get("Location").substring("/api/jobs/".length());
        Model m = f.store.graph(Graphs.job(job));
        Resource node = m.createResource(Graphs.job(job));
        assertTrue(m.contains(node, Cst.kind, Cst.Fence));
        assertTrue(m.contains(node, Cst.status, Cst.Queued));
        assertTrue(f.store.graph(Graphs.jobInput(job)).isIsomorphicWith(imported()));
        assertEquals(200, f.send("POST", base(WS) + "/access", "mode=read-only", Map.of(), new byte[0]).status());
        assertEquals(403, submit(WS, "reviewer", "kind=fence&target=import", IMPORTED).status());
    }

    @Test
    void fencingAFinishedJobAddsTheHoldingAndTheSameContentFromAnotherWorkspaceIsStoredOnce() {
        assertEquals(409, fence(WS, submit(WS, null, "kind=fence&target=import", IMPORTED).headers().get("Location").substring(10), null).status());
        ApiResponse r = fence(WS, finished(WS), "Reference data");
        assertEquals(201, r.status());
        assertTrue(Fixture.model(r).contains(Fixture.model(r).createResource(Graphs.workspace(WS)), Cst.holdsImport, Fixture.model(r).createResource(GRAPH)));
        assertTrue(f.store.graph(HELD).isIsomorphicWith(imported()));
        assertTrue(f.store.graph(Graphs.description(WS)).contains(f.store.graph(Graphs.description(WS)).createResource(GRAPH),
            org.apache.jena.vocabulary.RDFS.label, "Reference data"));
        assertEquals(201, fence(OTHER, finished(OTHER), null).status());
        assertTrue(f.store.graph(HELD).isIsomorphicWith(imported()), "one graph, since one digest is one content");
        assertEquals(1, f.store.graph(HELD).size());
        assertTrue(holds(OTHER));
        assertEquals(404, fence(OTHER, finished(WS), null).status(), "another workspace's job");
    }

    private boolean holds(String ws) {
        return org.nebularis.lattice.studio.model.Workspace.from(ws, f.store.graph(Graphs.description(ws))).imports().containsKey(GRAPH);
    }

    @Test
    void getReadsTheHeldGraphAndAWorkspaceThatDoesNotHoldItGets404() {
        assertEquals(404, held(WS).status());
        assertEquals(201, fence(WS, finished(WS), null).status());
        ApiResponse r = held(WS);
        assertEquals(200, r.status());
        assertTrue(Fixture.model(r).isIsomorphicWith(imported()));
        assertEquals(404, held(OTHER).status());
    }

    @Test
    void releasingLeavesTheGraphForTheOtherHolder() {
        assertEquals(201, fence(WS, finished(WS), null).status());
        assertEquals(201, fence(OTHER, finished(OTHER), null).status());
        assertEquals(204, f.send("DELETE", base(WS) + "/imports/" + DIGEST, null, Map.of(), new byte[0]).status());
        assertEquals(404, held(WS).status());
        assertEquals(404, f.send("DELETE", base(WS) + "/imports/" + DIGEST, null, Map.of(), new byte[0]).status());
        assertFalse(f.store.graph(HELD).isEmpty());
        assertEquals(200, held(OTHER).status());
    }

    @Test
    void aJobNamesTheHeldImportAsContextAndTheWriterRefusesOneThatIsNotHeld() {
        assertEquals(201, fence(WS, finished(WS), null).status());
        ApiResponse r = submit(WS, null, "kind=validate&target=surface", Fixture.PREFIXES + "ex:a ex:p ex:b .");
        assertEquals(202, r.status());
        Model m = Fixture.model(r);
        assertTrue(m.contains(null, Cst.contextGraph, m.createResource(HELD)));
        r = submit(OTHER, null, "kind=validate&target=surface", Fixture.PREFIXES + "ex:a ex:p ex:b .");
        assertFalse(Fixture.model(r).contains(null, Cst.contextGraph, m.createResource(HELD)));
        String job = Fixture.id(99);
        String jobIri = Graphs.job(job);
        Model forged = ModelFactory.createDefaultModel();
        Resource fj = forged.createResource(jobIri);
        fj.addProperty(org.apache.jena.vocabulary.RDF.type, Cst.Job);
        fj.addProperty(Cst.workspace, forged.createResource(Graphs.workspace(OTHER)));
        fj.addProperty(Cst.configGraph, forged.createResource(Graphs.jobInput(job)));
        fj.addProperty(Cst.baselineGraph, forged.createResource(Graphs.baseline(OTHER)));
        fj.addProperty(Cst.status, Cst.Queued);
        fj.addProperty(Cst.contextGraph, forged.createResource(HELD));
        Dataset d = DatasetFactory.create();
        d.addNamedModel(jobIri, forged);
        d.addNamedModel(Graphs.jobInput(job), ModelFactory.createDefaultModel());
        Writer w = new Writer(f.store, Fixture.OPS, Clock.fixed(Instant.parse("2026-10-27T10:00:00Z"), ZoneOffset.UTC));
        assertEquals(400, w.apply(Command.submitJob(OTHER, job, d)).status());
    }

    @Test
    void aPublishJobFromAnImportReadsTheImportAsItsInput() {
        Map<String, String> none = Map.of();
        assertEquals(404, f.send("POST", base(WS) + "/jobs", "kind=publish&target=import&graph=" + DIGEST + "&unit=" + UNIT, none, new byte[0]).status());
        assertEquals(201, fence(WS, finished(WS), null).status());
        ApiResponse r = f.send("POST", base(WS) + "/jobs", "kind=publish&target=import&graph=" + DIGEST + "&unit=" + UNIT, none, new byte[0]);
        assertEquals(202, r.status());
        String job = r.headers().get("Location").substring("/api/jobs/".length());
        assertTrue(f.store.graph(Graphs.jobInput(job)).isIsomorphicWith(imported()));
        Model m = f.store.graph(Graphs.job(job));
        assertTrue(m.contains(m.createResource(Graphs.job(job)), Cst.unit, m.createResource(UNIT)));
        assertEquals(404, f.send("POST", base(OTHER) + "/jobs", "kind=publish&target=import&graph=" + DIGEST + "&unit=" + UNIT, none, new byte[0]).status());
    }
}
