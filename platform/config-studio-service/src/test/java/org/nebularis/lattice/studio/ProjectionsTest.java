// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.OffsetDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.vocabulary.RDF;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.Projections;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Reply;

/** The studio's projections (ADR-A149 decision 14): rebuilt after each command, read in one read, and written only by a refresh job. */
class ProjectionsTest {
    private static final String WS = Fixture.id(1);
    private static final String BASE = "/api/workspaces/" + WS;
    private static final String UNIT = "https://example.org/unit/scheme";
    private static final String DIGEST = "0123456789abcdef";
    private static final String VERSION = UNIT + "/rev/1-" + DIGEST;
    private static final String IMPORT_DIGEST = "fedcba9876543210".repeat(4);
    private static final String SKOS = "http://www.w3.org/2004/02/skos/core#";
    private static final String CONFIG = Fixture.PREFIXES + "ex:cfg <https://www.nebularis.org/neuro-semantic/lattice/surface#label> \"one\" .";

    @TempDir Path dir;
    Fixture f;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir));
    }

    private ApiResponse as(String principal, String method, String path, String query, String body) {
        Map<String, String> headers = new HashMap<>(Map.of("content-type", Fixture.TURTLE));
        if (principal != null) {
            headers.put("x-lattice-principal", principal);
        }
        return f.send(method, path, query, headers, body == null ? new byte[0] : body.getBytes(StandardCharsets.UTF_8));
    }

    // --- 1. each projection equals a rebuild from the store, by the real worker ------------------------------------

    /** The projections the Python worker computes over a dump of the store, as Jena datasets by graph. */
    private Dataset workerRebuild() throws Exception {
        Path in = dir.resolve("store.nq");
        Path out = dir.resolve("projections.nq");
        Files.deleteIfExists(out);
        try (OutputStream os = Files.newOutputStream(in)) {
            RDFDataMgr.write(os, f.store.snapshot(), Lang.NQUADS);
        }
        Process p = new ProcessBuilder("python", "-m", "lattice_workers.config_studio_refresh", in.toString(), out.toString())
            .redirectErrorStream(true).start();
        String log = new String(p.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        assertEquals(0, p.waitFor(), "the worker's rebuild failed, run through mise so python has the workers installed: " + log);
        Dataset fresh = DatasetFactory.create();
        RDFDataMgr.read(fresh, out.toUri().toString(), Lang.NQUADS);
        return fresh;
    }

    /** What a projection says, without its refresh node and with each time as the instant it names, which rdflib writes another way. */
    private static Model said(Model projection, String graph) {
        Model out = ModelFactory.createDefaultModel();
        for (Statement st : projection.listStatements().toList()) {
            if (st.getSubject().getURI() != null && st.getSubject().getURI().equals(graph)) {
                continue;
            }
            RDFNode o = st.getObject();
            if (o.isLiteral() && XSDDatatype.XSDdateTime.getURI().equals(o.asLiteral().getDatatypeURI())) {
                o = out.createTypedLiteral(OffsetDateTime.parse(o.asLiteral().getLexicalForm()).toInstant().toString(), XSDDatatype.XSDdateTime);
            }
            out.add(st.getSubject(), st.getPredicate(), o);
        }
        return out;
    }

    private void everyProjectionEqualsARebuild(String after) throws Exception {
        Dataset fresh = workerRebuild();
        for (String key : Graphs.PROJECTIONS) {
            String graph = Graphs.projection(key);
            Model stored = said(f.store.graph(graph), graph);
            Model rebuilt = said(fresh.getNamedModel(graph), graph);
            assertTrue(stored.isIsomorphicWith(rebuilt), "after " + after + ", the " + key + " projection differs from the worker's rebuild.\nstored:\n"
                + stored.write(new java.io.StringWriter(), "N-TRIPLES") + "\nrebuilt:\n" + rebuilt.write(new java.io.StringWriter(), "N-TRIPLES"));
            assertTrue(f.store.graph(graph).contains(f.store.graph(graph).createResource(graph), RDF.type,
                f.store.graph(graph).createResource(Projections.NS + "Refresh")), key + " names the refresh that wrote it");
        }
    }

    private Model concepts() {
        Model m = ModelFactory.createDefaultModel();
        Resource v = m.createResource(VERSION);
        v.addProperty(Cst.Fnd.hasIdentity, m.createResource(UNIT));
        m.createResource(UNIT + "/fire").addProperty(RDF.type, m.createResource(SKOS + "Concept"))
            .addProperty(m.createProperty(SKOS + "prefLabel"), "Fire peril").addProperty(m.createProperty(SKOS + "inScheme"), v);
        m.createResource(UNIT + "/flood").addProperty(RDF.type, m.createResource(SKOS + "Concept"))
            .addProperty(m.createProperty(SKOS + "prefLabel"), "Flood").addProperty(m.createProperty(SKOS + "inScheme"), v);
        return m;
    }

    /** A job the worker has finished, with the artefact it leaves, as the other tests write it. */
    private String finishedJob(String ws, String query, String body, Model artefactContent, String path, Map<String, String> more) {
        ApiResponse r = as(null, "POST", "/api/workspaces/" + ws + "/jobs", query, body);
        assertEquals(202, r.status());
        String job = r.headers().get("Location").substring("/api/jobs/".length());
        String iri = Graphs.job(job);
        Model m = ModelFactory.createDefaultModel().add(f.store.graph(iri));
        Resource node = m.createResource(iri);
        m.removeAll(node, Cst.status, null);
        node.addProperty(Cst.status, Cst.Succeeded);
        more.forEach((p, o) -> {
            if (o.startsWith("http") || o.startsWith("urn")) {
                node.addProperty(m.createProperty(Cst.NS + p), m.createResource(o));
            } else {
                node.addProperty(m.createProperty(Cst.NS + p), o);
            }
        });
        java.io.StringWriter nt = new java.io.StringWriter();
        RDFDataMgr.write(nt, artefactContent, Lang.NTRIPLES);
        node.addProperty(Cst.artefact, m.createResource().addProperty(Cst.path, path)
            .addProperty(Cst.mediaType, "application/n-triples").addProperty(Cst.content, nt.toString()));
        Dataset d = DatasetFactory.create();
        d.addNamedModel(iri, m);
        assertEquals(200, f.writes.send(new Command(UUID.randomUUID().toString(), "worker", Command.Type.JOB_UPDATE, ws, job,
            null, null, null, null, null, d, null, false)).status());
        return job;
    }

    @Test
    void afterEachCommandEveryProjectionEqualsWhatTheWorkerRebuildsFromTheStore() throws Exception {
        assertEquals(201, f.createWorkspace("Plan").status());
        everyProjectionEqualsARebuild("create");
        assertEquals(201, as("reviewer", "POST", "/api/workspaces", null, Fixture.PREFIXES + "ex:a ex:p ex:b .").status());
        assertEquals(204, f.put(BASE + "/graphs/surface", "\"0\"", CONFIG).status());
        everyProjectionEqualsARebuild("save");
        assertEquals(200, as(null, "POST", BASE + "/access", "mode=read-only", null).status());
        everyProjectionEqualsARebuild("set-access");

        String published = finishedJob(WS, "kind=publish&target=surface&unit=" + UNIT, CONFIG, concepts(), "version.nt",
            Map.of("lineage", UNIT, "version", VERSION, "unitKind", "https://example.org/Kind", "digest", DIGEST.repeat(4)));
        assertEquals(201, as(null, "POST", BASE + "/publications", "job=" + published, null).status());
        everyProjectionEqualsARebuild("publish");

        assertEquals(200, as(null, "PUT", BASE + "/dependencies", null, Fixture.PREFIXES
            + "<urn:lattice:studio:ws:" + WS + "> cst:dependsOn <" + UNIT + "> , <" + VERSION + "> .").status());
        everyProjectionEqualsARebuild("set-dependencies");

        String job = as(null, "POST", BASE + "/jobs", "kind=validate&target=surface", CONFIG).headers().get("Location").substring("/api/jobs/".length());
        everyProjectionEqualsARebuild("submit-job");
        assertTrue(f.store.jobsOf(Graphs.workspace(WS)).contains(f.store.jobsOf(Graphs.workspace(WS)).createResource(Graphs.job(job)), Cst.workspace));

        String fence = finishedJob(WS, "kind=fence&target=import", Fixture.PREFIXES + "ex:imported ex:p ex:o .",
            Fixture.model(Fixture.PREFIXES + "ex:imported ex:p ex:o ."), "import.nt", Map.of("digest", IMPORT_DIGEST));
        assertEquals(201, as(null, "POST", BASE + "/imports", "job=" + fence + "&label=Held", null).status());
        everyProjectionEqualsARebuild("fence");
        assertEquals(204, as(null, "DELETE", BASE + "/imports/" + IMPORT_DIGEST, null, null).status());
        everyProjectionEqualsARebuild("release");

        assertEquals(204, as(null, "DELETE", "/api/jobs/" + job, null, null).status());
        everyProjectionEqualsARebuild("delete-job");
        assertEquals(204, as("reviewer", "DELETE", "/api/workspaces/" + Fixture.id(2), null, null).status());
        everyProjectionEqualsARebuild("delete-workspace");
        assertEquals(204, as(null, "DELETE", BASE, null, null).status());
        everyProjectionEqualsARebuild("delete-workspace of the last");
        assertTrue(f.store.summaries().isEmpty() && f.store.jobsOf(Graphs.workspace(WS)).isEmpty());
        assertEquals(List.of(), f.store.graphNames().stream().filter(g -> g.startsWith(Graphs.JOB_PREFIX)).toList(), "no refresh job is left behind");
    }

    // --- 3. the listing reads one graph -----------------------------------------------------------------------------

    @Test
    void theWorkspaceListingIsOneReadOfTheSummariesAndShowsAWorkspaceJustCreated() {
        assertEquals(201, f.createWorkspace("One").status());
        assertEquals(201, f.createWorkspace("Two").status());
        assertEquals(204, f.put(BASE + "/graphs/surface", "\"0\"", CONFIG).status());
        int before = Fixture.QUERIES.get();
        Model list = Fixture.model(f.get("/api/workspaces"));
        assertEquals(1, Fixture.QUERIES.get() - before, "one query for the listing, whatever the number of workspaces");
        Resource one = list.getResource(Graphs.workspace(WS));
        assertTrue(list.contains(one, RDF.type, Cst.Workspace));
        assertEquals("One", one.getProperty(org.apache.jena.vocabulary.RDFS.label).getString());
        assertEquals(1, one.getProperty(Cst.baselineRevision).getLong());
        assertEquals(1, one.getProperty(Cst.revision("surface")).getLong());
        assertTrue(list.contains(list.getResource(Graphs.workspace(Fixture.id(2))), RDF.type, Cst.Workspace));
    }

    // --- 4. who may write a projection ------------------------------------------------------------------------------

    private String submitRefresh() {
        String job = UUID.randomUUID().toString();
        Model m = ModelFactory.createDefaultModel();
        m.createResource(Graphs.job(job)).addProperty(RDF.type, Cst.Job).addProperty(Cst.kind, Cst.Refresh).addProperty(Cst.status, Cst.Queued);
        Dataset d = DatasetFactory.create();
        d.addNamedModel(Graphs.job(job), m);
        assertEquals(200, f.writes.send(Command.submitRefresh(job, d)).status());
        return job;
    }

    private Reply refreshUpdate(String job, Map<String, Model> carried) {
        Dataset d = DatasetFactory.create();
        Model m = ModelFactory.createDefaultModel();
        m.createResource(Graphs.job(job)).addProperty(RDF.type, Cst.Job).addProperty(Cst.kind, Cst.Refresh).addProperty(Cst.status, Cst.Succeeded);
        d.addNamedModel(Graphs.job(job), m);
        carried.forEach(d::addNamedModel);
        return f.writes.send(Command.jobUpdate(null, job, d));
    }

    private static Model one(String s, String p, String o) {
        Model m = ModelFactory.createDefaultModel();
        m.add(m.createResource(s), m.createProperty(p), m.createResource(o));
        return m;
    }

    @Test
    void aRefreshUpdateReplacesTheProjectionsItNamesWholeAndNothingElse() {
        assertEquals(201, f.createWorkspace("One").status());
        String job = submitRefresh();
        String registry = Graphs.projection("registry");
        assertEquals(200, refreshUpdate(job, Map.of(registry, one("urn:a", Projections.NS + "current", "urn:b"))).status());
        assertEquals(200, refreshUpdate(job, Map.of(registry, one("urn:c", Projections.NS + "current", "urn:d"))).status());
        Model now = f.store.graph(registry);
        assertEquals(1, now.size(), "the second update replaced the first whole");
        assertTrue(now.contains(now.createResource("urn:c"), null, (RDFNode) null));

        Reply foreign = refreshUpdate(job, Map.of(Graphs.baseline(WS), one("urn:x", "urn:y", "urn:z")));
        assertEquals(400, foreign.status(), "a refresh may carry the projections and nothing else");
        assertEquals(400, refreshUpdate(job, Map.of(Graphs.PROJECTION_PREFIX + "elsewhere", one("urn:x", "urn:y", "urn:z"))).status());
        Model blank = ModelFactory.createDefaultModel();
        blank.add(blank.createResource("urn:s"), blank.createProperty("urn:p"), blank.createResource());
        assertEquals(400, refreshUpdate(job, Map.of(registry, blank)).status(), "a projection holds IRIs and literals only");
        assertEquals(1, f.store.graph(registry).size());
    }

    @Test
    void noOtherUpdateMayCarryAProjectionAndARefreshJobNamesNoWorkspace() {
        assertEquals(201, f.createWorkspace("One").status());
        String jobId = as(null, "POST", BASE + "/jobs", "kind=validate&target=surface", CONFIG).headers().get("Location").substring("/api/jobs/".length());
        Model m = ModelFactory.createDefaultModel().add(f.store.graph(Graphs.job(jobId)));
        Dataset d = DatasetFactory.create();
        d.addNamedModel(Graphs.job(jobId), m);
        d.addNamedModel(Graphs.projection("registry"), one("urn:a", Projections.NS + "current", "urn:b"));
        assertEquals(400, f.writes.send(Command.jobUpdate(WS, jobId, d)).status(), "a workspace job's update carries no projection");
        assertTrue(f.store.graph(Graphs.projection("registry")).isEmpty() || f.store.graph(Graphs.projection("registry")).size() == 3);

        String refresh = UUID.randomUUID().toString();
        Model named = ModelFactory.createDefaultModel();
        named.createResource(Graphs.job(refresh)).addProperty(RDF.type, Cst.Job).addProperty(Cst.kind, Cst.Refresh).addProperty(Cst.status, Cst.Queued)
            .addProperty(Cst.workspace, named.createResource(Graphs.workspace(WS)));
        Dataset submitted = DatasetFactory.create();
        submitted.addNamedModel(Graphs.job(refresh), named);
        assertEquals(400, f.writes.send(Command.submitRefresh(refresh, submitted)).status(), "a refresh job names no workspace");
        assertEquals(400, f.writes.send(new Command(UUID.randomUUID().toString(), "service", Command.Type.SAVE, null, null, "surface", 0L, null,
            null, null, DatasetFactory.create(), null, false)).status(), "only a job's commands may name no workspace");
        // A workspace's command cannot reach a refresh job, and a refresh command cannot reach a workspace's job.
        String real = submitRefresh();
        Dataset update = DatasetFactory.create();
        update.addNamedModel(Graphs.job(real), ModelFactory.createDefaultModel());
        assertEquals(400, f.writes.send(Command.jobUpdate(WS, real, update)).status());
        assertEquals(400, f.writes.send(Command.jobUpdate(null, jobId, d)).status());
        assertEquals(200, f.writes.send(Command.deleteRefresh(real)).status(), "deleting a refresh job leaves nothing, receipts included");
        assertTrue(f.store.graphNames().stream().noneMatch(g -> g.contains(real)));
    }

    // --- 5. holders and terms ----------------------------------------------------------------------------------------

    private void publishScheme() {
        assertEquals(204, f.put(BASE + "/graphs/surface", "\"0\"", CONFIG).status());
        String job = finishedJob(WS, "kind=publish&target=surface&unit=" + UNIT, CONFIG, concepts(), "version.nt",
            Map.of("lineage", UNIT, "version", VERSION, "unitKind", "https://example.org/Kind", "digest", DIGEST.repeat(4)));
        assertEquals(201, as(null, "POST", BASE + "/publications", "job=" + job, null).status());
    }

    private static String enc(String s) {
        return java.net.URLEncoder.encode(s, StandardCharsets.UTF_8);
    }

    private Model get(String principal, String path, String query) {
        ApiResponse r = as(principal, "GET", path, query, null);
        assertEquals(200, r.status(), path + "?" + query);
        return Fixture.model(r);
    }

    @Test
    void theHoldersOfALineageAVersionAndAnImportAreTheWorkspacesThatReadThemAndALockedOneIsHidden() {
        assertEquals(201, f.createWorkspace("Open").status());
        assertEquals(201, f.createWorkspace("Pinning").status());
        publishScheme();
        String other = "/api/workspaces/" + Fixture.id(2);
        assertEquals(200, as(null, "PUT", BASE + "/dependencies", null, Fixture.PREFIXES + "<urn:lattice:studio:ws:" + WS + "> cst:dependsOn <" + UNIT + "> .").status());
        assertEquals(200, as(null, "PUT", other + "/dependencies", null, Fixture.PREFIXES + "<urn:lattice:studio:ws:" + Fixture.id(2) + "> cst:dependsOn <" + VERSION + "> .").status());
        assertEquals(200, as(null, "POST", other + "/access", "mode=locked", null).status());

        Resource open = ModelFactory.createDefaultModel().createResource(Graphs.workspace(WS));
        Resource locked = open.getModel().createResource(Graphs.workspace(Fixture.id(2)));
        Model asAdmin = get(null, "/api/registry/holders", "iri=" + enc(UNIT));
        assertTrue(asAdmin.contains(open, Cst.dependsOn, asAdmin.createResource(UNIT)), "followed by the open workspace");
        assertTrue(asAdmin.contains(locked, Cst.dependsOn, asAdmin.createResource(VERSION)), "an administrator also sees the one that pins a version of it");
        Model asReviewer = get("reviewer", "/api/registry/holders", "iri=" + enc(UNIT));
        assertTrue(asReviewer.contains(open, RDF.type, Cst.Workspace));
        assertFalse(asReviewer.containsResource(locked), "a locked workspace is hidden from a principal who may not read it");
        Model pinned = get(null, "/api/registry/holders", "iri=" + enc(VERSION));
        assertTrue(pinned.containsResource(locked) && !pinned.containsResource(open));
        assertEquals(400, as(null, "GET", "/api/registry/holders", "iri=not-an-iri", null).status());
        assertEquals(400, as(null, "GET", "/api/registry/holders", null, null).status());
        assertTrue(get(null, "/api/registry/holders", "iri=" + enc("https://example.org/never")).isEmpty());

        String digest = IMPORT_DIGEST;
        String fence = finishedJob(WS, "kind=fence&target=import", Fixture.PREFIXES + "ex:imported ex:p ex:o .", Fixture.model(Fixture.PREFIXES + "ex:imported ex:p ex:o ."), "import.nt", Map.of("digest", digest));
        assertEquals(201, as(null, "POST", BASE + "/imports", "job=" + fence + "&label=Held", null).status());
        Model held = get("reviewer", "/api/registry/holders", "iri=" + enc(Graphs.importGraph(digest)));
        assertTrue(held.contains(open, Cst.holdsImport, held.createResource(Graphs.importGraph(digest))));
    }

    @Test
    void theTermsRouteFindsConceptsByLabelInAnyCaseWithTheirVersionAndAtMostFifty() {
        assertEquals(201, f.createWorkspace("Open").status());
        publishScheme();
        Property label = ModelFactory.createDefaultModel().createProperty(SKOS + "prefLabel");
        Model found = get("reviewer", "/api/registry/terms", "q=FIRE");
        Resource fire = found.getResource(UNIT + "/fire");
        assertEquals("Fire peril", fire.getProperty(label).getString());
        assertEquals(VERSION, fire.getProperty(found.createProperty(SKOS + "inScheme")).getResource().getURI());
        assertFalse(found.containsResource(found.getResource(UNIT + "/flood")));
        assertTrue(get(null, "/api/registry/terms", "q=fl").containsResource(found.getResource(UNIT + "/flood")));
        assertTrue(get(null, "/api/registry/terms", "q=zebra").isEmpty());
        assertEquals(400, as(null, "GET", "/api/registry/terms", null, null).status());
        assertEquals(400, as(null, "GET", "/api/registry/terms", "q=%20", null).status());

        Model many = ModelFactory.createDefaultModel();
        for (int i = 0; i < 80; i++) {
            many.createResource(UNIT + "/c" + i).addProperty(many.createProperty(Projections.NS + "prefLabel"), "Peril " + i);
        }
        String job = submitRefresh();
        assertEquals(200, refreshUpdate(job, Map.of(Graphs.projection("terms"), many)).status());
        assertEquals(50, get(null, "/api/registry/terms", "q=peril").listSubjects().toList().size());
    }
}
