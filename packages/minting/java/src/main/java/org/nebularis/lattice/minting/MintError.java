// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

/** The named refusals of identity-minting-specification.md §9. Conformance vectors compare on these names. */
public enum MintError {
    UnsupportedRecipeFormat,
    RecipeDigestMismatch,
    RuntimeUnicodeTooOld,
    MissingKeyComponent,
    UnassignedCodePoint,
    EmptyKeyComponent,
    MissingSecret,
    PatternMismatch,
    PositionOutOfRange,
    CanonicalizerNotDeclared
}
