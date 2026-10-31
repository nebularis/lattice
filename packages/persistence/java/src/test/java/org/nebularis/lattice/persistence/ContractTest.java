// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.nebularis.lattice.persistence.TestSupport.operation;
import static org.nebularis.lattice.persistence.TestSupport.values;
import static org.nebularis.lattice.persistence.TestSupport.with;

import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;

/** Reading a compiled profile's contract, and the digest of requests to its operations. */
class ContractTest {
    private static final String REPLACE = "cas-replace-named-graph-patch-log";
    private static final String XSD_DATETIME = "http://www.w3.org/2001/XMLSchema#dateTime";

    static Triple t(String s, String p, String o) { return new Triple(Iri.of(s), Iri.of(p), Iri.of(o)); }

    @Test void readsEveryOperationAndItsParameters() {
        var ops = OperationContract.read(TestSupport.profiles().get("baseline-single-class"));
        var kinds = ops.stream().map(OperationContract::kind).collect(Collectors.toSet());
        assertTrue(kinds.containsAll(List.of(OperationKind.CREATE, OperationKind.REPLACE, OperationKind.TOMBSTONE, OperationKind.AUDIT)));
        var replace = operation("baseline-single-class", REPLACE);
        assertEquals("Position", replace.parameter("expectedSeq").orElseThrow().kind());
        assertEquals("Digest", replace.parameter("requestDigest").orElseThrow().kind());
        assertEquals("payloadTriples", replace.payload().parameter());
        assertEquals("root", replace.payload().root());
        assertTrue(replace.version() >= 1);
    }

    @Test void digestPartsInOrder() {
        var replace = operation("baseline-single-class", REPLACE);
        assertEquals(List.of("OperationKindPart", "TargetPart", "ExpectedSeqPart", "PayloadPart", "AddPart", "DelPart"),
            replace.digest().parts().stream().map(DigestPart::role).toList());
        assertEquals("SHA-256", replace.digest().algorithm());
        var append = operation("append-stream-dataset-guard", "append-event-dataset-guard");
        var last = append.digest().parts().get(append.digest().parts().size() - 1);
        assertEquals("EventPart", last.role());
        assertEquals(List.of("eventRows", "eventTriples"), last.sources());
        assertNull(operation("baseline-single-class", "key-claim-write").digest());
    }

    @Test void replaceDigestFromAProfile() {
        var replace = operation("baseline-single-class", REPLACE);
        Triple a = t("urn:example:r", "urn:example:p", "urn:example:a"), b = t("urn:example:r", "urn:example:p", "urn:example:b");
        var v = values("root", Iri.of("urn:example:r"), "expectedSeq", 3, "payloadTriples", Payload.of(a, b), "assertTriples", Payload.of(b), "retractTriples", Payload.of());
        String one = RequestDigest.requestDigest(replace, v);
        assertEquals(64, one.length());
        assertEquals(one, RequestDigest.requestDigest(replace, Map.copyOf(v)));
        assertNotEquals(one, RequestDigest.requestDigest(replace, with(v, "assertTriples", Payload.of(), "retractTriples", Payload.of(b))));
        assertNotEquals(one, RequestDigest.requestDigest(replace, with(v, "expectedSeq", 4)));
        assertTrue(new String(RequestDigest.requestInput(replace, v), StandardCharsets.UTF_8).startsWith("7:Replace13:urn:example:r1:3"));
    }

    @Test void appendDigestMergesRowsAndTriplesIntoOnePart() {
        var append = operation("append-stream-dataset-guard", "append-event-dataset-guard");
        var when = new Lit("2026-10-20T10:00:00Z", XSD_DATETIME, null);
        var rows = Rows.of(new EventRow(Iri.of("urn:e:1"), Iri.of("urn:T"), 1, when));
        var v = values("stream", "urn:example:s", "eventRows", rows, "eventTriples", Payload.of(t("urn:e:1", "urn:example:p", "urn:example:o")));
        String data = new String(RequestDigest.requestInput(append, v), StandardCharsets.UTF_8);
        assertTrue(data.startsWith("6:Append13:urn:example:s0:"));
        String needle = "urn:e:1> <urn:example:p>";
        assertEquals(1, data.split(java.util.regex.Pattern.quote(needle), -1).length - 1);
        assertNotEquals(RequestDigest.requestDigest(append, with(v, "eventTriples", Payload.of())), RequestDigest.requestDigest(append, v));
    }

    @Test void aMissingSourceIsNamed() {
        var replace = operation("baseline-single-class", REPLACE);
        var e = assertThrows(DigestException.class, () -> RequestDigest.requestDigest(replace,
            values("root", "urn:example:r", "expectedSeq", 1, "payloadTriples", Payload.of(), "assertTriples", Payload.of())));
        assertTrue(e.getMessage().contains("retractTriples"));
    }

    @Test void aBareStringIsNotAPayload() {
        var replace = operation("baseline-single-class", REPLACE);
        var e = assertThrows(DigestException.class, () -> RequestDigest.requestDigest(replace,
            values("root", "urn:example:r", "expectedSeq", 1, "payloadTriples", "<urn:a> <urn:b> <urn:c> .", "assertTriples", Payload.of(), "retractTriples", Payload.of())));
        assertTrue(e.getMessage().contains("Payload"));
    }

    @Test void anOperationWithoutADigestRefuses() {
        assertThrows(DigestException.class, () -> RequestDigest.requestDigest(operation("baseline-single-class", "key-claim-write"), Map.of()));
    }
}
