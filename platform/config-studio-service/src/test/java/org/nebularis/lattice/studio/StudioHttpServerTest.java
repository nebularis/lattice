// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.net.Socket;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.StudioApi;
import org.nebularis.lattice.studio.http.StudioHttpServer;

class StudioHttpServerTest {
    @TempDir Path dir;
    Fixture f;
    StudioHttpServer server;
    HttpClient client = HttpClient.newHttpClient();
    String base;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir.resolve("assets")));
        Path site = Files.createDirectories(dir.resolve("site"));
        Files.writeString(site.resolve("index.html"), "<html>spa</html>");
        Files.writeString(site.resolve("app.js"), "console.log(1)");
        Files.writeString(dir.resolve("secret.txt"), "TOP-SECRET");
        StudioApi api = new StudioApi(f.store, Fixture.OPS, f.writes, f.bus, Clock.systemUTC(), UUID::randomUUID, f.assets);
        server = new StudioHttpServer(api, "127.0.0.1", 0, site);
        server.start();
        base = "http://127.0.0.1:" + server.port();
    }

    @AfterEach
    void tearDown() {
        server.close();
    }

    private HttpResponse<String> get(String path) throws Exception {
        return client.send(HttpRequest.newBuilder(URI.create(base + path)).build(), HttpResponse.BodyHandlers.ofString());
    }

    @Test
    void healthAnswersOkWithSecurityHeaders() throws Exception {
        HttpResponse<String> r = get("/api/health");
        assertEquals(200, r.statusCode());
        assertEquals("ok", r.body());
        assertEquals("nosniff", r.headers().firstValue("X-Content-Type-Options").orElseThrow());
        assertEquals("no-store", r.headers().firstValue("Cache-Control").orElseThrow());
        assertEquals("no-referrer", r.headers().firstValue("Referrer-Policy").orElseThrow());
    }

    @Test
    void aTurtleRoundTripThroughHttp() throws Exception {
        HttpResponse<String> created = client.send(HttpRequest.newBuilder(URI.create(base + "/api/workspaces"))
            .header("Content-Type", "text/turtle").header("Slug", "Over%20http")
            .POST(HttpRequest.BodyPublishers.ofString("@prefix ex: <https://example.org/> . ex:a ex:p ex:b ."))
            .build(), HttpResponse.BodyHandlers.ofString());
        assertEquals(201, created.statusCode());
        assertTrue(created.headers().firstValue("Content-Type").orElseThrow().startsWith("text/turtle"));
        String location = created.headers().firstValue("Location").orElseThrow();
        HttpResponse<String> fetched = get(location);
        assertEquals(200, fetched.statusCode());
        assertTrue(fetched.body().contains("Over http"));
        HttpResponse<String> baseline = get(location + "/graphs/baseline");
        assertEquals("\"1\"", baseline.headers().firstValue("ETag").orElseThrow());
        HttpResponse<String> saved = client.send(HttpRequest.newBuilder(URI.create(base + location + "/graphs/surface"))
            .header("Content-Type", "text/turtle").header("If-Match", "\"0\"")
            .PUT(HttpRequest.BodyPublishers.ofString("<https://example.org/a> <https://www.nebularis.org/neuro-semantic/lattice/surface#p> 1 .")).build(), HttpResponse.BodyHandlers.ofString());
        assertEquals(204, saved.statusCode());
        assertEquals("\"1\"", saved.headers().firstValue("ETag").orElseThrow());
    }

    @Test
    void noResponseAllowsAnotherOriginAndAPreflightIsRefused() throws Exception {
        assertTrue(get("/api/health").headers().firstValue("Access-Control-Allow-Origin").isEmpty());
        assertTrue(get("/").headers().firstValue("Access-Control-Allow-Origin").isEmpty());
        HttpResponse<String> preflight = client.send(HttpRequest.newBuilder(URI.create(base + "/api/workspaces"))
            .header("Origin", "https://evil.example").header("Access-Control-Request-Method", "PUT")
            .method("OPTIONS", HttpRequest.BodyPublishers.noBody()).build(), HttpResponse.BodyHandlers.ofString());
        assertEquals(405, preflight.statusCode());
        assertTrue(preflight.headers().firstValue("Access-Control-Allow-Origin").isEmpty());
    }

    @Test
    void staticFilesAreServedWithTypesAndTheSpaFallsBackToIndex() throws Exception {
        HttpResponse<String> index = get("/");
        assertEquals("<html>spa</html>", index.body());
        assertTrue(index.headers().firstValue("Content-Type").orElseThrow().startsWith("text/html"));
        assertTrue(index.headers().firstValue("Content-Security-Policy").orElseThrow().contains("frame-ancestors 'none'"));
        assertEquals("nosniff", index.headers().firstValue("X-Content-Type-Options").orElseThrow());
        HttpResponse<String> js = get("/app.js");
        assertEquals("console.log(1)", js.body());
        assertTrue(js.headers().firstValue("Content-Type").orElseThrow().startsWith("text/javascript"));
        assertTrue(js.headers().firstValue("Content-Security-Policy").isEmpty());
        assertEquals("<html>spa</html>", get("/workspaces/abc/surface").body());
        assertEquals(404, get("/missing.png").statusCode());
    }

    @Test
    void headStatesTheLengthAndSendsNoBody() throws Exception {
        String response = raw("HEAD", "/");
        assertTrue(response.contains("Content-Length: 16"), response);
        assertFalse(response.contains("spa"), response);
    }

    @Test
    void pathTraversalNeverEscapesTheStaticDirectory() throws Exception {
        for (String target : new String[] {"/../secret.txt", "/%2e%2e/secret.txt", "/..%2fsecret.txt", "/%2e%2e%2fsecret.txt",
            "/static/../../secret.txt", "/..\\secret.txt"}) {
            String response = raw("GET", target);
            assertFalse(response.contains("TOP-SECRET"), target);
        }
        assertFalse(get("/../secret.txt").body().contains("TOP-SECRET"));
    }

    /** Sends the request line as written, which an HTTP client would normalise. */
    private String raw(String method, String target) throws IOException {
        try (Socket socket = new Socket("127.0.0.1", server.port())) {
            socket.getOutputStream().write((method + " " + target + " HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
                .getBytes(StandardCharsets.UTF_8));
            return new String(socket.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        }
    }
}
