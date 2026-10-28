// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.ResourceFactory;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.RDFS;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.model.Parts;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;

class StudioApiTest {
    private static final String WS = Fixture.id(1);
    private static final String WS_PATH = "/api/workspaces/" + WS;
    private static final String SURFACE = WS_PATH + "/graphs/surface";
    private static final String LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/";
    private static final String CONFIG = config("surface");

    /** A one-subject configuration that belongs to {@code part}, since it uses that part's namespace. */
    private static String config(String part) {
        return Fixture.PREFIXES + "ex:cfg <" + LATTICE + part + "#label> \"one\" .";
    }

    @TempDir Path dir;
    Fixture f;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir));
    }

    private static void same(Model expected, Model actual) {
        assertTrue(expected.isIsomorphicWith(actual), () -> "expected " + expected + " but was " + actual);
    }

    private Resource ws() {
        return f.store.graph(Graphs.workspace(WS)).createResource(Graphs.workspace(WS));
    }

    @Test
    void createsAWorkspaceFromTurtleAndUsesTheDecodedSlugAsLabel() {
        ApiResponse r = f.createWorkspace("Caf%C3%A9%20plan+1%20");
        assertEquals(201, r.status());
        assertEquals("/api/workspaces/" + WS, r.headers().get("Location"));
        assertEquals("text/turtle; charset=utf-8", r.headers().get("Content-Type"));
        Resource node = Fixture.model(r).getResource(Graphs.workspace(WS));
        assertEquals("Café plan+1", node.getProperty(RDFS.label).getString());
        assertEquals(1, node.getProperty(Cst.baselineRevision).getInt());
        for (String name : List.of("vocabulary", "quantification", "eligibility", "surface", "persistence")) {
            assertEquals(0, node.getProperty(Cst.revision(name)).getInt(), name);
        }
        assertEquals(Graphs.baseline(WS, 1), node.getProperty(Cst.baselineGraph).getResource().getURI());
        assertEquals("2026-10-27T10:00:00Z", node.getProperty(Cst.createdAt).getLiteral().getLexicalForm());
        assertEquals(1, f.store.graph(Graphs.baseline(WS, 1)).size());
    }

    @Test
    void missingOrBlankSlugGivesUntitledWorkspace() {
        f.createWorkspace("%20%20");
        assertEquals("Untitled workspace", ws().getProperty(RDFS.label).getString());
        assertEquals("Untitled workspace", Fixture.model(f.createWorkspace(null)).getResource(Graphs.workspace(Fixture.id(2)))
            .getProperty(RDFS.label).getString());
    }

    @Test
    void getAndListShowTheWorkspace() {
        f.createWorkspace("One");
        assertEquals(200, f.get(WS_PATH).status());
        Model list = Fixture.model(f.get("/api/workspaces"));
        assertTrue(list.contains(list.getResource(Graphs.workspace(WS)), RDF.type, Cst.Workspace));
        assertEquals(404, f.get("/api/workspaces/" + Fixture.id(9)).status());
    }

    @Test
    void baselineHasEtag1AndSurfaceEtag0() {
        f.createWorkspace("One");
        ApiResponse baseline = f.get(WS_PATH + "/graphs/baseline");
        assertEquals("\"1\"", baseline.headers().get("ETag"));
        assertTrue(new String(baseline.body()).contains("https://example.org/p"));
        ApiResponse surface = f.get(SURFACE);
        assertEquals("\"0\"", surface.headers().get("ETag"));
        assertEquals(200, surface.status());
        assertTrue(Fixture.model(surface).isEmpty());
    }

    @Test
    void putSurfaceWithMatchingIfMatchStoresTheGraphAndMovesTheRevision() {
        f.createWorkspace("One");
        ApiResponse r = f.put(SURFACE, "\"0\"", CONFIG);
        assertEquals(204, r.status());
        assertEquals("\"1\"", r.headers().get("ETag"));
        same(Fixture.model(CONFIG), f.store.graph(Graphs.config(WS, "surface")));
        assertEquals(1, ws().getProperty(Cst.surfaceRevision).getInt());
        assertEquals("\"1\"", f.get(SURFACE).headers().get("ETag"));
    }

    @Test
    void aGraphHoldingAnotherPartsTermsIs422AndLeavesTheGraphUnchanged() {
        f.createWorkspace("One");
        f.put(SURFACE, "\"0\"", CONFIG);
        for (String[] c : new String[][] {
            {SURFACE, Fixture.PREFIXES + "ex:cfg ex:p \"plain\" .", "belongs to baseline"},
            {SURFACE, CONFIG + "\nex:profile a <" + LATTICE + "persistence#DataAccessProfile> .", "belongs to persistence"},
            {WS_PATH + "/graphs/baseline", Fixture.PREFIXES + "ex:s a <http://www.w3.org/2004/02/skos/core#ConceptScheme> .", "belongs to vocabulary"},
        }) {
            ApiResponse r = f.put(c[0], "\"1\"", c[1]);
            assertEquals(422, r.status(), c[1]);
            String message = new String(r.body(), java.nio.charset.StandardCharsets.UTF_8);
            assertTrue(message.contains(c[2]), message);
        }
        same(Fixture.model(CONFIG), f.store.graph(Graphs.config(WS, "surface")));
        assertEquals(1, ws().getProperty(Cst.surfaceRevision).getInt());
    }

    @Test
    void partsAreDecidedAsTheBrowserSplitsThem() {
        String eligibility = LATTICE + "eligibility#";
        Model m = Fixture.model(Fixture.PREFIXES
            + "ex:q a <" + eligibility + "Question> ; <" + eligibility + "range> ex:r ; ex:path [ ex:step [ ex:n 1 ] ] .\n"
            + "ex:r a <" + LATTICE + "quantification#RangeSet> .\n"
            + "ex:c <http://www.w3.org/2004/02/skos/core#inScheme> ex:s .\n"
            + "ex:x ex:p ex:y .\n"
            + "[] ex:orphan 1 .");
        Map<Resource, String> owners = Parts.owners(m);
        assertEquals("eligibility", owners.get(m.getResource("https://example.org/q")));
        assertEquals("quantification", owners.get(m.getResource("https://example.org/r")));
        assertEquals("vocabulary", owners.get(m.getResource("https://example.org/c")));
        assertEquals("baseline", owners.get(m.getResource("https://example.org/x")));
        m.listSubjects().filterKeep(Resource::isAnon).forEachRemaining(b ->
            assertEquals(b.hasProperty(m.createProperty("https://example.org/orphan")) ? "baseline" : "eligibility", owners.get(b)));
    }

    @Test
    void blankNodesSurviveASaveWithTheirStructure() {
        f.createWorkspace("One");
        String config = Fixture.PREFIXES + "ex:cfg a <" + LATTICE + "surface#IndexContract> ; ex:list ( \"a\" \"b\" ) ; ex:node [ ex:p [ ex:q 1 ] ] .";
        assertEquals(204, f.put(SURFACE, "\"0\"", config).status());
        same(Fixture.model(config), f.store.graph(Graphs.config(WS, "surface")));
        same(Fixture.model(config), Fixture.model(f.get(SURFACE)));
    }

    @Test
    void putWithStaleIfMatchIs412AndLeavesTheGraphUnchanged() {
        f.createWorkspace("One");
        f.put(SURFACE, "\"0\"", CONFIG);
        ApiResponse r = f.put(SURFACE, "\"0\"", config("surface").replace("one", "two"));
        assertEquals(412, r.status());
        same(Fixture.model(CONFIG), f.store.graph(Graphs.config(WS, "surface")));
        assertEquals(1, ws().getProperty(Cst.surfaceRevision).getInt());
    }

    @Test
    void putWithoutIfMatchIs428() {
        f.createWorkspace("One");
        assertEquals(428, f.put(SURFACE, null, CONFIG).status());
        assertTrue(f.store.graph(Graphs.config(WS, "surface")).isEmpty());
    }

    @Test
    void putBaselineWritesRevision2InANewGraphAndKeepsRevision1() {
        f.createWorkspace("One");
        ApiResponse r = f.put(WS_PATH + "/graphs/baseline", "\"1\"", Fixture.PREFIXES + "ex:x ex:p ex:y , ex:z .");
        assertEquals(204, r.status());
        assertEquals("\"2\"", r.headers().get("ETag"));
        assertEquals(2, f.store.graph(Graphs.baseline(WS, 2)).size());
        assertEquals(1, f.store.graph(Graphs.baseline(WS, 1)).size());
        assertEquals(Graphs.baseline(WS, 2), ws().getProperty(Cst.baselineGraph).getResource().getURI());
        assertEquals(2, ws().getProperty(Cst.baselineRevision).getInt());
    }

    @Test
    void badTurtleIs400AndStoresNothing() {
        assertEquals(400, f.send("POST", "/api/workspaces", Map.of("content-type", Fixture.TURTLE), "ex:a ex:p").status());
        f.createWorkspace("One");
        assertEquals(400, f.put(SURFACE, "\"0\"", "this is not turtle {").status());
        assertTrue(f.store.graph(Graphs.config(WS, "surface")).isEmpty());
        assertEquals(0, ws().getProperty(Cst.surfaceRevision).getInt());
        assertEquals(400, f.post(WS_PATH + "/jobs", "kind=validate&target=surface", "nonsense (").status());
    }

    @Test
    void aWrongContentTypeIs415() {
        assertEquals(415, f.send("POST", "/api/workspaces", Map.of("content-type", "application/json"), "{}").status());
        assertEquals(415, f.send("POST", "/api/workspaces", Map.of(), "").status());
        f.createWorkspace("One");
        assertEquals(415, f.send("PUT", SURFACE, Map.of("content-type", "text/plain", "if-match", "\"0\""), "").status());
    }

    @Test
    void aBodyOver5MiBIs413() {
        byte[] big = new byte[5 * 1024 * 1024 + 1];
        assertEquals(413, f.send("POST", "/api/workspaces", null, Map.of("content-type", Fixture.TURTLE), big).status());
    }

    @Test
    void postJobWritesTheInputAndJobGraphsAndPublishesExactlyTheJobIri() {
        f.createWorkspace("One");
        String job = Fixture.id(2);
        ApiResponse r = f.post(WS_PATH + "/jobs", "kind=compile&target=persistence", CONFIG);
        assertEquals(202, r.status());
        assertEquals("/api/jobs/" + job, r.headers().get("Location"));
        assertEquals(List.of("urn:lattice:studio:job:" + job), f.bus.published());
        Model expected = Fixture.model(Fixture.PREFIXES + """
            <urn:lattice:studio:job:%1$s> a cst:Job ;
              cst:kind cst:Compile ; cst:target cst:Persistence ;
              cst:workspace <urn:lattice:studio:ws:%2$s> ;
              cst:configGraph <urn:lattice:studio:job:%1$s:input> ;
              cst:baselineGraph <urn:lattice:studio:ws:%2$s:baseline:1> ;
              cst:status cst:Queued ;
              cst:submittedAt "2026-10-27T10:00:00Z"^^<http://www.w3.org/2001/XMLSchema#dateTime> .
            """.formatted(job, WS));
        same(expected, f.store.graph(Graphs.job(job)));
        same(expected, Fixture.model(r));
        same(Fixture.model(CONFIG), f.store.graph(Graphs.jobInput(job)));
    }

    @Test
    void anInvalidKindOrTargetIs400() {
        f.createWorkspace("One");
        assertEquals(400, f.post(WS_PATH + "/jobs", "kind=build&target=surface", CONFIG).status());
        assertEquals(400, f.post(WS_PATH + "/jobs", "kind=validate&target=baseline", CONFIG).status());
        assertEquals(400, f.post(WS_PATH + "/jobs", "kind=compile&target=vocabulary", CONFIG).status());
        assertEquals(400, f.post(WS_PATH + "/jobs", "kind=compile&target=quantification", CONFIG).status());
        assertEquals(400, f.post(WS_PATH + "/jobs", null, CONFIG).status());
        assertEquals(404, f.post("/api/workspaces/" + Fixture.id(9) + "/jobs", "kind=validate&target=surface", CONFIG).status());
        assertTrue(f.bus.published().isEmpty());
    }

    @Test
    void aBusThatThrowsStillAnswers202WithAFailedJob() throws IOException {
        Fixture failing = new Fixture(Fixture.assetsDir(dir.resolve("b")), iri -> {
            throw new IOException("broker down");
        });
        failing.createWorkspace("One");
        ApiResponse r = failing.post(WS_PATH + "/jobs", "kind=validate&target=surface", CONFIG);
        assertEquals(202, r.status());
        Resource job = Fixture.model(r).getResource(Graphs.job(Fixture.id(2)));
        assertEquals(Cst.Failed, job.getPropertyResourceValue(Cst.status));
        assertTrue(job.getProperty(Cst.failureMessage).getString().contains("IOException"));
        assertEquals(1, failing.store.graph(Graphs.job(Fixture.id(2))).listObjectsOfProperty(Cst.status).toList().size());
        assertEquals(Cst.Failed, failing.store.graph(Graphs.job(Fixture.id(2))).getResource(Graphs.job(Fixture.id(2)))
            .getPropertyResourceValue(Cst.status));
    }

    @Test
    void getJobReturnsTheGraphAndDeleteDropsBothGraphs() {
        f.createWorkspace("One");
        f.post(WS_PATH + "/jobs", "kind=validate&target=surface", CONFIG);
        String job = Fixture.id(2);
        assertEquals(200, f.get("/api/jobs/" + job).status());
        assertEquals(204, f.send("DELETE", "/api/jobs/" + job, Map.of(), null).status());
        assertTrue(f.store.graph(Graphs.job(job)).isEmpty());
        assertTrue(f.store.graph(Graphs.jobInput(job)).isEmpty());
        assertEquals(404, f.get("/api/jobs/" + job).status());
        assertEquals(404, f.send("DELETE", "/api/jobs/" + job, Map.of(), null).status());
    }

    @Test
    void theWorkspaceJobListingHoldsCompileJobsOnlyWithoutReportOrArtefacts() {
        f.createWorkspace("One");
        f.post(WS_PATH + "/jobs", "kind=validate&target=surface", CONFIG);
        f.post(WS_PATH + "/jobs", "kind=compile&target=surface", CONFIG);
        String compile = Graphs.job(Fixture.id(3));
        // What the worker adds when a compilation ends.
        Model done = f.store.graph(compile);
        Resource job = done.getResource(compile);
        done.removeAll(job, Cst.status, null);
        Resource artefact = done.createResource();
        artefact.addProperty(ResourceFactory.createProperty(Cst.NS + "content"), "secret content");
        job.addProperty(Cst.status, ResourceFactory.createResource(Cst.NS + "Succeeded"))
            .addProperty(ResourceFactory.createProperty(Cst.NS + "artefact"), artefact)
            .addProperty(ResourceFactory.createProperty(Cst.NS + "report"), done.createResource())
            .addProperty(Cst.finishedAt, "2026-10-27T10:01:00Z");
        f.store.write(List.of(), Map.of(compile, done));

        Model list = Fixture.model(f.get(WS_PATH + "/jobs"));
        assertEquals(List.of(compile), list.listSubjectsWithProperty(RDF.type, Cst.Job).toList().stream()
            .map(Resource::getURI).toList());
        Resource listed = list.getResource(compile);
        assertEquals(Cst.Compile, listed.getPropertyResourceValue(Cst.kind));
        assertEquals(Cst.Surface, listed.getPropertyResourceValue(Cst.target));
        assertEquals("Succeeded", listed.getPropertyResourceValue(Cst.status).getLocalName());
        assertTrue(listed.hasProperty(Cst.submittedAt));
        assertTrue(listed.hasProperty(Cst.finishedAt));
        assertFalse(new String(f.get(WS_PATH + "/jobs").body()).contains("secret content"));
        assertEquals(0, list.listStatements(null, ResourceFactory.createProperty(Cst.NS + "artefact"), (Resource) null).toList().size());
        assertNull(listed.getProperty(ResourceFactory.createProperty(Cst.NS + "report")));
    }

    @Test
    void eachNewPartIsSavedUnderItsOwnRevisionAndCheckedAsATarget() {
        f.createWorkspace("One");
        for (String name : List.of("vocabulary", "quantification", "eligibility")) {
            ApiResponse saved = f.put(WS_PATH + "/graphs/" + name, "\"0\"", config(name));
            assertEquals(204, saved.status(), name);
            assertEquals("\"1\"", saved.headers().get("ETag"));
            same(Fixture.model(config(name)), f.store.graph(Graphs.config(WS, name)));
            assertEquals(1, ws().getProperty(Cst.revision(name)).getInt());
            assertEquals(202, f.post(WS_PATH + "/jobs", "kind=validate&target=" + name, CONFIG).status(), name);
        }
        assertEquals(202, f.post(WS_PATH + "/jobs", "kind=compile&target=eligibility", CONFIG).status());
        assertEquals(0, ws().getProperty(Cst.surfaceRevision).getInt());
    }

    @Test
    void aWorkspaceDescribedBeforeTheNewPartsReadsTheirRevisionsAsZero() {
        f.createWorkspace("One");
        Model old = f.store.graph(Graphs.workspace(WS));
        old.removeAll(null, Cst.revision("vocabulary"), null).removeAll(null, Cst.revision("eligibility"), null);
        f.store.write(List.of(), Map.of(Graphs.workspace(WS), old));
        assertEquals("\"0\"", f.get(WS_PATH + "/graphs/vocabulary").headers().get("ETag"));
        assertEquals(204, f.put(WS_PATH + "/graphs/eligibility", "\"0\"", config("eligibility")).status());
    }

    @Test
    void deleteWorkspaceDropsItsGraphs() {
        f.createWorkspace("One");
        f.put(WS_PATH + "/graphs/baseline", "\"1\"", Fixture.PREFIXES + "ex:x ex:p ex:y .");
        f.put(SURFACE, "\"0\"", CONFIG);
        assertEquals(204, f.send("DELETE", WS_PATH, Map.of(), null).status());
        for (String graph : List.of(Graphs.workspace(WS), Graphs.baseline(WS, 1), Graphs.baseline(WS, 2),
            Graphs.config(WS, "surface"), Graphs.config(WS, "persistence"), Graphs.config(WS, "vocabulary"),
            Graphs.config(WS, "quantification"), Graphs.config(WS, "eligibility"))) {
            assertTrue(f.store.graph(graph).isEmpty(), graph);
        }
        assertEquals(404, f.get(WS_PATH).status());
        assertEquals(404, f.send("DELETE", WS_PATH, Map.of(), null).status());
    }

    @Test
    void idsThatAreNotLowerCaseUuidsAre404() {
        assertEquals(404, f.get("/api/workspaces/not-a-uuid").status());
        assertEquals(404, f.get("/api/workspaces/" + WS.toUpperCase() + "/graphs/surface").status());
        assertEquals(404, f.get("/api/jobs/1").status());
        assertEquals(404, f.get("/api/jobs/" + Fixture.id(1) + "/").status());
        assertEquals(404, f.get(WS_PATH + "/graphs/other").status());
        assertEquals(404, f.get("/api/nothing").status());
    }

    @Test
    void aKnownPathWithAnotherMethodIs405() {
        assertEquals(405, f.send("DELETE", "/api/health", Map.of(), null).status());
        assertEquals(405, f.send("PUT", "/api/workspaces", Map.of(), null).status());
        assertEquals("GET, POST", f.send("OPTIONS", "/api/workspaces", Map.of(), null).headers().get("Allow"));
        assertEquals(405, f.send("POST", "/api/jobs/" + Fixture.id(1), Map.of(), null).status());
    }

    @Test
    void vocabularyCarriesAnEtagAndAMatchingIfNoneMatchGives304() {
        ApiResponse r = f.get("/api/vocabulary");
        assertEquals(200, r.status());
        String etag = r.headers().get("ETag");
        assertTrue(etag.startsWith("\"") && etag.endsWith("\""));
        assertEquals("no-cache", r.headers().get("Cache-Control"));
        ApiResponse again = f.send("GET", "/api/vocabulary", Map.of("if-none-match", etag), null);
        assertEquals(304, again.status());
        assertEquals(0, again.body().length);
        assertEquals(200, f.send("GET", "/api/vocabulary", Map.of("if-none-match", "\"other\""), null).status());
    }

    @Test
    void theSamplesListingAndASampleGraphAreServed() {
        assertTrue(new String(f.get("/api/samples").body()).contains("urn:lattice:studio:sample:lending"));
        ApiResponse sample = f.get("/api/samples/lending");
        assertEquals(200, sample.status());
        assertTrue(new String(sample.body()).contains("ex:loan"));
        assertEquals(404, f.get("/api/samples/missing").status());
        assertEquals(404, f.get("/api/samples/..%2Fvocabulary").status());
    }

    @Test
    void everyApiResponseIsNoStoreAndNosniffExceptTheVocabularyCache() {
        ApiResponse health = f.get("/api/health");
        assertEquals("ok", new String(health.body()));
        assertEquals("no-store", health.headers().get("Cache-Control"));
        assertEquals("nosniff", health.headers().get("X-Content-Type-Options"));
        assertEquals("no-store", f.get("/api/nothing").headers().get("Cache-Control"));
    }
}
