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
 * A workspace as the service sees it. The description aggregate ({@link #stored}) holds its label, owner, mode,
 * dependencies, the imports it holds with their labels and each document's title, template and time, and no revision. A
 * part's revision is its version row's sequence and a document's likewise, 0 with no row, so the service's view
 * ({@link #toModel}) adds {@code cst:<name>Revision}, each document's revision and the baseline part's graph.
 * {@code imports} maps the roots of the imports it holds to their labels.
 */
public record Workspace(String id, String label, Instant createdAt, Instant modifiedAt, Map<String, Long> revisions, String sample,
                        Map<String, Document> documents, String owner, String mode, Set<String> dependencies,
                        Map<String, String> imports) {

    /** Read and written by its owner and administrators only (ADR-A149 decision 9). */
    public static final String LOCKED = "locked";
    /** Read by everyone signed in, written by its owner and administrators. */
    public static final String READ_ONLY = "read-only";
    /** Read and written by everyone signed in, and the mode of a workspace with no owner. */
    public static final String SHARED = "shared";
    public static final List<String> MODES = List.of(LOCKED, READ_ONLY, SHARED);

    /** Whether {@code principal} may read it. */
    public boolean readableBy(String principal, boolean admin) {
        return readable(mode, owner, principal, admin);
    }

    /** As {@link #readableBy}, from a workspace's mode and owner alone, which a summary holds. */
    public static boolean readable(String mode, String owner, String principal, boolean admin) {
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
        return new Workspace(id, label, createdAt, modifiedAt, revisions, sample, documents, newOwner, newMode, dependencies, imports);
    }

    /** The same workspace depending on {@code iris}, each a published lineage it follows or a version it pins. */
    public Workspace withDependencies(Set<String> iris) {
        return new Workspace(id, label, createdAt, modifiedAt, revisions, sample, documents, owner, mode, Set.copyOf(new TreeSet<>(iris)), imports);
    }

    /** The same workspace holding import graph {@code graph} under {@code importLabel}, or no longer holding it when the label is null. */
    public Workspace withImport(String graph, String importLabel) {
        Map<String, String> next = new TreeMap<>(imports);
        if (importLabel == null) {
            next.remove(graph);
        } else {
            next.put(graph, importLabel);
        }
        return new Workspace(id, label, createdAt, modifiedAt, revisions, sample, documents, owner, mode, dependencies, Map.copyOf(next));
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
        return new Workspace(id, label, at, at, Map.copyOf(revisions), sample, Map.of(), owner, SHARED, Set.of(), Map.of());
    }

    /** The graph of the baseline part, which jobs read as saved (PB-D12). */
    public String baselineGraph() {
        return Graphs.baseline(id);
    }

    public long revision(String name) {
        return revisions.getOrDefault(name, 0L);
    }

    /** The same workspace with part {@code name} at {@code revision}. Its description is not written, so {@code modifiedAt} stays. */
    public Workspace revised(String name, long revision) {
        Map<String, Long> next = new LinkedHashMap<>(revisions);
        next.put(name, revision);
        return new Workspace(id, label, createdAt, modifiedAt, Map.copyOf(next), sample, documents, owner, mode, dependencies, imports);
    }

    /** The same workspace with these revisions, those of its parts by name and of its documents by id, 0 for a name or an id they lack. */
    public Workspace withRevisions(Map<String, Long> partRevisions, Map<String, Long> documentRevisions) {
        Map<String, Long> parts = new LinkedHashMap<>();
        GRAPHS.forEach(name -> parts.put(name, partRevisions.getOrDefault(name, 0L)));
        Map<String, Document> docs = new TreeMap<>();
        documents.forEach((doc, d) -> docs.put(doc, new Document(d.title(), d.template(), documentRevisions.getOrDefault(doc, 0L), d.modifiedAt())));
        return new Workspace(id, label, createdAt, modifiedAt, Map.copyOf(parts), sample, Map.copyOf(docs), owner, mode, dependencies, imports);
    }

    /** The same workspace with document {@code doc} at {@code revision}, its description unchanged. */
    public Workspace documentRevised(String doc, long revision) {
        Document d = documents.get(doc);
        return d == null ? this : withDocumentUnchanged(doc, new Document(d.title(), d.template(), revision, d.modifiedAt()));
    }

    private Workspace withDocumentUnchanged(String doc, Document document) {
        Map<String, Document> next = new TreeMap<>(documents);
        next.put(doc, document);
        return new Workspace(id, label, createdAt, modifiedAt, revisions, sample, Map.copyOf(next), owner, mode, dependencies, imports);
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
        return new Workspace(id, label, createdAt, at, revisions, sample, Map.copyOf(next), owner, mode, dependencies, imports);
    }

    /** The same workspace under another id and label, as an import makes it, owned by who imports it and shared. */
    public Workspace as(String newId, String newLabel, Instant at, String newOwner) {
        return new Workspace(newId, newLabel, createdAt, at, revisions, sample, documents, newOwner, SHARED, dependencies, imports);
    }

    /** What the description aggregate holds. It names no revision, and names the baseline part's graph nowhere. */
    public Model stored() {
        Model model = ModelFactory.createDefaultModel();
        Resource node = model.createResource(Graphs.workspace(id));
        node.addProperty(RDF.type, Cst.Workspace);
        node.addProperty(RDFS.label, label);
        node.addProperty(Cst.createdAt, model.createTypedLiteral(createdAt.toString(), XSDDatatype.XSDdateTime));
        node.addProperty(Cst.modifiedAt, model.createTypedLiteral(modifiedAt.toString(), XSDDatatype.XSDdateTime));
        if (sample != null) {
            node.addProperty(Cst.fromSample, model.createResource(SAMPLE_PREFIX + sample));
        }
        if (owner != null) {
            node.addProperty(Cst.owner, owner);
        }
        node.addProperty(Cst.mode, Cst.mode(mode));
        new TreeSet<>(dependencies).forEach(d -> node.addProperty(Cst.dependsOn, model.createResource(d)));
        new TreeMap<>(imports).forEach((graph, importLabel) -> {
            node.addProperty(Cst.holdsImport, model.createResource(graph));
            model.createResource(graph).addProperty(RDFS.label, importLabel);
        });
        new TreeMap<>(documents).forEach((doc, d) -> {
            Resource document = model.createResource(Graphs.document(id, doc));
            node.addProperty(Cst.document, document);
            document.addProperty(RDF.type, Cst.Document);
            document.addProperty(RDFS.label, d.title());
            document.addProperty(Cst.template, d.template());
            document.addProperty(Cst.modifiedAt, model.createTypedLiteral(d.modifiedAt().toString(), XSDDatatype.XSDdateTime));
        });
        return model;
    }

    /** The service's view: the stored description with every revision and the baseline part's graph. */
    public Model toModel() {
        Model model = stored();
        Resource node = model.createResource(Graphs.workspace(id));
        node.addProperty(Cst.baselineGraph, model.createResource(baselineGraph()));
        for (String name : GRAPHS) {
            node.addProperty(Cst.revision(name), model.createTypedLiteral(Long.toString(revision(name)), XSDDatatype.XSDinteger));
        }
        documents.forEach((doc, d) -> model.createResource(Graphs.document(id, doc)).addProperty(Cst.documentRevision,
            model.createTypedLiteral(Long.toString(d.revision()), XSDDatatype.XSDinteger)));
        return model;
    }

    /** Reads a stored description alone, every revision 0. */
    public static Workspace from(String id, Model description) {
        return from(id, description, Map.of(), Map.of());
    }

    /**
     * Reads a stored description with the revisions of its parts by name and of its documents by id, 0 for any they lack. It is
     * null when the graph holds no {@code cst:Workspace} or a malformed one.
     */
    public static Workspace from(String id, Model description, Map<String, Long> partRevisions, Map<String, Long> documentRevisions) {
        Resource node = description.createResource(Graphs.workspace(id));
        if (!description.contains(node, RDF.type, Cst.Workspace)) {
            return null;
        }
        try {
            Map<String, Long> revisions = new LinkedHashMap<>();
            for (String name : GRAPHS) {
                revisions.put(name, partRevisions.getOrDefault(name, 0L));
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
                documents.put(doc, new Document(text(d, RDFS.label), text(d, Cst.template), documentRevisions.getOrDefault(doc, 0L),
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
            Map<String, String> imports = new TreeMap<>();
            node.listProperties(Cst.holdsImport).forEachRemaining(st -> {
                Resource g = st.getResource();
                if (!Graphs.isImportGraph(g.getURI())) {
                    throw new IllegalArgumentException("not an import graph");
                }
                imports.put(g.getURI(), text(g, RDFS.label));
            });
            return new Workspace(id, text(node, RDFS.label), Instant.parse(text(node, Cst.createdAt)),
                Instant.parse(text(node, Cst.modifiedAt)), Map.copyOf(revisions), sample, Map.copyOf(documents),
                owner == null ? null : owner.getString(), m, Set.copyOf(dependencies), Map.copyOf(imports));
        } catch (RuntimeException e) {
            return null;
        }
    }

    private static String text(Resource node, Property p) {
        return node.getProperty(p).getLiteral().getLexicalForm();
    }
}
