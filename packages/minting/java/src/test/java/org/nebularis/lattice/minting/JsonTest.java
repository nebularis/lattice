// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

/** The restricted JSON reader and the RFC 8785 writer (specification §2.1). */
class JsonTest {
    private static final String BS = "\\";

    @Test
    void canonicalSortsMembersAndEscapesOnlyWhatItMust() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("b", 1L);
        m.put("a", List.of("x\n", Character.toString(0xE9), Character.toString(0x1F), "q\"s" + BS));
        m.put("B", null);
        m.put("c", true);
        String want = "{\"B\":null,\"a\":[\"x" + BS + "n\",\"" + Character.toString(0xE9) + "\",\"" + BS + "u001f\",\"q"
                + BS + "\"s" + BS + BS + "\"],\"b\":1,\"c\":true}";
        assertEquals(want, new String(Json.canonical(m), StandardCharsets.UTF_8));
    }

    @Test
    void canonicalRoundTripsParsedInput() {
        String text = "{ \"z\" : [1, -2, 0], \"a\": {\"k\": \"v\"} }";
        assertEquals("{\"a\":{\"k\":\"v\"},\"z\":[1,-2,0]}", new String(Json.canonical(Json.parse(text)), StandardCharsets.UTF_8));
    }

    @Test
    void integersBeyondALongStayExact() {
        assertEquals(Long.MAX_VALUE, Json.parse("9223372036854775807"));
        assertEquals(new BigInteger("9223372036854775808"), Json.parse("9223372036854775808"));
        assertEquals(-1L, Json.parse("-1"));
    }

    @Test
    void escapedSurrogatePairsBecomeOneCodePoint() {
        String json = "\"" + BS + "ud83d" + BS + "ude00\"";
        assertEquals(Character.toString(0x1F600), Json.parse(json));
    }

    @Test
    void restrictedInputIsRefused() {
        for (String bad : List.of("1.5", "1e3", "{\"a\":1,\"a\":2}", "\"" + BS + "ud83d\"", "[1,]", "{} x", "\"a\tb\"", "01", "\"" + BS + "u12G4\"")) {
            assertThrows(Json.SyntaxException.class, () -> Json.parse(bad), bad);
        }
    }

    @Test
    void canonicalRefusesNonIntegerNumbers() {
        assertThrows(IllegalArgumentException.class, () -> Json.canonical(List.of(1.5)));
    }
}
