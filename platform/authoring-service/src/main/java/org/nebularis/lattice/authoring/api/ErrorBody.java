// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.api;

import java.util.List;

/** The error schema's shape: {@code error} and {@code details}. */
public record ErrorBody(String error, List<String> details) {
    public ErrorBody {
        details = List.copyOf(details);
    }
}
