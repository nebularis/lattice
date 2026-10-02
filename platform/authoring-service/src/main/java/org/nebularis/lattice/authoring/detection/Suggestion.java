// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.detection;

import org.nebularis.lattice.authoring.model.ValueType;

/**
 * What the add-in offers to do with a detection. {@code action} is {@code mark-variable},
 * {@code mark-reference} or {@code none}; the other three are null where the action does not use
 * them (common schema {@code $defs/Suggestion}).
 */
public record Suggestion(String action, ValueType valueType, String suggestedKey, String targetElementId) {
    public static final String MARK_VARIABLE = "mark-variable";
    public static final String MARK_REFERENCE = "mark-reference";
    public static final String NONE = "none";

    public static Suggestion none() {
        return new Suggestion(NONE, null, null, null);
    }
}
