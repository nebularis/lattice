// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writes;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;

import java.io.StringReader;
import java.time.Instant;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.junit.jupiter.api.Test;

/** MSA-F14, TD-165. A command's digest tells blank nodes apart by their own quads, and ignores their labels. */
class CodecTest {
    private static final String WS = "00000000-0000-4000-8000-000000000001";
    private static final Instant AT = Instant.parse("2026-11-19T09:00:00Z");

    private static String digest(String turtle) {
        Model m = ModelFactory.createDefaultModel().read(new StringReader("@prefix ex: <https://example.org/> . " + turtle), null, "TTL");
        return Codec.digest(Command.save(WS, "surface", 0, AT, m));
    }

    @Test
    void twoBodiesThatDifferOnlyInHowTheirBlankNodesConnectDigestApart() {
        // With every blank node read as one label, each pair has the same sorted lines.
        assertNotEquals(digest("_:x ex:p _:y . _:y ex:q \"1\" . _:z ex:q \"2\" ."),
            digest("_:x ex:p _:z . _:y ex:q \"1\" . _:z ex:q \"2\" ."), "x names the node holding 1, then the node holding 2");
        assertNotEquals(digest("ex:a ex:p _:x . ex:b ex:p _:x ."), digest("ex:a ex:p _:x . ex:b ex:p _:y ."),
            "a and b name one node, then two");
    }

    /** MSA-F15. Where a blank node names another, and where it names itself, are two bodies, however a blank node is labelled. */
    @Test
    void aBlankNodeThatNamesAnotherAndOneThatNamesItselfDigestApart() {
        assertNotEquals(digest("_:x ex:p _:y ."), digest("_:x ex:p _:x ."), "x names y, then x names itself");
    }

    @Test
    void aBodyWhoseBlankNodesAreRelabelledDigestsTheSame() {
        assertEquals(digest("_:x ex:p _:y . _:y ex:q \"1\" . _:z ex:q \"2\" ."),
            digest("_:c ex:q \"2\" . _:b ex:q \"1\" . _:a ex:p _:b ."));
    }
}
