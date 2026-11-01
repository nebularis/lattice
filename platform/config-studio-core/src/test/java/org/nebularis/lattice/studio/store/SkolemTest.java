// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.store;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.StringReader;
import java.util.HashSet;
import java.util.Set;
import org.apache.jena.graph.Triple;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.junit.jupiter.api.Test;

/** ADR-A149 decision 13: a part's blank nodes are named before a write and read back as blank nodes. */
class SkolemTest {
    private static final String SHAPES = """
        @prefix sh: <http://www.w3.org/ns/shacl#> . @prefix ex: <https://example.org/> .
        ex:Shape a sh:NodeShape ;
          sh:property [ sh:path ex:colour ; sh:in ( ex:red ex:green ) ] ,
                      [ sh:path ex:size ; sh:minCount 1 ] .
        ex:m ex:guard [ ex:ref "x" ] , [ ex:ref "x" ] .
        [] a sh:NodeShape ; sh:targetClass ex:Thing .
        """;

    private static Model parse(String turtle) {
        return ModelFactory.createDefaultModel().read(new StringReader(turtle), null, "TTL");
    }

    private static Set<Triple> triples(Model m) {
        return new HashSet<>(m.getGraph().find().toList());
    }

    @Test
    void aSkolemisedGraphHoldsNoBlankNodeAndReadsBackAsItWas() {
        Model g = parse(SHAPES);
        Model named = Skolem.skolemise(g);
        assertFalse(named.getGraph().find().filterKeep(t -> t.getSubject().isBlank() || t.getObject().isBlank()).hasNext());
        assertEquals(g.size(), named.size());
        assertTrue(Skolem.unskolemise(named).isIsomorphicWith(g));
    }

    @Test
    void theSameContentGetsTheSameNamesHoweverItWasParsed() {
        assertEquals(triples(Skolem.skolemise(parse(SHAPES))), triples(Skolem.skolemise(parse(SHAPES))));
    }

    @Test
    void aChangeRenamesOnlyTheNodesItTouches() {
        Set<Triple> before = triples(Skolem.skolemise(parse(SHAPES)));
        Set<Triple> after = triples(Skolem.skolemise(parse(SHAPES.replace("sh:minCount 1", "sh:minCount 2"))));
        Set<Triple> added = new HashSet<>(after);
        added.removeAll(before);
        // The changed property shape's two triples and the edge naming it, nothing of the shape and list beside it.
        assertEquals(3, added.size());
    }

    @Test
    void aGraphWithNoSkolemIriReadsBackUnchanged() {
        Model g = parse(SHAPES);
        assertTrue(Skolem.unskolemise(g) == g);
    }
}
