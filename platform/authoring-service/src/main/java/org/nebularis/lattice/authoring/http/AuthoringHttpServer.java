// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.http;

import com.fasterxml.jackson.databind.JsonNode;
import io.javalin.Javalin;
import io.javalin.http.Context;
import io.javalin.http.HandlerType;
import io.javalin.json.JavalinJackson;
import java.util.List;
import org.nebularis.lattice.authoring.api.ApiResponse;
import org.nebularis.lattice.authoring.api.AuthoringApi;
import org.nebularis.lattice.authoring.api.ErrorBody;
import org.nebularis.lattice.authoring.json.Json;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The only class in this service that knows it runs over HTTP (plan WA4, decision WA-D4: Javalin).
 * Every handler reads path parameters and the body, calls {@link AuthoringApi}, and writes its
 * {@link ApiResponse}. No business logic lives here.
 */
public final class AuthoringHttpServer {
    private static final Logger LOG = LoggerFactory.getLogger(AuthoringHttpServer.class);
    private static final long MAX_REQUEST_SIZE = 1_048_576L;

    private final Javalin app;

    public AuthoringHttpServer(AuthoringApi api) {
        this.app = Javalin.create(config -> {
            config.showJavalinBanner = false;
            config.useVirtualThreads = true;
            config.http.prefer405over404 = true;
            config.jsonMapper(new JavalinJackson(Json.MAPPER, false));
        });
        configure(api);
    }

    private void configure(AuthoringApi api) {
        app.before(this::checkRequest);
        app.after(AuthoringHttpServer::setHeaders);

        app.get("/api/health", ctx -> write(ctx, api.health()));
        app.get("/api/templates", ctx -> write(ctx, api.listTemplates()));
        app.get("/api/templates/{templateId}", ctx -> write(ctx, api.getTemplate(ctx.pathParam("templateId"))));
        app.get("/api/samples", ctx -> write(ctx, api.listSamples()));
        app.get("/api/samples/{sampleId}", ctx -> write(ctx, api.getSample(ctx.pathParam("sampleId"))));
        app.get("/api/documents/{documentId}", ctx -> write(ctx, api.getDocument(ctx.pathParam("documentId"))));
        app.put("/api/documents/{documentId}/snapshot", ctx ->
            write(ctx, api.submitSnapshot(ctx.pathParam("documentId"), ctx.bodyAsClass(JsonNode.class))));
        app.get("/api/jobs/{jobId}", ctx -> write(ctx, api.getJob(ctx.pathParam("jobId"))));
        app.get("/api/documents/{documentId}/revisions/{revision}/analysis", ctx ->
            write(ctx, api.getAnalysis(ctx.pathParam("documentId"), ctx.pathParam("revision"))));
        app.get("/api/documents/{documentId}/revisions/{revision}/graph/{kind}", ctx ->
            write(ctx, api.getGraph(ctx.pathParam("documentId"), ctx.pathParam("revision"), ctx.pathParam("kind"))));

        app.error(404, ctx -> write(ctx, errorResponse(404, "not found")));
        app.error(405, ctx -> write(ctx, errorResponse(405, "method not allowed")));
        app.exception(PayloadTooLargeException.class, (e, ctx) ->
            write(ctx, errorResponse(413, "request body exceeds 1 MiB")));
        app.exception(UnsupportedMediaTypeException.class, (e, ctx) ->
            write(ctx, errorResponse(415, "Content-Type must be application/json")));
        app.exception(Exception.class, (e, ctx) -> {
            LOG.error("unexpected error handling {} {}", ctx.method(), ctx.path(), e);
            write(ctx, errorResponse(500, "internal error"));
        });
    }

    private void checkRequest(Context ctx) {
        if (ctx.req().getContentLengthLong() > MAX_REQUEST_SIZE) {
            throw new PayloadTooLargeException();
        }
        if (ctx.method() == HandlerType.PUT) {
            String contentType = ctx.contentType();
            if (contentType == null || !contentType.startsWith(ApiResponse.APPLICATION_JSON)) {
                throw new UnsupportedMediaTypeException();
            }
        }
    }

    private static void setHeaders(Context ctx) {
        ctx.header("X-Content-Type-Options", "nosniff");
        ctx.header("Cache-Control", "no-store");
    }

    private static ApiResponse<ErrorBody> errorResponse(int status, String message) {
        return new ApiResponse<>(status, new ErrorBody(message, List.of()), ApiResponse.APPLICATION_JSON);
    }

    private static void write(Context ctx, ApiResponse<?> response) {
        ctx.status(response.status()).contentType(response.contentType());
        if (ApiResponse.TEXT_TURTLE.equals(response.contentType())) {
            ctx.result((String) response.body());
        } else {
            ctx.json(response.body());
        }
    }

    /** {@code 0} for an ephemeral port, read back with {@link #port()}. */
    public void start(int port) {
        app.start(port);
    }

    public void stop() {
        app.stop();
    }

    public int port() {
        return app.port();
    }

    private static final class PayloadTooLargeException extends RuntimeException {
    }

    private static final class UnsupportedMediaTypeException extends RuntimeException {
    }
}
