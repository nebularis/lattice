// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.reasoning;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.StringReader;
import java.io.PrintStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.semanticweb.owlapi.reasoner.OWLReasoner;

class ReasoningTestkitTest {
    private static final String EX = "https://example.org/r#";
    private static final String TBOX = """
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
            @prefix ex: <https://example.org/r#> .
            ex:Engineer a owl:Class ; rdfs:subClassOf ex:Staff .
            ex:Staff a owl:Class .
            ex:Contractor a owl:Class ; owl:disjointWith ex:Staff .
            ex:Impossible a owl:Class ; rdfs:subClassOf ex:Engineer , ex:Contractor .
            """;
    // Two ontology documents: a rule and the data it applies to.
    private static final String RULE = """
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            @prefix swrl: <http://www.w3.org/2003/11/swrl#> .
            @prefix ex: <https://example.org/r#> .
            ex:holds a owl:ObjectProperty . ex:eligibleFor a owl:ObjectProperty .
            ex:x a swrl:Variable . ex:y a swrl:Variable .
            [] a swrl:Imp ;
              swrl:body ( [ a swrl:IndividualPropertyAtom ; swrl:propertyPredicate ex:holds ; swrl:argument1 ex:x ; swrl:argument2 ex:y ] ) ;
              swrl:head ( [ a swrl:IndividualPropertyAtom ; swrl:propertyPredicate ex:eligibleFor ; swrl:argument1 ex:x ; swrl:argument2 ex:y ] ) .
            """;
    private static final String DATA = """
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            @prefix ex: <https://example.org/r#> .
            ex:holds a owl:ObjectProperty .
            ex:alice a owl:NamedIndividual ; ex:holds ex:relocation .
            ex:relocation a owl:NamedIndividual .
            """;

    @TempDir Path dir;

    private Path write(String name, String text) throws Exception {
        return Files.writeString(dir.resolve(name), text);
    }

    @Test
    void decidesSatisfiabilityAndSubsumption() throws Exception {
        OWLReasoner reasoner = ReasoningTestkit.reasoner(List.of(write("tbox.ttl", TBOX)));
        assertTrue(ReasoningTestkit.satisfiable(reasoner, EX + "Engineer"));
        assertFalse(ReasoningTestkit.satisfiable(reasoner, EX + "Impossible"));
        assertTrue(ReasoningTestkit.subsumes(reasoner, EX + "Engineer", EX + "Staff"));
        assertFalse(ReasoningTestkit.subsumes(reasoner, EX + "Staff", EX + "Engineer"));
    }

    @Test
    void appliesRulesAcrossMergedFiles() throws Exception {
        OWLReasoner reasoner = ReasoningTestkit.reasoner(List.of(write("rule.ttl", RULE), write("data.ttl", DATA)));
        List<String[]> pairs = ReasoningTestkit.values(reasoner, EX + "eligibleFor");
        assertEquals(1, pairs.size());
        assertEquals(EX + "alice", pairs.get(0)[0]);
        assertEquals(EX + "relocation", pairs.get(0)[1]);
    }

    @Test
    void cliPrintsJson() throws Exception {
        Path tbox = write("tbox.ttl", TBOX);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        PrintStream original = System.out;
        System.setOut(new PrintStream(out));
        try {
            ReasoningTestkit.main(new String[] {"subsumes", EX + "Engineer", EX + "Staff", tbox.toString()});
        } finally {
            System.setOut(original);
        }
        assertEquals("{\"result\": true}", out.toString().trim());
    }

    private String served(ReasoningTestkit.ReasonerCache cache, String... requests) throws Exception {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ReasoningTestkit.serve(new BufferedReader(new StringReader(String.join("\n", requests) + "\n")), new PrintStream(out), cache);
        return out.toString().trim();
    }

    @Test
    void serveAnswersEachLineAndSurvivesAFailure() throws Exception {
        Path tbox = write("tbox.ttl", TBOX);
        String answers = served(new ReasoningTestkit.ReasonerCache(2),
                "satisfiable\t" + EX + "Engineer\t" + tbox,
                "satisfiable\t" + EX + "Impossible\t" + tbox,
                "nonsense\t" + tbox,
                "subsumes\t" + EX + "Engineer\t" + EX + "Staff\t" + tbox,
                "consistent\t" + dir.resolve("missing.ttl"));
        String[] lines = answers.split("\n");
        assertEquals(5, lines.length);
        assertEquals("{\"result\": true}", lines[0]);
        assertEquals("{\"result\": false}", lines[1]);
        assertTrue(lines[2].startsWith("{\"error\": \"IllegalArgumentException: unknown command nonsense"), lines[2]);
        assertEquals("{\"result\": true}", lines[3]);
        assertTrue(lines[4].startsWith("{\"error\": "), lines[4]);
    }

    @Test
    void serveKeepsOneReasonerPerDistinctClosureAndDropsTheOldest() throws Exception {
        Path tbox = write("tbox.ttl", TBOX);
        Path other = write("other.ttl", TBOX + "ex:Extra a owl:Class .\n");
        Path third = write("third.ttl", TBOX + "ex:More a owl:Class .\n");
        ReasoningTestkit.ReasonerCache cache = new ReasoningTestkit.ReasonerCache(2);
        served(cache, "consistent\t" + tbox, "consistent\t" + tbox, "consistent\t" + other);
        assertEquals(2, cache.size());
        served(cache, "consistent\t" + third);
        assertEquals(2, cache.size());
    }

    @Test
    void serveKeysAClosureByContentNotByName() throws Exception {
        Path first = write("first.ttl", TBOX);
        ReasoningTestkit.ReasonerCache cache = new ReasoningTestkit.ReasonerCache(4);
        served(cache, "consistent\t" + first);
        Files.writeString(first, TBOX + "ex:Changed a owl:Class .\n");
        served(cache, "consistent\t" + first);
        assertEquals(2, cache.size());
    }

    @Test
    void jsonStringEscapesWhatAMessageCanHold() {
        assertEquals("\"a\\\"b\\\\c\\nd\\u0001\"", ReasoningTestkit.jsonString("a\"b\\c\nd\u0001"));
    }
}
