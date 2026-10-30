// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.model;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.vocabulary.RDF;

/**
 * Which part of a workspace each subject of a graph belongs to, by the rule of the browser's {@code src/rdf/split.ts}:
 * the first part whose namespace a named subject uses in its {@code rdf:type} or its predicates, a concept scheme or
 * concept for vocabulary, baseline otherwise, and a blank node with the subject that refers to it, as is a named node of a
 * mapping's own structure that uses no part's terms, such as a guard's shape. The service checks a
 * saved graph with it, since it cannot know the browser sorted the graph (STD-279).
 */
public final class Parts {
    private static final String LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/";
    private static final String SKOS = "http://www.w3.org/2004/02/skos/core#";
    private static final String CST = "https://www.nebularis.org/neuro-semantic/lattice/config-studio#";
    private static final String MORK = "http://www.nebularis.org/ontologies/Mork#";
    private static final String SHACL = "http://www.w3.org/ns/shacl#";
    private static final java.util.Set<String> MAPPING_STRUCTURE = java.util.Set.of(MORK + "appliesWhen", SHACL + "declare", SHACL + "property");
    private static final Map<String, Predicate<Statement>> OWNERS = new LinkedHashMap<>();

    static {
        // An assembly and the value records it sets come first, since a value record uses Wording's terms too.
        OWNERS.put("assembly", s -> (s.getPredicate().equals(RDF.type)
            && (isIri(s.getObject(), CST + "Assembly") || isIri(s.getObject(), LATTICE + "wording#VariableValue")))
            || s.getPredicate().getURI().equals(CST + "assembles") || s.getPredicate().getURI().equals(LATTICE + "wording#forVariable"));
        // A proposal and its decision, then stated meaning: any subject using Instrument's terms (ADR-A138).
        OWNERS.put("review", s -> (s.getPredicate().equals(RDF.type) && isIri(s.getObject(), CST + "Proposal"))
            || s.getPredicate().getURI().equals(CST + "proposes"));
        OWNERS.put("mapping", uses(MORK));
        OWNERS.put("meaning", uses(LATTICE + "instrument#"));
        OWNERS.put("persistence", uses(LATTICE + "persistence#"));
        OWNERS.put("surface", uses(LATTICE + "surface#"));
        OWNERS.put("eligibility", uses(LATTICE + "eligibility#"));
        OWNERS.put("quantification", uses(LATTICE + "quantification#"));
        OWNERS.put("vocabulary", uses(LATTICE + "vocabulary#").or(s -> s.getPredicate().getURI().equals(SKOS + "inScheme")
            || (s.getPredicate().equals(RDF.type) && (isIri(s.getObject(), SKOS + "Concept") || isIri(s.getObject(), SKOS + "ConceptScheme")))));
        OWNERS.put("library", uses(LATTICE + "wording#"));
    }

    private Parts() {
    }

    private static Predicate<Statement> uses(String base) {
        return s -> s.getPredicate().getURI().startsWith(base)
            || (s.getPredicate().equals(RDF.type) && s.getObject().isURIResource() && s.getObject().asResource().getURI().startsWith(base));
    }

    private static boolean isIri(RDFNode node, String iri) {
        return node.isURIResource() && node.asResource().getURI().equals(iri);
    }

    /** The part each subject of {@code graph} belongs to. */
    public static Map<Resource, String> owners(Model graph) {
        Map<Resource, String> owner = new HashMap<>();
        Deque<Resource> pending = new ArrayDeque<>();
        graph.listSubjects().forEachRemaining(s -> {
            if (s.isURIResource()) {
                List<Statement> statements = s.listProperties().toList();
                owner.put(s, OWNERS.entrySet().stream().filter(e -> statements.stream().anyMatch(e.getValue()))
                    .map(Map.Entry::getKey).findFirst().orElse("baseline"));
                pending.add(s);
            }
        });
        // Blank nodes take their referrer's part, breadth first from the named subjects, and so do a mapping's own named nodes.
        while (!pending.isEmpty()) {
            Resource s = pending.poll();
            s.listProperties().forEachRemaining(st -> {
                RDFNode o = st.getObject();
                boolean structure = o.isURIResource() && "mapping".equals(owner.get(s)) && "baseline".equals(owner.get(o.asResource()))
                    && MAPPING_STRUCTURE.contains(st.getPredicate().getURI());
                // A blank node first reached from a named node that later moved to mapping moves with it.
                boolean blank = o.isAnon() && (!owner.containsKey(o.asResource())
                    || ("baseline".equals(owner.get(o.asResource())) && !"baseline".equals(owner.get(s))));
                if (blank || structure) {
                    owner.put(o.asResource(), owner.get(s));
                    pending.add(o.asResource());
                }
            });
        }
        graph.listSubjects().forEachRemaining(s -> owner.putIfAbsent(s, "baseline"));
        return owner;
    }

    /** Up to {@code limit} subjects of {@code graph} that belong to a part other than {@code part}, each with its part. */
    public static List<String> strangers(Model graph, String part, int limit) {
        List<String> out = new ArrayList<>();
        for (Map.Entry<Resource, String> e : owners(graph).entrySet()) {
            if (!e.getValue().equals(part) && out.size() < limit) {
                out.add((e.getKey().isURIResource() ? "<" + e.getKey().getURI() + ">" : "a blank node") + " belongs to " + e.getValue());
            }
        }
        out.sort(null);
        return out;
    }
}
