// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.nebularis.lattice.persistence.TestSupport.operation;
import static org.nebularis.lattice.persistence.TestSupport.values;

import java.util.List;
import org.junit.jupiter.api.Test;

/** The text that fills a payload slot under each payload encoding. */
class RowsEncodingTest {
    private static final String REPLACE = "cas-replace-named-graph-patch-log";
    private static final Iri R = Iri.of("urn:example:r"), P = Iri.of("urn:example:p");

    private static Triple t(String o) { return new Triple(R, P, Iri.of(o)); }

    @Test void rowsAreSortedWithNoDuplicate() {
        Payload p = Payload.of(t("urn:example:b"), t("urn:example:a"), t("urn:example:b"));
        assertEquals("(<urn:example:r> <urn:example:p> <urn:example:a>)\n(<urn:example:r> <urn:example:p> <urn:example:b>)", p.rows());
        assertEquals("", Payload.of().rows());
    }

    @Test void literalsRenderInARowAsInSparql() {
        Triple lang = new Triple(R, P, new Lit("chat", null, "fr"));
        Triple typed = new Triple(R, P, new Lit("7", "http://www.w3.org/2001/XMLSchema#integer", null));
        assertEquals("(<urn:example:r> <urn:example:p> \"chat\"@fr)", lang.row());
        assertEquals("(<urn:example:r> <urn:example:p> \"7\"^^<http://www.w3.org/2001/XMLSchema#integer>)", typed.row());
        for (Triple x : List.of(lang, typed)) assertEquals(x.sparql(), x.row().substring(0, x.row().length() - 1).substring(1) + " .");
    }

    @Test void aGroundFixtureFillsAsTriples() {
        var replace = operation("baseline-whole-state", REPLACE);
        assertEquals("GroundNTriples", replace.payload().encoding());
        Payload p = Payload.of(t("urn:example:a"), t("urn:example:b"));
        assertEquals(p.sparql(), Payload.slotText(replace, "payloadTriples", p));
    }

    @Test void aRowsContractFillsAsRows() {
        var ground = operation("baseline-whole-state", REPLACE);
        var c = ground.payload();
        var rows = ground.withPayload(new PayloadContract(c.parameter(), c.root(), c.edges(), c.shape(), c.recordClasses(), "TripleRows"));
        Payload p = Payload.of(t("urn:example:a"), t("urn:example:b"));
        assertEquals(p.rows(), Payload.slotText(rows, "payloadTriples", p));
        assertEquals("TripleRows", rows.payload().withEdges(c.edges()).encoding());
        Rows events = Rows.of();
        assertEquals(events.sparql(), Payload.slotText(rows, "eventRows", events));
        assertThrows(PayloadException.class, () -> Payload.slotText(rows, "payloadTriples", "text"));
    }

    @Test void theDigestDoesNotDependOnTheEncoding() {
        var ground = operation("baseline-whole-state", REPLACE);
        var c = ground.payload();
        var rows = ground.withPayload(new PayloadContract(c.parameter(), c.root(), c.edges(), c.shape(), c.recordClasses(), "TripleRows"));
        var v = values("root", R, "expectedSeq", 3, "payloadTriples", Payload.of(t("urn:example:a"), t("urn:example:b")),
            "assertTriples", Payload.of(t("urn:example:b")), "retractTriples", Payload.of());
        assertEquals(RequestDigest.requestDigest(ground, v), RequestDigest.requestDigest(rows, v));
    }

    @Test void aProfileWithARowsReplaceIsReadWithItsEncoding() {
        var ops = OperationContract.read(TestSupport.profiles().get("replace-form-rows"));
        var invoice = ops.stream().filter(o -> o.templateId().equals("cas-replace-named-graph-rows-patch-log")).toList();
        var memo = ops.stream().filter(o -> o.templateId().equals("cas-replace-named-graph-patch-log")).toList();
        assertEquals(1, invoice.size());
        assertEquals(1, memo.size());
        assertEquals("TripleRows", invoice.get(0).payload().encoding());
        assertEquals("GroundNTriples", memo.get(0).payload().encoding());
        Payload p = Payload.of(t("urn:example:a"));
        assertEquals(p.rows(), Payload.slotText(invoice.get(0), "payloadTriples", p));
        assertEquals(p.sparql(), Payload.slotText(memo.get(0), "payloadTriples", p));
    }
}
