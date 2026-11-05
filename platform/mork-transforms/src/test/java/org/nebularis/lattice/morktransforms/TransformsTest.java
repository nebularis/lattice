// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.morktransforms;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class TransformsTest {
    private static final String XSLT = "<xsl:stylesheet version=\"3.0\" xmlns:xsl=\"http://www.w3.org/1999/XSL/Transform\">"
            + "<xsl:output method=\"text\"/><xsl:template match=\"/a\">line <xsl:value-of select=\"@n\"/><xsl:text>&#10;</xsl:text></xsl:template></xsl:stylesheet>";

    @Test
    void xsltWritesTextFromAnElement() throws Exception {
        assertEquals("line 7\n", Transforms.xslt(XSLT, "<a n=\"7\"/>"));
    }

    @Test
    void xsltRefusesADoctype() {
        String xml = "<!DOCTYPE a [<!ENTITY e SYSTEM \"file:///etc/hostname\">]><a n=\"&e;\"/>";
        TransformException e = assertThrows(TransformException.class, () -> Transforms.xslt(XSLT, xml));
        assertTrue(!e.getMessage().contains("etc/hostname"));
    }

    @Test
    void joltShift() throws Exception {
        String chain = "[{\"operation\":\"shift\",\"spec\":{\"a\":\"b\"}}]";
        assertEquals("{\"b\":1}", Transforms.jolt(chain, "{\"a\":1}"));
    }

    @Test
    void malformedChainIsRefused() {
        assertThrows(TransformException.class, () -> Transforms.jolt("[{\"operation\":\"nope\"}]", "{}"));
        assertThrows(TransformException.class, () -> Transforms.jolt("not json", "{}"));
    }

    // A shift can write a key that begins with @ when the right side escapes it. In JSON the right side is "\\@id", the string \@id.
    @Test
    void shiftWritesAtKeyWhenEscaped() throws Exception {
        String chain = "[{\"operation\":\"shift\",\"spec\":{\"id\":\"\\\\@id\",\"t\":\"\\\\@type\"}}]";
        assertEquals("{\"@id\":\"urn:x\",\"@type\":\"Foo\"}", Transforms.jolt(chain, "{\"id\":\"urn:x\",\"t\":\"Foo\"}"));
    }

    // An unescaped @id on the right side is the JOLT @ path syntax, and writes nothing.
    @Test
    void shiftWithUnescapedAtWritesNothing() throws Exception {
        String chain = "[{\"operation\":\"shift\",\"spec\":{\"id\":\"@id\"}}]";
        assertEquals("null", Transforms.jolt(chain, "{\"id\":\"urn:x\"}"));
    }

    // modify-overwrite-beta cannot name @id unescaped (the chain is refused), and sets it when the key is escaped as "\\@id".
    @Test
    void modifyOverwriteBetaSetsAtKeyOnlyWhenEscaped() throws Exception {
        String bad = "[{\"operation\":\"modify-overwrite-beta\",\"spec\":{\"@id\":\"=concat('a',@(1,id))\"}}]";
        assertThrows(TransformException.class, () -> Transforms.jolt(bad, "{\"id\":\"x\"}"));
        String ok = "[{\"operation\":\"modify-overwrite-beta\",\"spec\":{\"\\\\@id\":\"=concat('a',@(1,id))\"}}]";
        assertEquals("{\"id\":\"x\",\"@id\":\"ax\"}", Transforms.jolt(ok, "{\"id\":\"x\"}"));
    }
}
