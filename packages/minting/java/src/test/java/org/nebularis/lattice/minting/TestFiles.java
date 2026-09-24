// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

/** Locations of the anchors and generated testdata, shared with the Python library. */
final class TestFiles {
    static final Path MINTING = Path.of(System.getProperty("minting.dir", "..")).toAbsolutePath().normalize();
    static final Path REPO = MINTING.getParent().getParent();
    static final Path ANCHORS = REPO.resolve("contracts/identity/anchor-vectors.json");
    static final Path TESTDATA = MINTING.resolve("testdata");

    private TestFiles() {
    }

    static List<Path> withSuffix(String suffix) {
        try (Stream<Path> s = Files.list(TESTDATA)) {
            return s.filter(p -> p.getFileName().toString().endsWith(suffix)).sorted().toList();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    static List<Path> vectorFiles() {
        return withSuffix(".vectors.json");
    }

    static Map<String, Object> load(Path p) {
        try {
            return Values.map(Json.parse(Files.readString(p)));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    /** A fresh, mutable copy of the committed recipe whose file name starts with this class name. */
    static Map<String, Object> recipe(String prefix) {
        return load(withSuffix(".recipe.json").stream()
                .filter(p -> p.getFileName().toString().startsWith(prefix + "-")).findFirst().orElseThrow());
    }

    /** The recipe with its digest recomputed after a deliberate change. */
    static Map<String, Object> reseal(Map<String, Object> r) {
        Map<String, Object> body = new LinkedHashMap<>(r);
        body.remove("recipeDigest");
        r.put("recipeDigest", "sha256:" + HexFormat.of().formatHex(Canonical.sha256(Json.canonical(body))));
        return r;
    }
}
