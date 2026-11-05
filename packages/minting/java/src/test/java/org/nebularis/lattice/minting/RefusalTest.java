// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.function.Executable;

/** Refusals outside the vector files: recipe loading, the runtime Unicode check, secrets and randomness (§9). */
class RefusalTest {
    private static final Map<String, Object> PERSON = Map.of("key", List.of("ada@example.org"), "scope", "acme",
            "surrogate", "8f2c1b7e-3e4a-4f7c-9a6d-2b1e0c5d7f90");

    private static MintError kind(Executable call) {
        return assertThrows(MintException.class, call).kind();
    }

    @Test
    void unknownRecipeFormat() {
        Map<String, Object> r = TestFiles.recipe("Product");
        r.put("recipeFormat", "lattice-minting-recipe/2");
        assertEquals(MintError.UnsupportedRecipeFormat, kind(() -> Recipe.parse(r)));
    }

    @Test
    void unknownStrategy() {
        Map<String, Object> r = TestFiles.recipe("Product");
        r.put("strategy", "GuessedIdentity");
        assertEquals(MintError.UnsupportedRecipeFormat, kind(() -> Recipe.parse(r)));
    }

    @Test
    void anyChangeBreaksTheDigest() {
        Map<String, Object> r = TestFiles.recipe("Product");
        r.put("iriTemplate", ((String) r.get("iriTemplate")).replace("sku", "SKU"));
        assertEquals(MintError.RecipeDigestMismatch, kind(() -> Recipe.parse(new String(Json.canonical(r), java.nio.charset.StandardCharsets.UTF_8))));
    }

    @Test
    void notJsonIsAnUnsupportedFormat() {
        assertEquals(MintError.UnsupportedRecipeFormat, kind(() -> Recipe.parse("{\"recipeFormat\": 1.5}")));
    }

    @Test
    void pipelineOfAnotherUnicodeVersion() {
        Map<String, Object> r = TestFiles.recipe("Product");
        Values.map(Values.map(r.get("key")).get("pipeline")).put("unicodeVersion", "15.1.0");
        assertEquals(MintError.UnsupportedRecipeFormat, kind(() -> Recipe.parse(TestFiles.reseal(r))));
    }

    @Test
    void claimsWithDifferentKeys() {
        Map<String, Object> r = TestFiles.recipe("Person");
        List<Object> claims = new ArrayList<>(Values.list(r.get("claims")));
        Map<String, Object> second = Values.map(Json.parse(new String(Json.canonical(claims.get(0)), java.nio.charset.StandardCharsets.UTF_8)));
        second.put("schemeVersion", "v2");
        Values.map(second.get("key")).put("pipeline", Values.map(TestFiles.recipe("Product").get("key")).get("pipeline"));
        claims.add(second);
        r.put("claims", claims);
        assertEquals(MintError.UnsupportedRecipeFormat, kind(() -> Recipe.parse(TestFiles.reseal(r))));
    }

    @Test
    void olderRuntimeUnicode() {
        assertEquals(MintError.RuntimeUnicodeTooOld, kind(() -> Ucd.checkRuntime(cp -> false)));
    }

    @Test
    void anEmptySecretIsNoSecret() {
        Minter minter = new Minter(Recipe.parse(TestFiles.recipe("Person")), Map.of("example-key-v1", new byte[0]));
        assertEquals(MintError.MissingSecret, kind(() -> minter.mint(PERSON)));
    }

    @Test
    void theMinterCopiesSecrets() {
        byte[] secret = "k".repeat(32).getBytes(java.nio.charset.StandardCharsets.US_ASCII);
        Map<String, byte[]> secrets = new HashMap<>(Map.of("example-key-v1", secret));
        Minter minter = new Minter(Recipe.parse(TestFiles.recipe("Person")), secrets);
        String before = minter.mint(PERSON).claimIris().get(0);
        secret[0] = 'x';
        secrets.clear();
        assertEquals(before, minter.mint(PERSON).claimIris().get(0));
    }

    @Test
    void aBlankCanonicalizerIsJudgedByWhiteSpace() {
        Minter minter = new Minter(Recipe.parse(TestFiles.recipe("Contract")));
        String nquads = "<urn:a> <urn:b> \"c\" .\n";
        assertEquals(MintError.CanonicalizerNotDeclared,
                kind(() -> minter.mint(Map.of("canonicalNQuads", nquads, "canonicalizer", Character.toString(0xA0)))));
        assertEquals(MintError.CanonicalizerNotDeclared, kind(() -> minter.mint(Map.of("canonicalNQuads", nquads))));
        assertTrue(minter.mint(Map.of("canonicalNQuads", nquads, "canonicalizer", Character.toString(0x1F))).iri().startsWith("urn:rev:content:"));
    }

    private static Map<String, Object> scopedNaturalKey() {
        Map<String, Object> r = TestFiles.recipe("Policy");
        Values.map(r.get("key")).put("scopeProperty", "https://example.org/lending#tenant");
        return r;
    }

    @Test
    void aDotSegmentIsRefusedInANaturalKey() {
        Minter minter = new Minter(Recipe.parse(TestFiles.reseal(scopedNaturalKey())));
        for (String dots : List.of(".", "..", "\uFF0E\uFF0E")) {
            assertEquals(MintError.DotSegment, kind(() -> minter.mint(Map.of("key", List.of(dots, "p-1"), "scope", "acme"))));
            if (dots.length() <= 2 && dots.charAt(0) == '.') { // a scope is not normalized, so only the literal forms are segments
                assertEquals(MintError.DotSegment, kind(() -> minter.mint(Map.of("key", List.of("acme", "p-1"), "scope", dots))));
            }
        }
        assertTrue(minter.mint(Map.of("key", List.of("acme", "..."), "scope", "acme")).iri().endsWith("/ACME/..."));
        assertTrue(new Minter(Recipe.parse(TestFiles.recipe("Product"))).mint(Map.of("key", List.of(".."))).iri().startsWith("urn:ex:sku:"));
    }

    @Test
    void anEmptyScopeIsRefused() {
        Minter minter = new Minter(Recipe.parse(TestFiles.reseal(scopedNaturalKey())));
        assertEquals(MintError.EmptyScope, kind(() -> minter.mint(Map.of("key", List.of("acme", "p-1"), "scope", ""))));
        Minter claimed = new Minter(Recipe.parse(TestFiles.recipe("Person")), Map.of("example-key-v1", "k".repeat(32).getBytes(java.nio.charset.StandardCharsets.US_ASCII)));
        assertEquals(MintError.EmptyScope, kind(() -> claimed.mint(Map.of("key", List.of("ada@example.org"), "scope", "",
                "surrogate", "8f2c1b7e-3e4a-4f7c-9a6d-2b1e0c5d7f90"))));
    }

    private static Minter permissiveSurrogate(String pattern) {
        Map<String, Object> r = TestFiles.recipe("Person");
        Values.map(r.get("surrogate")).put("pattern", pattern);
        return new Minter(Recipe.parse(TestFiles.reseal(r)), Map.of("example-key-v1", "k".repeat(32).getBytes(java.nio.charset.StandardCharsets.US_ASCII)));
    }

    @Test
    void aSurrogateOutsideTheUnreservedSetIsRefused() {
        Minter minter = permissiveSurrogate(".*");
        for (String surrogate : List.of("a/b", "a#b", "a?b", "a b", "a%2Fb", "", "caf\u00e9")) {
            assertEquals(MintError.UnsafeSurrogate,
                    kind(() -> minter.mint(Map.of("key", List.of("ada@example.org"), "scope", "acme", "surrogate", surrogate))), surrogate);
        }
        assertEquals("urn:person:A-b.c_d~9",
                minter.mint(Map.of("key", List.of("ada@example.org"), "scope", "acme", "surrogate", "A-b.c_d~9")).iri());
        assertEquals(MintError.DotSegment,
                kind(() -> minter.mint(Map.of("key", List.of("ada@example.org"), "scope", "acme", "surrogate", ".."))));
    }

    @Test
    void aPositionWiderThanItsWidthIsRefusedWithBothNumbers() {
        Minter minter = new Minter(Recipe.parse(TestFiles.recipe("Shipment")));
        MintException e = assertThrows(MintException.class, () -> minter.mint(Map.of("namespaceToken", "ship-1", "epoch", 10000L, "seq", 1L)));
        assertEquals(MintError.PositionWidthOverflow, e.kind());
        assertTrue(e.getMessage().contains("10000") && e.getMessage().contains("4"));
        assertTrue(minter.mint(Map.of("namespaceToken", "ship-1", "epoch", 9999L, "seq", 1L)).iri().startsWith("urn:ev:shipment:"));
        assertEquals(MintError.DotSegment, kind(() -> minter.mint(Map.of("namespaceToken", "..", "epoch", 1L, "seq", 1L))));
    }

    @Test
    void randomSurrogatesUseTheSuppliedSource() {
        Recipe recipe = Recipe.parse(TestFiles.recipe("LineItem"));
        assertEquals("urn:ex:line-item:00000000-0000-4000-8000-000000000000",
                new Minter(recipe, Map.of(), byte[]::new).mint(Map.of()).iri());
        Pattern uuid = Pattern.compile("urn:ex:line-item:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}");
        Minter minter = new Minter(recipe);
        Set<String> seen = new HashSet<>();
        for (int i = 0; i < 50; i++) {
            String iri = minter.mint(Map.of()).iri();
            assertTrue(uuid.matcher(iri).matches(), iri);
            assertTrue(seen.add(iri));
        }
        assertFalse(seen.isEmpty());
    }
}
