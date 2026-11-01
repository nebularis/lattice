// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.apache.jena.graph.Node;

/**
 * Ground triples, with no blank node, as a set (ADR-A132 decision 2). {@link #nt()} is the canonical N-Triples the request digest is taken
 * over. {@link #sparql()} is the text that fills a request-time slot, built from typed terms only.
 */
public record Payload(Set<Triple> triples) {
    public Payload {
        triples = Set.copyOf(triples);
    }

    /** A payload of these triples. */
    public static Payload of(Triple... triples) {
        return new Payload(new HashSet<>(List.of(triples)));
    }

    /** A payload from Jena triples, such as the triples of a graph. A blank node is refused, since the store would mint it. */
    public static Payload ofJena(Iterable<org.apache.jena.graph.Triple> triples) {
        Set<Triple> out = new HashSet<>();
        for (org.apache.jena.graph.Triple t : triples) {
            out.add(new Triple(iri(t.getSubject(), "subject"), iri(t.getPredicate(), "predicate"), term(t.getObject())));
        }
        return new Payload(out);
    }

    private static Iri iri(Node node, String role) {
        if (node.isBlank()) throw new PayloadException("a payload holds no blank node, got _:" + node.getBlankNodeLabel());
        if (!node.isURI()) throw new PayloadException("the " + role + " of a payload triple must be an Iri, got " + node);
        try {
            return Iri.of(node.getURI());
        } catch (SparqlTermException e) {
            throw new PayloadException(e.getMessage(), e);
        }
    }

    private static Term term(Node node) {
        if (node.isLiteral()) {
            String lang = node.getLiteralLanguage();
            return lang == null || lang.isEmpty() ? new Lit(node.getLiteralLexicalForm(), node.getLiteralDatatypeURI(), null)
                : new Lit(node.getLiteralLexicalForm(), null, lang);
        }
        return iri(node, "object");
    }

    /** The canonical N-Triples lines, sorted by their UTF-8 bytes, with no duplicate. */
    public List<String> lines() {
        List<String> all = new ArrayList<>();
        for (Triple t : triples) all.add(t.nt());
        return Text.sortedUnique(all);
    }

    /** The canonical N-Triples text. */
    public String nt() { return String.join("\n", lines()); }

    /** The text that fills a slot. */
    public String sparql() {
        List<String> all = new ArrayList<>();
        for (Triple t : triples) all.add(t.sparql());
        return String.join("\n", Text.sortedUnique(all));
    }

    /** The subjects of the triples. */
    public Set<Iri> subjects() {
        Set<Iri> out = new HashSet<>();
        for (Triple t : triples) out.add(t.subject());
        return out;
    }

    public int size() { return triples.size(); }
}
