// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.update.UpdateAction;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.junit.jupiter.api.Test;

class PayloadTest {
    static final Iri S = Iri.of("urn:example:s"), P = Iri.of("urn:example:p"), O = Iri.of("urn:example:o");

    static org.apache.jena.graph.Triple jena(org.apache.jena.graph.Node s, org.apache.jena.graph.Node p, org.apache.jena.graph.Node o) {
        return org.apache.jena.graph.Triple.create(s, p, o);
    }

    static org.apache.jena.graph.Node uri(String u) { return NodeFactory.createURI(u); }

    @Test void aBlankNodeIsRefused() {
        var e = assertThrows(PayloadException.class, () -> Payload.ofJena(List.of(jena(NodeFactory.createBlankNode("b0"), uri("urn:example:p"), uri("urn:example:o")))));
        assertTrue(e.getMessage().contains("blank node"));
        e = assertThrows(PayloadException.class, () -> Payload.ofJena(List.of(jena(uri("urn:example:s"), uri("urn:example:p"), NodeFactory.createBlankNode()))));
        assertTrue(e.getMessage().contains("blank node"));
    }

    @Test void anIriWithAForbiddenCharacterIsRefused() {
        assertThrows(PayloadException.class, () -> Payload.ofJena(List.of(jena(uri("urn:example:s"), uri("urn:example:p"), uri("urn:example:o> . <urn:x> <urn:y> <urn:z")))));
        assertThrows(SparqlTermException.class, () -> Iri.of("urn:example:o> . <urn:x>"));
    }

    @Test void aLiteralStaysALiteral() {
        var p = Payload.of(new Triple(S, P, new Lit("} } ; DROP ALL\" . <urn:evil> <urn:p> <urn:o>")));
        assertEquals(1, p.lines().size());
        assertEquals(1, p.sparql().split("<urn:evil>", -1).length - 1);
        assertTrue(p.sparql().startsWith("<urn:example:s> <urn:example:p> \"} } ; DROP ALL\\\" ."));
    }

    @Test void canonicalTextEscapesABackslashOnce() {
        assertEquals("\"\\\\u0041\"", new Lit("\\u0041").nt());
    }

    @ParameterizedTest
    @ValueSource(strings = {"\\u0041", "\\U0001F600", "a\\\\u0041", "\\u00e9\\u00e9", "q\"uo\\te\n", "\\"})
    void slotTextRoundTripsThroughAnEngine(String value) {
        Model model = ModelFactory.createDefaultModel();
        UpdateAction.parseExecute("INSERT DATA { " + Payload.of(new Triple(S, P, new Lit(value))).sparql() + " }", DatasetFactory.wrap(model));
        var objects = model.listObjects().toList();
        assertEquals(1, objects.size());
        assertEquals(value, objects.get(0).asLiteral().getLexicalForm());
    }

    @Test void xsdStringIsPlainAndLanguageIsLowerCase() {
        assertEquals("\"x\"", new Lit("x", XSDDatatype.XSDstring.getURI(), null).nt());
        assertEquals("\"x\"@en-gb", new Lit("x", null, "EN-GB").nt());
        assertEquals(new Lit("x"), new Lit("x", XSDDatatype.XSDstring.getURI(), null));
    }

    @Test void linesAreSortedAndUnique() {
        var t1 = new Triple(S, P, O);
        var t2 = new Triple(O, P, S);
        assertEquals(new java.util.ArrayList<>(new TreeSet<>(Set.of(t1.nt(), t2.nt()))), Payload.of(t1, t2, t1).lines());
        var p = Payload.ofJena(List.of(jena(uri("urn:example:s"), uri("urn:example:p"), NodeFactory.createLiteralDT("1", XSDDatatype.XSDlong))));
        assertEquals(List.of("<urn:example:s> <urn:example:p> \"1\"^^<http://www.w3.org/2001/XMLSchema#long> ."), p.lines());
    }

    @Test void linesSortByUtf8BytesNotUtf16Units() {
        // U+FF5E is a BMP character and U+1F600 an astral one. UTF-8 puts U+FF5E first, UTF-16 code units put the surrogate first.
        var p = Payload.of(new Triple(S, P, new Lit("～")), new Triple(S, P, new Lit("😀")));
        assertEquals(List.of(new Triple(S, P, new Lit("～")).nt(), new Triple(S, P, new Lit("😀")).nt()), p.lines());
    }

    @Test void rowsTextAndTriples() {
        var when = new Lit("2026-10-20T10:00:00Z", XSDDatatype.XSDdateTime.getURI(), null);
        var rows = Rows.of(new EventRow(Iri.of("urn:e:2"), Iri.of("urn:T"), 2, when), new EventRow(Iri.of("urn:e:1"), Iri.of("urn:T"), 1, when));
        assertTrue(rows.sparql().lines().findFirst().orElseThrow().startsWith("(<urn:e:1> <urn:T> \"1\"^^<http://www.w3.org/2001/XMLSchema#long> "));
        assertEquals(6, rows.payload().size());
    }

    @Test void anEventRowNeedsATypedOccurredAt() {
        assertThrows(PayloadException.class, () -> new EventRow(Iri.of("urn:e:1"), Iri.of("urn:T"), 1, new Lit("2026-10-20T10:00:00Z")));
        assertThrows(PayloadException.class, () -> new EventRow(Iri.of("urn:e:1"), Iri.of("urn:T"), 1, null));
    }
}
