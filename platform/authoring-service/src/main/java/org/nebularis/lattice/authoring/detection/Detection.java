// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.detection;

/**
 * One construct found in a literal part. {@code start} and {@code end} are UTF-16 code units into
 * the <em>element</em> text, {@code end} exclusive (plan §2.5).
 */
public record Detection(
    String elementId,
    int partIndex,
    int start,
    int end,
    String text,
    String kind,
    Suggestion suggestion
) {
}
