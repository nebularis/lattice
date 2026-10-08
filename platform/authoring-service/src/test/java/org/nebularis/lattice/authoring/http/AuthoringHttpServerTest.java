// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.http;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.StringReader;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.List;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.authoring.ApiFixture;
import org.nebularis.lattice.authoring.TestEvents;
import org.nebularis.lattice.authoring.TestSamples;
import org.nebularis.lattice.authoring.json.Json;
import org.nebularis.lattice.authoring.rdf.CanonicalHash;

/** Exercises the real HTTP surface over an ephemeral port (L3). */
class AuthoringHttpServerTest {
    private ApiFixture fx;
    private AuthoringHttpServer server;
    private HttpClient client;
    private int port;

    @BeforeEach
    void start() {
        fx = new ApiFixture();
        server = new AuthoringHttpServer(fx.api);
        server.start(0);
        port = server.port();
        client = HttpClient.newHttpClient();
    }

    @AfterEach
    void stop() {
        server.stop();
    }

    /** S4-09: every route, called once with valid input, gives its table status and a schema-valid body. */
    @Test
    void everyRouteGivesItsTableStatusAndASchemaValidBody() throws Exception {
        JsonNode snapshot = TestSamples.rawNode(TestSamples.FACILITY_AGREEMENT);
        String documentId = snapshot.get("documentId").asText();

        HttpResponse<String> accepted = put("/api/documents/" + documentId + "/snapshot",
            fx.submission(null, snapshot).toString(), "application/json");
        assertEquals(200, accepted.statusCode());
        assertValid("snapshot-accepted", accepted.body());
        String jobId = Json.MAPPER.readTree(accepted.body()).get("job").get("jobId").asText();

        fx.bus.deliver(TestEvents.completedResult(fx, jobId, documentId, 1));

        assertRoute("GET", "/api/health", 200, "health");
        assertRoute("GET", "/api/templates", 200, "template-list");
        assertRoute("GET", "/api/templates/facility-agreement", 200, "authoring-template");
        assertRoute("GET", "/api/samples", 200, "sample-list");
        assertRoute("GET", "/api/samples/facility-agreement", 200, "document-snapshot");
        assertRoute("GET", "/api/documents/" + documentId, 200, "document-view");
        assertRoute("GET", "/api/jobs/" + jobId, 200, "job-view");
        assertRoute("GET", "/api/documents/" + documentId + "/revisions/1/analysis", 200, "analysis-view");

        HttpResponse<String> graph = get("/api/documents/" + documentId + "/revisions/1/graph/wording");
        assertEquals(200, graph.statusCode());
        assertTrue(contentType(graph).startsWith("text/turtle"));
    }

    /** S4-10: an oversized body and the wrong content type give 413 and 415, unknown routes 404 and 405. */
    @Test
    void rejectsOversizedBodiesWrongContentTypesAndUnknownRoutes() throws Exception {
        String path = "/api/documents/00000009-0000-4000-8000-000000000000/snapshot";
        byte[] oversized = new byte[1_048_577];

        HttpRequest tooLarge = HttpRequest.newBuilder(uri(path))
            .header("Content-Type", "application/json")
            .PUT(HttpRequest.BodyPublishers.ofByteArray(oversized))
            .build();
        assertEquals(413, client.send(tooLarge, HttpResponse.BodyHandlers.ofString()).statusCode());

        assertEquals(415, put(path, "{}", "text/plain").statusCode());
        assertEquals(404, get("/api/no-such-route").statusCode());

        HttpRequest wrongMethod = HttpRequest.newBuilder(uri("/api/templates"))
            .POST(HttpRequest.BodyPublishers.noBody())
            .build();
        assertEquals(405, client.send(wrongMethod, HttpResponse.BodyHandlers.ofString()).statusCode());
    }

    /** S4-11: every response carries the two security headers, and no CORS header. */
    @Test
    void setsSecurityHeadersOnEveryResponse() throws Exception {
        HttpResponse<String> response = get("/api/health");

        assertEquals("nosniff", response.headers().firstValue("X-Content-Type-Options").orElse(null));
        assertEquals("no-store", response.headers().firstValue("Cache-Control").orElse(null));
        assertTrue(response.headers().firstValue("Access-Control-Allow-Origin").isEmpty());
    }

    /** S4-12: the stored wording graph is served as isomorphic Turtle, an unknown kind gives 400. */
    @Test
    void servesTheWordingGraphAsTurtleAndRejectsAnUnknownKind() throws Exception {
        JsonNode snapshot = TestSamples.rawNode(TestSamples.SOFTWARE_LICENCE);
        String documentId = snapshot.get("documentId").asText();
        put("/api/documents/" + documentId + "/snapshot", fx.submission(null, snapshot).toString(), "application/json");

        HttpResponse<String> turtle = get("/api/documents/" + documentId + "/revisions/1/graph/wording");
        assertEquals(200, turtle.statusCode());
        Model parsed = ModelFactory.createDefaultModel();
        RDFDataMgr.read(parsed, new StringReader(turtle.body()), null, Lang.TURTLE);
        Model stored = fx.store.getGraph(fx.minter.wordingGraph(documentId, 1)).orElseThrow();
        assertEquals(CanonicalHash.sortedNTriplesLines(stored), CanonicalHash.sortedNTriplesLines(parsed));

        assertEquals(400, get("/api/documents/" + documentId + "/revisions/1/graph/other").statusCode());
    }

    private void assertRoute(String method, String path, int status, String schemaName) throws Exception {
        HttpResponse<String> response = "GET".equals(method) ? get(path) : null;
        assertEquals(status, response.statusCode());
        assertValid(schemaName, response.body());
    }

    private void assertValid(String schemaName, String body) throws Exception {
        JsonNode node = Json.MAPPER.readTree(body);
        assertEquals(List.of(), fx.schemas.validate(schemaName, node));
    }

    private HttpResponse<String> get(String path) throws Exception {
        HttpRequest request = HttpRequest.newBuilder(uri(path)).GET().build();
        return client.send(request, HttpResponse.BodyHandlers.ofString());
    }

    private HttpResponse<String> put(String path, String body, String contentType) throws Exception {
        HttpRequest request = HttpRequest.newBuilder(uri(path))
            .header("Content-Type", contentType)
            .PUT(HttpRequest.BodyPublishers.ofString(body))
            .build();
        return client.send(request, HttpResponse.BodyHandlers.ofString());
    }

    private URI uri(String path) {
        return URI.create("http://localhost:" + port + path);
    }

    private static String contentType(HttpResponse<String> response) {
        return response.headers().firstValue("Content-Type").orElse("");
    }
}
