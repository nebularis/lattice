// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.store.Graphs;

/** CS10: RDF/XML beside Turtle, chosen by Accept for a response and by Content-Type for a body. */
class RdfXmlTest {
    private static final String WS = Fixture.id(1);
    private static final String SURFACE = "/api/workspaces/" + WS + "/graphs/surface";
    private static final String SRF = "https://www.nebularis.org/neuro-semantic/lattice/surface#";
    private static final String CONFIG = Fixture.PREFIXES + "ex:cfg <" + SRF + "label> \"one\" ; <" + SRF + "node> [ <" + SRF + "n> 1 ] .";
    private static final String XML = "application/rdf+xml";

    @TempDir Path dir;
    Fixture f;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir));
        f.createWorkspace("One");
        assertEquals(204, f.put(SURFACE, "\"0\"", CONFIG).status());
    }

    private ApiResponse get(String path, String accept) {
        return f.send("GET", path, accept == null ? Map.of() : Map.of("accept", accept), null);
    }

    private static Model xml(ApiResponse r) {
        Model m = ModelFactory.createDefaultModel();
        RDFDataMgr.read(m, new ByteArrayInputStream(r.body()), "urn:test:", Lang.RDFXML);
        return m;
    }

    private static boolean isXml(ApiResponse r) {
        return r.headers().get("Content-Type").startsWith(XML);
    }

    @Test
    void aGraphIsServedAsRdfXmlWhenAcceptPrefersIt() {
        ApiResponse r = get(SURFACE, XML);
        assertEquals(200, r.status());
        assertTrue(isXml(r), r.headers().toString());
        assertTrue(Fixture.model(CONFIG).isIsomorphicWith(xml(r)));
        assertEquals("\"1\"", r.headers().get("ETag"));
        assertEquals("Accept", r.headers().get("Vary"));
        assertEquals("Accept", get(SURFACE, null).headers().get("Vary"));
    }

    @Test
    void turtleStaysTheDefaultUnlessRdfXmlRanksHigher() {
        for (String accept : new String[] {null, "*/*", "text/turtle", "text/turtle, application/rdf+xml;q=0.5",
            "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "application/rdf+xml;q=0.4, */*;q=0.9"}) {
            assertFalse(isXml(get(SURFACE, accept)), String.valueOf(accept));
        }
        for (String accept : new String[] {"application/rdf+xml", "application/rdf+xml, text/turtle;q=0.9", "application/*",
            "application/rdf+xml;q=1, */*;q=0.1"}) {
            assertTrue(isXml(get(SURFACE, accept)), accept);
        }
    }

    @Test
    void everyTurtleRouteNegotiatesAndOtherResponsesAreLeftAlone() {
        for (String path : new String[] {"/api/workspaces", "/api/workspaces/" + WS, "/api/vocabulary", "/api/samples",
            "/api/samples/lending"}) {
            ApiResponse r = get(path, XML);
            assertEquals(200, r.status(), path);
            assertTrue(isXml(r), path);
            xml(r);
        }
        ApiResponse health = get("/api/health", XML);
        assertEquals("ok", new String(health.body(), StandardCharsets.UTF_8));
        assertEquals(404, get("/api/workspaces/" + Fixture.id(9), XML).status());
    }

    @Test
    void aGraphRdfXmlCannotWriteIs406() {
        assertEquals(204, f.put(SURFACE, "\"1\"", Fixture.PREFIXES + "ex:cfg <" + SRF + "label> 1 ; <https://example.org/2> 3 .").status());
        ApiResponse r = get(SURFACE, XML);
        assertEquals(406, r.status());
        assertEquals("Accept", r.headers().get("Vary"));
        assertEquals(200, get(SURFACE, "text/turtle").status());
    }

    @Test
    void aBodyInRdfXmlIsReadAsTheSameGraph() {
        byte[] body = get(SURFACE, XML).body();
        ApiResponse saved = f.send("PUT", SURFACE, null, Map.of("content-type", XML + "; charset=utf-8", "if-match", "\"1\""), body);
        assertEquals(204, saved.status());
        assertTrue(Fixture.model(CONFIG).isIsomorphicWith(f.store.graph(Graphs.config(WS, "surface"))));
        assertEquals(400, f.send("PUT", SURFACE, null, Map.of("content-type", XML, "if-match", "\"2\""),
            "<rdf:RDF".getBytes(StandardCharsets.UTF_8)).status());
        assertEquals(415, f.send("PUT", SURFACE, null, Map.of("content-type", "application/json", "if-match", "\"2\""),
            "{}".getBytes(StandardCharsets.UTF_8)).status());
    }

    @Test
    void anRdfXmlBodyNeverReadsAnExternalEntity() throws IOException {
        Path secret = Files.writeString(dir.resolve("secret.txt"), "TOP-SECRET");
        String body = "<?xml version=\"1.0\"?>\n<!DOCTYPE rdf:RDF [ <!ENTITY leak SYSTEM \"" + secret.toUri() + "\"> ]>\n"
            + "<rdf:RDF xmlns:rdf=\"http://www.w3.org/1999/02/22-rdf-syntax-ns#\" xmlns:srf=\"" + SRF + "\">\n"
            + "  <rdf:Description rdf:about=\"https://example.org/cfg\"><srf:label>&leak;</srf:label></rdf:Description>\n"
            + "</rdf:RDF>\n";
        ApiResponse r = f.send("PUT", SURFACE, null, Map.of("content-type", XML, "if-match", "\"1\""),
            body.getBytes(StandardCharsets.UTF_8));
        assertEquals(400, r.status());
        assertFalse(f.store.graph(Graphs.config(WS, "surface")).toString().contains("TOP-SECRET"));
    }
}
