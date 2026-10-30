// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.model;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
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
 * description lacks reads as 0, so a workspace made before a graph was added still opens. It names each document of the
 * workspace's library with its title, template, revision and time, by the document's id.
 */
public record Workspace(String id, String label, Instant createdAt, Instant modifiedAt, Map<String, Long> revisions, String sample,
                        Map<String, Document> documents) {

    /** A document of the workspace, as its description holds it. */
    public record Document(String title, String template, long revision, Instant modifiedAt) {
    }

    /** The baseline, then the configurations, in the order the contract lists them. */
    public static final String SAMPLE_PREFIX = "urn:lattice:studio:sample:";

    public static final List<String> GRAPHS = List.of("baseline", "library", "assembly", "meaning", "review", "mapping", "vocabulary", "quantification",
        "eligibility", "surface", "persistence");

    /** {@code sample} is the id of the sample it was made from, or null. */
    public static Workspace created(String id, String label, Instant at, String sample) {
        Map<String, Long> revisions = new LinkedHashMap<>();
        for (String name : GRAPHS) {
            revisions.put(name, name.equals("baseline") ? 1L : 0L);
        }
        return new Workspace(id, label, at, at, Map.copyOf(revisions), sample, Map.of());
    }

    public String baselineGraph() {
        return Graphs.baseline(id, revision("baseline"));
    }

    public long revision(String name) {
        return revisions.getOrDefault(name, 0L);
    }

    public Workspace revised(String name, long revision, Instant at) {
        Map<String, Long> next = new LinkedHashMap<>(revisions);
        next.put(name, revision);
        return new Workspace(id, label, createdAt, at, Map.copyOf(next), sample, documents);
    }

    /** The revision of document {@code doc}, 0 when the workspace holds none. */
    public long documentRevision(String doc) {
        Document d = documents.get(doc);
        return d == null ? 0L : d.revision();
    }

    /** The workspace with document {@code doc} saved as {@code document}, or removed when it is null. */
    public Workspace withDocument(String doc, Document document, Instant at) {
        Map<String, Document> next = new TreeMap<>(documents);
        if (document == null) {
            next.remove(doc);
        } else {
            next.put(doc, document);
        }
        return new Workspace(id, label, createdAt, at, revisions, sample, Map.copyOf(next));
    }

    /** The same workspace under another id and label, as an import makes it. */
    public Workspace as(String newId, String newLabel, Instant at) {
        return new Workspace(newId, newLabel, createdAt, at, revisions, sample, documents);
    }

    public Model toModel() {
        Model model = ModelFactory.createDefaultModel();
        Resource node = model.createResource(Graphs.workspace(id));
        node.addProperty(RDF.type, Cst.Workspace);
        node.addProperty(RDFS.label, label);
        node.addProperty(Cst.createdAt, model.createTypedLiteral(createdAt.toString(), XSDDatatype.XSDdateTime));
        node.addProperty(Cst.modifiedAt, model.createTypedLiteral(modifiedAt.toString(), XSDDatatype.XSDdateTime));
        node.addProperty(Cst.baselineGraph, model.createResource(baselineGraph()));
        if (sample != null) {
            node.addProperty(Cst.fromSample, model.createResource(SAMPLE_PREFIX + sample));
        }
        for (String name : GRAPHS) {
            node.addProperty(Cst.revision(name), model.createTypedLiteral(Long.toString(revision(name)), XSDDatatype.XSDinteger));
        }
        new TreeMap<>(documents).forEach((doc, d) -> {
            Resource document = model.createResource(Graphs.document(id, doc));
            node.addProperty(Cst.document, document);
            document.addProperty(RDF.type, Cst.Document);
            document.addProperty(RDFS.label, d.title());
            document.addProperty(Cst.template, d.template());
            document.addProperty(Cst.documentRevision, model.createTypedLiteral(Long.toString(d.revision()), XSDDatatype.XSDinteger));
            document.addProperty(Cst.modifiedAt, model.createTypedLiteral(d.modifiedAt().toString(), XSDDatatype.XSDdateTime));
        });
        return model;
    }

    /** Reads a description, or null when the graph holds none or a malformed one. */
    public static Workspace from(String id, Model model) {
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
            Statement from = node.getProperty(Cst.fromSample);
            String sample = from == null ? null : from.getResource().getURI().substring(SAMPLE_PREFIX.length());
            Map<String, Document> documents = new TreeMap<>();
            node.listProperties(Cst.document).forEachRemaining(st -> {
                Resource d = st.getResource();
                String doc = Graphs.documentId(id, d.getURI());
                if (doc == null) {
                    throw new IllegalArgumentException("a document of another workspace");
                }
                documents.put(doc, new Document(text(d, RDFS.label), text(d, Cst.template), d.getProperty(Cst.documentRevision).getLong(),
                    Instant.parse(text(d, Cst.modifiedAt))));
            });
            return new Workspace(id, text(node, RDFS.label), Instant.parse(text(node, Cst.createdAt)),
                Instant.parse(text(node, Cst.modifiedAt)), Map.copyOf(revisions), sample, Map.copyOf(documents));
        } catch (RuntimeException e) {
            return null;
        }
    }

    private static String text(Resource node, Property p) {
        return node.getProperty(p).getLiteral().getLexicalForm();
    }
}
