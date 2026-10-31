// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.stream.Stream;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.atlas.json.JsonValue;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;

/** Finds the repository files through the {@code persistence.dir} system property and reads the vectors and the compiled profiles. */
final class TestSupport {
    private TestSupport() {}

    static final Path PERSISTENCE = Path.of(System.getProperty("persistence.dir", "..")).toAbsolutePath().normalize();
    static final Path VECTORS = PERSISTENCE.resolve("../../contracts/persistence/vectors.json").normalize();
    static final Path DATA = PERSISTENCE.resolve("python/tests/data");

    private static JsonObject vectors;
    private static Map<String, Model> profiles;

    static synchronized JsonObject vectors() {
        if (vectors == null) {
            try {
                vectors = JSON.parse(Files.readString(VECTORS, StandardCharsets.UTF_8));
            } catch (IOException e) {
                throw new IllegalStateException(e);
            }
        }
        return vectors;
    }

    /** The compiled profiles in the Python library's tests/data, by example name. */
    static synchronized Map<String, Model> profiles() {
        if (profiles == null) {
            profiles = new TreeMap<>();
            try (Stream<Path> files = Files.list(DATA)) {
                for (Path p : files.filter(f -> f.getFileName().toString().endsWith(".compiled.ttl")).sorted().toList()) {
                    profiles.put(p.getFileName().toString().replace(".compiled.ttl", ""), RDFDataMgr.loadModel(p.toString(), Lang.TURTLE));
                }
            } catch (IOException e) {
                throw new IllegalStateException(e);
            }
        }
        return profiles;
    }

    static OperationContract operation(String example, String template) {
        return OperationContract.read(profiles().get(example)).stream().filter(o -> o.templateId().equals(template)).findFirst().orElseThrow();
    }

    static Map<String, Object> values(Object... pairs) {
        Map<String, Object> m = new HashMap<>();
        for (int i = 0; i < pairs.length; i += 2) m.put((String) pairs[i], pairs[i + 1]);
        return m;
    }

    static Map<String, Object> with(Map<String, Object> base, Object... pairs) {
        Map<String, Object> m = new HashMap<>(base);
        m.putAll(values(pairs));
        return m;
    }

    static List<String> codes(List<Refusal> refusals) {
        return refusals.stream().map(Refusal::code).distinct().sorted().toList();
    }

    // ---- JSON helpers

    static JsonValue get(JsonValue o, String key) {
        JsonObject jo = o.getAsObject();
        return jo.hasKey(key) ? jo.get(key) : null;
    }

    static String str(JsonValue v) {
        return v == null || v.isNull() ? null : v.getAsString().value();
    }

    static List<JsonValue> list(JsonValue v) {
        List<JsonValue> out = new ArrayList<>();
        if (v != null && !v.isNull()) v.getAsArray().forEach(out::add);
        return out;
    }

    static List<String> strings(JsonValue v) {
        return list(v).stream().map(TestSupport::str).toList();
    }
}
