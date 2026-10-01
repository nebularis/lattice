// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.validation;

public record ValidationResult(String shapeId, String severity, String focusNode, String elementId, String message) {
}
