// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.api;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.RDFS;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;

/**
 * The workspace description as read from, and written to, the workspace's own graph. Each named
 * graph has a revision, {@code cst:<name>Revision}, from 0 before its first save. A revision a
 * description lacks reads as 0, so a workspace made before a graph was added still opens.
 */
record Workspace(String id, String label, Instant createdAt, Instant modifiedAt, Map<String, Long> revisions) {

    /** The baseline, then the configurations, in the order the contract lists them. */
    static final List<String> GRAPHS = List.of("baseline", "vocabulary", "quantification", "eligibility", "surface", "persistence");

    static Workspace created(String id, String label, Instant at) {
        Map<String, Long> revisions = new LinkedHashMap<>();
        for (String name : GRAPHS) {
            revisions.put(name, name.equals("baseline") ? 1L : 0L);
        }
        return new Workspace(id, label, at, at, Map.copyOf(revisions));
    }

    String baselineGraph() {
        return Graphs.baseline(id, revision("baseline"));
    }

    long revision(String name) {
        return revisions.getOrDefault(name, 0L);
    }

    Workspace revised(String name, long revision, Instant at) {
        Map<String, Long> next = new LinkedHashMap<>(revisions);
        next.put(name, revision);
        return new Workspace(id, label, createdAt, at, Map.copyOf(next));
    }

    Model toModel() {
        Model model = ModelFactory.createDefaultModel();
        Resource node = model.createResource(Graphs.workspace(id));
        node.addProperty(RDF.type, Cst.Workspace);
        node.addProperty(RDFS.label, label);
        node.addProperty(Cst.createdAt, model.createTypedLiteral(createdAt.toString(), XSDDatatype.XSDdateTime));
        node.addProperty(Cst.modifiedAt, model.createTypedLiteral(modifiedAt.toString(), XSDDatatype.XSDdateTime));
        node.addProperty(Cst.baselineGraph, model.createResource(baselineGraph()));
        for (String name : GRAPHS) {
            node.addProperty(Cst.revision(name), model.createTypedLiteral(Long.toString(revision(name)), XSDDatatype.XSDinteger));
        }
        return model;
    }

    /** Reads a description, or null when the graph holds none or a malformed one. */
    static Workspace from(String id, Model model) {
        Resource node = model.createResource(Graphs.workspace(id));
        try {
            Map<String, Long> revisions = new LinkedHashMap<>();
            for (String name : GRAPHS) {
                Statement s = node.getProperty(Cst.revision(name));
                revisions.put(name, s == null ? 0L : s.getLong());
            }
            if (revisions.get("baseline") < 1) {
                return null;
            }
            return new Workspace(id, text(node, RDFS.label), Instant.parse(text(node, Cst.createdAt)),
                Instant.parse(text(node, Cst.modifiedAt)), Map.copyOf(revisions));
        } catch (RuntimeException e) {
            return null;
        }
    }

    private static String text(Resource node, Property p) {
        return node.getProperty(p).getLiteral().getLexicalForm();
    }
}
