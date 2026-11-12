// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.ResourceFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.RDFS;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.model.Workspace;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.StudioOperations.Family;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Reply;

/**
 * A closure of imports held by one command, and what an import declares, as the finished fence job says it (ADR-A149 decisions 6 and 13,
 * PRI-75). The jobs are written into the store as the worker leaves them, so that nothing here depends on the worker.
 */
class ImportsClosureTest {
    private static final String WS = Fixture.id(1);
    private static final String OTHER = Fixture.id(2);
    private static final String ONTOLOGY = "https://example.org/onto/a";
    private static final String VERSION = "https://example.org/onto/a/1.0";

    @TempDir Path dir;
    Fixture f;
    private int jobs;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir));
        assertEquals(201, f.createWorkspace("One").status());
        assertEquals(201, f.createWorkspace("Two").status());
    }

    private static String digest(int n) {
        return String.format("%064x", n);
    }

    private static String root(int n) {
        return Graphs.importGraph(digest(n));
    }

    private static Model content(int n) {
        return Fixture.model(Fixture.PREFIXES + "ex:imported" + n + " ex:p ex:o .");
    }

    /** A job as the worker leaves it, digesting import {@code n} of {@code ws}. */
    private String job(String ws, int n, Resource status, String ontology, String version) {
        return job(ws, n, Cst.Fence, status, ontology, version);
    }

    private String job(String ws, int n, Resource kind, Resource status, String ontology, String version) {
        String id = Fixture.id(1000 + (++jobs));
        String iri = Graphs.job(id);
        Model m = ModelFactory.createDefaultModel();
        Resource node = m.createResource(iri);
        node.addProperty(RDF.type, Cst.Job);
        node.addProperty(Cst.workspace, m.createResource(Graphs.workspace(ws)));
        node.addProperty(Cst.kind, kind);
        node.addProperty(Cst.status, status);
        node.addProperty(Cst.digest, digest(n));
        java.io.StringWriter nt = new java.io.StringWriter();
        RDFDataMgr.write(nt, content(n), Lang.NTRIPLES);
        node.addProperty(Cst.artefact, m.createResource(iri + "#artefact-1").addProperty(Cst.path, "import.nt")
            .addProperty(Cst.mediaType, "application/n-triples").addProperty(Cst.content, nt.toString()));
        if (ontology != null) {
            node.addProperty(Cst.declaresOntology, m.createResource(ontology));
        }
        if (version != null) {
            node.addProperty(Cst.declaresVersion, m.createResource(version));
        }
        f.store.write(List.of(), Map.of(iri, m));
        return id;
    }

    private String done(String ws, int n) {
        return job(ws, n, Cst.Succeeded, null, null);
    }

    private ApiResponse hold(String ws, String query) {
        return f.send("POST", "/api/workspaces/" + ws + "/imports", query, Map.of(), new byte[0]);
    }

    private static String query(List<String> jobIds, List<String> labels) {
        List<String> parts = new ArrayList<>();
        jobIds.forEach(j -> parts.add("job=" + j));
        labels.forEach(l -> parts.add("label=" + l));
        return String.join("&", parts);
    }

    private Workspace stored(String ws) {
        return Workspace.from(ws, f.store.graph(Graphs.description(ws)));
    }

    private long steps(String ws) {
        return Fixture.OPS.seq(f.store, Family.DESCRIPTION, Graphs.workspace(ws)).orElse(0L);
    }

    private long fenceReceipts(String ws) {
        return f.store.graph(Graphs.receipts(ws)).listSubjectsWithProperty(Cst.command, "fence").toList().size();
    }

    private boolean nothingWritten(String ws, long stepsBefore, long receiptsBefore, int... digests) {
        boolean clean = steps(ws) == stepsBefore && fenceReceipts(ws) == receiptsBefore && stored(ws).imports().isEmpty();
        for (int n : digests) {
            clean &= f.store.graph(Graphs.importedGraph(digest(n))).isEmpty();
        }
        return clean;
    }

    @Test
    void severalJobsAreHeldByOneCommandWhichReplacesTheDescriptionOnce() {
        String a = done(WS, 1);
        String b = done(WS, 2);
        String c = done(WS, 3);
        long before = steps(WS);
        long receipts = fenceReceipts(WS);
        ApiResponse r = hold(WS, query(List.of(a, b, c), List.of("Alpha", "Beta", "Gamma")));
        assertEquals(201, r.status());
        assertEquals(before + 1, steps(WS), "the description moved by one step");
        assertEquals(receipts + 1, fenceReceipts(WS), "and one command left one receipt");
        Workspace ws = stored(WS);
        assertEquals(Map.of(root(1), "Alpha", root(2), "Beta", root(3), "Gamma"), ws.imports());
        for (int n = 1; n <= 3; n++) {
            assertTrue(content(n).isIsomorphicWith(f.store.graph(Graphs.importedGraph(digest(n)))), "import " + n + " is stored");
        }
        Model reply = Fixture.model(r);
        for (int n = 1; n <= 3; n++) {
            assertTrue(reply.contains(reply.createResource(Graphs.workspace(WS)), Cst.holdsImport, reply.createResource(root(n))));
        }
        assertEquals("/api/workspaces/" + WS + "/imports/" + digest(1), r.headers().get("Location"));
        Model receipt = f.store.graph(Graphs.receipts(WS));
        Resource fence = receipt.listSubjectsWithProperty(Cst.command, "fence").next();
        assertEquals(4, fence.listProperties(Cst.wrote).toList().size(), "the three imports and the description, in one receipt");
    }

    @Test
    void twoJobsOfOneDigestHoldItOnceUnderTheFirstLabel() {
        String a = done(WS, 1);
        String b = done(WS, 1);
        long before = steps(WS);
        assertEquals(201, hold(WS, query(List.of(a, b), List.of("First", "Second"))).status());
        assertEquals(Map.of(root(1), "First"), stored(WS).imports());
        assertEquals(before + 1, steps(WS));
        assertEquals(java.util.Optional.of(1L), Fixture.OPS.seq(f.store, Family.IMPORT, root(1)), "the import is created once");
    }

    @Test
    void aSingleJobIsHeldAsBefore() {
        String a = done(WS, 1);
        long before = steps(WS);
        assertEquals(201, hold(WS, "job=" + a).status(), "a label is optional for one job");
        assertEquals(Map.of(root(1), "Import"), stored(WS).imports());
        assertEquals(before + 1, steps(WS));
        String b = done(WS, 2);
        assertEquals(201, hold(WS, "job=" + b + "&label=Named").status());
        assertEquals(Map.of(root(1), "Import", root(2), "Named"), stored(WS).imports());
    }

    @Test
    void aFailedForeignUnfinishedOrUnknownJobAmongThemRefusesTheWholeRequestAndWritesNothing() {
        String good = done(WS, 1);
        long before = steps(WS);
        long receipts = fenceReceipts(WS);
        List<String> labels = List.of("Good", "Bad");
        assertEquals(409, hold(WS, query(List.of(good, job(WS, 2, Cst.Failed, null, null)), labels)).status(), "failed");
        assertEquals(409, hold(WS, query(List.of(good, job(WS, 3, Cst.Queued, null, null)), labels)).status(), "unfinished");
        assertEquals(409, hold(WS, query(List.of(good, job(WS, 4, Cst.Validate, Cst.Succeeded, null, null)), labels)).status(), "not a fence job");
        assertEquals(404, hold(WS, query(List.of(good, job(OTHER, 5, Cst.Succeeded, null, null)), labels)).status(), "another workspace's");
        assertEquals(404, hold(WS, query(List.of(good, Fixture.id(99999)), labels)).status(), "no such job");
        assertEquals(404, hold(WS, query(List.of(good, "not-an-id"), labels)).status(), "not a job id");
        assertTrue(nothingWritten(WS, before, receipts, 1, 2, 3, 4, 5), "the good job was not held either");
    }

    @Test
    void thePairingOfJobsAndLabelsIsExact() {
        String a = done(WS, 1);
        String b = done(WS, 2);
        long before = steps(WS);
        long receipts = fenceReceipts(WS);
        assertEquals(400, hold(WS, query(List.of(a, b), List.of("One"))).status(), "fewer labels than jobs");
        assertEquals(400, hold(WS, query(List.of(a), List.of("One", "Two"))).status(), "more labels than jobs");
        assertEquals(400, hold(WS, query(List.of(a, b), List.of())).status(), "several jobs need a label each");
        assertEquals(400, hold(WS, query(List.of(a, b), List.of("One", ""))).status(), "an empty label");
        assertEquals(400, hold(WS, query(List.of(a), List.of("x".repeat(201)))).status(), "a long label");
        assertEquals(404, hold(WS, "label=One").status(), "no job");
        assertTrue(nothingWritten(WS, before, receipts, 1, 2));
        assertEquals(201, hold(WS, "label=Second&job=" + b + "&label=Third&job=" + a).status(),
            "labels pair with jobs by their order among their own kind, wherever they stand in the query");
        assertEquals(Map.of(root(2), "Second", root(1), "Third"), stored(WS).imports());
    }

    @Test
    void atMostSixtyFourJobsAreHeldInOneRequest() {
        List<String> ids = new ArrayList<>();
        List<String> labels = new ArrayList<>();
        for (int n = 1; n <= 65; n++) {
            ids.add(Fixture.id(5000 + n));
            labels.add("L" + n);
        }
        long before = steps(WS);
        long receipts = fenceReceipts(WS);
        assertEquals(400, hold(WS, query(ids, labels)).status(), "65, whether or not the jobs exist");
        assertTrue(nothingWritten(WS, before, receipts));
        ids.clear();
        labels.clear();
        for (int n = 1; n <= 64; n++) {
            ids.add(done(WS, n));
            labels.add("L" + n);
        }
        assertEquals(201, hold(WS, query(ids, labels)).status());
        assertEquals(64, stored(WS).imports().size());
        assertEquals(before + 1, steps(WS));
    }

    @Test
    void whatADocumentDeclaresIsReadBackFromTheDescriptionTheWorkspaceAndTheSummaries() throws IOException {
        String a = job(WS, 1, Cst.Succeeded, ONTOLOGY, VERSION);
        String b = job(WS, 2, Cst.Succeeded, "https://example.org/onto/b", null);
        String c = done(WS, 3);
        assertEquals(201, hold(WS, query(List.of(a, b, c), List.of("A", "B", "C"))).status());
        Map<String, Workspace.Declared> declared = stored(WS).declared();
        assertEquals(Map.of(root(1), new Workspace.Declared(ONTOLOGY, VERSION), root(2), new Workspace.Declared("https://example.org/onto/b", null)), declared);
        Model description = f.store.graph(Graphs.description(WS));
        Resource one = description.createResource(root(1));
        assertTrue(description.contains(one, Cst.declaresOntology, description.createResource(ONTOLOGY)));
        assertTrue(description.contains(one, Cst.declaresVersion, description.createResource(VERSION)));
        assertTrue(description.contains(one, RDFS.label, "A"), "beside its label");
        assertFalse(description.contains(description.createResource(root(3)), Cst.declaresOntology, (org.apache.jena.rdf.model.RDFNode) null));
        // the workspace's own description
        Model got = Fixture.model(f.get("/api/workspaces/" + WS));
        assertTrue(got.contains(got.createResource(root(1)), Cst.declaresOntology, got.createResource(ONTOLOGY)));
        assertTrue(got.contains(got.createResource(root(1)), Cst.declaresVersion, got.createResource(VERSION)));
        assertFalse(got.contains(got.createResource(root(2)), Cst.declaresVersion, (org.apache.jena.rdf.model.RDFNode) null));
        // the summaries, by the contract's query as it stands
        Path query = Path.of(System.getProperty("studio.assets")).resolve("../../contracts/config-studio/workspace-summaries.rq").normalize();
        Files.copy(query, dir.resolve("promotions").resolve("workspace-summaries.rq"), java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        Model summaries = Fixture.model(f.get("/api/workspaces"));
        assertTrue(summaries.contains(summaries.createResource(root(1)), Cst.declaresOntology, summaries.createResource(ONTOLOGY)));
        assertTrue(summaries.contains(summaries.createResource(root(1)), Cst.declaresVersion, summaries.createResource(VERSION)));
        assertTrue(summaries.contains(summaries.createResource(root(1)), RDFS.label, "A"));
        assertTrue(summaries.contains(summaries.createResource(root(2)), Cst.declaresOntology, summaries.createResource("https://example.org/onto/b")));
        assertFalse(summaries.contains(summaries.createResource(root(3)), Cst.declaresOntology, (org.apache.jena.rdf.model.RDFNode) null));
    }

    @Test
    void aVersionIriWithoutItsOntologyIriAndAnOntologyIriThatIsNotAnIriAreNotRecorded() {
        String a = job(WS, 1, Cst.Succeeded, null, VERSION);
        assertEquals(201, hold(WS, "job=" + a).status());
        assertTrue(stored(WS).declared().isEmpty());
        // a job that gives two ontology IRIs, which a fence job does not, is read as giving none
        String b = job(WS, 2, Cst.Succeeded, ONTOLOGY, null);
        Model m = ModelFactory.createDefaultModel().add(f.store.graph(Graphs.job(b)));
        m.add(m.createResource(Graphs.job(b)), Cst.declaresOntology, m.createResource("https://example.org/onto/two"));
        f.store.write(List.of(), Map.of(Graphs.job(b), m));
        assertEquals(201, hold(WS, "job=" + b).status());
        assertTrue(stored(WS).declared().isEmpty());
    }

    @Test
    void theIrisComeFromTheJobsGraphAndNothingInTheRequestCanSayOtherwise() {
        String a = job(WS, 1, Cst.Succeeded, ONTOLOGY, VERSION);
        String b = done(WS, 2);
        String forged = "&ontology=https%3A%2F%2Fexample.org%2Fforged&version=https%3A%2F%2Fexample.org%2Fforged%2F1";
        assertEquals(201, hold(WS, query(List.of(a, b), List.of("A", "B")) + forged).status());
        assertEquals(Map.of(root(1), new Workspace.Declared(ONTOLOGY, VERSION)), stored(WS).declared(), "the job's, and none for the job that gave none");
        // the writer takes no claim in a command either
        String c = done(WS, 3);
        Command base = Command.fence(WS, List.of(new Command.Fenced(digest(3), "C", c, content(3))));
        Dataset body = DatasetFactory.create();
        body.getDefaultModel().add(base.body().getDefaultModel());
        base.body().listNames().forEachRemaining(n -> body.addNamedModel(n, base.body().getNamedModel(n)));
        body.getDefaultModel().add(ResourceFactory.createResource(root(3)), Cst.declaresOntology, ResourceFactory.createResource("https://example.org/forged"));
        Reply refused = f.writes.send(new Command(base.id(), base.sender(), base.type(), WS, null, null, null, null, null, null, body, null, false));
        assertEquals(400, refused.status(), refused.message());
        assertFalse(stored(WS).imports().containsKey(root(3)));
    }

    @Test
    void theWriterChecksEachJobItselfWhateverTheServiceChecked() {
        String own = done(WS, 1);
        long before = steps(WS);
        long receipts = fenceReceipts(WS);
        Command.Fenced good = new Command.Fenced(digest(1), "Good", own, content(1));
        assertEquals(400, f.writes.send(Command.fence(WS, List.of(good, new Command.Fenced(digest(2), "Failed", job(WS, 2, Cst.Failed, null, null), content(2))))).status());
        assertEquals(400, f.writes.send(Command.fence(WS, List.of(good, new Command.Fenced(digest(3), "Foreign", job(OTHER, 3, Cst.Succeeded, null, null), content(3))))).status());
        assertEquals(400, f.writes.send(Command.fence(WS, List.of(good, new Command.Fenced(digest(4), "Other digest", job(WS, 5, Cst.Succeeded, null, null), content(4))))).status(),
            "a job that digested another import");
        assertEquals(400, f.writes.send(Command.fence(WS, List.of(good, new Command.Fenced(digest(6), "Missing", Fixture.id(77777), content(6))))).status(), "no such job");
        assertEquals(400, f.writes.send(Command.fence(WS, List.of())).status(), "nothing to hold");
        List<Command.Fenced> many = new ArrayList<>();
        for (int n = 0; n <= Command.MAX_FENCED; n++) {
            many.add(new Command.Fenced(digest(100 + n), "L", own, content(100 + n)));
        }
        assertEquals(400, f.writes.send(Command.fence(WS, many)).status(), "more than the limit");
        assertEquals(400, f.writes.send(Command.fence(WS, List.of(new Command.Fenced(digest(1), "x".repeat(201), own, content(1))))).status(), "a long label");
        assertEquals(400, f.writes.send(Command.fence(WS, List.of(new Command.Fenced(digest(1), "Empty", own, ModelFactory.createDefaultModel())))).status(), "an empty graph");
        assertTrue(nothingWritten(WS, before, receipts, 1, 2, 3, 4, 6));
    }

    @Test
    void aFenceCommandSurvivesTheWireAsTheWriterReadsIt() {
        String a = job(WS, 1, Cst.Succeeded, ONTOLOGY, null);
        String b = done(WS, 2);
        Command sent = Command.fence(WS, List.of(new Command.Fenced(digest(1), "A", a, content(1)), new Command.Fenced(digest(2), "B", b, content(2))));
        Command read = org.nebularis.lattice.studio.writes.Codec.decode(org.nebularis.lattice.studio.writes.Codec.headers(sent),
            org.nebularis.lattice.studio.writes.Codec.body(sent));
        assertEquals(Reply.ok(), f.writes.send(read));
        assertEquals(Map.of(root(1), "A", root(2), "B"), stored(WS).imports());
        assertEquals(Map.of(root(1), new Workspace.Declared(ONTOLOGY, null)), stored(WS).declared());
    }

    @Test
    void aWorkspaceThatIsReadOnlyForAPrincipalRefusesTheWholeCommand() {
        String a = done(WS, 1);
        assertEquals(200, f.send("POST", "/api/workspaces/" + WS + "/access", "mode=read-only", Map.of(), new byte[0]).status());
        long before = steps(WS);
        Reply reply = f.writes.send(Command.fence(WS, List.of(new Command.Fenced(digest(1), "A", a, content(1)))).by("reviewer", false));
        assertEquals(403, reply.status());
        assertEquals(before, steps(WS));
        assertTrue(f.store.graph(Graphs.importedGraph(digest(1))).isEmpty());
        assertEquals(Set.of(), stored(WS).imports().keySet());
    }

    @Test
    void aHeldImportReleasedAndHeldAgainKeepsWhatItsJobDeclares() {
        String a = job(WS, 1, Cst.Succeeded, ONTOLOGY, VERSION);
        assertEquals(201, hold(WS, "job=" + a).status());
        assertEquals(204, f.send("DELETE", "/api/workspaces/" + WS + "/imports/" + digest(1), null, Map.of(), new byte[0]).status());
        assertTrue(stored(WS).declared().isEmpty(), "released, so nothing of it stays in the description");
        assertEquals(201, hold(WS, "job=" + a).status());
        assertEquals(Map.of(root(1), new Workspace.Declared(ONTOLOGY, VERSION)), stored(WS).declared());
    }

    @Test
    void anExportCarriesTheHeldImportsAndTheirLabelsAndWhatTheyDeclareAndAnImportRestoresThemWithoutTheirContent() {
        String a = job(WS, 1, Cst.Succeeded, ONTOLOGY, VERSION);
        assertEquals(201, hold(WS, query(List.of(a), List.of("Reference"))).status());
        ApiResponse export = f.get("/api/workspaces/" + WS + "/export");
        assertEquals(200, export.status());
        Dataset trig = DatasetFactory.create();
        RDFDataMgr.read(trig, new java.io.ByteArrayInputStream(export.body()), Lang.TRIG);
        Model description = trig.getNamedModel(Graphs.workspace(WS));
        assertTrue(description.contains(description.createResource(Graphs.workspace(WS)), Cst.holdsImport, description.createResource(root(1))));
        assertTrue(description.contains(description.createResource(root(1)), RDFS.label, "Reference"));
        assertTrue(description.contains(description.createResource(root(1)), Cst.declaresOntology, description.createResource(ONTOLOGY)));
        assertFalse(trig.containsNamedModel(Graphs.importedGraph(digest(1))), "the content of an import is not exported (TD-135)");
        ApiResponse imported = f.send("POST", "/api/workspaces", null, Map.of("content-type", "application/trig"), export.body());
        assertEquals(201, imported.status());
        String id = imported.headers().get("Location").substring("/api/workspaces/".length());
        Workspace again = stored(id);
        assertEquals(Map.of(root(1), "Reference"), again.imports(), "held by name, with its label");
        assertEquals(Map.of(root(1), new Workspace.Declared(ONTOLOGY, VERSION)), again.declared());
    }
}
