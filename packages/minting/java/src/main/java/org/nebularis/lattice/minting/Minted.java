// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

import java.util.List;
import java.util.Map;

/**
 * One minting result: the IRI, any claim IRIs, a trace of every intermediate
 * value in the conformance vectors' format (§10.1), and, for content-addressed
 * identity, the canonicalizer the caller declared.
 */
public record Minted(String iri, List<String> claimIris, List<Map<String, Object>> trace, String canonicalizer) {
}
