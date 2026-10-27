// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.http;

import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.Executors;
import org.nebularis.lattice.studio.api.ApiRequest;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.api.StudioApi;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Adapts the JDK's {@link HttpServer} to {@link StudioApi}, and serves the built SPA from one directory. */
public final class StudioHttpServer implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(StudioHttpServer.class);
    private static final String CSP =
        "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'";
    private static final Map<String, String> TYPES = Map.of(
        "html", "text/html; charset=utf-8", "js", "text/javascript; charset=utf-8",
        "css", "text/css; charset=utf-8", "svg", "image/svg+xml", "woff2", "font/woff2",
        "json", "application/json; charset=utf-8", "ico", "image/x-icon");

    private final HttpServer server;
    private final StudioApi api;
    private final Path staticRoot;

    /** {@code staticDir} may be null. */
    public StudioHttpServer(StudioApi api, String bind, int port, Path staticDir) throws IOException {
        this.api = api;
        this.staticRoot = staticDir == null ? null : realPath(staticDir);
        this.server = HttpServer.create(new InetSocketAddress(bind, port), 0);
        this.server.createContext("/", this::handle);
        this.server.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
    }

    private static Path realPath(Path dir) throws IOException {
        return dir.toRealPath();
    }

    public void start() {
        server.start();
    }

    public int port() {
        return server.getAddress().getPort();
    }

    @Override
    public void close() {
        server.stop(0);
        ((java.util.concurrent.ExecutorService) server.getExecutor()).shutdown();
    }

    private void handle(HttpExchange exchange) throws IOException {
        try (exchange) {
            String path = exchange.getRequestURI().getRawPath();
            ApiResponse response;
            if (path.equals("/api") || path.startsWith("/api/")) {
                response = api(exchange, path);
            } else {
                response = staticFile(exchange.getRequestMethod(), exchange.getRequestURI().getPath());
            }
            send(exchange, response);
        } catch (RuntimeException e) {
            LOG.error("request failed", e);
            try {
                exchange.sendResponseHeaders(500, -1);
            } catch (IOException | RuntimeException ignored) {
                // The response had already started.
            }
        }
    }

    private ApiResponse api(HttpExchange exchange, String path) throws IOException {
        String method = exchange.getRequestMethod();
        byte[] body = new byte[0];
        if (method.equals("POST") || method.equals("PUT")) {
            String declared = exchange.getRequestHeaders().getFirst("Content-Length");
            if (declared != null && parseLength(declared) > StudioApi.MAX_BODY_BYTES) {
                return StudioApi.tooLarge();
            }
            // One byte past the limit is enough to know the body is too large, and nothing more is read.
            body = exchange.getRequestBody().readNBytes(StudioApi.MAX_BODY_BYTES + 1);
            if (body.length > StudioApi.MAX_BODY_BYTES) {
                return StudioApi.tooLarge();
            }
        }
        Map<String, String> headers = new HashMap<>();
        exchange.getRequestHeaders().forEach((k, v) -> {
            if (!v.isEmpty()) {
                headers.put(k.toLowerCase(Locale.ROOT), v.get(0));
            }
        });
        return api.handle(new ApiRequest(method, path, exchange.getRequestURI().getRawQuery(), headers, body));
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

    private void send(HttpExchange exchange, ApiResponse r) throws IOException {
        var out = exchange.getResponseHeaders();
        r.headers().forEach(out::set);
        out.set("X-Content-Type-Options", "nosniff");
        out.set("Referrer-Policy", "no-referrer");
        String type = r.headers().getOrDefault("Content-Type", "");
        if (type.startsWith("text/html")) {
            out.set("Content-Security-Policy", CSP);
        }
        boolean head = exchange.getRequestMethod().equals("HEAD");
        boolean noBody = r.body().length == 0 || r.status() == 204 || r.status() == 304;
        if (noBody || head) {
            exchange.sendResponseHeaders(r.status(), -1);
            return;
        }
        exchange.sendResponseHeaders(r.status(), r.body().length);
        try (OutputStream os = exchange.getResponseBody()) {
            os.write(r.body());
        }
    }
}
