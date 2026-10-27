// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.api;

import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;

/** A response as {@link StudioApi} produces it. */
public record ApiResponse(int status, Map<String, String> headers, byte[] body) {
    public static final String TURTLE = "text/turtle; charset=utf-8";
    public static final String TEXT = "text/plain; charset=utf-8";

    public static ApiResponse text(int status, String message) {
        return new ApiResponse(status, new LinkedHashMap<>(Map.of("Content-Type", TEXT)),
            message.getBytes(StandardCharsets.UTF_8));
    }

    public static ApiResponse empty(int status) {
        return new ApiResponse(status, new LinkedHashMap<>(), new byte[0]);
    }

    public static ApiResponse turtle(int status, byte[] body) {
        return new ApiResponse(status, new LinkedHashMap<>(Map.of("Content-Type", TURTLE)), body);
    }

    public ApiResponse with(String name, String value) {
        Map<String, String> copy = new LinkedHashMap<>(headers);
        copy.put(name, value);
        return new ApiResponse(status, copy, body);
    }
}
