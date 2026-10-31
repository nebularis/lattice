// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.vocabulary.RDF;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Reply;

/** A workspace's dependencies on published units, and the jobs that read them (ADR-A149 decision 5). */
class DependenciesTest {
    private static final String WS = Fixture.id(1);
    private static final String BASE = "/api/workspaces/" + WS;
    private static final String CONFIG = Fixture.PREFIXES
        + "ex:cfg <https://www.nebularis.org/neuro-semantic/lattice/surface#label> \"one\" .";
    private static final String UNIT = "https://example.org/unit/scheme";
    private static final String D1 = "0123456789abcdef";
    private static final String D2 = "fedcba9876543210";

    @TempDir Path dir;
    Fixture f;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir));
        assertEquals(201, f.createWorkspace("Plan").status());
        assertEquals(204, f.put(BASE + "/graphs/surface", "\"0\"", CONFIG).status());
    }

    private static String version(String digest) {
        return UNIT + "/rev/1-" + digest;
    }

    private static Model content(String digest) {
        Model m = ModelFactory.createDefaultModel();
        m.createResource(version(digest)).addProperty(Cst.Fnd.hasIdentity, m.createResource(UNIT))
            .addProperty(m.createProperty("https://example.org/p"), digest);
        return m;
    }

    /** Publishes {@code digest} straight through the writer, as a finished publish job would. */
    private void published(String digest) {
        assertEquals(200, f.writes.send(Command.publish(WS, UNIT, version(digest), content(digest))).status());
    }

    private ApiResponse depend(String principal, String... iris) {
        StringBuilder ttl = new StringBuilder(Fixture.PREFIXES);
        for (String iri : iris) {
            ttl.append("<").append(Graphs.workspace(WS)).append("> cst:dependsOn <").append(iri).append("> .\n");
        }
        return dependBody(principal, ttl.toString());
    }

    private ApiResponse dependBody(String principal, String body) {
        Map<String, String> headers = new HashMap<>(Map.of("content-type", Fixture.TURTLE));
        if (principal != null) {
            headers.put("x-lattice-principal", principal);
        }
        return f.send("PUT", BASE + "/dependencies", null, headers, body.getBytes(StandardCharsets.UTF_8));
    }

    private Set<String> dependencies(ApiResponse r) {
        Model m = Fixture.model(r);
        return m.listObjectsOfProperty(m.createResource(Graphs.workspace(WS)), Cst.dependsOn).toList().stream()
            .map(o -> o.asResource().getURI()).collect(Collectors.toSet());
    }

    /** The context graphs of a job of {@code kind} that the workspace submits now. */
    private Set<String> contexts(String kind) {
        Map<String, String> headers = Map.of("content-type", Fixture.TURTLE);
        String query = "kind=" + kind + "&target=surface" + (kind.equals("publish") ? "&unit=" + UNIT : "");
        ApiResponse r = f.send("POST", BASE + "/jobs", query, headers, CONFIG.getBytes(StandardCharsets.UTF_8));
        assertEquals(202, r.status());
        String job = Graphs.job(r.headers().get("Location").substring("/api/jobs/".length()));
        Model m = f.store.graph(job);
        return m.listObjectsOfProperty(m.createResource(job), Cst.contextGraph).toList().stream()
            .map(o -> o.asResource().getURI()).collect(Collectors.toSet());
    }

    @Test
    void dependenciesOnALineageAndOnAVersionAreStoredAndReturned() {
        published(D1);
        ApiResponse r = depend(null, UNIT, version(D1));
        assertEquals(200, r.status());
        assertEquals(Set.of(UNIT, version(D1)), dependencies(r));
        assertEquals(Set.of(UNIT, version(D1)), dependencies(f.get(BASE)));
        assertEquals(200, dependBody(null, Fixture.PREFIXES).status(), "an empty body clears them");
        assertTrue(dependencies(f.get(BASE)).isEmpty());
    }

    @Test
    void anIriTheRegistryDoesNotHoldIs422() {
        published(D1);
        assertEquals(422, depend(null, "https://example.org/never").status());
        assertEquals(422, depend(null, version(D2)).status());
        assertTrue(dependencies(f.get(BASE)).isEmpty());
    }

    @Test
    void aBodyWithAnotherTripleOrABadIriIsRefused() {
        published(D1);
        assertEquals(400, dependBody(null, Fixture.PREFIXES + "<" + Graphs.workspace(WS) + "> cst:dependsOn <" + UNIT
            + "> ; cst:mode cst:Locked .").status());
        assertEquals(400, depend(null, "urn:lattice:studio:ws:x").status());
        assertEquals(400, dependBody(null, Fixture.PREFIXES + "<" + Graphs.workspace(WS) + "> cst:dependsOn \"" + UNIT + "\" .").status());
        assertTrue(dependencies(f.get(BASE)).isEmpty());
    }

    @Test
    void aReaderOfAReadOnlyWorkspaceMayNotSetThem() {
        published(D1);
        assertEquals(200, f.send("POST", BASE + "/access", "mode=read-only", Map.of(), new byte[0]).status());
        assertEquals(403, depend("reviewer", UNIT).status());
        assertEquals(200, depend(null, UNIT).status());
    }

    @Test
    void jobsNameTheCurrentVersionOfAFollowedLineageAndThePinnedVersionOfAPinnedOne() {
        published(D1);
        assertEquals(200, depend(null, UNIT).status());
        String first = Graphs.version(UNIT, D1);
        String second = Graphs.version(UNIT, D2);
        for (String kind : List.of("validate", "publish")) {
            assertTrue(contexts(kind).contains(first), kind);
        }
        assertTrue(contexts("publish").contains(Graphs.config(WS, "mapping")), "a publish job reads the other parts too");
        assertFalse(contexts("publish").contains(Graphs.config(WS, "surface")), "but not its own, which is its input");
        published(D2);
        for (String kind : List.of("validate", "publish")) {
            Set<String> c = contexts(kind);
            assertTrue(c.contains(second), kind);
            assertFalse(c.contains(first), kind);
        }
        assertEquals(200, depend(null, version(D1)).status());
        Set<String> pinned = contexts("validate");
        assertTrue(pinned.contains(first));
        assertFalse(pinned.contains(second));
    }

    @Test
    void theWriterAcceptsAVersionGraphAsContextAndRefusesAMalformedOne() {
        String good = Graphs.version(UNIT, D1);
        Reply ok = submitWith(good);
        assertEquals(200, ok.status(), ok.message());
        assertEquals(400, submitWith(Graphs.lineage(UNIT)).status(), "a lineage graph is not a version graph");
        assertEquals(400, submitWith(good + "0").status());
        assertEquals(400, submitWith(Graphs.PUBLICATION_PREFIX + "ABC:rev:" + D1).status());
        assertEquals(400, submitWith(Graphs.workspace(Fixture.id(2)) + ":surface").status());
    }

    private Reply submitWith(String contextGraph) {
        String id = java.util.UUID.randomUUID().toString();
        String iri = Graphs.job(id);
        String input = Graphs.jobInput(id);
        Model job = ModelFactory.createDefaultModel();
        Resource node = job.createResource(iri);
        node.addProperty(RDF.type, Cst.Job);
        node.addProperty(Cst.workspace, job.createResource(Graphs.workspace(WS)));
        node.addProperty(Cst.configGraph, job.createResource(input));
        node.addProperty(Cst.baselineGraph, job.createResource(Graphs.baseline(WS, 1)));
        node.addProperty(Cst.status, Cst.Queued);
        node.addProperty(Cst.contextGraph, job.createResource(contextGraph));
        Dataset d = DatasetFactory.create();
        d.addNamedModel(iri, job);
        d.addNamedModel(input, content(D1));
        return f.writes.send(Command.submitJob(WS, id, d));
    }
}
