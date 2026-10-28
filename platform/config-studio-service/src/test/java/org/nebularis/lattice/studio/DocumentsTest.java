// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.vocabulary.RDF;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;

/** A workspace's documents over the HTTP API: markup in, Wording and markup out, guarded by revision (CS12d). */
class DocumentsTest {
    private static final String WS = Fixture.id(1);
    private static final String DOC = "00000002-0000-4000-8000-000000000000";
    private static final String DOCS = "/api/workspaces/" + WS + "/documents";
    private static final String WRD = "https://www.nebularis.org/neuro-semantic/lattice/wording#";

    @TempDir Path dir;
    Fixture f;
    String licence;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir));
        assertEquals(201, f.createWorkspace("Docs").status());
        licence = new String(f.get("/api/document-samples/software-licence").body(), StandardCharsets.UTF_8);
    }

    private ApiResponse put(String doc, String ifMatch, String body, String type) {
        Map<String, String> headers = new HashMap<>(Map.of("content-type", type));
        if (ifMatch != null) {
            headers.put("if-match", ifMatch);
        }
        return f.send("PUT", DOCS + "/" + doc, null, headers, body.getBytes(StandardCharsets.UTF_8));
    }

    private ApiResponse put(String ifMatch, String body) {
        return put(DOC, ifMatch, body, "application/xml");
    }

    @Test
    void templatesAndSamplesAreServed() {
        String templates = new String(f.get("/api/document-templates").body(), StandardCharsets.UTF_8);
        assertTrue(templates.contains("facility-agreement") && templates.contains("software-licence"));
        assertFalse(templates.contains("DocumentSample"));
        assertTrue(new String(f.get("/api/document-samples").body(), StandardCharsets.UTF_8).contains("DocumentSample"));
        ApiResponse sample = f.get("/api/document-samples/software-licence");
        assertEquals("application/xml; charset=utf-8", sample.headers().get("Content-Type"));
        assertEquals(404, f.get("/api/document-samples/property-policy").status());
        assertEquals(404, f.get("/api/document-samples/..%2Fsecret").status());
    }

    @Test
    void aNewDocumentIsSavedAndReadBackAsMarkupAndAsWording() {
        ApiResponse saved = put("\"0\"", licence);
        assertEquals(204, saved.status(), () -> new String(saved.body(), StandardCharsets.UTF_8));
        assertEquals("\"1\"", saved.headers().get("ETag"));

        ApiResponse markup = f.send("GET", DOCS + "/" + DOC, null, Map.of("accept", "application/xml"), new byte[0]);
        assertEquals(licence, new String(markup.body(), StandardCharsets.UTF_8), "the markup comes back exactly");
        assertEquals("\"1\"", markup.headers().get("ETag"));

        Model wording = f.store.graph(Graphs.document(WS, DOC));
        Resource w = wording.createResource(Graphs.documentNode(DOC) + "wording");
        assertTrue(wording.contains(w, RDF.type, wording.createResource(WRD + "Wording")));
        assertTrue(new String(f.get(DOCS + "/" + DOC).body(), StandardCharsets.UTF_8).contains("Wording"), "Turtle by default");

        String listed = new String(f.get(DOCS).body(), StandardCharsets.UTF_8);
        assertTrue(listed.contains("Software Licence (sample)") && listed.contains("software-licence"));
    }

    @Test
    void aStaleOrMissingIfMatchIsRefused() {
        assertEquals(204, put("\"0\"", licence).status());
        ApiResponse stale = put("\"0\"", licence);
        assertEquals(412, stale.status());
        assertEquals("\"1\"", stale.headers().get("ETag"));
        assertEquals(428, put(null, licence).status());
        assertEquals(204, put("\"1\"", licence).status());
        assertEquals(2, f.store.graph(Graphs.workspace(WS)).createResource(Graphs.document(WS, DOC)).getProperty(Cst.documentRevision).getLong());
    }

    @Test
    void whatTheServiceCannotTrustIsRefused() {
        assertEquals(415, put(DOC, "\"0\"", licence, "text/plain").status());
        assertEquals(400, put("\"0\"", "<document").status());
        assertEquals(400, put("\"0\"", "<?xml version=\"1.0\"?><!DOCTYPE d [<!ENTITY x SYSTEM \"file:///etc/passwd\">]>" + licence.substring(licence.indexOf("<document"))).status());
        assertEquals(422, put("\"0\"", licence.replace("<title>Software Licence (sample)</title>", "<title></title>")).status());
        assertEquals(422, put("\"0\"", licence.replace("<template>software-licence</template>", "<template>no-such-template</template>")).status());
        assertEquals(422, put("00000003-0000-4000-8000-000000000000", "\"0\"", licence, "application/xml").status(), "the root id is not the path's");
        assertTrue(f.store.graph(Graphs.document(WS, DOC)).isEmpty());
    }

    @Test
    void theWriterRefusesADocumentGraphHoldingOtherTerms() {
        Model graph = org.apache.jena.rdf.model.ModelFactory.createDefaultModel();
        Resource node = graph.createResource(Graphs.documentNode(DOC));
        node.addProperty(Cst.markup, "<document/>");
        node.addProperty(graph.createProperty("https://www.nebularis.org/neuro-semantic/lattice/persistence#label"), "x");
        var reply = f.writes.send(org.nebularis.lattice.studio.writes.Command.saveDocument(WS, DOC, 0, java.time.Instant.parse("2026-10-27T10:00:00Z"), "T", "software-licence", graph));
        assertEquals(400, reply.status());
        Model foreign = org.apache.jena.rdf.model.ModelFactory.createDefaultModel();
        foreign.createResource("https://example.org/elsewhere").addProperty(Cst.markup, "<document/>");
        assertEquals(400, f.writes.send(org.nebularis.lattice.studio.writes.Command.saveDocument(WS, DOC, 0, java.time.Instant.parse("2026-10-27T10:00:00Z"), "T", "software-licence", foreign)).status());
        assertTrue(f.store.graph(Graphs.document(WS, DOC)).isEmpty());
    }

    @Test
    void aDocumentIsDeletedWithItsGraphAndWithItsWorkspace() {
        assertEquals(204, put("\"0\"", licence).status());
        assertEquals(204, f.send("DELETE", DOCS + "/" + DOC, null, Map.of(), new byte[0]).status());
        assertTrue(f.store.graph(Graphs.document(WS, DOC)).isEmpty());
        assertEquals(404, f.get(DOCS + "/" + DOC).status());

        assertEquals(204, put("\"0\"", licence).status());
        assertEquals(204, f.send("DELETE", "/api/workspaces/" + WS, null, Map.of(), new byte[0]).status());
        assertTrue(f.store.graph(Graphs.document(WS, DOC)).isEmpty());
    }

    @Test
    void anExportCarriesItsDocumentsIntoTheImport() {
        assertEquals(204, put("\"0\"", licence).status());
        ApiResponse export = f.get("/api/workspaces/" + WS + "/export");
        ApiResponse imported = f.send("POST", "/api/workspaces", null, Map.of("content-type", "application/trig"), export.body());
        assertEquals(201, imported.status(), () -> new String(imported.body(), StandardCharsets.UTF_8));
        String copy = imported.headers().get("Location").substring("/api/workspaces/".length());
        ApiResponse markup = f.send("GET", "/api/workspaces/" + copy + "/documents/" + DOC, null, Map.of("accept", "application/xml"), new byte[0]);
        assertEquals(licence, new String(markup.body(), StandardCharsets.UTF_8));
    }

    @Test
    void anAnalysisReadsTheSavedDocument() {
        assertEquals(404, f.send("POST", "/api/workspaces/" + WS + "/jobs", "kind=analyse&target=" + DOC, Map.of(), new byte[0]).status());
        assertEquals(204, put("\"0\"", licence).status());
        ApiResponse job = f.send("POST", "/api/workspaces/" + WS + "/jobs", "kind=analyse&target=" + DOC, Map.of(), new byte[0]);
        assertEquals(202, job.status(), () -> new String(job.body(), StandardCharsets.UTF_8));
        String jobId = job.headers().get("Location").substring("/api/jobs/".length());
        Model description = f.store.graph(Graphs.job(jobId));
        Resource node = description.createResource(Graphs.job(jobId));
        assertTrue(description.contains(node, Cst.kind, Cst.Analyse));
        assertTrue(description.contains(node, Cst.target, description.createResource(Graphs.document(WS, DOC))));
        assertTrue(f.store.graph(Graphs.jobInput(jobId)).isIsomorphicWith(f.store.graph(Graphs.document(WS, DOC))));
        assertEquals(1, f.bus.published().size());
    }
}
