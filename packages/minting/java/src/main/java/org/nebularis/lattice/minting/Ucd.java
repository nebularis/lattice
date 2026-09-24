// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.IntPredicate;
import java.util.function.UnaryOperator;

/**
 * Unicode 16.0.0 behaviour from the pinned tables (identity-minting-specification.md §3).
 * Every step except NFC and NFKC reads the tables generated from the Unicode
 * Character Database, never Java's own case or whitespace handling, so this
 * library and the Python library agree byte for byte. NFC and NFKC use
 * {@link Normalizer}, which is safe only on Unicode 16.0.0 or later data and
 * only for assigned code points: see {@link #checkRuntime()} and
 * {@code reject_unassigned}.
 */
public final class Ucd {
    public static final String VERSION = "16.0.0";

    /** U+1C89 CYRILLIC CAPITAL LETTER TJE, first assigned in Unicode 16.0. */
    private static final int FIRST_IN_16 = 0x1C89;
    private static final int CAPITAL_SIGMA = 0x03A3;
    private static final int FINAL_SIGMA = 0x03C2;

    static final Ranges ASSIGNED = ranges("assigned.txt");
    static final Ranges WHITE_SPACE = ranges("white_space.txt");
    static final Ranges CASED = ranges("cased.txt");
    static final Ranges CASE_IGNORABLE = ranges("case_ignorable.txt");
    static final Map<Integer, String> NFKC_CF = mapping("nfkc_cf.txt");
    static final Map<Integer, String> UPPER = mapping("upper.txt");
    static final Map<Integer, String> LOWER = mapping("lower.txt");

    private static final Map<String, UnaryOperator<String>> STEPS = Map.of(
            "reject_unassigned", Ucd::rejectUnassigned,
            "nfc", Ucd::nfc,
            "nfkc", Ucd::nfkc,
            "nfkc_casefold", Ucd::nfkcCasefold,
            "trim_white_space", Ucd::trimWhiteSpace,
            "uppercase_full", Ucd::uppercaseFull,
            "lowercase_full", Ucd::lowercaseFull);

    private Ucd() {
    }

    /** Sorted, non-overlapping code point ranges. */
    static final class Ranges {
        private final int[] starts;
        private final int[] ends;

        Ranges(List<int[]> spans) {
            List<int[]> sorted = new ArrayList<>(spans);
            sorted.sort(Comparator.comparingInt(a -> a[0]));
            starts = sorted.stream().mapToInt(a -> a[0]).toArray();
            ends = sorted.stream().mapToInt(a -> a[1]).toArray();
        }

        boolean contains(int cp) {
            int i = Arrays.binarySearch(starts, cp);
            if (i < 0) {
                i = -i - 2;
            }
            return i >= 0 && cp <= ends[i];
        }
    }

    private static List<String> rows(String name) {
        try (InputStream in = Ucd.class.getResourceAsStream("ucd/" + VERSION + "/" + name)) {
            if (in == null) {
                throw new IllegalStateException("missing Unicode table " + name);
            }
            return new String(in.readAllBytes(), StandardCharsets.UTF_8).lines()
                    .filter(l -> !l.isEmpty() && !l.startsWith("#"))
                    .toList();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static int[] span(String field) {
        int dot = field.indexOf("..");
        return dot < 0
                ? new int[] {Integer.parseInt(field, 16), Integer.parseInt(field, 16)}
                : new int[] {Integer.parseInt(field.substring(0, dot), 16), Integer.parseInt(field.substring(dot + 2), 16)};
    }

    private static Ranges ranges(String name) {
        return new Ranges(rows(name).stream().map(Ucd::span).toList());
    }

    private static Map<Integer, String> mapping(String name) {
        Map<Integer, String> out = new HashMap<>();
        for (String row : rows(name)) {
            int semi = row.indexOf(';');
            StringBuilder target = new StringBuilder();
            for (String cp : row.substring(semi + 1).trim().split("\\s+")) {
                if (!cp.isEmpty()) {
                    target.appendCodePoint(Integer.parseInt(cp, 16));
                }
            }
            int[] s = span(row.substring(0, semi));
            for (int cp = s[0]; cp <= s[1]; cp++) {
                out.put(cp, target.toString());
            }
        }
        return Map.copyOf(out);
    }

    /** Refuses a runtime whose Unicode data predates 16.0.0 ({@code RuntimeUnicodeTooOld}). */
    public static void checkRuntime() {
        checkRuntime(Character::isDefined);
    }

    static void checkRuntime(IntPredicate defined) {
        if (!defined.test(FIRST_IN_16)) {
            throw new MintException(MintError.RuntimeUnicodeTooOld,
                    "this Java runtime's Unicode data is older than " + VERSION + " (U+1C89 is undefined)");
        }
    }

    /** The pipeline step with this name, or null. */
    public static UnaryOperator<String> step(String name) {
        return STEPS.get(name);
    }

    public static String rejectUnassigned(String s) {
        s.codePoints().filter(cp -> !ASSIGNED.contains(cp)).findFirst().ifPresent(cp -> {
            throw new MintException(MintError.UnassignedCodePoint, String.format("U+%04X is unassigned in Unicode %s", cp, VERSION));
        });
        return s;
    }

    public static String nfc(String s) {
        return Normalizer.normalize(s, Normalizer.Form.NFC);
    }

    public static String nfkc(String s) {
        return Normalizer.normalize(s, Normalizer.Form.NFKC);
    }

    /** toNFKC_Casefold: map each code point through NFKC_CF, then NFC. */
    public static String nfkcCasefold(String s) {
        return nfc(mapEach(s, NFKC_CF));
    }

    public static String trimWhiteSpace(String s) {
        int[] cps = s.codePoints().toArray();
        int i = 0;
        int j = cps.length;
        while (i < j && WHITE_SPACE.contains(cps[i])) {
            i++;
        }
        while (j > i && WHITE_SPACE.contains(cps[j - 1])) {
            j--;
        }
        return new String(cps, i, j - i);
    }

    public static String uppercaseFull(String s) {
        return mapEach(s, UPPER);
    }

    public static String lowercaseFull(String s) {
        int[] cps = s.codePoints().toArray();
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < cps.length; i++) {
            if (cps[i] == CAPITAL_SIGMA && finalSigma(cps, i)) {
                sb.appendCodePoint(FINAL_SIGMA);
            } else {
                String t = LOWER.get(cps[i]);
                if (t != null) {
                    sb.append(t);
                } else {
                    sb.appendCodePoint(cps[i]);
                }
            }
        }
        return sb.toString();
    }

    /** Unicode §3.13 Final_Sigma: preceded by a cased letter (skipping case-ignorables) and not followed by one. */
    private static boolean finalSigma(int[] cps, int i) {
        int j = i - 1;
        while (j >= 0 && CASE_IGNORABLE.contains(cps[j])) {
            j--;
        }
        if (j < 0 || !CASED.contains(cps[j])) {
            return false;
        }
        j = i + 1;
        while (j < cps.length && CASE_IGNORABLE.contains(cps[j])) {
            j++;
        }
        return j == cps.length || !CASED.contains(cps[j]);
    }

    private static String mapEach(String s, Map<Integer, String> table) {
        StringBuilder sb = new StringBuilder();
        s.codePoints().forEach(cp -> {
            String t = table.get(cp);
            if (t != null) {
                sb.append(t);
            } else {
                sb.appendCodePoint(cp);
            }
        });
        return sb.toString();
    }
}
