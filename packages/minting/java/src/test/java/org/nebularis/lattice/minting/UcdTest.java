// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * The pinned Unicode 16.0.0 tables and pipeline steps (specification §3),
 * cross-checked over every code point against the JDK's own Unicode data
 * where the two define the same thing, and the UTF-8 byte counting of §4.1.
 */
class UcdTest {
    private static final int LAST = 0x10FFFF;

    private static List<String> assigned() {
        List<String> out = new ArrayList<>();
        for (int cp = 0; cp <= LAST; cp++) {
            if (Ucd.ASSIGNED.contains(cp) && Character.getType(cp) != Character.SURROGATE) {
                out.add(Character.toString(cp));
            }
        }
        return out;
    }

    private static String u(int... cps) {
        return new String(cps, 0, cps.length);
    }

    @Test
    void tablesAreTheCopiesThePythonLibraryReads() throws Exception {
        Path python = TestFiles.MINTING.resolve("python/src/lattice_minting/ucd/" + Ucd.VERSION);
        Path java = TestFiles.MINTING.resolve("java/src/main/resources/org/nebularis/lattice/minting/ucd/" + Ucd.VERSION);
        try (Stream<Path> files = Files.list(python)) {
            for (Path p : files.toList()) {
                assertEquals(HexFormat.of().formatHex(Files.readAllBytes(p)),
                        HexFormat.of().formatHex(Files.readAllBytes(java.resolve(p.getFileName()))), p.getFileName().toString());
            }
        }
    }

    @Test
    void assignedMatchesTheJdk() {
        List<String> differ = new ArrayList<>();
        for (int cp = 0; cp <= LAST; cp++) {
            if (Ucd.ASSIGNED.contains(cp) != Character.isDefined(cp)) {
                differ.add(String.format("U+%04X", cp));
            }
        }
        assertEquals(List.of(), differ);
    }

    @Test
    void fullCaseMappingsMatchTheJdkRootLocale() {
        List<String> differ = new ArrayList<>();
        for (String s : assigned()) {
            if (!Ucd.uppercaseFull(s).equals(s.toUpperCase(Locale.ROOT)) || !Ucd.lowercaseFull(s).equals(s.toLowerCase(Locale.ROOT))) {
                differ.add(String.format("U+%04X", s.codePointAt(0)));
            }
        }
        assertEquals(List.of(), differ);
    }

    @Test
    void finalSigmaInContext() {
        int sigma = 0x03A3;
        int finalSigma = 0x03C2;
        int small = 0x03C3;
        // OMICRON DELTA OMICRON SIGMA: the last sigma is final.
        assertEquals(u(0x03BF, 0x03B4, 0x03BF, finalSigma), Ucd.lowercaseFull(u(0x039F, 0x0394, 0x039F, sigma)));
        // A sigma on its own, or followed by a letter, is not final.
        assertEquals(u(small), Ucd.lowercaseFull(u(sigma)));
        assertEquals(u(0x03B1, small, 0x03B1), Ucd.lowercaseFull(u(0x0391, sigma, 0x0391)));
        // A combining accent between letter and sigma is case-ignorable.
        assertEquals(u(0x03B1, 0x0301, finalSigma), Ucd.lowercaseFull(u(0x0391, 0x0301, sigma)));
        for (String s : List.of(u(0x039F, 0x0394, 0x039F, sigma, ' ', 0x039F, 0x0394, 0x039F, sigma), u(0x0391, sigma, '.'), u(0x0391, '\'', sigma))) {
            assertEquals(s.toLowerCase(Locale.ROOT), Ucd.lowercaseFull(s));
        }
    }

    @Test
    void whiteSpaceIsNotJavaWhitespace() {
        List<Integer> differ = new ArrayList<>();
        for (int cp = 0; cp <= LAST; cp++) {
            if (Ucd.WHITE_SPACE.contains(cp) != Character.isWhitespace(cp)) {
                differ.add(cp);
            }
        }
        assertEquals(List.of(0x1C, 0x1D, 0x1E, 0x1F, 0x85, 0xA0, 0x2007, 0x202F), differ);
    }

    /** The three pipelines of specification §3.2. */
    static final Map<String, List<String>> PIPELINES = Map.of(
            "NfkcTrimCasefold", List.of("reject_unassigned", "nfkc_casefold", "trim_white_space"),
            "NfkcTrimUppercase", List.of("reject_unassigned", "nfkc", "trim_white_space", "uppercase_full", "nfkc"),
            "NfkcTrimLowercase", List.of("reject_unassigned", "nfkc", "trim_white_space", "lowercase_full", "nfkc"));

    @Test
    void recipesUseThePipelinesOfTheSpecification() {
        for (Path p : TestFiles.withSuffix(".recipe.json")) {
            Map<String, Object> r = TestFiles.load(p);
            List<Object> keys = new ArrayList<>();
            if (r.get("key") != null) {
                keys.add(r.get("key"));
            }
            if (r.get("claims") instanceof List<?> claims) {
                claims.forEach(c -> keys.add(Values.map(c).get("key")));
            }
            for (Object k : keys) {
                Map<String, Object> pipeline = Values.map(Values.map(k).get("pipeline"));
                assertEquals(PIPELINES.get(pipeline.get("id")), pipeline.get("steps"), p.getFileName().toString());
            }
        }
    }

    @Test
    void everyPipelineIsIdempotent() {
        List<String> corpus = assigned();
        PIPELINES.forEach((id, steps) -> {
            for (String s : corpus) {
                String once = run(steps, s);
                assertEquals(once, run(steps, once), () -> id + " " + String.format("U+%04X", s.codePointAt(0)));
            }
        });
    }

    private static String run(List<?> steps, String s) {
        for (Object step : steps) {
            s = Ucd.step((String) step).apply(s);
        }
        return s;
    }

    @Test
    void unassignedCodePointsAreRefused() {
        MintException e = assertThrows(MintException.class, () -> Ucd.rejectUnassigned("sample" + u(0x0378)));
        assertEquals(MintError.UnassignedCodePoint, e.kind());
    }

    @Test
    void tupleLengthsAreUtf8Bytes() {
        String mathBold = u(0x1D400) + "bc";
        assertEquals(4, mathBold.length());
        assertEquals(3, mathBold.codePointCount(0, mathBold.length()));
        byte[] tuple = Canonical.tupleBytes(List.of(mathBold, u(0x1F600), "", u(0xE9)));
        String text = new String(tuple, StandardCharsets.UTF_8);
        assertEquals("6:" + mathBold + "4:" + u(0x1F600) + "0:2:" + u(0xE9), text);
    }

    @Test
    void percentEncodingIsPerUtf8Byte() {
        assertEquals("a%2Fb%20c%25d-._~%C3%A9%F0%9F%98%80", Canonical.percentEncode("a/b c%d-._~" + u(0xE9) + u(0x1F600)));
    }

    @Test
    void base32MatchesRfc4648() {
        // RFC 4648 §10 test vectors, unpadded.
        String[][] cases = {{"", ""}, {"f", "MY"}, {"fo", "MZXQ"}, {"foo", "MZXW6"}, {"foob", "MZXW6YQ"}, {"fooba", "MZXW6YTB"}, {"foobar", "MZXW6YTBOI"}};
        for (String[] c : cases) {
            assertEquals(c[1], Canonical.encode(c[0].getBytes(StandardCharsets.US_ASCII), "base32"));
        }
        assertTrue(Canonical.encode(new byte[] {(byte) 0xfb, (byte) 0xff}, "base64url").equals("-_8"));
    }
}
