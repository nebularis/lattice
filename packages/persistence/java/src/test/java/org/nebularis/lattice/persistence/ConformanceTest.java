// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.nebularis.lattice.persistence.TestSupport.codes;
import static org.nebularis.lattice.persistence.TestSupport.get;
import static org.nebularis.lattice.persistence.TestSupport.list;
import static org.nebularis.lattice.persistence.TestSupport.str;
import static org.nebularis.lattice.persistence.TestSupport.strings;
import static org.nebularis.lattice.persistence.TestSupport.vectors;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.apache.jena.atlas.json.JsonValue;
import org.apache.jena.datatypes.BaseDatatype;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.junit.jupiter.api.Test;

/** The library against contracts/persistence/vectors.json, which verify-vectors.py checks without this library (ADR-A132 decision 4). */
class ConformanceTest {
    private static final Map<String, String> SLOT = Map.of("PayloadPart", "payloadTriples", "AddPart", "assertTriples", "DelPart", "retractTriples");

    static Term typed(JsonValue t) {
        if (t == null || t.isNull()) throw new PayloadException("UNDEF");
        if (get(t, "literal") != null) return new Lit(str(get(t, "literal")), str(get(t, "datatype")), str(get(t, "language")));
        return Iri.of(str(get(t, "iri")));
    }

    static Payload payload(List<JsonValue> triples) {
        Set<Triple> out = new HashSet<>();
        for (JsonValue t : triples) out.add(new Triple((Iri) typed(get(t, "s")), (Iri) typed(get(t, "p")), typed(get(t, "o"))));
        return new Payload(out);
    }

    static Node jenaNode(JsonValue t) {
        if (get(t, "bnode") != null) return NodeFactory.createBlankNode(str(get(t, "bnode")));
        if (get(t, "literal") != null) {
            String lex = str(get(t, "literal"));
            if (str(get(t, "language")) != null) return NodeFactory.createLiteralLang(lex, str(get(t, "language")));
            if (str(get(t, "datatype")) != null) return NodeFactory.createLiteralDT(lex, new BaseDatatype(str(get(t, "datatype"))));
            return NodeFactory.createLiteralString(lex);
        }
        return NodeFactory.createURI(str(get(t, "iri")));
    }

    static EventRow row(JsonValue r) {
        return new EventRow(Iri.of(str(get(r, "event"))), Iri.of(str(get(r, "type"))), get(r, "opSeq").getAsNumber().value().longValue(), (Lit) typed(get(r, "occurredAt")));
    }

    /** A synthetic operation for a digest vector, and the values of its request. */
    static Map.Entry<OperationContract, Map<String, Object>> operation(JsonValue v) {
        JsonValue target = get(v, "target"), expected = get(v, "expected");
        boolean hasTarget = target != null && !target.isNull() && !str(target).isEmpty();
        boolean hasExpected = expected != null && !expected.isNull();
        List<DigestPart> parts = new ArrayList<>(List.of(
            new DigestPart(1, "OperationKindPart"), new DigestPart(2, "TargetPart", hasTarget ? List.of("root") : List.of()),
            new DigestPart(3, "ExpectedSeqPart", hasExpected ? List.of("expectedSeq") : List.of())));
        Map<String, Object> values = new HashMap<>();
        values.put("root", str(target));
        values.put("expectedSeq", hasExpected ? (Object) expected.getAsNumber().value().longValue() : null);
        int order = 4;
        for (JsonValue p : list(get(v, "parts"))) {
            String role = str(get(p, "role"));
            if (role.equals("EventPart")) {
                parts.add(new DigestPart(order, "EventPart", List.of("eventRows", "eventTriples")));
                values.put("eventRows", new Rows(list(get(p, "rows")).stream().map(ConformanceTest::row).toList()));
                values.put("eventTriples", payload(list(get(p, "triples"))));
            } else {
                parts.add(new DigestPart(order, role, List.of(SLOT.get(role))));
                values.put(SLOT.get(role), payload(list(get(p, "triples"))));
            }
            order++;
        }
        var op = new OperationContract(null, str(get(v, "id")), OperationKind.of(str(get(v, "operationKind"))), 1, List.of(), null, new DigestSpec("SHA-256", parts));
        return Map.entry(op, values);
    }

    @Test void everyVectorSetIsPresent() {
        for (String set : List.of("ntriples", "refusals", "digests", "payloadChecks", "eventChecks", "callerChecks", "auditOutcomes", "referenceChecks", "checkpointChecks")) {
            assertTrue(!list(get(vectors(), set)).isEmpty(), set);
        }
    }

    @Test void everyNtriplesVector() {
        for (JsonValue v : list(get(vectors(), "ntriples"))) {
            assertEquals(strings(get(v, "canonical")), payload(list(get(v, "triples"))).lines(), str(get(v, "id")));
        }
    }

    @Test void everyRefusalVector() {
        for (JsonValue v : list(get(vectors(), "refusals"))) {
            List<org.apache.jena.graph.Triple> triples = new ArrayList<>();
            for (JsonValue t : list(get(v, "triples"))) {
                triples.add(org.apache.jena.graph.Triple.create(jenaNode(get(t, "s")), jenaNode(get(t, "p")), jenaNode(get(t, "o"))));
            }
            assertThrows(PayloadException.class, () -> Payload.ofJena(triples), str(get(v, "id")));
        }
    }

    @Test void everyDigestVector() {
        for (JsonValue v : list(get(vectors(), "digests"))) {
            var e = operation(v);
            assertEquals(str(get(v, "encodedHex")), java.util.HexFormat.of().formatHex(RequestDigest.requestInput(e.getKey(), e.getValue())), str(get(v, "id")));
            assertEquals(str(get(v, "sha256")), RequestDigest.requestDigest(e.getKey(), e.getValue()), str(get(v, "id")));
        }
    }

    @Test void digestVectorsCoverTheOperationKindsAndParts() {
        Set<String> kinds = new HashSet<>(), roles = new HashSet<>();
        for (JsonValue v : list(get(vectors(), "digests"))) {
            kinds.add(str(get(v, "operationKind")));
            for (JsonValue p : list(get(v, "parts"))) roles.add(str(get(p, "role")));
        }
        assertTrue(kinds.containsAll(Set.of("Create", "Replace", "Tombstone", "Append", "AppendVersion")));
        assertEquals(Set.of("PayloadPart", "EventPart", "AddPart", "DelPart"), roles);
    }

    @Test void partOrderIsHashed() {
        JsonValue v = list(get(vectors(), "digests")).stream().filter(d -> str(get(d, "id")).equals("digest-replace-patch-log")).findFirst().orElseThrow();
        var e = operation(v);
        List<DigestPart> parts = new ArrayList<>(e.getKey().digest().parts());
        parts.set(3, new DigestPart(4, "PayloadPart", List.of("retractTriples")));
        parts.set(5, new DigestPart(6, "DelPart", List.of("payloadTriples")));
        var swapped = new OperationContract(null, "x", e.getKey().kind(), 1, List.of(), null, new DigestSpec("SHA-256", parts));
        assertNotEquals(str(get(v, "sha256")), RequestDigest.requestDigest(swapped, e.getValue()));
    }

    // ---- the payload checks, the caller check and the audit outcome

    static PayloadContract contract(JsonValue v) {
        List<EdgeContract> edges = new ArrayList<>();
        for (JsonValue e : list(get(v, "edges"))) {
            edges.add(new EdgeContract(str(get(e, "source")), str(get(e, "predicate")), get(e, "inverse").toString().equals("true"), str(get(e, "ownership")), null,
                str(get(e, "mode")), str(get(e, "targetShape"))));
        }
        return new PayloadContract("payloadTriples", "root", edges, str(get(v, "shape")));
    }

    static OperationContract synthetic(String kind, List<ParameterContract> parameters, PayloadContract payload, List<Binding> bindings) {
        return new OperationContract(null, "vector", OperationKind.of(kind), 1, parameters, payload, null, bindings, null, List.of());
    }

    @Test void everyPayloadCheckVector() {
        for (JsonValue v : list(get(vectors(), "payloadChecks"))) {
            List<String> found = Bound.outsideBound(contract(v), Iri.of(str(get(v, "root"))), payload(list(get(v, "triples")))).stream().map(Iri::value).toList();
            assertEquals(strings(get(v, "outside")), found, str(get(v, "id")));
        }
    }

    @Test void everyEventCheckVector() {
        var op = synthetic("Append", List.of(new ParameterContract("eventRows", "Rows", true), new ParameterContract("eventTriples", "Payload", true)), null, List.of());
        for (JsonValue v : list(get(vectors(), "eventChecks"))) {
            Rows rows;
            try {
                rows = new Rows(list(get(v, "events")).stream().map(ConformanceTest::row).toList());
            } catch (PayloadException e) {
                assertEquals(List.of("UndefInRow"), strings(get(v, "refusals")), str(get(v, "id")));
                continue;
            }
            var found = CallerCheck.refusals(op, TestSupport.values("eventRows", rows, "eventTriples", payload(list(get(v, "triples")))));
            assertEquals(strings(get(v, "refusals")), codes(found), str(get(v, "id")));
        }
    }

    static Object value(JsonValue form) {
        for (String k : List.of("iri", "int", "literal", "string", "strings")) {
            JsonValue raw = get(form, k);
            if (raw == null) continue;
            return switch (k) {
                case "iri" -> Iri.of(str(raw));
                case "int" -> raw.getAsNumber().value().longValue();
                case "literal" -> new Lit(str(raw), str(get(form, "datatype")), null);
                case "string" -> str(raw);
                default -> strings(raw);
            };
        }
        throw new IllegalArgumentException(form.toString());
    }

    @Test void everyCallerCheckVector() {
        for (JsonValue v : list(get(vectors(), "callerChecks"))) {
            JsonValue o = get(v, "operation");
            List<ParameterContract> params = new ArrayList<>();
            for (JsonValue p : list(get(o, "parameters"))) {
                params.add(new ParameterContract(str(get(p, "name")), str(get(p, "kind")), get(p, "required").toString().equals("true"),
                    get(p, "equalsGraphName") != null && get(p, "equalsGraphName").toString().equals("true"), false));
            }
            List<Binding> bindings = new ArrayList<>();
            for (String k : List.of("graphPrefix", "graphSuffix")) if (get(o, k) != null) bindings.add(new Binding(k, "\"" + str(get(o, k)) + "\""));
            var op = synthetic(str(get(o, "kind")), params, null, bindings);
            Map<String, Object> values = new HashMap<>();
            for (String k : get(v, "values").getAsObject().keys()) values.put(k, value(get(get(v, "values"), k)));
            boolean allow = get(v, "allowEmptyLogGraphs") != null && get(v, "allowEmptyLogGraphs").toString().equals("true");
            var found = CallerCheck.refusals(op, values, CallerCheck.Options.none().allowEmptyLogGraphs(allow));
            assertEquals(strings(get(v, "refusals")), codes(found), str(get(v, "id")));
        }
    }

    @Test void everyAuditOutcomeVector() {
        for (JsonValue v : list(get(vectors(), "auditOutcomes"))) {
            JsonValue lg = get(v, "logGraphs"), ex = get(v, "examined");
            List<Iri> graphs = lg == null || lg.isNull() ? null : strings(lg).stream().map(Iri::of).toList();
            Long examined = ex == null || ex.isNull() ? null : ex.getAsNumber().value().longValue();
            List<String> rows = new ArrayList<>();
            for (long i = 0; i < get(v, "rows").getAsNumber().value().longValue(); i++) rows.add("row");
            assertEquals(str(get(v, "outcome")), Audit.outcome(rows, graphs, examined).value(), str(get(v, "id")));
        }
    }

    @Test void everyReferenceCheckVector() {
        for (JsonValue v : list(get(vectors(), "referenceChecks"))) {
            var op = synthetic("Replace", List.of(new ParameterContract("root", "Iri", true), new ParameterContract("payloadTriples", "Payload", true)), contract(v), List.of());
            Set<String> versions = new HashSet<>(strings(get(v, "versions")));
            var found = CallerCheck.refusals(op,
                TestSupport.values("root", Iri.of(str(get(v, "root"))), "payloadTriples", payload(list(get(v, "triples")))),
                CallerCheck.Options.none().versionOf(x -> versions.contains(x.value())));
            assertEquals(strings(get(v, "refusals")), codes(found.stream().filter(r -> r.code().equals("ReferenceModeViolation")).toList()), str(get(v, "id")));
        }
    }

    @Test void everyCheckpointVector() {
        for (JsonValue v : list(get(vectors(), "checkpointChecks"))) {
            var op = synthetic("AppendVersion", List.of(new ParameterContract("newVersion", "Iri", true), new ParameterContract("payloadTriples", "Payload", true)),
                new PayloadContract("payloadTriples", "newVersion", List.of(), null), List.of());
            var m = new Membership(Iri.of(str(get(v, "membershipProperty"))), new HashSet<>(strings(get(v, "members")).stream().map(Iri::of).toList()),
                get(v, "checkpoint").toString().equals("true"));
            var found = CallerCheck.refusals(op, TestSupport.values("newVersion", Iri.of(str(get(v, "version"))), "payloadTriples", payload(list(get(v, "triples")))),
                CallerCheck.Options.none().membership(m));
            assertEquals(strings(get(v, "refusals")), codes(found), str(get(v, "id")));
        }
    }
}
