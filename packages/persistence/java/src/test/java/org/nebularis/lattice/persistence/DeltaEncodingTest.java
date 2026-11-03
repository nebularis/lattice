// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.nebularis.lattice.persistence.TestSupport.get;
import static org.nebularis.lattice.persistence.TestSupport.list;
import static org.nebularis.lattice.persistence.TestSupport.operation;
import static org.nebularis.lattice.persistence.TestSupport.str;
import static org.nebularis.lattice.persistence.TestSupport.values;
import static org.nebularis.lattice.persistence.TestSupport.vectors;
import static org.nebularis.lattice.persistence.TestSupport.with;

import java.util.List;
import java.util.Map;
import org.apache.jena.atlas.json.JsonValue;
import org.junit.jupiter.api.Test;

/**
 * DR2: the delta replace (dal:ChangedTriples) in the caller library. Its request carries the triples retracted and asserted and no whole state, so its
 * digest has no payload part and the caller check refuses an overlap and an empty delta, and checks the aggregate only against the next state the caller
 * passes (obligation 8 of tools/persistence/README.md). Mirrors the Python library's test_delta_encoding.py. Test IDs are DR2-Ln.
 */
class DeltaEncodingTest {
    static final String EX = "https://example.org/projects#";

    static Iri iri(String x) { return Iri.of(x.contains(":") ? x : EX + x); }

    static Triple t(String s, String p, Term o) { return new Triple(iri(s), iri(p), o); }

    static Triple t(String s, String p, String o) { return t(s, p, iri(o)); }

    static OperationContract named() { return operation("replace-encoding", "cas-replace-named-graph-delta-patch-log"); }

    static OperationContract composite() { return operation("composite-project-ownership", "cas-replace-composite-property-delta-patch-log"); }

    static Map<String, Object> request(List<Triple> add, List<Triple> delete) {
        return values(
            "root", iri("urn:p1"), "epoch", 1, "expectedSeq", 3, "nextSeq", 4, "newRev", iri("urn:rev:4"), "txnId", iri("urn:txn:1"), "requestDigest", "0".repeat(64),
            "assertTriples", new Payload(new java.util.HashSet<>(add)), "retractTriples", new Payload(new java.util.HashSet<>(delete)));
    }

    static List<String> codes(OperationContract op, Map<String, Object> v, CallerCheck.Options options) {
        return CallerCheck.refusals(op, v, options).stream().map(Refusal::code).toList();
    }

    static List<String> codes(OperationContract op, Map<String, Object> v) { return codes(op, v, CallerCheck.Options.none()); }

    static final Triple A = t("urn:p1", "name", new Lit("A")), B = t("urn:p1", "name", new Lit("B"));

    @Test void theContractIsADeltaReplaceWhoseDigestHasTheChangeAndNoPayloadPart() {
        var op = named();
        assertEquals(OperationKind.DELTA_REPLACE, op.kind());
        assertEquals("assertTriples", op.payload().parameter());
        assertEquals("GroundNTriples", op.payload().encoding());
        assertEquals(List.of("OperationKindPart", "TargetPart", "ExpectedSeqPart", "AddPart", "DelPart"), op.digest().parts().stream().map(DigestPart::role).toList());
        assertEquals(List.of("assertTriples"), op.digest().parts().get(3).sources());
        assertTrue(op.parameter("payloadTriples").isEmpty());
    }

    @Test void theRequestDigestOfADeltaIsTheOpensslVector() {
        JsonValue v = list(get(vectors(), "digests")).stream().filter(d -> str(get(d, "id")).equals("digest-delta-replace")).findFirst().orElseThrow();
        Payload add = part(v, "AddPart"), delete = part(v, "DelPart");
        var values = values("root", str(get(v, "target")), "expectedSeq", get(v, "expected").getAsNumber().value().longValue(), "assertTriples", add, "retractTriples", delete);
        assertEquals(str(get(v, "sha256")), RequestDigest.requestDigest(named(), values));
        assertNotEquals(str(get(v, "sha256")), RequestDigest.requestDigest(named(), with(values, "assertTriples", delete, "retractTriples", add)), "a triple's role is part of what is hashed");
    }

    static Payload part(JsonValue v, String role) {
        JsonValue p = list(get(v, "parts")).stream().filter(x -> str(get(x, "role")).equals(role)).findFirst().orElseThrow();
        return ConformanceTest.payload(list(get(p, "triples")));
    }

    @Test void aDeltaWithAChangePassesWithoutTheNextStateAndTheBoundIsNotRunOverTheAssertedTriples() {
        assertEquals(List.of(), CallerCheck.refusals(named(), request(List.of(B), List.of(A))));
        assertEquals(List.of(), CallerCheck.refusals(composite(), request(List.of(t("urn:t9", "assignee", "urn:alice")), List.of())));
    }

    @Test void anOverlapIsRefusedAndNamed() {
        var found = CallerCheck.refusals(named(), request(List.of(A, B), List.of(A)));
        assertEquals(List.of("DeltaOverlap:assertTriples"), found.stream().map(r -> r.code() + ":" + r.where()).toList());
        assertThrows(CallerCheckException.class, () -> CallerCheck.check(named(), request(List.of(A), List.of(A))));
    }

    @Test void aDeltaThatAssertsAndRetractsNothingIsRefusedAndOneThatDoesEitherIsNot() {
        assertEquals(List.of("EmptyDelta"), codes(named(), request(List.of(), List.of())));
        assertEquals(List.of(), codes(named(), request(List.of(A), List.of())));
        assertEquals(List.of(), codes(named(), request(List.of(), List.of(A))));
    }

    @Test void theNextStateHoldsEveryAssertedTripleAndNoRetractedOne() {
        var state = Payload.of(B, t("urn:p1", "note", new Lit("k")));
        var options = CallerCheck.Options.none().nextState(state);
        assertEquals(List.of(), CallerCheck.refusals(named(), request(List.of(B), List.of(A)), options));
        assertEquals(List.of("AssertOutsideNextState"), codes(named(), request(List.of(B, t("urn:p1", "name", new Lit("C"))), List.of(A)), options));
        assertEquals(List.of("RetractInNextState"), codes(named(), request(List.of(B), List.of(A)), CallerCheck.Options.none().nextState(Payload.of(B, A))));
    }

    @Test void theNextStateIsHeldToTheBoundaryAndAWholeStateReplaceIgnoresTheOption() {
        var inside = Payload.of(B, t("urn:p1", "hasMilestone", "urn:m1"), t("urn:m1", "name", new Lit("M")));
        assertEquals(List.of(), CallerCheck.refusals(composite(), request(List.of(B), List.of()), CallerCheck.Options.none().nextState(inside)));
        var stray = Payload.of(t("urn:other", "name", new Lit("X")));
        var strayState = new Payload(new java.util.HashSet<>(inside.triples()) {{ addAll(stray.triples()); }});
        var found = CallerCheck.refusals(composite(), request(List.of(B), List.of()), CallerCheck.Options.none().nextState(strayState));
        assertEquals(List.of("PayloadOutsideBound:nextState"), found.stream().map(r -> r.code() + ":" + r.where()).toList());
        var whole = operation("composite-whole-state", "cas-replace-composite-property-patch-log");
        var wholeRequest = with(request(List.of(), List.of()), "payloadTriples", inside);
        assertEquals(List.of(), CallerCheck.refusals(whole, wholeRequest, CallerCheck.Options.none().nextState(strayState)));
    }

    @Test void theReferenceModesOfTheNextStateAreCheckedWhereTheCallerCanSayWhatIsAVersion() {
        var r = composite();
        var edges = r.payload().edges().stream().map(e -> e.predicate().equals(EX + "forClient") ? e.withReferenceMode("Pinned") : e).toList();
        var pinned = r.withPayload(r.payload().withEdges(edges));
        var versions = Map.of(EX + "org/v2", true, EX + "org", false);
        var good = Payload.of(B, t("urn:p1", "forClient", iri(EX + "org/v2")));
        var bad = Payload.of(B, t("urn:p1", "forClient", iri(EX + "org")));
        var classify = CallerCheck.Options.none().versionOf(x -> versions.getOrDefault(x.value(), false));
        assertEquals(List.of(), CallerCheck.refusals(pinned, request(List.of(B), List.of()), classify.nextState(good)));
        assertEquals(List.of("ReferenceModeViolation"), codes(pinned, request(List.of(B), List.of()), classify.nextState(bad)));
        assertEquals(List.of(), CallerCheck.refusals(pinned, request(List.of(B), List.of()), CallerCheck.Options.none().nextState(bad)), "without a classifier the mode is not checked");
    }
}
