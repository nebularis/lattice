// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.store;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.query.ParameterizedSparqlString;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.sparql.core.Quad;
import org.apache.jena.sparql.core.Var;
import org.apache.jena.sparql.modify.request.UpdateModify;
import org.apache.jena.sparql.syntax.Element;
import org.apache.jena.sparql.syntax.ElementGroup;
import org.apache.jena.sparql.syntax.ElementOptional;
import org.apache.jena.sparql.syntax.PatternVars;
import org.apache.jena.update.Update;
import org.apache.jena.update.UpdateFactory;
import org.nebularis.lattice.persistence.CallerCheck;
import org.nebularis.lattice.persistence.Iri;
import org.nebularis.lattice.persistence.Namespaces;
import org.nebularis.lattice.persistence.OperationContract;
import org.nebularis.lattice.persistence.OperationKind;
import org.nebularis.lattice.persistence.ParameterContract;
import org.nebularis.lattice.persistence.Payload;
import org.nebularis.lattice.persistence.RequestDigest;
import org.nebularis.lattice.studio.model.Workspace;

/**
 * The operations the persistence compiler generated for the studio's profiles (ADR-A149 decisions 12 and 13), ready to run.
 * {@link #load} reads the folder the stage tool wrote, and each operation method returns the {@link Update}s to add to one
 * request. Every parameter is checked by the caller library before anything is built, the request digest is the profile's,
 * and a payload with a blank node is refused (skolemise it first, {@link Skolem#skolemise}). The class sends nothing, and reads the store
 * only in {@link #seq}, {@link #claimed}, {@link #workspace} and {@link #asOf}.
 */
public final class StudioOperations {
    /** The studio's aggregate families, each the target of one persistence profile. */
    public enum Family {
        DESCRIPTION("Workspace"), PART("Part"), DOCUMENT("Document"), LINEAGE("Lineage"), VERSION("PublishedVersion"), IMPORT("FencedImport");

        private final String target;

        Family(String target) {
            this.target = target;
        }
    }

    private static final Set<OperationKind> USED = Set.of(OperationKind.CREATE, OperationKind.REPLACE, OperationKind.TOMBSTONE);
    private static final Pattern SLOT = Pattern.compile("\\{\\{\\{([A-Za-z]+)\\}\\}\\}");
    private static final Set<Var> SWEPT = Set.of(Var.alloc("s"), Var.alloc("p"), Var.alloc("o"));
    /** The namespace of the marker triple a payload slot is filled with before parsing, replaced by the payload's quads after. */
    private static final String MARKER = "urn:lattice:studio:slot:";

    private record Operation(OperationContract contract, String text) {
    }

    private final long epoch;
    private final Map<Family, Map<OperationKind, Operation>> operations;
    private final String txnGraph;

    private StudioOperations(long epoch, Map<Family, Map<OperationKind, Operation>> operations, String txnGraph) {
        this.epoch = epoch;
        this.operations = operations;
        this.txnGraph = txnGraph;
    }

    /**
     * Reads {@code folder/profile.ttl} and the text of the create, replace and tombstone of every family. A contract belongs to
     * the family whose target the profile names for it ({@code dal:forTarget}), and its text is {@code {target}/{dal:forOperation}.rq}.
     * A missing family or operation, or a second contract for one, fails here and not at the first write.
     */
    public static StudioOperations load(Path folder, long epoch) {
        Model profile = RDFDataMgr.loadModel(folder.resolve("profile.ttl").toUri().toString());
        Property generated = profile.createProperty(Namespaces.DAL + "generatedOperation");
        Property forTarget = profile.createProperty(Namespaces.DAL + "forTarget");
        Property forOperation = profile.createProperty(Namespaces.DAL + "forOperation");
        Map<Family, Map<OperationKind, Operation>> found = new EnumMap<>(Family.class);
        for (OperationContract contract : OperationContract.read(profile)) {
            if (!USED.contains(contract.kind()) || contract.node() == null) {
                continue;
            }
            List<Resource> owners = profile.listSubjectsWithProperty(generated, contract.node()).toList();
            if (owners.size() != 1 || !owners.get(0).hasProperty(forTarget)) {
                throw new IllegalStateException(contract.templateId() + " is generated for " + owners.size() + " targets, not one");
            }
            String targetIri = owners.get(0).getPropertyResourceValue(forTarget).getURI();
            String target = targetIri.substring(targetIri.lastIndexOf('#') + 1);
            Family family = null;
            for (Family f : Family.values()) {
                if (f.target.equals(target)) {
                    family = f;
                }
            }
            if (family == null) {
                continue;
            }
            String name = contract.node().asResource().getProperty(forOperation).getString();
            Path file = folder.resolve(target).resolve(name + ".rq");
            try {
                Operation previous = found.computeIfAbsent(family, k -> new EnumMap<>(OperationKind.class))
                    .put(contract.kind(), new Operation(contract, Files.readString(file, StandardCharsets.UTF_8)));
                if (previous != null) {
                    throw new IllegalStateException(target + " has two " + contract.kind() + " operations");
                }
            } catch (IOException e) {
                throw new UncheckedIOException("cannot read " + file, e);
            }
        }
        Set<String> txnGraphs = new HashSet<>();
        for (Family f : Family.values()) {
            for (OperationKind k : USED) {
                Operation op = found.getOrDefault(f, Map.of()).get(k);
                if (op == null) {
                    throw new IllegalStateException("the staged profile has no " + k + " operation for " + f.target);
                }
                txnGraphs.add(graphOf(op.contract, "txnGraph"));
            }
        }
        if (txnGraphs.size() != 1) {
            throw new IllegalStateException("the operations name more than one transaction graph, " + txnGraphs);
        }
        return new StudioOperations(epoch, found, txnGraphs.iterator().next());
    }

    private static String graphOf(OperationContract contract, String binding) {
        String text = contract.binding(binding).orElseThrow(() -> new IllegalStateException(contract.templateId() + " has no " + binding + " binding"));
        return text.substring(1, text.length() - 1);
    }

    private Operation operation(Family f, OperationKind kind) {
        return operations.get(f).get(kind);
    }

    /** The graph of {@code root} in family {@code f}, by the profile's naming rule. */
    public String graph(Family f, String root) {
        return CallerCheck.graphName(operation(f, OperationKind.CREATE).contract, Iri.of(root));
    }

    /** The revision named by the root, the epoch and the sequence, 19 digits each (PB-D10). */
    public String revision(Family f, String root, long seq) {
        return String.format("urn:rev:studio/%s/e%019d/%019d", encodeForUri(root), epoch, seq);
    }

    private static String encodeForUri(String text) {
        return Graphs.encodeForUri(text);
    }

    // ---- reads

    /** The graph that holds every transaction's claim, which a command's receipt is guarded on. */
    public String txnGraph() {
        return txnGraph;
    }

    private String metaGraph(Family f) {
        return graphOf(operation(f, OperationKind.CREATE).contract, "metaGraphPrefix");
    }

    /** Runs a read beside the caller's, so two reads of one request cost one round trip and not two. */
    public static <T> java.util.concurrent.CompletableFuture<T> beside(java.util.function.Supplier<T> read) {
        return java.util.concurrent.CompletableFuture.supplyAsync(read, BESIDE);
    }

    private static final java.util.concurrent.ExecutorService BESIDE = java.util.concurrent.Executors.newVirtualThreadPerTaskExecutor();

    /**
     * The workspace {@code id} as the service sees it, or null when the store holds none. Its description and its parts' version rows
     * are read at once, then the rows of the documents the description lists, when it lists any, each row by its root.
     */
    public Workspace workspace(StudioStore store, String id) {
        String prefix = Graphs.workspace(id);
        Map<String, String> parts = new HashMap<>();
        Workspace.GRAPHS.forEach(name -> parts.put(Graphs.partRoot(id, name), metaGraph(Family.PART)));
        var partRows = beside(() -> store.versionRows(parts));
        Model description = store.graph(graph(Family.DESCRIPTION, prefix));
        Resource node = description.createResource(prefix);
        if (!description.contains(node, org.apache.jena.vocabulary.RDF.type, Cst.Workspace)) {
            partRows.cancel(false);
            return null;
        }
        Map<String, String> documents = new HashMap<>();
        node.listProperties(Cst.document).forEachRemaining(st -> {
            if (st.getObject().isURIResource()) {
                documents.put(st.getResource().getURI(), metaGraph(Family.DOCUMENT));
            }
        });
        Map<String, Long> rows = new HashMap<>(partRows.join());
        rows.putAll(store.versionRows(documents));
        return Workspace.from(id, description, partRevisions(rows, id), documentRevisions(rows, id));
    }

    private static Map<String, Long> partRevisions(Map<String, Long> rows, String id) {
        Map<String, Long> out = new HashMap<>();
        for (String name : Workspace.GRAPHS) {
            Long seq = rows.get(Graphs.partRoot(id, name));
            if (seq != null) {
                out.put(name, seq);
            }
        }
        return out;
    }

    private static Map<String, Long> documentRevisions(Map<String, Long> rows, String id) {
        Map<String, Long> out = new HashMap<>();
        rows.forEach((root, seq) -> {
            String doc = Graphs.documentId(id, root);
            if (doc != null) {
                out.put(doc, seq);
            }
        });
        return out;
    }

    /**
     * {@code root}'s graph as it was at revision {@code at}, rebuilt from the current graph, at revision {@code current}, by
     * undoing each later revision's delta from the newest back, with each skolem IRI read as a blank node.
     */
    public Model asOf(StudioStore store, Family f, String root, long current, long at) {
        Model m = store.rawGraph(graph(f, root));
        for (long k = current; k > at; k--) {
            String rev = revision(f, root, k);
            m.remove(store.rawGraph(rev + "/add"));
            m.add(store.rawGraph(rev + "/del"));
        }
        return Skolem.unskolemise(m);
    }

    /** The sequence of {@code root}'s version row, empty when it has no row or it is tombstoned. */
    public Optional<Long> seq(StudioStore store, Family f, String root) {
        return store.versionSeq(graphOf(operation(f, OperationKind.CREATE).contract, "metaGraphPrefix"), root);
    }

    /** The revision that transaction {@code txnId} claimed, empty when it has claimed none. */
    public Optional<String> claimed(StudioStore store, String txnId) {
        return store.claimRev(txnGraph, txnId);
    }

    // ---- operations

    /** Creates the aggregate at sequence 1, writing nothing when it has a version row or the transaction has a claim. */
    public List<Update> create(Family f, String root, Model payload, String txnId) {
        Operation op = operation(f, OperationKind.CREATE);
        Map<String, Object> values = common(f, root, txnId, 1);
        values.put("payloadTriples", payload);
        return List.of(build(op, values));
    }

    /**
     * Replaces the aggregate with {@code payload} when its version row is at {@code expectedSeq}, the generated {@code cas-replace}.
     * {@code asserted} and {@code retracted} are the patch log's delta, used where the family's operation has those slots.
     */
    public List<Update> replace(Family f, String root, long expectedSeq, Model payload, Model asserted, Model retracted, String txnId) {
        return List.of(replaceUpdate(f, root, expectedSeq, payload, asserted, retracted, txnId));
    }

    /**
     * The replace of a part or a document as its delta (TD-136): the generated replace with its sweep taken out, the retracted
     * triples deleted from the graph and the asserted ones inserted, so a save writes what changed and not the whole part. The version
     * row move, the claim, the receipt, the patch log and the request digest are as generated, the digest over {@code payload}, the
     * state the write leaves. It is derived from the generated syntax tree, never from its text. It is right only when the stored graph
     * is the state {@code asserted} and {@code retracted} were computed from, which the guard on {@code expectedSeq} gives as long as
     * every write of the graph is one of these operations.
     */
    public List<Update> replaceDelta(Family f, String root, long expectedSeq, Model payload, Model asserted, Model retracted, String txnId) {
        if (f != Family.PART && f != Family.DOCUMENT) {
            throw new IllegalArgumentException("a delta replace is for a part or a document, not " + f);
        }
        UpdateModify generated = (UpdateModify) replaceUpdate(f, root, expectedSeq, payload, asserted, retracted, txnId,
            Map.of("payloadTriples", asserted));
        List<Quad> sweeps = generated.getDeleteQuads().stream().filter(StudioOperations::isSweep).toList();
        ElementGroup where = generated.getWherePattern() instanceof ElementGroup g ? g : null;
        List<Element> optionals = where == null ? List.of() : where.getElements().stream().filter(StudioOperations::isSweep).toList();
        if (sweeps.size() != 1 || optionals.size() != 1) {
            throw new IllegalStateException("the generated replace has " + sweeps.size() + " sweep quads and " + optionals.size() + " sweep patterns, not one of each");
        }
        UpdateModify write = new UpdateModify();
        generated.getDeleteQuads().stream().filter(q -> q != sweeps.get(0)).forEach(q -> write.getDeleteAcc().addQuad(q));
        org.apache.jena.graph.Node graph = sweeps.get(0).getGraph();
        retracted.getGraph().find().forEachRemaining(tr -> write.getDeleteAcc().addQuad(Quad.create(graph, tr)));
        generated.getInsertQuads().forEach(q -> write.getInsertAcc().addQuad(q));
        write.setHasDeleteClause(true);
        write.setHasInsertClause(true);
        ElementGroup rest = new ElementGroup();
        where.getElements().stream().filter(e -> e != optionals.get(0)).forEach(rest::addElement);
        write.setElement(rest);
        return List.of(write);
    }

    /** Deletes the aggregate and marks its version row deleted when the row is at {@code expectedSeq}. */
    public List<Update> tombstone(Family f, String root, long expectedSeq, String txnId, String cause, String actor) {
        Operation op = operation(f, OperationKind.TOMBSTONE);
        Map<String, Object> values = common(f, root, txnId, expectedSeq + 1);
        values.put("expectedSeq", expectedSeq);
        values.put("cause", Iri.of(cause));
        values.put("actor", Iri.of(actor));
        return List.of(build(op, values));
    }

    private Update replaceUpdate(Family f, String root, long expectedSeq, Model payload, Model asserted, Model retracted, String txnId) {
        return replaceUpdate(f, root, expectedSeq, payload, asserted, retracted, txnId, Map.of());
    }

    private Update replaceUpdate(Family f, String root, long expectedSeq, Model payload, Model asserted, Model retracted, String txnId,
                                 Map<String, Model> written) {
        Operation op = operation(f, OperationKind.REPLACE);
        Map<String, Object> values = common(f, root, txnId, expectedSeq + 1);
        values.put("expectedSeq", expectedSeq);
        values.put("payloadTriples", payload);
        if (asserted != null) {
            values.put("assertTriples", asserted);
        }
        if (retracted != null) {
            values.put("retractTriples", retracted);
        }
        return build(op, values, written);
    }

    /** The parameters every operation has, with the revision it mints at {@code seq}. */
    private Map<String, Object> common(Family f, String root, String txnId, long seq) {
        Map<String, Object> values = new HashMap<>();
        values.put("root", Iri.of(root));
        values.put("epoch", epoch);
        values.put("nextSeq", seq);
        values.put("newRev", Iri.of(revision(f, root, seq)));
        values.put("txnId", Iri.of(txnId));
        values.put("g", Iri.of(graph(f, root)));
        return values;
    }

    private static Payload payload(Model model) {
        return Payload.ofJena(model.getGraph().find().toList());
    }

    /**
     * Checks the request, binds its parameters as typed terms, fills its slots and parses it. A payload is given as a {@link Model}.
     * Each payload slot is filled with one marker triple, and the parsed request's marker quads are then replaced by the payload's
     * quads in the marker's graph, so a payload is never written out as text and parsed again, which cost a large part's save most of
     * its time in the writer. The parameters are bound before any slot is filled, so nothing in a payload is ever read as a variable.
     */
    private Update build(Operation op, Map<String, Object> given) {
        return build(op, given, Map.of());
    }

    /** As {@link #build(Operation, Map)}, with each slot named in {@code written} filled with that graph rather than the one digested. */
    private Update build(Operation op, Map<String, Object> given, Map<String, Model> written) {
        OperationContract contract = op.contract;
        Map<String, Object> values = new HashMap<>();
        Map<String, Model> payloads = new HashMap<>();
        for (ParameterContract p : contract.parameters()) {
            if (p.kind().equals("Payload")) {
                Model m = given.get(p.name()) instanceof Model model ? model : org.apache.jena.rdf.model.ModelFactory.createDefaultModel();
                payloads.put(p.name(), m);
                values.put(p.name(), payload(m));
            } else if (given.containsKey(p.name())) {
                values.put(p.name(), given.get(p.name()));
            }
        }
        if (contract.parameter("requestDigest").isPresent()) {
            values.put("requestDigest", RequestDigest.requestDigest(contract, values));
        }
        CallerCheck.check(contract, values);
        ParameterizedSparqlString bound = new ParameterizedSparqlString(op.text);
        Map<String, String> slots = new HashMap<>();
        for (ParameterContract p : contract.parameters()) {
            Object value = values.get(p.name());
            if (value == null) {
                continue;
            }
            switch (p.kind()) {
                case "Iri" -> bound.setParam(p.name(), NodeFactory.createURI(((Iri) value).value()));
                case "Long", "Position" -> bound.setParam(p.name(), NodeFactory.createLiteralDT(value.toString(), XSDDatatype.XSDlong));
                case "Digest", "String" -> bound.setParam(p.name(), NodeFactory.createLiteralString((String) value));
                case "Payload" -> slots.put(p.name(), "<" + MARKER + p.name() + "> <" + MARKER + p.name() + "> <" + MARKER + p.name() + "> .");
                default -> throw new IllegalStateException("parameter " + p.name() + " of kind " + p.kind() + " is not one the studio binds");
            }
        }
        Matcher m = SLOT.matcher(bound.toString());
        String text = m.replaceAll(r -> {
            String slot = slots.get(r.group(1));
            if (slot == null) {
                throw new IllegalStateException(contract.templateId() + " has a slot " + r.group(1) + " that the request does not fill");
            }
            return Matcher.quoteReplacement(slot);
        });
        Map<String, Model> spliced = new HashMap<>(payloads);
        spliced.putAll(written);
        return splice((UpdateModify) UpdateFactory.create(text).getOperations().get(0), spliced, contract.templateId());
    }

    /** The parsed request with each marker quad replaced by its payload's triples in the marker's graph, in the template's order. */
    private static UpdateModify splice(UpdateModify parsed, Map<String, Model> payloads, String template) {
        if (parsed.getWherePattern() != null && parsed.getWherePattern().toString().contains(MARKER)) {
            throw new IllegalStateException(template + " has a payload slot in its WHERE clause, which the studio does not fill");
        }
        UpdateModify out = new UpdateModify();
        out.setWithIRI(parsed.getWithIRI());
        parsed.getUsing().forEach(out::addUsing);
        parsed.getUsingNamed().forEach(out::addUsingNamed);
        spliced(parsed.getDeleteQuads(), payloads).forEach(out.getDeleteAcc()::addQuad);
        spliced(parsed.getInsertQuads(), payloads).forEach(out.getInsertAcc()::addQuad);
        out.setHasDeleteClause(parsed.hasDeleteClause());
        out.setHasInsertClause(parsed.hasInsertClause());
        out.setElement(parsed.getWherePattern());
        return out;
    }

    private static List<Quad> spliced(List<Quad> quads, Map<String, Model> payloads) {
        List<Quad> out = new java.util.ArrayList<>();
        for (Quad q : quads) {
            String s = q.getSubject().isURI() ? q.getSubject().getURI() : "";
            if (s.startsWith(MARKER)) {
                payloads.get(s.substring(MARKER.length())).getGraph().find().forEachRemaining(t -> out.add(Quad.create(q.getGraph(), t)));
            } else {
                out.add(q);
            }
        }
        return out;
    }

    /** A quad that deletes every triple of a graph, as {@code ?s ?p ?o}. */
    private static boolean isSweep(Quad q) {
        return q.getSubject().isVariable() && q.getPredicate().isVariable() && q.getObject().isVariable();
    }

    /** The {@code OPTIONAL} that binds every triple of the graph for the sweep to delete. */
    private static boolean isSweep(Element e) {
        return e instanceof ElementOptional o && PatternVars.vars(o.getOptionalElement()).equals(SWEPT);
    }
}
