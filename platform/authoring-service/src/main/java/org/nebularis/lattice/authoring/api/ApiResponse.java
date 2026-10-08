// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.api;

import java.util.List;

/**
 * What {@link AuthoringApi} returns from every route method: a status, a body to serialise as
 * JSON (or, for {@link #TEXT_TURTLE}, as plain text), and the content type to send. Framework
 * neutral: {@code http.AuthoringHttpServer} is the only class that knows this is HTTP.
 */
public record ApiResponse<T>(int status, T body, String contentType) {
    public static final String APPLICATION_JSON = "application/json";
    public static final String TEXT_TURTLE = "text/turtle; charset=utf-8";

    public static <T> ApiResponse<T> ok(T body) {
        return new ApiResponse<>(200, body, APPLICATION_JSON);
    }

    public static <T> ApiResponse<T> ok(T body, String contentType) {
        return new ApiResponse<>(200, body, contentType);
    }

    public static <T> ApiResponse<T> unavailable(T body) {
        return new ApiResponse<>(503, body, APPLICATION_JSON);
    }

    public static ApiResponse<ErrorBody> notFound(String message) {
        return new ApiResponse<>(404, new ErrorBody(message, List.of()), APPLICATION_JSON);
    }

    public static ApiResponse<ErrorBody> badRequest(String message, List<String> details) {
        return new ApiResponse<>(400, new ErrorBody(message, details), APPLICATION_JSON);
    }

    public static ApiResponse<ErrorBody> conflict(String message) {
        return new ApiResponse<>(409, new ErrorBody(message, List.of()), APPLICATION_JSON);
    }
}
