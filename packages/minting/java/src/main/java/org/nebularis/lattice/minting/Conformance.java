// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

import static org.nebularis.lattice.minting.Values.list;
import static org.nebularis.lattice.minting.Values.map;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * Runs conformance vectors or anchors against this library
 * (identity-minting-specification.md §10). Each positive vector is minted
 * from its inputs and compared <em>trace step by trace step</em>, then by IRI.
 * The {@code ucd} member of a normalize step is a citation and is not compared.
 * Negative vectors must raise the named error. Format vectors check their
 * examples and, for random strategies, freshly minted identifiers.
 */
public final class Conformance {

    /** Checks passed, and one line per failure. */
    public static final class Report {
        private int passed;
        private final List<String> failures = new ArrayList<>();

        public int passed() {
            return passed;
        }

        public List<String> failures() {
            return List.copyOf(failures);
        }

        public boolean ok() {
            return failures.isEmpty();
        }

        void check(String where, boolean ok, String detail) {
            if (ok) {
                passed++;
            } else {
                failures.add(where + ": " + detail);
            }
        }
    }

    private Conformance() {
    }

    public static Report verify(Path path) throws IOException {
        return verify(Json.parse(Files.readString(path)));
    }

    /** Verify a parsed vectors or anchors document. */
    public static Report verify(Object document) {
        Map<String, Object> doc = map(document);
        Report report = new Report();
        if (doc.containsKey("sets")) {
            List<?> sets = list(doc.get("sets"));
            for (int i = 0; i < sets.size(); i++) {
                Map<String, Object> set = map(sets.get(i));
                verifySet(set, report, "set " + i + " (" + map(set.get("recipe")).get("strategy") + ")");
            }
        } else {
            String description = String.valueOf(doc.getOrDefault("description", "vectors"));
            verifySet(doc, report, description.substring(0, Math.min(40, description.length())));
        }
        return report;
    }

    private static Map<String, Object> strip(Object step) {
        Map<String, Object> m = new LinkedHashMap<>(map(step));
        m.remove("ucd");
        return m;
    }

    private static List<Map<String, Object>> stripAll(List<?> trace) {
        return trace.stream().map(Conformance::strip).toList();
    }

    private static String firstDifference(List<?> want, List<?> got) {
        for (int i = 0; i < Math.min(want.size(), got.size()); i++) {
            if (!strip(want.get(i)).equals(strip(got.get(i)))) {
                return "step " + i + " (" + map(want.get(i)).get("step") + "): expected " + strip(want.get(i)) + ", got " + strip(got.get(i));
            }
        }
        return "trace length: expected " + want.size() + " steps, got " + got.size();
    }

    private static void verifySet(Map<String, Object> doc, Report report, String where) {
        Recipe recipe;
        try {
            recipe = Recipe.parse(map(doc.get("recipe")));
        } catch (MintException e) {
            report.check(where + " recipe", false, e.getMessage());
            return;
        }
        report.check(where + " recipe", true, "");
        Map<String, byte[]> secrets = new HashMap<>();
        if (doc.get("testSecrets") instanceof Map<?, ?> ts) {
            map(ts).forEach((k, v) -> secrets.put(k, HexFormat.of().parseHex((String) map(v).get("hex"))));
        }
        for (Object o : list(doc.get("positive"))) {
            Map<String, Object> vec = map(o);
            String at = where + " " + vec.get("id");
            Minted minted;
            try {
                minted = new Minter(recipe, secrets).mint(map(vec.get("inputs")));
            } catch (MintException e) {
                report.check(at, false, "raised " + e.getMessage());
                continue;
            }
            List<?> want = list(vec.get("trace"));
            boolean same = stripAll(want).equals(stripAll(minted.trace()));
            report.check(at + " trace", same, same ? "" : firstDifference(want, minted.trace()));
            report.check(at + " iri", minted.iri().equals(vec.get("iri")), "expected " + vec.get("iri") + ", got " + minted.iri());
            if (vec.containsKey("claimIris")) {
                report.check(at + " claimIris", minted.claimIris().equals(vec.get("claimIris")),
                        "expected " + vec.get("claimIris") + ", got " + minted.claimIris());
            }
        }
        for (Object o : list(doc.get("negative"))) {
            Map<String, Object> vec = map(o);
            String at = where + " " + vec.get("id");
            Map<String, Object> inputs = new LinkedHashMap<>(map(vec.get("inputs")));
            Object omit = inputs.remove("omitSecret");
            Map<String, byte[]> use = new HashMap<>(secrets);
            use.remove(omit);
            try {
                Minted minted = new Minter(recipe, use).mint(inputs);
                report.check(at, false, "expected " + vec.get("error") + ", minted " + minted.iri());
            } catch (MintException e) {
                report.check(at, e.kind().name().equals(vec.get("error")), "expected " + vec.get("error") + ", got " + e.kind());
            }
        }
        for (Object o : list(doc.get("format"))) {
            Map<String, Object> vec = map(o);
            String at = where + " " + vec.get("id");
            Pattern pattern = Pattern.compile((String) vec.get("pattern"));
            for (Object s : list(vec.get("accept"))) {
                report.check(at + " accept", pattern.matcher((String) s).matches(), (String) s);
            }
            for (Object s : list(vec.get("reject"))) {
                report.check(at + " reject", !pattern.matcher((String) s).matches(), (String) s);
            }
            if ("RandomSurrogateIdentity".equals(recipe.strategy())) {
                for (int i = 0; i < 5; i++) {
                    String iri = new Minter(recipe).mint(Map.of()).iri();
                    report.check(at + " minted", pattern.matcher(iri).matches(), iri);
                }
            }
        }
    }
}
