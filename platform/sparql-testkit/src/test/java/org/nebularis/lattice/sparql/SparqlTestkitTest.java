// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.sparql;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;

import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.junit.jupiter.api.Test;

class SparqlTestkitTest {
    private static String q(String text) {
        return "{\"op\": \"query\", \"text\": " + SparqlTestkit.jsonString(text) + "}";
    }

    private static String u(String text) {
        return "{\"op\": \"update\", \"text\": " + SparqlTestkit.jsonString(text) + "}";
    }

    private static JsonObject parsed(String answer) {
        return JSON.parse(answer);
    }

    private static JsonObject firstO(JsonObject answer) {
        return answer.get("result").getAsObject().get("results").getAsObject().get("bindings").getAsArray().get(0).getAsObject().get("o").getAsObject();
    }

    @Test
    void loadThenSelectGivesSparqlJsonWithDatatypesAndLanguageTags() {
        SparqlTestkit kit = new SparqlTestkit();
        String data = "<urn:s> <urn:p> \"1\"^^<http://www.w3.org/2001/XMLSchema#integer> <urn:g> .\n<urn:s> <urn:q> \"hi\"@en .\n";
        assertEquals("{\"result\": \"ok\"}", kit.answer("{\"op\": \"load\", \"format\": \"nquads\", \"data\": " + SparqlTestkit.jsonString(data) + "}"));
        JsonObject a = parsed(kit.answer(q("SELECT ?o WHERE { GRAPH <urn:g> { <urn:s> <urn:p> ?o } }")));
        assertEquals("select", a.get("form").getAsString().value());
        JsonObject binding = firstO(a);
        assertEquals("1", binding.get("value").getAsString().value());
        assertEquals("http://www.w3.org/2001/XMLSchema#integer", binding.get("datatype").getAsString().value());
        assertEquals("en", firstO(parsed(kit.answer(q("SELECT ?o WHERE { <urn:s> <urn:q> ?o }")))).get("xml:lang").getAsString().value());
    }

    @Test
    void askAndConstructAndAnErrorThatDoesNotEndTheServer() {
        SparqlTestkit kit = new SparqlTestkit();
        kit.answer(u("INSERT DATA { <urn:s> <urn:p> 1 }"));
        assertTrue(parsed(kit.answer(q("ASK { <urn:s> <urn:p> 1 }"))).get("result").getAsObject().get("boolean").getAsBoolean().value());
        JsonObject graph = parsed(kit.answer(q("CONSTRUCT { ?s <urn:r> ?o } WHERE { ?s <urn:p> ?o }")));
        assertEquals("graph", graph.get("form").getAsString().value());
        assertTrue(graph.get("result").getAsString().value().contains("<urn:r>"));
        assertTrue(kit.answer(q("SELECT WHERE {")).startsWith("{\"error\":"));
        assertTrue(kit.answer("not json").startsWith("{\"error\":"));
        assertTrue(kit.answer("{\"op\": \"nope\"}").startsWith("{\"error\":"));
        assertTrue(kit.answer(q("ASK { <urn:s> <urn:p> 1 }")).contains("true"));
    }

    @Test
    void aFailingLoadLeavesTheDatasetAsItWas() {
        SparqlTestkit kit = new SparqlTestkit();
        kit.answer(u("INSERT DATA { <urn:s> <urn:p> 1 }"));
        String answer = kit.answer("{\"op\": \"load\", \"format\": \"nquads\", \"data\": \"<urn:a> <urn:p> 2 .\\n<urn:broken\"}");
        assertTrue(answer.startsWith("{\"error\":"));
        assertFalse(kit.answer(q("ASK { <urn:a> <urn:p> 2 }")).contains("true"));
        assertTrue(kit.answer(q("ASK { <urn:s> <urn:p> 1 }")).contains("true"));
    }

    @Test
    void aFailingUpdateLeavesTheDatasetAsItWas() {
        SparqlTestkit kit = new SparqlTestkit();
        // The first operation succeeds, the second names a SERVICE that cannot be reached, so it fails while running
        String answer = kit.answer(u("INSERT DATA { <urn:a> <urn:p> 1 } ; INSERT { <urn:b> <urn:p> 2 } WHERE { SERVICE <http://localhost:1/sparql> { ?s ?p ?o } }"));
        assertTrue(answer.startsWith("{\"error\":"), answer);
        assertFalse(kit.answer(q("ASK { <urn:a> <urn:p> 1 }")).contains("true"));
    }

    @Test
    void resetEmptiesEveryGraph() {
        SparqlTestkit kit = new SparqlTestkit();
        kit.answer(u("INSERT DATA { <urn:s> <urn:p> 1 . GRAPH <urn:g> { <urn:s> <urn:p> 2 } }"));
        kit.answer("{\"op\": \"reset\"}");
        assertFalse(kit.answer(q("ASK { { ?s ?p ?o } UNION { GRAPH ?g { ?s ?p ?o } } }")).contains("true"));
    }

    @Test
    void serveAnswersOneLinePerRequestAndSkipsBlankLines() throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        new SparqlTestkit().serve(new BufferedReader(new StringReader("{\"op\": \"reset\"}\n\n{\"op\": \"x\"}\n")), new PrintStream(bytes, true, StandardCharsets.UTF_8));
        String[] lines = bytes.toString(StandardCharsets.UTF_8).split("\n");
        assertEquals(2, lines.length);
        assertEquals("{\"result\": \"ok\"}", lines[0]);
        assertTrue(lines[1].startsWith("{\"error\":"));
    }

    @Test
    void datasetsAreSeparateAndAReusedBlankNodeLabelIsTheSameNode() {
        SparqlTestkit kit = new SparqlTestkit();
        kit.answer("{\"op\": \"update\", \"dataset\": \"a\", \"text\": \"INSERT DATA { <urn:s> <urn:p> 1 }\"}");
        assertFalse(kit.answer("{\"op\": \"query\", \"dataset\": \"b\", \"text\": \"ASK { <urn:s> <urn:p> 1 }\"}").contains("true"));
        kit.answer("{\"op\": \"load\", \"format\": \"nquads\", \"data\": \"_:x <urn:p> \\\"1\\\" .\\n\"}");
        kit.answer("{\"op\": \"load\", \"format\": \"nquads\", \"data\": \"_:x <urn:q> \\\"2\\\" .\\n\"}");
        assertTrue(kit.answer(q("ASK { ?b <urn:p> \"1\" . ?b <urn:q> \"2\" }")).contains("true"));
        kit.answer("{\"op\": \"drop\", \"dataset\": \"a\"}");
        assertFalse(kit.answer("{\"op\": \"query\", \"dataset\": \"a\", \"text\": \"ASK { <urn:s> <urn:p> 1 }\"}").contains("true"));
    }
}
