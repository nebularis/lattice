// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.http;

import io.helidon.webserver.WebServer;
import io.helidon.webserver.http.ServerRequest;
import io.helidon.webserver.http.ServerResponse;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import org.nebularis.lattice.studio.api.ApiRequest;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.api.StudioApi;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Adapts Helidon SE's {@link WebServer} to {@link StudioApi}, and serves the built SPA from one directory. Helidon runs
 * each request on a virtual thread, so a handler may block on the store.
 */
public final class StudioHttpServer implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(StudioHttpServer.class);
    private static final String CSP =
        "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'";
    private static final Map<String, String> TYPES = Map.of(
        "html", "text/html; charset=utf-8", "js", "text/javascript; charset=utf-8",
        "css", "text/css; charset=utf-8", "svg", "image/svg+xml", "woff2", "font/woff2",
        "json", "application/json; charset=utf-8", "ico", "image/x-icon");

    private final WebServer server;
    private final StudioApi api;
    private final Path staticRoot;

    /** {@code staticDir} may be null. */
    public StudioHttpServer(StudioApi api, String bind, int port, Path staticDir) throws IOException {
        this.api = api;
        this.staticRoot = staticDir == null ? null : realPath(staticDir);
        this.server = WebServer.builder().host(bind).port(port).routing(r -> r.any(this::handle)).build();
    }

    private static Path realPath(Path dir) throws IOException {
        return dir.toRealPath();
    }

    public void start() {
        server.start();
    }

    public int port() {
        return server.port();
    }

    @Override
    public void close() {
        server.stop();
    }

    private void handle(ServerRequest req, ServerResponse res) {
        String method = req.prologue().method().text();
        try {
            String path = req.path().rawPath();
            ApiResponse response;
            if (path.equals("/api") || path.startsWith("/api/") || path.equals("/mcp")) {
                response = api(req, method, path);
            } else {
                response = staticFile(method, req.path().path());
            }
            send(res, method, response);
        } catch (IOException | RuntimeException e) {
            LOG.error("request failed", e);
            if (!res.isSent()) {
                res.status(500).send();
            }
        }
    }

    private ApiResponse api(ServerRequest req, String method, String path) throws IOException {
        Map<String, String> headers = new HashMap<>();
        req.headers().forEach(h -> headers.putIfAbsent(h.name().toLowerCase(Locale.ROOT), h.value()));
        byte[] body = new byte[0];
        if ((method.equals("POST") || method.equals("PUT")) && req.content().hasEntity()) {
            String declared = headers.get("content-length");
            if (declared != null && parseLength(declared) > StudioApi.MAX_BODY_BYTES) {
                return StudioApi.tooLarge();
            }
            // One byte past the limit is enough to know the body is too large, and nothing more is read.
            body = req.content().inputStream().readNBytes(StudioApi.MAX_BODY_BYTES + 1);
            if (body.length > StudioApi.MAX_BODY_BYTES) {
                return StudioApi.tooLarge();
            }
        }
        return api.handle(new ApiRequest(method, path, req.query().rawValue(), headers, body));
    }

    private static long parseLength(String s) {
        try {
            return Long.parseLong(s.trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private ApiResponse staticFile(String method, String decodedPath) throws IOException {
        if (staticRoot == null) {
            return ApiResponse.text(404, "not found");
        }
        if (!method.equals("GET") && !method.equals("HEAD")) {
            return ApiResponse.text(405, "method not allowed").with("Allow", "GET, HEAD");
        }
        Path file = resolve(decodedPath);
        if (file == null) {
            // A path with a file extension is a missing asset, any other is a route of the SPA.
            String last = decodedPath.substring(decodedPath.lastIndexOf('/') + 1);
            file = last.contains(".") ? null : resolve("/index.html");
        }
        if (file == null) {
            return ApiResponse.text(404, "not found");
        }
        String name = file.getFileName().toString();
        String type = TYPES.getOrDefault(name.substring(name.lastIndexOf('.') + 1).toLowerCase(Locale.ROOT),
            "application/octet-stream");
        return new ApiResponse(200, new java.util.LinkedHashMap<>(Map.of("Content-Type", type)), Files.readAllBytes(file));
    }

    /** The regular file under the static root that the decoded path names, or null. */
    private Path resolve(String decodedPath) {
        if (decodedPath.indexOf('\0') >= 0 || decodedPath.indexOf('\\') >= 0) {
            return null;
        }
        try {
            String relative = decodedPath.equals("/") ? "index.html" : decodedPath.substring(1);
            Path file = staticRoot.resolve(relative).normalize().toRealPath();
            return file.startsWith(staticRoot) && Files.isRegularFile(file) ? file : null;
        } catch (IOException | RuntimeException e) {
            return null;
        }
    }

    private static void send(ServerResponse res, String method, ApiResponse r) {
        res.status(r.status());
        r.headers().forEach(res::header);
        res.header("X-Content-Type-Options", "nosniff");
        res.header("Referrer-Policy", "no-referrer");
        if (r.headers().getOrDefault("Content-Type", "").startsWith("text/html")) {
            res.header("Content-Security-Policy", CSP);
        }
        if (r.body().length == 0 || r.status() == 204 || r.status() == 304) {
            res.send();
        } else if (method.equals("HEAD")) {
            // Helidon would send a HEAD response's body, so the length is stated and nothing sent.
            res.contentLength(r.body().length);
            res.send();
        } else {
            res.send(r.body());
        }
    }
}
