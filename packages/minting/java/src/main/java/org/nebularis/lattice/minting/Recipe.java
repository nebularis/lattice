// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

import static org.nebularis.lattice.minting.Values.list;
import static org.nebularis.lattice.minting.Values.map;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * A verified recipe (identity-minting-specification.md §2). Construct with
 * {@link #parse(String)}, which checks the format, the strategy, the digest,
 * that every claim carries the same key, and the Unicode version and steps of
 * every pipeline.
 */
public final class Recipe {
    public static final String FORMAT = "lattice-minting-recipe/1";
    static final Set<String> STRATEGIES = Set.of(
            "NaturalKeyIdentity", "DerivedHashIdentity", "SurrogateClaimedIdentity", "RandomSurrogateIdentity",
            "PositionDerivedEvent", "ContentAddressedIdentity", "AdoptedIdentity", "ExternalRegistryIdentity");

    private final Map<String, Object> data;

    private Recipe(Map<String, Object> data) {
        this.data = data;
    }

    public Map<String, Object> data() {
        return data;
    }

    public String strategy() {
        return (String) data.get("strategy");
    }

    public String digest() {
        return (String) data.get("recipeDigest");
    }

    public static Recipe parse(String json) {
        Object parsed;
        try {
            parsed = Json.parse(json);
        } catch (Json.SyntaxException e) {
            throw new MintException(MintError.UnsupportedRecipeFormat, "not a recipe: " + e.getMessage());
        }
        if (!(parsed instanceof Map<?, ?>)) {
            throw new MintException(MintError.UnsupportedRecipeFormat, "a recipe is a JSON object");
        }
        return parse(map(parsed));
    }

    public static Recipe parse(Map<String, ?> source) {
        Map<String, Object> data = new LinkedHashMap<>(source);
        if (!FORMAT.equals(data.get("recipeFormat"))) {
            throw new MintException(MintError.UnsupportedRecipeFormat, "recipeFormat " + data.get("recipeFormat"));
        }
        if (!STRATEGIES.contains(data.get("strategy"))) {
            throw new MintException(MintError.UnsupportedRecipeFormat, "strategy " + data.get("strategy"));
        }
        Map<String, Object> body = new LinkedHashMap<>(data);
        body.remove("recipeDigest");
        String want;
        try {
            want = "sha256:" + HexFormat.of().formatHex(Canonical.sha256(Json.canonical(body)));
        } catch (IllegalArgumentException e) {
            throw new MintException(MintError.UnsupportedRecipeFormat, e.getMessage());
        }
        if (!want.equals(data.get("recipeDigest"))) {
            throw new MintException(MintError.RecipeDigestMismatch, "recipe says " + data.get("recipeDigest") + ", content is " + want);
        }
        try {
            List<?> claims = data.containsKey("claims") ? list(data.get("claims")) : List.of();
            for (Object c : claims) {
                if (!map(c).get("key").equals(map(claims.get(0)).get("key"))) {
                    throw new MintException(MintError.UnsupportedRecipeFormat, "every claim must carry the same key, which is normalized once");
                }
            }
            List<Object> pipelines = new ArrayList<>();
            if (data.containsKey("key")) {
                pipelines.add(map(data.get("key")).get("pipeline"));
            }
            for (Object c : claims) {
                pipelines.add(map(map(c).get("key")).get("pipeline"));
            }
            for (Object p : pipelines) {
                checkPipeline(map(p));
            }
        } catch (ClassCastException | NullPointerException e) {
            throw new MintException(MintError.UnsupportedRecipeFormat, "malformed key or claims: " + e.getMessage());
        }
        return new Recipe(Collections.unmodifiableMap(data));
    }

    private static void checkPipeline(Map<String, Object> p) {
        if (!Ucd.VERSION.equals(p.get("unicodeVersion"))) {
            throw new MintException(MintError.UnsupportedRecipeFormat,
                    "pipeline Unicode " + p.get("unicodeVersion") + ", this library supports " + Ucd.VERSION);
        }
        List<?> steps = p.get("steps") instanceof List<?> l ? l : List.of();
        boolean known = steps.stream().allMatch(s -> s instanceof String name && Ucd.step(name) != null);
        if (steps.isEmpty() || !"reject_unassigned".equals(steps.get(0)) || !known) {
            throw new MintException(MintError.UnsupportedRecipeFormat, "pipeline steps " + steps + " are not a supported sequence");
        }
    }
}
