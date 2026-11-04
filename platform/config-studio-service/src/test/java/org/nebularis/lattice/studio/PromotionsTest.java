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
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.RDFNode;
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
import org.nebularis.lattice.studio.store.Promotions;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Reply;

/** The studio's promoted partitions (ADR-A149 decision 14, PM2): kept by the write that changes their source, and rebuilt only by a rebuild job. */
class PromotionsTest {
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
        f = new Fixture(Fixture.assetsDir(dir.resolve("assets")));
    }

    private ApiResponse as(String principal, String method, String path, String query, String body) {
        Map<String, String> headers = new HashMap<>(Map.of("content-type", Fixture.TURTLE));
        if (principal != null) {
            headers.put("x-lattice-principal", principal);
        }
        return f.send(method, path, query, headers, body == null ? new byte[0] : body.getBytes(StandardCharsets.UTF_8));
    }

    // --- 1. each partition equals a rebuild from the store, by the real worker -------------------------------------

    /** The partitions and record the Python worker computes over a dump of the store, as Jena datasets by graph. */
    private Dataset workerRebuild() throws Exception {
        Path in = dir.resolve("store.nq");
        Path out = dir.resolve("promoted.nq");
        Files.deleteIfExists(out);
        try (OutputStream os = Files.newOutputStream(in)) {
            RDFDataMgr.write(os, f.store.snapshot(), Lang.NQUADS);
        }
        Process p = new ProcessBuilder("python", "-m", "lattice_workers.config_studio_rebuild", in.toString(), out.toString())
            .redirectErrorStream(true).start();
        String log = new String(p.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        assertEquals(0, p.waitFor(), "the worker's rebuild failed, run through mise so python has the workers installed: " + log);
        Dataset fresh = DatasetFactory.create();
        RDFDataMgr.read(fresh, out.toUri().toString(), Lang.NQUADS);
        return fresh;
    }

    private static String summariesQuery() throws IOException {
        return Files.readString(Path.of(System.getProperty("studio.assets"), "promotions", "workspace-summaries.rq"));
    }

    private static Model nonEmpty(Dataset d, String name) {
        return d.containsNamedModel(name) ? d.getNamedModel(name) : ModelFactory.createDefaultModel();
    }

    private void everyPartitionEqualsARebuild(String after) throws Exception {
        Dataset fresh = workerRebuild();
        java.util.TreeSet<String> names = new java.util.TreeSet<>(f.store.graphNames().stream().filter(g -> g.startsWith(Graphs.PROMOTED_PREFIX)).toList());
        fresh.listNames().forEachRemaining(g -> {
            if (g.startsWith(Graphs.PROMOTED_PREFIX) && !fresh.getNamedModel(g).isEmpty()) {
                names.add(g);
            }
        });
        for (String graph : names) {
            Model stored = f.store.graph(graph);
            Model rebuilt = nonEmpty(fresh, graph);
            assertTrue(stored.isIsomorphicWith(rebuilt), "after " + after + ", the partition " + graph + " differs from the worker's rebuild.\nstored:\n"
                + stored.write(new java.io.StringWriter(), "N-TRIPLES") + "\nrebuilt:\n" + rebuilt.write(new java.io.StringWriter(), "N-TRIPLES"));
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
    void everyPromotedPartitionTheWritesKeepEqualsWhatTheWorkerRebuildsFromTheStore() throws Exception {
        assertEquals(201, f.createWorkspace("Plan").status());
        everyPartitionEqualsARebuild("create");
        assertEquals(201, as("reviewer", "POST", "/api/workspaces", null, Fixture.PREFIXES + "ex:a ex:p ex:b .").status());
        assertEquals(204, f.put(BASE + "/graphs/surface", "\"0\"", CONFIG).status());
        everyPartitionEqualsARebuild("save");
        assertEquals(200, as(null, "POST", BASE + "/access", "mode=read-only", null).status());
        everyPartitionEqualsARebuild("set-access");

        String published = finishedJob(WS, "kind=publish&target=surface&unit=" + UNIT, CONFIG, concepts(), "version.nt",
            Map.of("lineage", UNIT, "version", VERSION, "unitKind", "https://example.org/Kind", "digest", DIGEST.repeat(4)));
        assertEquals(201, as(null, "POST", BASE + "/publications", "job=" + published, null).status());
        everyPartitionEqualsARebuild("publish");

        assertEquals(200, as(null, "PUT", BASE + "/dependencies", null, Fixture.PREFIXES
            + "<urn:lattice:studio:ws:" + WS + "> cst:dependsOn <" + UNIT + "> , <" + VERSION + "> .").status());
        everyPartitionEqualsARebuild("set-dependencies");

        String job = as(null, "POST", BASE + "/jobs", "kind=validate&target=surface", CONFIG).headers().get("Location").substring("/api/jobs/".length());
        everyPartitionEqualsARebuild("submit-job");
        assertTrue(f.store.jobsOf(Graphs.workspace(WS)).contains(f.store.jobsOf(Graphs.workspace(WS)).createResource(Graphs.job(job)), Cst.workspace));

        String fence = finishedJob(WS, "kind=fence&target=import", Fixture.PREFIXES + "ex:imported ex:p ex:o .",
            Fixture.model(Fixture.PREFIXES + "ex:imported ex:p ex:o ."), "import.nt", Map.of("digest", IMPORT_DIGEST));
        assertEquals(201, as(null, "POST", BASE + "/imports", "job=" + fence + "&label=Held", null).status());
        everyPartitionEqualsARebuild("fence");
        assertEquals(204, as(null, "DELETE", BASE + "/imports/" + IMPORT_DIGEST, null, null).status());
        everyPartitionEqualsARebuild("release");

        assertEquals(204, as(null, "DELETE", "/api/jobs/" + job, null, null).status());
        everyPartitionEqualsARebuild("delete-job");
        assertEquals(204, as("reviewer", "DELETE", "/api/workspaces/" + Fixture.id(2), null, null).status());
        everyPartitionEqualsARebuild("delete-workspace");
        assertEquals(204, as(null, "DELETE", BASE, null, null).status());
        everyPartitionEqualsARebuild("delete-workspace of the last");
        assertTrue(f.store.summaries(summariesQuery()).isEmpty() && f.store.jobsOf(Graphs.workspace(WS)).isEmpty());
        assertEquals(List.of(), f.store.graphNames().stream().filter(g -> g.startsWith(Graphs.JOB_PREFIX)).toList(), "no job graph is left behind");
    }

    // --- 3. the listing reads the summaries query once -----------------------------------------------------------------------------

    @Test
    void theWorkspaceListingIsOneReadOfTheSummariesQueryAndShowsAWorkspaceJustCreated() {
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

    // --- 4. who may write a promoted partition ------------------------------------------------------------------------------

    private String submitRebuild() {
        String job = UUID.randomUUID().toString();
        Model m = ModelFactory.createDefaultModel();
        m.createResource(Graphs.job(job)).addProperty(RDF.type, Cst.Job).addProperty(Cst.kind, Cst.Rebuild).addProperty(Cst.status, Cst.Queued);
        Dataset d = DatasetFactory.create();
        d.addNamedModel(Graphs.job(job), m);
        assertEquals(200, f.writes.send(Command.submitRebuild(job, d)).status());
        return job;
    }

    private Reply rebuildUpdate(String job, Map<String, Model> carried) {
        Dataset d = DatasetFactory.create();
        Model m = ModelFactory.createDefaultModel();
        m.createResource(Graphs.job(job)).addProperty(RDF.type, Cst.Job).addProperty(Cst.kind, Cst.Rebuild).addProperty(Cst.status, Cst.Succeeded);
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
    void aStartRebuildsWhenThePromotionsGrewAndWarnsWithoutRebuildingWhenOneChanged() throws Exception {
        Map<String, String> staged = Promotions.digests(Files.readAllBytes(dir.resolve("assets").resolve("promotions").resolve("promotions.ttl")));
        f.api.startUp();
        long deadline = System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(30);
        while (Promotions.recorded(f.store.graph(Graphs.PROMOTED_RECORD)).isEmpty() && System.nanoTime() < deadline) {
            Thread.sleep(50);
        }
        assertEquals(staged, Promotions.recorded(f.store.graph(Graphs.PROMOTED_RECORD)), "a start with no record rebuilds and records every contract");

        int published = f.bus.published().size();
        f.api.startUp();
        assertEquals(published, f.bus.published().size(), "a start with nothing changed rebuilds nothing");

        Map<String, String> altered = new java.util.TreeMap<>(staged);
        String changed = altered.keySet().iterator().next();
        altered.put(changed, "0".repeat(64));
        f.store.write(List.of(), Map.of(Graphs.PROMOTED_RECORD, Promotions.record(altered)));
        f.api.startUp();
        assertEquals(published, f.bus.published().size(), "a changed contract is not rebuilt, since that would lose its old rows");
        String status = new String(f.send("GET", "/api/status", "", Map.of(), new byte[0]).body(), StandardCharsets.UTF_8);
        assertTrue(status.contains(changed), "the start's warning names the changed contract: " + status);
    }

    @Test
    void aRebuildUpdateReplacesThePartitionsAndTheRecordItNamesWholeAndNothingElse() {
        assertEquals(201, f.createWorkspace("One").status());
        String job = submitRebuild();
        String partition = Graphs.promoted(Graphs.lineage(UNIT));
        assertEquals(200, rebuildUpdate(job, Map.of(partition, one("urn:a", Promotions.NS + "current", "urn:b"))).status());
        assertTrue(f.store.graph(Graphs.job(job)).isEmpty() && f.store.graph(Graphs.jobReceipts(job)).isEmpty(),
            "a rebuild that succeeded is deleted with its receipts by the update that wrote its partitions");
        assertEquals(404, rebuildUpdate(job, Map.of(partition, one("urn:c", Promotions.NS + "current", "urn:d"))).status());
        job = submitRebuild();
        assertEquals(200, rebuildUpdate(job, Map.of(partition, one("urn:c", Promotions.NS + "current", "urn:d"))).status());
        Model now = f.store.graph(partition);
        assertEquals(1, now.size(), "the second update replaced the first whole");
        assertTrue(now.contains(now.createResource("urn:c"), null, (RDFNode) null));

        job = submitRebuild();
        Model record = ModelFactory.createDefaultModel();
        record.add(record.createResource("urn:contract"), Cst.contractDigest, "abc");
        assertEquals(200, rebuildUpdate(job, Map.of(Graphs.PROMOTED_RECORD, record)).status(), "a rebuild may carry the record");
        assertTrue(f.store.graph(Graphs.PROMOTED_RECORD).contains(record.createResource("urn:contract"), Cst.contractDigest, "abc"));

        job = submitRebuild();
        Reply foreign = rebuildUpdate(job, Map.of(Graphs.baseline(WS), one("urn:x", "urn:y", "urn:z")));
        assertEquals(400, foreign.status(), "a rebuild may carry the promoted partitions and the record and nothing else");
        assertEquals(400, rebuildUpdate(job, Map.of(Graphs.PROMOTED_PREFIX + "elsewhere", one("urn:x", "urn:y", "urn:z"))).status());
        Model blank = ModelFactory.createDefaultModel();
        blank.add(blank.createResource("urn:s"), blank.createProperty("urn:p"), blank.createResource());
        assertEquals(400, rebuildUpdate(job, Map.of(partition, blank)).status(), "a partition holds IRIs and literals only");
        assertEquals(1, f.store.graph(partition).size());
    }

    @Test
    void noOtherUpdateMayCarryAPromotedPartitionAndARebuildJobNamesNoWorkspace() {
        assertEquals(201, f.createWorkspace("One").status());
        String jobId = as(null, "POST", BASE + "/jobs", "kind=validate&target=surface", CONFIG).headers().get("Location").substring("/api/jobs/".length());
        Model m = ModelFactory.createDefaultModel().add(f.store.graph(Graphs.job(jobId)));
        Dataset d = DatasetFactory.create();
        d.addNamedModel(Graphs.job(jobId), m);
        String partition = Graphs.promoted(Graphs.lineage(UNIT));
        d.addNamedModel(partition, one("urn:a", Promotions.NS + "current", "urn:b"));
        assertEquals(400, f.writes.send(Command.jobUpdate(WS, jobId, d)).status(), "a workspace job's update carries no promoted partition");
        assertTrue(f.store.graph(partition).isEmpty());

        String rebuild = UUID.randomUUID().toString();
        Model named = ModelFactory.createDefaultModel();
        named.createResource(Graphs.job(rebuild)).addProperty(RDF.type, Cst.Job).addProperty(Cst.kind, Cst.Rebuild).addProperty(Cst.status, Cst.Queued)
            .addProperty(Cst.workspace, named.createResource(Graphs.workspace(WS)));
        Dataset submitted = DatasetFactory.create();
        submitted.addNamedModel(Graphs.job(rebuild), named);
        assertEquals(400, f.writes.send(Command.submitRebuild(rebuild, submitted)).status(), "a rebuild job names no workspace");
        assertEquals(400, f.writes.send(new Command(UUID.randomUUID().toString(), "service", Command.Type.SAVE, null, null, "surface", 0L, null,
            null, null, DatasetFactory.create(), null, false)).status(), "only a job's commands may name no workspace");
        // A workspace's command cannot reach a rebuild job, and a rebuild command cannot reach a workspace's job.
        String real = submitRebuild();
        Dataset update = DatasetFactory.create();
        update.addNamedModel(Graphs.job(real), ModelFactory.createDefaultModel());
        assertEquals(400, f.writes.send(Command.jobUpdate(WS, real, update)).status());
        assertEquals(400, f.writes.send(Command.jobUpdate(null, jobId, d)).status());
        assertEquals(200, f.writes.send(Command.deleteRebuild(real)).status(), "deleting a rebuild job leaves nothing, receipts included");
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
            many.createResource(UNIT + "/c" + i).addProperty(many.createProperty(Promotions.NS + "prefLabel"), "Peril " + i);
        }
        String job = submitRebuild();
        assertEquals(200, rebuildUpdate(job, Map.of(Graphs.promoted(Graphs.version(UNIT, DIGEST)), many)).status());
        assertEquals(50, get(null, "/api/registry/terms", "q=peril").listSubjects().toList().size());
    }

    @Test
    void aPublishIsOneCommitAndItsRegistryEntryIsReadableAtOnceWithNoJobRun() {
        assertEquals(201, f.createWorkspace("Open").status());
        int rebuilds = f.rebuildWorker.runs();
        publishScheme();
        Model registry = f.store.registry();
        assertTrue(registry.containsResource(registry.getResource(UNIT)) && registry.containsResource(registry.getResource(VERSION)),
            "the lineage and its current version are listed at once");
        Model api = get(null, "/api/registry", null);
        assertTrue(api.containsResource(api.getResource(UNIT)));
        assertEquals(rebuilds, f.rebuildWorker.runs(), "no rebuild ran");
    }

    @Test
    void theJavaDigestsOfThePromotionContractsEqualTheRecordThePythonWorkerWrites() throws Exception {
        Model record = workerRebuild().getNamedModel(Graphs.PROMOTED_RECORD);
        Map<String, String> staged = org.nebularis.lattice.studio.store.Promotions.digests(
            Files.readAllBytes(Path.of(System.getProperty("studio.assets"), "promotions", "promotions.ttl")));
        assertFalse(staged.isEmpty());
        assertEquals(staged, org.nebularis.lattice.studio.store.Promotions.recorded(record));
    }
}
