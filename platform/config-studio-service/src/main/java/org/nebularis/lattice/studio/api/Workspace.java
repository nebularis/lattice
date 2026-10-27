// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.api;

import java.time.Instant;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.RDFS;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;

/** The workspace description as read from, and written to, the workspace's own graph. */
record Workspace(String id, String label, Instant createdAt, Instant modifiedAt, long baselineRevision,
                 long surfaceRevision, long persistenceRevision) {

    String baselineGraph() {
        return Graphs.baseline(id, baselineRevision);
    }

    long revision(String name) {
        return switch (name) {
            case "baseline" -> baselineRevision;
            case "surface" -> surfaceRevision;
            default -> persistenceRevision;
        };
    }

    Workspace revised(String name, long revision, Instant at) {
        return switch (name) {
            case "baseline" -> new Workspace(id, label, createdAt, at, revision, surfaceRevision, persistenceRevision);
            case "surface" -> new Workspace(id, label, createdAt, at, baselineRevision, revision, persistenceRevision);
            default -> new Workspace(id, label, createdAt, at, baselineRevision, surfaceRevision, revision);
        };
    }

    Model toModel() {
        Model model = ModelFactory.createDefaultModel();
        Resource node = model.createResource(Graphs.workspace(id));
        node.addProperty(RDF.type, Cst.Workspace);
        node.addProperty(RDFS.label, label);
        node.addProperty(Cst.createdAt, model.createTypedLiteral(createdAt.toString(), XSDDatatype.XSDdateTime));
        node.addProperty(Cst.modifiedAt, model.createTypedLiteral(modifiedAt.toString(), XSDDatatype.XSDdateTime));
        node.addProperty(Cst.baselineGraph, model.createResource(baselineGraph()));
        node.addProperty(Cst.baselineRevision, integer(model, baselineRevision));
        node.addProperty(Cst.surfaceRevision, integer(model, surfaceRevision));
        node.addProperty(Cst.persistenceRevision, integer(model, persistenceRevision));
        return model;
    }

    /** Reads a description, or null when the graph holds none or a malformed one. */
    static Workspace from(String id, Model model) {
        Resource node = model.createResource(Graphs.workspace(id));
        try {
            return new Workspace(id, text(node, RDFS.label), Instant.parse(text(node, Cst.createdAt)),
                Instant.parse(text(node, Cst.modifiedAt)), number(node, Cst.baselineRevision),
                number(node, Cst.surfaceRevision), number(node, Cst.persistenceRevision));
        } catch (RuntimeException e) {
            return null;
        }
    }

    private static org.apache.jena.rdf.model.Literal integer(Model model, long n) {
        return model.createTypedLiteral(Long.toString(n), XSDDatatype.XSDinteger);
    }

    private static String text(Resource node, org.apache.jena.rdf.model.Property p) {
        Statement s = node.getProperty(p);
        return s.getLiteral().getLexicalForm();
    }

    private static long number(Resource node, org.apache.jena.rdf.model.Property p) {
        return node.getProperty(p).getLong();
    }
}
