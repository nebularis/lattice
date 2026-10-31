// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.model;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
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
                        Map<String, Document> documents, String owner, String mode, Set<String> dependencies) {

    /** Read and written by its owner and administrators only (ADR-A149 decision 9). */
    public static final String LOCKED = "locked";
    /** Read by everyone signed in, written by its owner and administrators. */
    public static final String READ_ONLY = "read-only";
    /** Read and written by everyone signed in, and the mode of a workspace with no owner. */
    public static final String SHARED = "shared";
    public static final List<String> MODES = List.of(LOCKED, READ_ONLY, SHARED);

    /** Whether {@code principal} may read it. */
    public boolean readableBy(String principal, boolean admin) {
        return admin || !LOCKED.equals(mode) || (owner != null && owner.equals(principal));
    }

    /** Whether {@code principal} may change its configuration. */
    public boolean writableBy(String principal, boolean admin) {
        return admin || SHARED.equals(mode) || (owner != null && owner.equals(principal));
    }

    /** Whether {@code principal} may delete it or change its mode: its owner or an administrator. */
    public boolean managedBy(String principal, boolean admin) {
        return admin || (owner != null && owner.equals(principal));
    }

    /** The same workspace with another owner and mode. */
    public Workspace withAccess(String newOwner, String newMode) {
        return new Workspace(id, label, createdAt, modifiedAt, revisions, sample, documents, newOwner, newMode, dependencies);
    }

    /** The same workspace depending on {@code iris}, each a published lineage it follows or a version it pins. */
    public Workspace withDependencies(Set<String> iris) {
        return new Workspace(id, label, createdAt, modifiedAt, revisions, sample, documents, owner, mode, Set.copyOf(new TreeSet<>(iris)));
    }

    /** A document of the workspace, as its description holds it. */
    public record Document(String title, String template, long revision, Instant modifiedAt) {
    }

    /** The baseline, then the configurations, in the order the contract lists them. */
    public static final String SAMPLE_PREFIX = "urn:lattice:studio:sample:";

    public static final List<String> GRAPHS = List.of("baseline", "library", "assembly", "meaning", "review", "mapping", "vocabulary", "quantification",
        "eligibility", "surface", "persistence");

    /** The configuration parts, which are the graphs but the baseline. */
    public static final List<String> CONFIGS = GRAPHS.subList(1, GRAPHS.size());

    /** {@code sample} is the id of the sample it was made from, or null. */
    public static Workspace created(String id, String label, Instant at, String sample) {
        return created(id, label, at, sample, null);
    }

    /** {@code owner} is the principal who made it, shared until they choose another mode. */
    public static Workspace created(String id, String label, Instant at, String sample, String owner) {
        Map<String, Long> revisions = new LinkedHashMap<>();
        for (String name : GRAPHS) {
            revisions.put(name, name.equals("baseline") ? 1L : 0L);
        }
        return new Workspace(id, label, at, at, Map.copyOf(revisions), sample, Map.of(), owner, SHARED, Set.of());
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
        return new Workspace(id, label, createdAt, at, Map.copyOf(next), sample, documents, owner, mode, dependencies);
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
        return new Workspace(id, label, createdAt, at, revisions, sample, Map.copyOf(next), owner, mode, dependencies);
    }

    /** The same workspace under another id and label, as an import makes it, owned by who imports it and shared. */
    public Workspace as(String newId, String newLabel, Instant at, String newOwner) {
        return new Workspace(newId, newLabel, createdAt, at, revisions, sample, documents, newOwner, SHARED, dependencies);
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
        if (owner != null) {
            node.addProperty(Cst.owner, owner);
        }
        node.addProperty(Cst.mode, Cst.mode(mode));
        new TreeSet<>(dependencies).forEach(d -> node.addProperty(Cst.dependsOn, model.createResource(d)));
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
            // A workspace from before modes has no owner and is shared.
            Statement mode = node.getProperty(Cst.mode);
            String m = mode == null ? SHARED : Cst.modeName(mode.getResource());
            if (m == null) {
                return null;
            }
            Statement owner = node.getProperty(Cst.owner);
            Set<String> dependencies = new TreeSet<>();
            node.listProperties(Cst.dependsOn).forEachRemaining(st -> dependencies.add(st.getResource().getURI()));
            return new Workspace(id, text(node, RDFS.label), Instant.parse(text(node, Cst.createdAt)),
                Instant.parse(text(node, Cst.modifiedAt)), Map.copyOf(revisions), sample, Map.copyOf(documents),
                owner == null ? null : owner.getString(), m, Set.copyOf(dependencies));
        } catch (RuntimeException e) {
            return null;
        }
    }

    private static String text(Resource node, Property p) {
        return node.getProperty(p).getLiteral().getLexicalForm();
    }
}
