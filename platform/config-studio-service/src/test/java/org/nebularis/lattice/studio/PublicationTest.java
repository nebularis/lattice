// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.io.StringReader;
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
import org.nebularis.lattice.studio.writes.Reply;
import org.nebularis.lattice.studio.writes.Writer;

/** Publishing a unit's version into the registry (ADR-A149 decisions 1 to 4). */
class PublicationTest {
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
        assertEquals(204, f.put(BASE + "/graphs/surface", "\"0\"", CONFIG).status(), "a job needs a saved part to read");
    }

    private ApiResponse submit(String principal, String unit) {
        Map<String, String> headers = new HashMap<>();
        if (principal != null) {
            headers.put("x-lattice-principal", principal);
        }
        return f.send("POST", BASE + "/jobs", "kind=publish&target=surface&unit=" + unit, headers, new byte[0]);
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

    /** A publish job as the worker leaves it when it succeeds, written with a job update. */
    private String finished(String digest) {
        ApiResponse r = submit(null, UNIT);
        assertEquals(202, r.status());
        String job = r.headers().get("Location").substring("/api/jobs/".length());
        String iri = Graphs.job(job);
        Model m = ModelFactory.createDefaultModel().add(f.store.graph(iri));
        Resource node = m.createResource(iri);
        m.removeAll(node, Cst.status, null);
        node.addProperty(Cst.status, Cst.Succeeded);
        node.addProperty(Cst.lineage, m.createResource(UNIT));
        node.addProperty(Cst.version, m.createResource(version(digest)));
        node.addProperty(Cst.digest, digest + digest + digest + digest);
        node.addProperty(Cst.unitKind, m.createResource("https://example.org/Kind"));
        // What the version pins, which the worker writes on the job too (ADR-A149 decision 5).
        node.addProperty(m.createProperty(Cst.NS + "pins"), m.createResource("https://example.org/other/rev/1-0000000000000000"));
        java.io.StringWriter nt = new java.io.StringWriter();
        RDFDataMgr.write(nt, content(digest), Lang.NTRIPLES);
        node.addProperty(Cst.artefact, m.createResource().addProperty(Cst.path, "version.nt")
            .addProperty(Cst.mediaType, "application/n-triples").addProperty(Cst.content, nt.toString()));
        Dataset d = DatasetFactory.create();
        d.addNamedModel(iri, m);
        assertEquals(200, f.writes.send(new Command(java.util.UUID.randomUUID().toString(), "worker", Command.Type.JOB_UPDATE, WS, job,
            null, null, null, null, null, d, null, false)).status());
        return job;
    }

    private ApiResponse publish(String job) {
        return f.send("POST", BASE + "/publications", "job=" + job, Map.of(), new byte[0]);
    }

    @Test
    void aPublishJobNamesItsUnitAndReadsTheSavedPart() {
        ApiResponse r = submit(null, UNIT);
        assertEquals(202, r.status());
        String job = r.headers().get("Location").substring("/api/jobs/".length());
        Model m = f.store.graph(Graphs.job(job));
        Resource node = m.createResource(Graphs.job(job));
        assertTrue(m.contains(node, Cst.kind, Cst.Publish));
        assertTrue(m.contains(node, Cst.unit, m.createResource(UNIT)));
        assertTrue(f.store.graph(Graphs.jobInput(job)).isIsomorphicWith(f.store.graph(Graphs.config(WS, "surface"))));
        assertFalse(f.store.graph(Graphs.jobInput(job)).isEmpty());
    }

    @Test
    void aReaderOfAReadOnlyWorkspaceMayNotSubmitOneAndABadUnitIsRefused() {
        assertEquals(200, f.send("POST", BASE + "/access", "mode=read-only", Map.of(), new byte[0]).status());
        assertEquals(403, submit("reviewer", UNIT).status());
        assertEquals(400, submit(null, "not-an-iri").status());
        assertEquals(400, submit(null, "ftp://example.org/x").status());
        assertEquals(400, submit(null, "urn:lattice:studio:ws:x").status());
        assertEquals(400, f.send("POST", BASE + "/jobs", "kind=publish&target=baseline&unit=" + UNIT, Map.of(), new byte[0]).status());
    }

    @Test
    void publishingAFinishedJobWritesTheLineageAndTheVersion() {
        ApiResponse r = publish(finished(D1));
        assertEquals(201, r.status());
        assertEquals("/api/registry/lineage?iri=" + java.net.URLEncoder.encode(UNIT, StandardCharsets.UTF_8), r.headers().get("Location"));
        Model lineage = f.store.graph(Graphs.lineage(UNIT));
        Resource unit = lineage.createResource(UNIT);
        Resource v = lineage.createResource(version(D1));
        assertTrue(lineage.contains(unit, org.apache.jena.vocabulary.RDF.type, Cst.Fnd.PersistentIdentity));
        assertTrue(lineage.contains(unit, Cst.Fnd.hasVersion, v));
        assertTrue(lineage.contains(unit, Cst.current, v));
        Resource event = lineage.createResource(UNIT + "/evt/e1/000001");
        assertTrue(lineage.contains(event, Cst.sequence, lineage.createTypedLiteral(1L)));
        assertTrue(lineage.contains(event, Cst.Prov.generated, v));
        assertTrue(lineage.contains(event, Cst.principal, "developer"));
        assertTrue(lineage.contains(event, Cst.fromWorkspace, lineage.createResource(Graphs.workspace(WS))));
        assertTrue(lineage.contains(event, org.apache.jena.vocabulary.RDF.type, Cst.Prov.Activity));
        assertFalse(lineage.contains(event, Cst.previousPublication));
        assertTrue(f.store.graph(Graphs.version(UNIT, D1)).isIsomorphicWith(content(D1)));
        assertTrue(Fixture.model(r).isIsomorphicWith(lineage), "the answer is the registry graph");
    }

    @Test
    void publishingTheSameVersionAgainWritesNoSecondEvent() {
        assertEquals(201, publish(finished(D1)).status());
        assertEquals(200, publish(finished(D1)).status());
        Model lineage = f.store.graph(Graphs.lineage(UNIT));
        assertEquals(1, lineage.listSubjectsWithProperty(Cst.sequence).toList().size());
    }

    @Test
    void aSecondVersionSupersedesTheFirst() {
        assertEquals(201, publish(finished(D1)).status());
        assertEquals(201, publish(finished(D2)).status());
        Model lineage = f.store.graph(Graphs.lineage(UNIT));
        Resource unit = lineage.createResource(UNIT);
        assertEquals(1, lineage.listObjectsOfProperty(unit, Cst.current).toList().size());
        assertTrue(lineage.contains(unit, Cst.current, lineage.createResource(version(D2))));
        assertTrue(lineage.contains(unit, Cst.Fnd.hasVersion, lineage.createResource(version(D1))));
        assertTrue(lineage.contains(lineage.createResource(version(D1)), Cst.Fnd.supersededBy, lineage.createResource(version(D2))));
        Resource second = lineage.createResource(UNIT + "/evt/e1/000002");
        assertTrue(lineage.contains(second, Cst.sequence, lineage.createTypedLiteral(2L)));
        assertTrue(lineage.contains(second, Cst.previousPublication, lineage.createResource(UNIT + "/evt/e1/000001")));
        assertFalse(f.store.graph(Graphs.version(UNIT, D1)).isEmpty(), "the first version stays");
    }

    @Test
    void theWriterRefusesWhatIsNotAVersionOfItsLineage() {
        Writer w = new Writer(f.store, Fixture.OPS, Clock.fixed(Instant.parse("2026-10-27T10:00:00Z"), ZoneOffset.UTC));
        Model ok = content(D1);
        assertEquals(200, new Writer(f.store, Fixture.OPS, Clock.systemUTC()).apply(Command.publish(WS, UNIT, version(D1), ok)).status());
        assertEquals(400, w.apply(Command.publish(WS, UNIT, "https://example.org/other/rev/1-" + D1, ok)).status());
        assertEquals(400, w.apply(Command.publish(WS, UNIT, UNIT + "/rev/1-ABCDEF0123456789", ok)).status());
        Model noIdentity = ModelFactory.createDefaultModel();
        noIdentity.createResource(version(D2)).addProperty(noIdentity.createProperty("https://example.org/p"), "x");
        assertEquals(400, w.apply(Command.publish(WS, UNIT, version(D2), noIdentity)).status());
        String studio = "urn:lattice:studio:unit";
        Model mine = ModelFactory.createDefaultModel();
        mine.createResource(studio + "/rev/1-" + D2).addProperty(Cst.Fnd.hasIdentity, mine.createResource(studio));
        Reply r = w.apply(Command.publish(WS, studio, studio + "/rev/1-" + D2, mine));
        assertEquals(400, r.status());
        assertTrue(f.store.graph(Graphs.lineage(studio)).isEmpty());
    }

    @Test
    void anUnfinishedJobIs409AndAnotherWorkspacesJobIs404() {
        ApiResponse r = submit(null, UNIT);
        String queued = r.headers().get("Location").substring("/api/jobs/".length());
        assertEquals(409, publish(queued).status());
        String done = finished(D1);
        assertEquals(201, f.createWorkspace("Other").status());
        assertEquals(404, f.send("POST", "/api/workspaces/" + Fixture.id(2) + "/publications", "job=" + done, Map.of(), new byte[0]).status());
        assertTrue(f.store.graph(Graphs.lineage(UNIT)).isEmpty());
    }

    @Test
    void theRegistryIsReadByAnyPrincipalByLineageAndVersion() {
        assertEquals(201, publish(finished(D1)).status());
        assertEquals(201, publish(finished(D2)).status());
        Map<String, String> reviewer = Map.of("x-lattice-principal", "reviewer");
        ApiResponse list = f.send("GET", "/api/registry", null, reviewer, new byte[0]);
        assertEquals(200, list.status());
        assertTrue(Fixture.model(list).contains(null, Cst.current, Fixture.model(list).createResource(version(D2))));
        String enc = java.net.URLEncoder.encode(UNIT, java.nio.charset.StandardCharsets.UTF_8);
        ApiResponse lineage = f.send("GET", "/api/registry/lineage", "iri=" + enc, reviewer, new byte[0]);
        assertEquals(200, lineage.status());
        assertTrue(Fixture.model(lineage).contains(null, Cst.Fnd.supersededBy, Fixture.model(lineage).createResource(version(D2))));
        ApiResponse first = f.send("GET", "/api/registry/version", "iri=" + java.net.URLEncoder.encode(version(D1), java.nio.charset.StandardCharsets.UTF_8), reviewer, new byte[0]);
        assertEquals(200, first.status());
        assertTrue(Fixture.model(first).isIsomorphicWith(content(D1)), "a superseded version reads as it was published");
        assertEquals(404, f.send("GET", "/api/registry/lineage", "iri=https%3A%2F%2Fexample.org%2Fnever", reviewer, new byte[0]).status());
        assertEquals(404, f.send("GET", "/api/registry/version", "iri=" + enc + "%2Frev%2F1-" + "1111111111111111", reviewer, new byte[0]).status());
    }
}
