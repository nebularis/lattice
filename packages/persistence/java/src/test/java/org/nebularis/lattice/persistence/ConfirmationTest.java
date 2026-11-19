// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.nebularis.lattice.persistence.TestSupport.get;
import static org.nebularis.lattice.persistence.TestSupport.list;
import static org.nebularis.lattice.persistence.TestSupport.str;
import static org.nebularis.lattice.persistence.TestSupport.vectors;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.apache.jena.atlas.json.JsonValue;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.sparql.core.DatasetGraph;
import org.apache.jena.sparql.core.DatasetGraphFactory;
import org.apache.jena.sparql.core.Quad;
import org.junit.jupiter.api.Test;

/** The confirmation read and its classification against contracts/persistence/vectors.json, which verify-vectors.py decides without this library. */
class ConfirmationTest {
    /** The adopter's client, over an in-memory Jena dataset that holds the quads of a vector. */
    static final class DatasetClient implements SelectClient {
        final DatasetGraph dataset = DatasetGraphFactory.create();
        final List<String> queries = new ArrayList<>();

        DatasetClient(List<JsonValue> quads) {
            for (JsonValue q : quads) {
                dataset.add(new Quad(NodeFactory.createURI(str(get(q, "graph"))), ConformanceTest.jenaNode(get(q, "s")), ConformanceTest.jenaNode(get(q, "p")),
                    ConformanceTest.jenaNode(get(q, "o"))));
            }
        }

        @Override public List<Map<String, Object>> select(String query) {
            queries.add(query);
            List<Map<String, Object>> rows = new ArrayList<>();
            try (QueryExecution qe = QueryExecutionFactory.create(query, DatasetFactory.wrap(dataset))) {
                for (var rs = qe.execSelect(); rs.hasNext();) {
                    QuerySolution s = rs.next();
                    Map<String, Object> row = new HashMap<>();
                    row.put("fact", s.getLiteral("fact").getString());
                    RDFNode value = s.get("value");
                    row.put("value", value.isLiteral() ? value.asLiteral().getLexicalForm() : value.asResource().getURI());
                    rows.add(row);
                }
            }
            return rows;
        }
    }

    static OperationContract operation(JsonValue v) {
        JsonValue o = get(v, "operation");
        OperationKind kind = OperationKind.of(str(get(o, "kind")));
        boolean claiming = kind != OperationKind.KEY_CLAIM_WRITE && kind != OperationKind.KEY_CLAIM_WRITE_DUAL;
        List<ParameterContract> parameters = claiming
            ? List.of(new ParameterContract("txnId", "Iri", true, false, false), new ParameterContract("requestDigest", "Digest", true, false, false)) : List.of();
        List<Binding> bindings = new ArrayList<>();
        get(o, "bindings").getAsObject().forEach((k, x) -> bindings.add(new Binding(k, "<" + x.getAsString().value() + ">")));
        return new OperationContract(null, str(get(o, "templateId")), kind, 1, parameters, null, null, bindings, null, List.of());
    }

    static Map<String, Object> values(JsonValue v) {
        Map<String, Object> out = new HashMap<>();
        get(v, "values").getAsObject().forEach((name, form) -> {
            if (get(form, "iri") != null) out.put(name, Iri.of(str(get(form, "iri"))));
            else if (get(form, "int") != null) out.put(name, get(form, "int").getAsNumber().value().longValue());
            else out.put(name, str(get(form, "string")));
        });
        return out;
    }

    static JsonValue vector(String id) {
        return list(get(vectors(), "confirmationChecks")).stream().filter(v -> str(get(v, "id")).equals(id)).findFirst().orElseThrow();
    }

    @Test void everyConfirmationVectorThroughAStore() {
        for (JsonValue v : list(get(vectors(), "confirmationChecks"))) {
            Confirmation got = Confirmation.run(new DatasetClient(list(get(v, "quads"))), operation(v), values(v));
            assertEquals(str(get(v, "outcome")), got.outcome().value(), str(get(v, "id")));
            assertEquals(str(get(v, "classification")), got.classification().value(), str(get(v, "id")));
            assertEquals(str(get(v, "revision")), got.revision(), str(get(v, "id")));
            assertFalse(got.reason().isEmpty(), str(get(v, "id")));
        }
    }

    @Test void theVectorsCoverEveryOutcomeAndEveryCause() {
        Set<String> outcomes = new HashSet<>(), causes = new HashSet<>();
        for (JsonValue v : list(get(vectors(), "confirmationChecks"))) {
            outcomes.add(str(get(v, "outcome")));
            causes.add(str(get(v, "classification")));
        }
        assertEquals(new HashSet<>(List.of(Outcome.values())).stream().map(Outcome::value).collect(java.util.stream.Collectors.toSet()), outcomes);
        assertEquals(new HashSet<>(List.of(Classification.values())).stream().map(Classification::value).collect(java.util.stream.Collectors.toSet()), causes);
    }

    @Test void eachClassificationGivesItsOutcome() {
        for (Classification c : Classification.values()) {
            Outcome expected = c == Classification.APPLIED ? Outcome.APPLIED : c == Classification.IDEMPOTENCY_KEY_REUSE ? Outcome.REFUSED : Outcome.LOST_RACE;
            assertEquals(expected, c.outcome(), c.value());
        }
    }

    @Test void theReadAsksOnlyWhatTheOperationsGuardsTest() {
        JsonValue replace = vector("cf-epoch-changed");
        String query = Confirmation.query(operation(replace), values(replace));
        assertTrue(query.startsWith("SELECT ?fact ?value WHERE"));
        for (String fact : List.of("claimRev", "claimDigest", "datasetEpoch", "rowSeq", "rowEpoch", "rowDeleted")) assertTrue(query.contains("\"" + fact + "\""), fact);
        assertFalse(query.contains("dataPresent"));
        JsonValue rowLevel = vector("cf-the-dataset-epoch-is-not-read-when-the-guard-is-the-row's");
        assertFalse(Confirmation.query(operation(rowLevel), values(rowLevel)).contains("datasetEpoch"));
        JsonValue create = vector("cf-already-exists-by-the-row");
        assertFalse(Confirmation.query(operation(create), values(create)).contains("rowEpoch"));
        JsonValue composite = vector("cf-already-exists-by-data-with-no-row");
        assertTrue(Confirmation.query(operation(composite), values(composite)).contains("dataPresent"));
    }

    @Test void theReadHoldsNothingOfTheRequestButTypedIris() {
        JsonValue v = vector("cf-reused-key");
        String query = Confirmation.query(operation(v), values(v));
        assertFalse(query.contains(str(get(get(get(v, "values"), "requestDigest"), "string"))));
        Map<String, Object> hostile = new HashMap<>(values(v));
        hostile.put("root", "urn:x> } } DROP ALL #");
        assertThrows(ConfirmationException.class, () -> Confirmation.query(operation(v), hostile));
    }

    @Test void anOperationThatRecordsNoClaimIsNotConfirmed() {
        JsonValue v = vector("cf-applied-replace");
        OperationContract bootstrap = new OperationContract(null, "bootstrap-version-row", OperationKind.BOOTSTRAP, 1, List.of(), null, null, operation(v).bindings(), null, List.of());
        assertFalse(Confirmation.confirms(bootstrap));
        assertTrue(Confirmation.confirms(operation(v)));
        assertThrows(ConfirmationException.class, () -> Confirmation.query(bootstrap, values(v)));
        assertThrows(ConfirmationException.class, () -> Confirmation.classify(bootstrap, values(v), List.of()));
    }

    @Test void aRequestWithoutWhatTheReadNeedsIsRefused() {
        JsonValue v = vector("cf-applied-replace");
        Map<String, Object> noTxn = new HashMap<>(values(v));
        noTxn.remove("txnId");
        assertThrows(ConfirmationException.class, () -> Confirmation.query(operation(v), noTxn));
        OperationContract stripped = new OperationContract(null, "cas-replace-named-graph", OperationKind.REPLACE, 1, operation(v).parameters(), null, null, List.of(), null, List.of());
        assertThrows(ConfirmationException.class, () -> Confirmation.query(stripped, values(v)));
    }

    @Test void theReasonsSayWhatWasFound() {
        for (var e : Map.of("cf-precondition-failed", "position 6, not 4", "cf-epoch-changed", "epoch is 4, not 3", "cf-applied-replace", "earlier attempt", "cf-gone", "tombstoned").entrySet()) {
            JsonValue v = vector(e.getKey());
            String reason = Confirmation.run(new DatasetClient(list(get(v, "quads"))), operation(v), values(v)).reason();
            assertTrue(reason.contains(e.getValue()), reason);
        }
    }

    @Test void theRowsOfAClientMayHoldNumbersAndPlainText() {
        JsonValue v = vector("cf-precondition-failed");
        List<Map<String, Object>> rows = List.of(Map.of("fact", "rowSeq", "value", 6), Map.of("fact", "rowEpoch", "value", "3"), Map.of("fact", "datasetEpoch", "value", 3L));
        assertEquals(Classification.PRECONDITION_FAILED, Confirmation.classify(operation(v), values(v), rows).classification());
    }

}
