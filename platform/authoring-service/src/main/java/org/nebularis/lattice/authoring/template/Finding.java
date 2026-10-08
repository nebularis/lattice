// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.template;

import org.nebularis.lattice.authoring.model.Severity;

/**
 * One thing the author should look at: a mismatch between the document and its template (at
 * snapshot time) or between the reading and its template (conformance). {@code kind} is one of the
 * six values of the common schema's {@code $defs/Finding}.
 */
public record Finding(String kind, Severity severity, String sectionKey, String elementId, String message) {
}
