// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.nebularis.lattice.persistence.TestSupport.codes;
import static org.nebularis.lattice.persistence.TestSupport.operation;
import static org.nebularis.lattice.persistence.TestSupport.values;
import static org.nebularis.lattice.persistence.TestSupport.with;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;

/** The payload bound, the caller check and the audit outcome, over compiled profiles read by the library alone. */
class CheckTest {
    static final String EX = "https://example.org/projects#";
    static final String XSD = "http://www.w3.org/2001/XMLSchema#";
    static final String XSD_LONG = XSD + "long";
    static final String XSD_DATETIME = XSD + "dateTime";

    static Iri iri(String x) { return Iri.of(x.contains(":") ? x : EX + x); }

    static Triple t(String s, String p, Term o) { return new Triple(iri(s), iri(p), o); }

    static Triple t(String s, String p, String o) { return t(s, p, iri(o)); }

    static OperationContract replace() { return operation("composite-project-ownership", "cas-replace-composite-property-patch-log"); }

    static Map<String, Object> request(Object... over) {
        Map<String, Object> base = values(
            "root", iri("urn:p1"), "epoch", 1, "expectedSeq", 3, "nextSeq", 4, "newRev", iri("urn:rev:4"), "txnId", iri("urn:txn:1"), "requestDigest", "0".repeat(64),
            "assertTriples", Payload.of(), "retractTriples", Payload.of(),
            "payloadTriples", Payload.of(t("urn:p1", "name", new Lit("A")), t("urn:p1", "hasMilestone", "urn:m1"), t("urn:m1", "due", new Lit("2026-01-01", XSD + "date", null))));
        return with(base, over);
    }

    static List<String> codesOf(OperationContract op, Map<String, Object> v) { return CallerCheck.refusals(op, v).stream().map(Refusal::code).toList(); }

    // ---- the payload bound

    @Test void aPayloadWithinTheAggregatePasses() { assertEquals(List.of(), CallerCheck.refusals(replace(), request())); }

    @Test void aSubjectOutsideTheAggregateIsRefusedAndNamed() {
        var stray = Payload.of(t("urn:p1", "name", new Lit("A")), t("urn:other", "name", new Lit("B")));
        var found = CallerCheck.refusals(replace(), request("payloadTriples", stray));
        assertEquals(List.of("PayloadOutsideBound"), found.stream().map(Refusal::code).toList());
        assertTrue(found.get(0).reason().contains("urn:other"));
        assertEquals(List.of(iri("urn:other")), Bound.outsideBound(replace().payload(), iri("urn:p1"), stray));
    }

    @Test void aNodeReachedOnlyThroughAReferenceEdgeIsOutside() {
        var p = Payload.of(t("urn:p1", "forClient", "urn:org"), t("urn:org", "name", new Lit("Org")));
        assertEquals(List.of(iri("urn:org")), Bound.outsideBound(replace().payload(), iri("urn:p1"), p));
    }

    @Test void theWalkFollowsInverseRecursiveAndNestedEdges() {
        var p = Payload.of(
            t("urn:p1", "hasMilestone", "urn:m1"), t("urn:m1", "hasTask", "urn:t1"), t("urn:t1", "hasSubtask", "urn:t2"),
            t("urn:t2", "hasSubtask", "urn:t3"), t("urn:t3", "attachment", "urn:d1"), t("urn:d1", "title", new Lit("x")),
            t("urn:c1", "onTask", "urn:t3"), t("urn:c1", "text", new Lit("hello")));
        assertEquals(List.of(), Bound.outsideBound(replace().payload(), iri("urn:p1"), p));
        var q = Payload.of(t("urn:p1", "hasMilestone", "urn:m1"), t("urn:c1", "onTask", "urn:t9"), t("urn:c1", "text", new Lit("hello")));
        assertEquals(Set.of(iri("urn:c1")), new HashSet<>(Bound.outsideBound(replace().payload(), iri("urn:p1"), q)));
    }

    @Test void aCycleTerminates() {
        var p = Payload.of(t("urn:p1", "hasMilestone", "urn:m1"), t("urn:m1", "hasTask", "urn:t1"), t("urn:t1", "hasSubtask", "urn:t1"));
        assertEquals(List.of(), Bound.outsideBound(replace().payload(), iri("urn:p1"), p));
    }

    @Test void aFamilyWithNoShapeBoundsNothing() {
        var create = operation("baseline-single-class", "create-if-absent-named-graph-patch-log");
        assertNull(create.payload().shape());
        assertEquals(List.of(), Bound.outsideBound(create.payload(), iri("urn:a"), Payload.of(t("urn:z", "name", new Lit("x")))));
    }

    // ---- the parameters

    @Test void aMissingAndAnUnknownParameterAreNamed() {
        var v = request("epock", 1);
        v.remove("epoch");
        var got = CallerCheck.refusals(replace(), v).stream().map(r -> r.code() + ":" + r.where()).collect(Collectors.toSet());
        assertEquals(Set.of("MissingParameter:epoch", "UnknownParameter:epock"), got);
    }

    static List<Object> notLongs() {
        return List.of(new Lit("1", XSD + "integer", null), NodeFactory.createLiteralDT("1", XSDDatatype.XSDinteger), NodeFactory.createLiteralString("1"));
    }

    static List<Object> longs() {
        return List.of(1, 1L, new Lit("1", XSD_LONG, null), NodeFactory.createLiteralDT("1", XSDDatatype.XSDlong));
    }

    @ParameterizedTest @MethodSource("notLongs")
    void anEpochThatIsNotExactlyXsdLongIsRefused(Object epoch) { assertEquals(List.of("NotXsdLong"), codesOf(replace(), request("epoch", epoch))); }

    @ParameterizedTest @MethodSource("longs")
    void anXsdLongInAnyFormPasses(Object epoch) { assertEquals(List.of(), CallerCheck.refusals(replace(), request("epoch", epoch))); }

    @Test void anIllTypedOrMisplacedLongIsRefused() {
        assertEquals(List.of("IllTypedLiteral"), codesOf(replace(), request("epoch", new Lit("abc", XSD_LONG, null))));
        assertEquals(List.of("IllTypedLiteral"), codesOf(replace(), request("epoch", BigInteger.TWO.pow(63))));
        assertEquals(List.of("WrongKind"), codesOf(replace(), request("epoch", true)));
        assertEquals(List.of("WrongKind"), codesOf(replace(), request("epoch", iri("urn:x"))));
        assertEquals(List.of("WrongKind"), codesOf(replace(), request("epoch", "1")));
        assertEquals(List.of("WrongKind"), codesOf(replace(), request("epoch", 1.0)));
    }

    @Test void aLiteralIsNotAnIriAndAnIriIsNotALiteral() {
        assertEquals("WrongKind", codesOf(replace(), request("root", new Lit("urn:p1"))).get(0));
        assertTrue(CallerCheck.refusals(replace(), request("root", 42)).stream().anyMatch(r -> r.code().equals("WrongKind") && r.where().equals("root")));
    }

    @Test void aDigestIsSixtyFourLowerCaseHexCharacters() { assertEquals(List.of("WrongKind"), codesOf(replace(), request("requestDigest", "ABC"))); }

    @Test void aBareStringIsNotAPayload() {
        assertEquals(List.of("WrongKind"), codesOf(replace(), request("payloadTriples", "<urn:a> <urn:b> <urn:c> .")));
    }

    @Test void theCheckThrowsWithEveryReason() {
        var e = assertThrows(CallerCheckException.class, () -> CallerCheck.check(replace(),
            request("epoch", NodeFactory.createLiteralDT("1", XSDDatatype.XSDinteger), "payloadTriples", Payload.of(t("urn:z", "name", new Lit("x"))))));
        assertEquals(Set.of("NotXsdLong", "PayloadOutsideBound"), e.refusals().stream().map(Refusal::code).collect(Collectors.toSet()));
        assertTrue(e.getMessage().contains("refused before sending"));
    }

    // ---- a caller-named graph

    @Test void theNamingRuleIsReadFromTheBindingsOfTheProfile() {
        var named = operation("baseline-single-class", "cas-replace-named-graph-patch-log");
        assertTrue(named.parameter("g").isEmpty());
        assertEquals("urn:g:loan-application/urn%3Aa", CallerCheck.graphName(named, iri("urn:a")));
    }

    @Test void aCallerNamedGraphMustEqualTheRule() {
        var base = operation("baseline-single-class", "cas-replace-named-graph-patch-log");
        List<ParameterContract> params = new ArrayList<>(base.parameters());
        params.add(new ParameterContract("g", "Iri", true, true, false));
        List<Binding> bindings = new ArrayList<>(base.bindings().stream().filter(b -> !b.name().equals("graphPrefix") && !b.name().equals("graphSuffix")).toList());
        bindings.add(new Binding("graphPrefix", "\"urn:g:loan/\""));
        bindings.add(new Binding("graphSuffix", "\"\""));
        var named = base.withParameters(params).withBindings(bindings);
        var root = iri("urn:a/b?c");
        assertEquals("urn:g:loan/urn%3Aa%2Fb%3Fc", CallerCheck.graphName(named, root));
        assertEquals(0, CallerCheck.refusals(named, values("root", root, "g", iri("urn:g:loan/urn%3Aa%2Fb%3Fc"))).stream().filter(r -> r.code().equals("GraphNameMismatch")).count());
        assertEquals(1, CallerCheck.refusals(named, values("root", root, "g", iri("urn:g:loan/urn:a/b?c"))).stream().filter(r -> r.code().equals("GraphNameMismatch")).count());
    }

    @Test void theGraphNameEncodesNonAsciiAsUtf8() {
        var base = operation("baseline-single-class", "cas-replace-named-graph-patch-log");
        var named = base.withBindings(List.of(new Binding("graphPrefix", "\"urn:g:\""), new Binding("graphSuffix", "\"\"")));
        assertEquals("urn:g:urn%3Ax-%C3%A9-%F0%9F%98%80_.~", CallerCheck.graphName(named, Iri.of("urn:x-\u00e9-\uD83D\uDE00_.~")));
    }

    // ---- the log graphs and the audit outcome

    static OperationContract gap() { return operation("baseline-single-class", "gap-scan-audit"); }

    @Test void anEmptyLogGraphsIsRefusedUnlessTheCallerAllowsIt() {
        assertEquals(List.of("EmptyLogGraphs"), codesOf(gap(), values("logGraphs", List.of())));
        assertEquals(List.of(), CallerCheck.refusals(gap(), values("logGraphs", List.of()), CallerCheck.Options.none().allowEmptyLogGraphs(true)));
        assertEquals(List.of(), CallerCheck.refusals(gap(), values("logGraphs", List.of(iri("urn:g:txlog/2026-10")))));
        assertEquals(List.of("LogGraphNotIri"), codesOf(gap(), values("logGraphs", List.of("not an iri"))));
        assertEquals(List.of("MissingParameter"), codesOf(gap(), values()));
    }

    @Test void theOutcomeHasThreeValues() {
        List<String> row = List.of("row");
        assertEquals(AuditOutcome.FAILED, Audit.outcome(row, null, null));
        assertEquals(AuditOutcome.CLEAN, Audit.outcome(List.of(), List.of(iri("urn:g:a")), 7L));
        assertEquals(AuditOutcome.NOTHING_EXAMINED, Audit.outcome(List.of(), List.of(), null));
        assertEquals(AuditOutcome.NOTHING_EXAMINED, Audit.outcome(List.of(), List.of(iri("urn:g:a")), 0L));
        assertEquals(AuditOutcome.CLEAN, Audit.outcome(List.of(), null, null));
        assertEquals(AuditOutcome.FAILED, Audit.outcome(row, List.of(), null));
    }

    @Test void theProfileDeclaresWhatAnAuditExamines() {
        var ops = OperationContract.read(TestSupport.profiles().get("baseline-single-class")).stream().collect(Collectors.toMap(OperationContract::templateId, o -> o));
        assertEquals("logGraphs", ops.get("gap-scan-audit").examines());
        assertNull(ops.get("fork-detection-audit").examines());
        assertTrue(ops.values().stream().filter(o -> o.templateId().endsWith("-audit")).allMatch(o -> o.outcomes().equals(List.of("Clean", "Failed", "NothingExamined"))));
        assertEquals(List.of(), ops.get("create-if-absent-named-graph-patch-log").outcomes());
    }

    static final class FakeClient implements SelectClient {
        final List<Map<String, Object>> rows, counted;
        final List<String> seen = new ArrayList<>();

        FakeClient(List<Map<String, Object>> rows, List<Map<String, Object>> counted) { this.rows = rows; this.counted = counted; }

        @Override public List<Map<String, Object>> select(String query) {
            seen.add(query);
            return query.startsWith("SELECT (COUNT(?r)") ? counted : rows;
        }
    }

    @Test void runAuditReportsNothingExaminedForAnEmptyRegistryAndForBucketsWithNoReceipt() {
        String query = "SELECT * WHERE { VALUES ?log { <urn:g:txlog/pinned> {{{logGraphs}}} } }";
        var graphs = List.of(iri("urn:g:txlog/2026-10"));
        assertEquals(AuditOutcome.NOTHING_EXAMINED, Audit.run(new FakeClient(List.of(), List.of()), gap(), query, List.of()).outcome());
        assertEquals(AuditOutcome.NOTHING_EXAMINED, Audit.run(new FakeClient(List.of(), List.of(Map.of("n", "0"))), gap(), query, graphs).outcome());
        var client = new FakeClient(List.of(), List.of(Map.of("n", "12")));
        assertEquals(AuditOutcome.CLEAN, Audit.run(client, gap(), query, graphs).outcome());
        assertTrue(client.seen.get(0).contains("<urn:g:txlog/2026-10>") && !client.seen.get(0).contains("{{{"));
        assertEquals(AuditOutcome.FAILED, Audit.run(new FakeClient(List.of(Map.of("target", "x")), List.of()), gap(), query, graphs).outcome());
        assertThrows(IllegalArgumentException.class, () -> Audit.run(new FakeClient(List.of(), List.of()), gap(), query, null));
    }

    @Test void theExaminedQueryCountsThePinnedGraphAndTheListedOnes() {
        String text = Audit.examinedQuery(gap(), List.of(iri("urn:g:a")));
        assertTrue(text.contains("<urn:g:txlog/pinned> <urn:g:a>"));
        assertEquals("<urn:g:a>", Audit.registryText(List.of(iri("urn:g:a"))));
    }

    // ---- events

    static OperationContract append() { return operation("append-stream-dataset-guard", "append-event-dataset-guard"); }

    static EventRow row(int n, String event, Integer seq) {
        return new EventRow(iri(event != null ? event : "urn:ev:" + n), iri("urn:type:Opened"), seq != null ? seq : n, new Lit("2026-10-20T00:00:00Z", XSD_DATETIME, null));
    }

    static Map<String, Object> events(Object... over) {
        return with(values("stream", iri("urn:s"), "epoch", 1, "revBase", "urn:rev:", "txnId", iri("urn:txn:1"), "requestDigest", "0".repeat(64),
            "eventRows", Rows.of(row(1, null, null), row(2, null, null)),
            "eventTriples", Payload.of(t("urn:ev:1", "about", "urn:agg"), t("urn:ev:2/part/a", "note", new Lit("x")))), over);
    }

    @Test void anEventMayNameAnAggregateAndNeverDescribeOne() {
        assertEquals(List.of(), CallerCheck.refusals(append(), events()));
        var found = CallerCheck.refusals(append(), events("eventTriples", Payload.of(t("urn:agg", "name", new Lit("changed")))));
        assertEquals(List.of("EventOutsideBound"), found.stream().map(Refusal::code).toList());
        assertTrue(found.get(0).reason().contains("urn:agg"));
        // a prefix of the name is not a part
        assertEquals(List.of("EventOutsideBound"), codesOf(append(), events("eventTriples", Payload.of(t("urn:ev:10", "x", new Lit("y"))))));
        assertEquals(List.of(), Bound.outsideEvents(List.of(iri("urn:ev:1")), Payload.of(t("urn:ev:1/part/a/b", "p", new Lit("v")))));
    }

    @Test void theRowsOfABatch() {
        assertEquals(List.of("NoEvents"), codesOf(append(), events("eventRows", Rows.of(), "eventTriples", Payload.of())));
        assertEquals(List.of("DuplicateEvent"), codesOf(append(), events("eventRows", Rows.of(row(1, null, null), row(2, "urn:ev:1", null)), "eventTriples", Payload.of())));
        assertEquals(List.of("DuplicateOpSeq"), codesOf(append(), events("eventRows", Rows.of(row(1, null, null), row(2, null, 1)), "eventTriples", Payload.of())));
    }

    // ---- reference modes (TD-67)

    static OperationContract pinned() {
        var r = replace();
        var edges = r.payload().edges().stream().map(e -> e.predicate().equals(EX + "forClient") ? e.withReferenceMode("Pinned") : e).toList();
        return r.withPayload(r.payload().withEdges(edges));
    }

    @Test void anObjectOnAPinnedEdgeMustBeAVersionAndOnAnIdentityEdgeMustNotBe() {
        var versions = Map.of(EX + "org/v2", true, EX + "org", false);
        var options = CallerCheck.Options.none().versionOf(x -> versions.getOrDefault(x.value(), false));
        var op = pinned();
        assertEquals(List.of(), CallerCheck.refusals(op, request("payloadTriples", Payload.of(t("urn:p1", "forClient", iri(EX + "org/v2")))), options));
        var byIdentity = Payload.of(t("urn:p1", "forClient", iri(EX + "org")));
        assertEquals(List.of("ReferenceModeViolation"), CallerCheck.refusals(op, request("payloadTriples", byIdentity), options).stream().map(Refusal::code).toList());
        var unknown = Payload.of(t("urn:p1", "forClient", iri("urn:never-seen")));
        assertEquals(List.of("ReferenceModeViolation"), CallerCheck.refusals(op, request("payloadTriples", unknown), options).stream().map(Refusal::code).toList());
        var versionOnIdentity = Payload.of(t("urn:p1", "hasMilestone", "urn:m1"), t("urn:m1", "hasTask", "urn:t1"), t("urn:t1", "assignee", iri(EX + "org/v2")));
        assertEquals(List.of("ReferenceModeViolation"), CallerCheck.refusals(op, request("payloadTriples", versionOnIdentity), options).stream().map(Refusal::code).toList());
        // without a classifier the mode is not checked
        assertEquals(List.of(), CallerCheck.refusals(op, request("payloadTriples", byIdentity)));
    }

    // ---- delta membership checkpoints

    @Test void theRootOfANewVersionIsTheVersion() {
        assertEquals("newVersion", operation("write-discipline-delta-membership", "append-version-delta-dataset-guard").payload().root());
    }

    @Test void aCheckpointListsEveryMemberAndSaysSo() {
        var delta = operation("write-discipline-delta-membership", "append-version-delta-dataset-guard");
        var prop = iri("https://example.org/location#hasLocation");
        var version = iri("urn:v:17");
        var members = Set.of(iri("urn:loc:1"), iri("urn:loc:2"));
        var mark = new Triple(version, Iri.of(Namespaces.PAT + "checkpoint"), new Lit("true", XSD + "boolean", null));
        var listed = new ArrayList<Triple>();
        members.forEach(m -> listed.add(new Triple(version, prop, m)));
        var full = Payload.of(java.util.stream.Stream.concat(listed.stream(), java.util.stream.Stream.of(mark)).toArray(Triple[]::new));
        var partial = Payload.of(new Triple(version, prop, iri("urn:loc:1")), mark);
        var unmarked = Payload.of(listed.toArray(Triple[]::new));
        var plainVersion = Payload.of(new Triple(version, iri("urn:p"), new Lit("x")));
        java.util.function.BiFunction<Payload, Boolean, List<String>> found = (payload, checkpoint) ->
            CallerCheck.refusals(delta, values("newVersion", version, "payloadTriples", payload), CallerCheck.Options.none().membership(new Membership(prop, members, checkpoint)))
                .stream().map(Refusal::code).filter(c -> c.equals("CheckpointNotFull") || c.equals("UnexpectedFullList")).toList();
        assertEquals(List.of(), found.apply(full, true));
        assertEquals(List.of("CheckpointNotFull"), found.apply(partial, true));
        assertEquals(List.of("CheckpointNotFull"), found.apply(unmarked, true));
        assertEquals(List.of(), found.apply(plainVersion, false));
        assertEquals(List.of("UnexpectedFullList"), found.apply(full, false));
    }
}
