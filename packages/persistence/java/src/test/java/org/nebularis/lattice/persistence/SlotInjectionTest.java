// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.update.UpdateAction;
import org.apache.jena.update.UpdateFactory;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * The injection corpus over the library's slot filling. A slot is where text enters a generated operation, so every value the library puts
 * into one is run through the encoders with adversarial input. A value the encoder refuses is a pass. One it accepts must come back out of the
 * store as exactly the term that went in, and the filled text must still be one operation.
 */
class SlotInjectionTest {
    static final String[] IRIS = {
        "urn:g:orders> } ; DROP GRAPH <urn:g:keys> ; ASK { <urn:g:x",
        "urn:g:orders/{ INSERT DATA { <urn:x> <urn:y> <urn:z> } }",
        "urn:g:orders/​",
        "urn:g:orders/‮",
        "urn:g:orders/\"; DELETE WHERE { ?s ?p ?o } #",
        "urn:g:orders/<script>",
        "urn:g:orders/\n\rDELETE",
        "urn:g:orders/|pipe",
        "urn:g:orders/`backtick`",
        "urn:g:orders/{{{eventRows}}}",
        "",
    };
    static final String[] LITERALS = {
        "value\" ; DROP GRAPH <urn:g:keys> ; INSERT DATA { <urn:x> <urn:y> \"",
        "value\\\" } } DELETE { ?s ?p ?o",
        "line1\nline2\rline3\ttabbed",
        "back\\slash",
        "\\u0041",
        "{{{payloadTriples}}}",
        "unicode​zero‮width",
        "",
    };
    static final String S = "urn:s:1", P = "urn:p:1";

    static List<String> iris() { return List.of(IRIS); }

    static List<String> literals() { return List.of(LITERALS); }

    static int operations(String text) { return UpdateFactory.create(text).getOperations().size(); }

    static Set<org.apache.jena.graph.Triple> stored(String text) {
        Dataset dataset = DatasetFactory.createTxnMem();
        UpdateAction.parseExecute(text, dataset);
        return new HashSet<>(dataset.asDatasetGraph().getGraph(NodeFactory.createURI("urn:g:data")).find().toList());
    }

    @ParameterizedTest
    @org.junit.jupiter.params.provider.MethodSource("literals")
    void aPayloadLiteralComesBackAsTheSameLiteralOrIsRefused(String value) {
        Payload payload;
        try {
            payload = Payload.of(new Triple(Iri.of(S), Iri.of(P), new Lit(value)));
        } catch (PayloadException | SparqlTermException e) {
            return;
        }
        String text = "INSERT DATA { GRAPH <urn:g:data> { " + payload.sparql() + " } }";
        assertEquals(1, operations(text));
        assertEquals(Set.of(org.apache.jena.graph.Triple.create(NodeFactory.createURI(S), NodeFactory.createURI(P), NodeFactory.createLiteralString(value))), stored(text));
    }

    @ParameterizedTest
    @org.junit.jupiter.params.provider.MethodSource("iris")
    void aPayloadIriComesBackAsTheSameIriOrIsRefused(String value) {
        Payload payload;
        try {
            payload = Payload.of(new Triple(Iri.of(S), Iri.of(P), Iri.of(value)));
        } catch (PayloadException | SparqlTermException e) {
            return;
        }
        String text = "INSERT DATA { GRAPH <urn:g:data> { " + payload.sparql() + " } }";
        assertEquals(1, operations(text));
        assertEquals(Set.of(org.apache.jena.graph.Triple.create(NodeFactory.createURI(S), NodeFactory.createURI(P), NodeFactory.createURI(value))), stored(text));
    }

    @ParameterizedTest
    @org.junit.jupiter.params.provider.MethodSource("iris")
    void aListedLogGraphIsOneGraphOrIsRefused(String value) {
        String filled;
        try {
            filled = "SELECT ?log WHERE { VALUES ?log { <urn:g:txlog/pinned> " + Audit.registryText(List.of(value)) + " } }";
        } catch (SparqlTermException e) {
            return;
        }
        QueryFactory.create(filled);
        Set<String> seen = new TreeSet<>();
        try (var exec = QueryExecutionFactory.create(filled, DatasetFactory.create())) {
            var results = exec.execSelect();
            while (results.hasNext()) {
                QuerySolution row = results.next();
                seen.add(row.getResource("log").getURI());
            }
        }
        assertEquals(new TreeSet<>(Set.of("urn:g:txlog/pinned", value)), seen);
    }

    @ParameterizedTest
    @org.junit.jupiter.params.provider.MethodSource("literals")
    void anEventRowIsOneRowOrIsRefused(String value) {
        EventRow row;
        try {
            row = new EventRow(Iri.of("urn:e:1"), Iri.of("urn:t:1"), 1, new Lit(value, "http://www.w3.org/2001/XMLSchema#dateTime", null));
        } catch (PayloadException | SparqlTermException e) {
            return;
        }
        String query = "SELECT * WHERE { VALUES (?event ?type ?opSeq ?at) { " + Rows.of(row).sparql() + " } }";
        try (var exec = QueryExecutionFactory.create(query, DatasetFactory.create())) {
            var rows = org.apache.jena.query.ResultSetFactory.copyResults(exec.execSelect());
            assertEquals(1, rows.size());
            QuerySolution r = rows.next();
            assertEquals("urn:e:1", r.getResource("event").getURI());
            Node at = r.get("at").asNode();
            assertEquals(NodeFactory.createLiteralDT(value, XSDDatatype.XSDdateTime), at);
        }
    }
}
