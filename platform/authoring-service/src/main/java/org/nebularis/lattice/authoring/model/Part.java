// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

/** The three forms a text part takes (CCS sketch §4.1): a literal, a variable reference or an
 *  object reference. */
public sealed interface Part permits LiteralPart, VariablePart, ReferencePart {
    /** The text shown in place of this part when the element's text is read as one string. */
    String displayText();
}
