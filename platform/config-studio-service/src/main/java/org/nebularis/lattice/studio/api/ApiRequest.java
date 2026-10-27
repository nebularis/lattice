// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.api;

import java.util.Map;

/** A request as {@link StudioApi} sees it. {@code path} is the raw path, {@code headers} has lower-case names. */
public record ApiRequest(String method, String path, String query, Map<String, String> headers, byte[] body) {
    public String header(String lowerCaseName) {
        return headers.get(lowerCaseName);
    }
}
