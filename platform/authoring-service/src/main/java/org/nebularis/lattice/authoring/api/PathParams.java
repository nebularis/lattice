// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.api;

import java.util.regex.Pattern;

/**
 * The common schema's path-parameter patterns (plan \u00a72.4), checked by {@link AuthoringApi}
 * itself so its L1 tests see the same 400s a real HTTP call would get.
 */
final class PathParams {
    static final Pattern UUID = Pattern.compile("^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$");
    static final Pattern KEY = Pattern.compile("^[a-z][a-z0-9-]{0,39}$");
    static final Pattern REVISION = Pattern.compile("^[1-9][0-9]{0,8}$");

    private PathParams() {
    }

    static boolean isUuid(String value) {
        return value != null && UUID.matcher(value).matches();
    }

    static boolean isKey(String value) {
        return value != null && KEY.matcher(value).matches();
    }

    static boolean isRevision(String value) {
        return value != null && REVISION.matcher(value).matches();
    }
}
