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
