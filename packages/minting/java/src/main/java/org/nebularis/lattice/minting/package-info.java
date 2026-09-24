// SPDX-License-Identifier: MPL-2.0
/**
 * LATTICE identity minting (ADR-A84). Mints IRIs from a LATTICE minting
 * recipe, exactly as the identity minting specification defines, using only
 * JDK 25 and tables pinned to Unicode 16.0.0. Typical use:
 *
 * <pre>{@code
 * Recipe recipe = Recipe.parse(Files.readString(recipeFile));
 * Minter minter = new Minter(recipe, Map.of("example-key-v1", secretBytes));
 * Minted minted = minter.mint(Map.of("key", List.of("Ada@Example.org"), "scope", "acme",
 *         "surrogate", "8f2c1b7e-3e4a-4f7c-9a6d-2b1e0c5d7f90"));
 * minted.iri(); minted.claimIris(); minted.trace();
 * }</pre>
 *
 * <p>A refusal throws {@link org.nebularis.lattice.minting.MintException} with a named
 * {@link org.nebularis.lattice.minting.MintError}.
 */
package org.nebularis.lattice.minting;
