// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.http;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import io.helidon.webserver.WebServer;
import io.helidon.webserver.http.Handler;
import io.helidon.webserver.http.HttpRouting;
import io.helidon.webserver.http.ServerRequest;
import io.helidon.webserver.http.ServerResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;
import org.nebularis.lattice.authoring.api.ApiResponse;
import org.nebularis.lattice.authoring.api.AuthoringApi;
import org.nebularis.lattice.authoring.api.ErrorBody;
import org.nebularis.lattice.authoring.json.Json;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The only class in this service that knows it runs over HTTP, on Helidon SE's WebServer (CS12a, replacing Javalin and
 * its Jetty). Every handler reads path parameters and the body, calls {@link AuthoringApi}, and writes its
 * {@link ApiResponse}. No business logic lives here. Each request runs on a virtual thread.
 */
public final class AuthoringHttpServer {
    private static final Logger LOG = LoggerFactory.getLogger(AuthoringHttpServer.class);
    private static final int MAX_REQUEST_SIZE = 1_048_576;
    /** Every route's path, so a request for a known path with another method is 405 rather than 404. */
    private static final List<Pattern> ROUTES = List.of(
        "/api/health", "/api/templates", "/api/templates/[^/]+", "/api/samples", "/api/samples/[^/]+",
        "/api/documents/[^/]+", "/api/documents/[^/]+/snapshot", "/api/jobs/[^/]+",
        "/api/documents/[^/]+/revisions/[^/]+/analysis", "/api/documents/[^/]+/revisions/[^/]+/graph/[^/]+")
        .stream().map(Pattern::compile).toList();

    private final AuthoringApi api;
    private WebServer server;

    public AuthoringHttpServer(AuthoringApi api) {
        this.api = api;
    }

    private void routing(HttpRouting.Builder r) {
        r.get("/api/health", handle((req, p) -> api.health()))
            .get("/api/templates", handle((req, p) -> api.listTemplates()))
            .get("/api/templates/{templateId}", handle((req, p) -> api.getTemplate(p.get("templateId"))))
            .get("/api/samples", handle((req, p) -> api.listSamples()))
            .get("/api/samples/{sampleId}", handle((req, p) -> api.getSample(p.get("sampleId"))))
            .get("/api/documents/{documentId}", handle((req, p) -> api.getDocument(p.get("documentId"))))
            .put("/api/documents/{documentId}/snapshot", handle(this::submitSnapshot))
            .get("/api/jobs/{jobId}", handle((req, p) -> api.getJob(p.get("jobId"))))
            .get("/api/documents/{documentId}/revisions/{revision}/analysis",
                handle((req, p) -> api.getAnalysis(p.get("documentId"), p.get("revision"))))
            .get("/api/documents/{documentId}/revisions/{revision}/graph/{kind}",
                handle((req, p) -> api.getGraph(p.get("documentId"), p.get("revision"), p.get("kind"))))
            .any((req, res) -> {
                String path = req.path().path();
                boolean known = ROUTES.stream().anyMatch(route -> route.matcher(path).matches());
                write(res, error(known ? 405 : 404, known ? "method not allowed" : "not found"));
            });
    }

    private ApiResponse<?> submitSnapshot(ServerRequest req, io.helidon.common.parameters.Parameters p) throws IOException {
        String type = req.headers().contentType().map(t -> t.text().toLowerCase(Locale.ROOT)).orElse("");
        if (!type.startsWith(ApiResponse.APPLICATION_JSON)) {
            return error(415, "Content-Type must be application/json");
        }
        long declared = req.headers().contentLength().orElse(-1L);
        if (declared > MAX_REQUEST_SIZE) {
            return tooLarge();
        }
        // One byte past the limit is enough to know the body is too large, and nothing more is read.
        byte[] body = req.content().hasEntity() ? req.content().inputStream().readNBytes(MAX_REQUEST_SIZE + 1) : new byte[0];
        if (body.length > MAX_REQUEST_SIZE) {
            return tooLarge();
        }
        JsonNode json;
        try {
            json = Json.MAPPER.readTree(body);
        } catch (JsonProcessingException e) {
            return error(400, "the body is not JSON");
        }
        if (json == null || json.isMissingNode()) {
            return error(400, "the body is not JSON");
        }
        return api.submitSnapshot(p.get("documentId"), json);
    }

    private interface Route {
        ApiResponse<?> apply(ServerRequest req, io.helidon.common.parameters.Parameters pathParameters) throws IOException;
    }

    private static Handler handle(Route route) {
        return (req, res) -> {
            ApiResponse<?> response;
            try {
                response = route.apply(req, req.path().pathParameters());
            } catch (IOException | RuntimeException e) {
                LOG.error("unexpected error handling {} {}", req.prologue().method().text(), req.path().path(), e);
                response = error(500, "internal error");
            }
            write(res, response);
        };
    }

    private static ApiResponse<ErrorBody> tooLarge() {
        return error(413, "request body exceeds 1 MiB");
    }

    private static ApiResponse<ErrorBody> error(int status, String message) {
        return new ApiResponse<>(status, new ErrorBody(message, List.of()), ApiResponse.APPLICATION_JSON);
    }

    private static void write(ServerResponse res, ApiResponse<?> response) {
        byte[] body;
        try {
            body = ApiResponse.TEXT_TURTLE.equals(response.contentType())
                ? ((String) response.body()).getBytes(StandardCharsets.UTF_8)
                : Json.MAPPER.writeValueAsBytes(response.body());
        } catch (JsonProcessingException e) {
            LOG.error("could not write a response body", e);
            response = error(500, "internal error");
            body = "{\"error\":\"internal error\",\"details\":[]}".getBytes(StandardCharsets.UTF_8);
        }
        res.status(response.status());
        res.header("Content-Type", response.contentType());
        res.header("X-Content-Type-Options", "nosniff");
        res.header("Cache-Control", "no-store");
        res.send(body);
    }

    /** {@code 0} for an ephemeral port, read back with {@link #port()}. Listens on every address, as in its container. */
    public void start(int port) {
        server = WebServer.builder().host("0.0.0.0").port(port).routing(this::routing).build().start();
    }

    public void stop() {
        server.stop();
    }

    public int port() {
        return server.port();
    }
}
