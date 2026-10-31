// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writes;

import java.time.Clock;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.function.Supplier;
import java.util.regex.Pattern;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.graph.Triple;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.sparql.core.Quad;
import org.apache.jena.sparql.core.Var;
import org.apache.jena.sparql.expr.E_NotExists;
import org.apache.jena.sparql.modify.request.UpdateModify;
import org.apache.jena.sparql.syntax.Element;
import org.apache.jena.sparql.syntax.ElementFilter;
import org.apache.jena.sparql.syntax.ElementGroup;
import org.apache.jena.sparql.syntax.ElementNamedGraph;
import org.apache.jena.sparql.syntax.ElementPathBlock;
import org.apache.jena.update.Update;
import org.apache.jena.update.UpdateRequest;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.RDFS;
import org.nebularis.lattice.studio.model.Parts;
import org.nebularis.lattice.studio.model.Workspace;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.Skolem;
import org.nebularis.lattice.studio.store.StudioOperations;
import org.nebularis.lattice.studio.store.StudioOperations.Family;
import org.nebularis.lattice.studio.store.StudioStore;

/**
 * Applies {@link Command}s to the store, a batch in one SPARQL Update request, so the batch costs one commit (TSD-44).
 * The writer of a partition is the only code that writes the graphs of the workspaces routed to it, and it checks every
 * command it receives, whatever its sender checked (STD-298).
 *
 * <p>A command on the workspace's aggregates, its description, parts and documents, runs one generated operation for
 * each aggregate through {@link StudioOperations}, each guarded by the aggregate's version row and in a transaction of its
 * own, {@code urn:txn:{command id}/{n}}. Its {@code cst:Receipt}, with its cause, sender and transaction time (PRI-54), is
 * the last operation, guarded on the claim of the command's last operation, so a guard that fails part way leaves no
 * receipt and the order of the operations leaves nothing a reader acts on (ADR-A149 decision 13). A command on a job or the
 * registry inserts its receipt first, only where its precondition holds, and its other operations are conditional on that
 * receipt. After the commit the receipts present are exactly the commands applied. A command whose receipt already exists
 * was applied before, and is answered from the receipt rather than applied again.
 */
public final class Writer {
    private static final Pattern SAMPLE_ID = Pattern.compile("[a-z0-9][a-z0-9-]*");
    private static final int MAX_LABEL = 500;
    private static final int MAX_TITLE = 200;
    private static final int MAX_DEPENDENCIES = 200;
    /** What a job update may change. Anything else on the job node is the service's and must stay as it wrote it. */
    private static final Set<Property> WORKER_PREDICATES = Set.of(
        Cst.status, Cst.startedAt, Cst.finishedAt, Cst.failureMessage, p("conforms"), p("report"), p("artefact"),
        Cst.lineage, Cst.version, Cst.digest, Cst.unitKind, p("pins"),
        p("gap"), p("resolution"), p("expansion"), p("testResult"));
    private static final List<String> CONFIGS = Workspace.CONFIGS;
    private static final Var S = Var.alloc("s");
    private static final Var P = Var.alloc("p");
    private static final Var O = Var.alloc("o");

    private static final Node CLAIM = NodeFactory.createURI(org.nebularis.lattice.persistence.Namespaces.PAT + "rev");

    private final StudioStore store;
    private final StudioOperations ops;
    private final Clock clock;

    public Writer(StudioStore store, StudioOperations ops, Clock clock) {
        this.store = store;
        this.ops = ops;
        this.clock = clock;
    }

    public Reply apply(Command c) {
        return apply(List.of(c)).get(0);
    }

    /** One reply per command, in order. The commands that pass their checks are applied in one request. */
    public List<Reply> apply(List<Command> batch) {
        Reply[] replies = new Reply[batch.size()];
        Set<String> ids = new HashSet<>();
        for (Command c : batch) {
            if (c != null && Graphs.isId(c.id())) {
                ids.add(c.id());
            }
        }
        Map<String, Long> done = store.receipts(ids);
        Batch b = new Batch();
        for (int i = 0; i < batch.size(); i++) {
            Command c = batch.get(i);
            Reply refused = check(c);
            if (refused != null) {
                replies[i] = refused;
            } else if (done.containsKey(c.id())) {
                replies[i] = Reply.ok(done.get(c.id()));
            } else {
                replies[i] = b.plan(i, c);
            }
        }
        if (!b.planned.isEmpty()) {
            store.update(b.request);
            Map<String, Long> applied = store.receipts(b.planned.keySet());
            b.planned.forEach((id, plan) -> replies[plan.index] = applied.containsKey(id) ? plan.reply : plan.unapplied.get());
        }
        return List.of(replies);
    }

    private static Reply check(Command c) {
        if (c == null || c.type() == null || !Graphs.isId(c.workspace())) {
            return Reply.refused("a write names a workspace by its id");
        }
        if (!Graphs.isId(c.id())) {
            return Reply.refused("a write carries its own id");
        }
        if (c.job() != null && !Graphs.isId(c.job())) {
            return Reply.refused("a write names a job by its id");
        }
        return null;
    }

    /** A command's place in the batch, the reply when its receipt is present after the commit, and the one when not. */
    private record Plan(int index, Reply reply, Supplier<Reply> unapplied) {
    }

    /** The commands of one request, and what the writer knows of each workspace and job as the batch would leave them. */
    private final class Batch {
        final UpdateRequest request = new UpdateRequest();
        final Map<String, Plan> planned = new LinkedHashMap<>();
        final Map<String, Optional<Workspace>> workspaces = new HashMap<>();
        final Map<String, Optional<Model>> jobs = new HashMap<>();
        /** The registry graphs of lineages, as the batch would leave them, so two publishes of one lineage see each other. */
        final Map<String, Model> lineages = new HashMap<>();
        /** The sequence of the descriptions the batch has moved, by root, so two commands on one workspace see each other. */
        final Map<String, Long> seqs = new HashMap<>();
        /** The parts and documents as stored, skolemised, as the batch would leave them, the base of the next delta. */
        final Map<String, Model> rawGraphs = new HashMap<>();

        Optional<Workspace> workspace(String id) {
            return workspaces.computeIfAbsent(id, k -> Optional.ofNullable(ops.workspace(store, k)));
        }

        long seq(Family f, String root) {
            return seqs.computeIfAbsent(root, r -> ops.seq(store, f, r).orElse(0L));
        }

        /** The operations of one command in order, each in a transaction of its own (PB-D10), and its receipt after them. */
        final class Steps {
            final Command c;
            final List<Update> updates = new ArrayList<>();
            final List<String> wrote = new ArrayList<>();
            String first;
            String last;
            private int n;

            Steps(Command c) {
                this.c = c;
            }

            /** Adds what {@code build} makes of the next transaction id, which writes {@code graph}. */
            void op(String graph, java.util.function.Function<String, List<Update>> build) {
                String txn = "urn:txn:" + c.id() + "/" + (++n);
                updates.addAll(build.apply(txn));
                wrote.add(graph);
                first = first == null ? txn : first;
                last = txn;
            }

            void raw(Update u) {
                updates.add(u);
            }

            /** Adds the operations, then the receipt, guarded on the claim of the last operation. */
            void commit(String receipts, Long revision) {
                commit(receipts, last, revision);
            }

            void commit(String receipts, String claim, Long revision) {
                updates.forEach(request::add);
                Node claimed = iri(claim);
                receipt(c, receipts, quad(ops.txnGraph(), claimed, CLAIM, Var.alloc("claimed")), wrote, revision);
            }
        }

        Optional<Model> job(String id) {
            return jobs.computeIfAbsent(id, k -> {
                Model m = store.graph(Graphs.job(k));
                return m.isEmpty() ? Optional.empty() : Optional.of(m);
            });
        }

        /** Null when the command is planned, otherwise the reply it gets without being applied. */
        Reply plan(int index, Command c) {
            Reply denied = access(c);
            if (denied != null) {
                return denied;
            }
            return switch (c.type()) {
                case CREATE -> create(index, c);
                case SAVE -> save(index, c);
                case IMPORT -> importing(index, c);
                case SAVE_DOCUMENT -> saveDocument(index, c);
                case DELETE_DOCUMENT -> deleteDocument(index, c);
                case DELETE_WORKSPACE -> deleteWorkspace(index, c);
                case SUBMIT_JOB -> submitJob(index, c);
                case JOB_UPDATE -> jobUpdate(index, c);
                case DELETE_JOB -> deleteJob(index, c);
                case SET_ACCESS -> setAccess(index, c);
                case PUBLISH -> publish(index, c);
                case SET_DEPENDENCIES -> setDependencies(index, c);
                case FENCE -> fence(index, c);
                case RELEASE -> release(index, c);
            };
        }

        /**
         * Null when the command's principal may make it, else the refusal (ADR-A149 decision 9). A command with no
         * principal is the worker's, for a job it was given. A workspace a principal may not read is not found by them.
         */
        private Reply access(Command c) {
            if (c.principal() == null || c.type() == Command.Type.CREATE || c.type() == Command.Type.IMPORT) {
                return null;
            }
            Optional<Workspace> found = workspace(c.workspace());
            if (found.isEmpty()) {
                return null;
            }
            Workspace ws = found.get();
            if (!ws.readableBy(c.principal(), c.admin())) {
                return Reply.notFound();
            }
            boolean allowed = switch (c.type()) {
                case SAVE, SAVE_DOCUMENT, DELETE_DOCUMENT, PUBLISH, SET_DEPENDENCIES, FENCE, RELEASE -> ws.writableBy(c.principal(), c.admin());
                case DELETE_WORKSPACE, SET_ACCESS -> ws.managedBy(c.principal(), c.admin());
                default -> true;
            };
            return allowed ? null : Reply.forbidden(c.principal() + " may not " + c.type().wire + " in this workspace, which is " + ws.mode());
        }

        /** A workspace's mode in {@code part}, and its owner in {@code label}, which only an administrator moves. */
        private Reply setAccess(int index, Command c) {
            if (!Workspace.MODES.contains(c.part()) || named(c).hasNext() || !c.body().getDefaultModel().isEmpty()) {
                return Reply.refused("a change of access names one of " + Workspace.MODES + " and carries no graph");
            }
            Optional<Workspace> found = workspace(c.workspace());
            if (found.isEmpty()) {
                return Reply.notFound();
            }
            Workspace ws = found.get();
            String owner = c.label() == null ? ws.owner() : c.label();
            if (!java.util.Objects.equals(owner, ws.owner()) && !c.admin()) {
                return Reply.forbidden("only an administrator gives a workspace another owner");
            }
            if (owner == null && !Workspace.SHARED.equals(c.part())) {
                return Reply.refused("a workspace with no owner stays shared");
            }
            return describeOnly(index, c, ws.withAccess(owner, c.part()));
        }

        /** A workspace's dependencies, replaced by the {@code cst:dependsOn} triples of the body. */
        private Reply setDependencies(int index, Command c) {
            Model body = c.body().getDefaultModel();
            Resource node = body.createResource(Graphs.workspace(c.workspace()));
            Set<String> iris = new java.util.TreeSet<>();
            boolean clean = named(c).hasNext() == false && body.size() == body.listStatements(node, Cst.dependsOn, (RDFNode) null).toList().size();
            for (Statement st : body.listStatements(node, Cst.dependsOn, (RDFNode) null).toList()) {
                clean &= st.getObject().isURIResource();
                if (clean) {
                    iris.add(st.getResource().getURI());
                }
            }
            if (!clean || iris.size() > MAX_DEPENDENCIES) {
                return Reply.refused("a change of dependencies is at most " + MAX_DEPENDENCIES + " cst:dependsOn triples of the workspace");
            }
            for (String iri : iris) {
                if (!Graphs.isUnitIri(iri) && !isVersionOfUnit(iri)) {
                    return Reply.refused("a dependency is a published unit or one of its versions: " + iri);
                }
            }
            Optional<Workspace> found = workspace(c.workspace());
            if (found.isEmpty()) {
                return Reply.notFound();
            }
            return describeOnly(index, c, found.get().withDependencies(iris));
        }

        /**
         * Imported RDF into the import of its digest, which is stored once since the same digest is the same content (a create
         * over an existing import writes nothing), then the workspace's holding of it with its label.
         */
        private Reply fence(int index, Command c) {
            Model content = c.body().getDefaultModel();
            if (!Graphs.isDigest(c.part()) || content.isEmpty() || named(c).hasNext()) {
                return Reply.refused("a fence names a digest of 64 lower-case hexadecimal digits and carries the imported graph alone, which is not empty");
            }
            String label = c.label() == null || c.label().isBlank() ? "Import" : c.label();
            if (label.length() > MAX_TITLE) {
                return Reply.refused("an import's label is at most " + MAX_TITLE + " characters");
            }
            Optional<Workspace> found = workspace(c.workspace());
            if (found.isEmpty()) {
                return Reply.notFound();
            }
            Workspace updated = found.get().withImport(Graphs.importGraph(c.part()), label);
            Steps s = new Steps(c);
            s.op(Graphs.importedGraph(c.part()), txn -> ops.create(Family.IMPORT, Graphs.importGraph(c.part()), Skolem.skolemise(content), txn));
            describe(s, updated, false);
            s.commit(Graphs.receipts(updated.id()), null);
            workspaces.put(updated.id(), Optional.of(updated));
            return planned(index, c, Reply.ok(), () -> changed(updated.id()));
        }

        /** The workspace stops holding an import. The import stays, since other workspaces may hold it and it is never tombstoned. */
        private Reply release(int index, Command c) {
            Optional<Workspace> found = workspace(c.workspace());
            if (found.isEmpty() || !Graphs.isDigest(c.part()) || !found.get().imports().containsKey(Graphs.importGraph(c.part()))) {
                return Reply.notFound();
            }
            return describeOnly(index, c, found.get().withImport(Graphs.importGraph(c.part()), null));
        }

        /** A command that only changes the description. */
        private Reply describeOnly(int index, Command c, Workspace updated) {
            Steps s = new Steps(c);
            describe(s, updated, false);
            s.commit(Graphs.receipts(updated.id()), null);
            workspaces.put(updated.id(), Optional.of(updated));
            return planned(index, c, Reply.ok(), () -> changed(updated.id()));
        }

        /** The reply for a command whose receipt is absent although its precondition held when it was read, since another writer moved the workspace. */
        private Reply changed(String id) {
            return ops.workspace(store, id) == null ? Reply.notFound() : Reply.refused("the workspace changed while the command was applied, so send it again");
        }

        private boolean isVersionOfUnit(String iri) {
            int at = iri.lastIndexOf("/rev/1-");
            return at > 0 && Graphs.isUnitIri(iri.substring(0, at)) && iri.substring(at + 7).matches("[0-9a-f]{16}");
        }

        /** The description first created or replaced, as the last step of a command that writes one. */
        private void describe(Steps s, Workspace updated, boolean create) {
            String root = Graphs.workspace(updated.id());
            Model body = Skolem.skolemise(updated.stored());
            if (create) {
                s.op(Graphs.description(updated.id()), txn -> ops.create(Family.DESCRIPTION, root, body, txn));
                seqs.put(root, 1L);
            } else {
                long seq = seq(Family.DESCRIPTION, root);
                s.op(Graphs.description(updated.id()), txn -> ops.replace(Family.DESCRIPTION, root, seq, body, null, null, txn));
                seqs.put(root, seq + 1);
            }
        }

        /** Part or document {@code root} created when {@code expect} is 0, otherwise replaced linearly with the delta from what the batch leaves it as. */
        private void write(Steps s, Family f, String root, long expect, Model body) {
            String graph = ops.graph(f, root);
            Model next = Skolem.skolemise(body);
            if (expect == 0) {
                s.op(graph, txn -> ops.create(f, root, next, txn));
            } else {
                Model old = rawGraphs.computeIfAbsent(graph, store::rawGraph);
                Model asserted = next.difference(old);
                Model retracted = old.difference(next);
                s.op(graph, txn -> ops.replaceLinear(f, root, expect, next, asserted, retracted, txn));
            }
            rawGraphs.put(graph, next);
        }

        private Reply create(int index, Command c) {
            if (c.label() == null || c.label().isBlank() || c.label().length() > MAX_LABEL || c.at() == null) {
                return Reply.refused("a creation carries a label of at most " + MAX_LABEL + " characters and a time");
            }
            if (c.sample() != null && !SAMPLE_ID.matcher(c.sample()).matches()) {
                return Reply.refused("a sample id is lower-case letters, digits and hyphens");
            }
            if (named(c).hasNext()) {
                return Reply.refused("a creation carries the baseline alone, in the default graph");
            }
            Model baseline = c.body().getDefaultModel();
            List<String> strangers = Parts.strangers(baseline, "baseline", 5);
            if (!strangers.isEmpty()) {
                return Reply.refused("the baseline holds terms of another part: " + String.join(", ", strangers));
            }
            if (workspace(c.workspace()).isPresent()) {
                return Reply.refused("the workspace exists");
            }
            Workspace ws = Workspace.created(c.workspace(), c.label(), c.at(), c.sample(), c.principal());
            Steps s = new Steps(c);
            write(s, Family.PART, Graphs.partRoot(ws.id(), "baseline"), 0, baseline);
            describe(s, ws, true);
            s.commit(Graphs.receipts(ws.id()), 1L);
            workspaces.put(ws.id(), Optional.of(ws));
            return planned(index, c, Reply.ok(1), () -> Reply.refused("the workspace exists"));
        }

        /** A part is created or replaced, and its version row moves with it. The description is not written, so saves of two parts never contend. */
        private Reply save(int index, Command c) {
            String part = c.part();
            if (part == null || !Workspace.GRAPHS.contains(part) || c.expect() == null || c.at() == null || named(c).hasNext()) {
                return Reply.refused("a save names a graph of the workspace, the revision it expects and a time, and carries the graph alone");
            }
            Model graph = c.body().getDefaultModel();
            List<String> strangers = Parts.strangers(graph, part, 5);
            if (!strangers.isEmpty()) {
                return Reply.refused("the graph holds terms of another part: " + String.join(", ", strangers));
            }
            Optional<Workspace> found = workspace(c.workspace());
            if (found.isEmpty()) {
                return Reply.notFound();
            }
            Workspace ws = found.get();
            if (ws.revision(part) != c.expect()) {
                return Reply.stale(ws.revision(part));
            }
            long next = ws.revision(part) + 1;
            Steps s = new Steps(c);
            write(s, Family.PART, Graphs.partRoot(ws.id(), part), c.expect(), graph);
            s.commit(Graphs.receipts(ws.id()), next);
            workspaces.put(ws.id(), Optional.of(ws.revised(part, next)));
            String id = ws.id();
            return planned(index, c, Reply.ok(next), () -> {
                Workspace now = ops.workspace(store, id);
                return now == null ? Reply.notFound() : Reply.stale(now.revision(part));
            });
        }

        /** A document's graph, and its node in the description when it is new or its title or template changed. */
        private Reply saveDocument(int index, Command c) {
            String doc = c.part();
            if (!Graphs.isId(doc) || c.expect() == null || c.at() == null || c.label() == null || c.label().isBlank()
                || c.label().length() > MAX_TITLE || c.sample() == null || !SAMPLE_ID.matcher(c.sample()).matches() || named(c).hasNext()) {
                return Reply.refused("a document's save names the document, the revision it expects, a time, its title and its template, and carries its graph alone");
            }
            Model graph = c.body().getDefaultModel();
            String problem = documentProblem(graph, doc);
            if (problem != null) {
                return Reply.refused(problem);
            }
            Optional<Workspace> found = workspace(c.workspace());
            if (found.isEmpty()) {
                return Reply.notFound();
            }
            Workspace ws = found.get();
            if (ws.documentRevision(doc) != c.expect()) {
                return Reply.stale(ws.documentRevision(doc));
            }
            long next = c.expect() + 1;
            Workspace.Document held = ws.documents().get(doc);
            boolean described = held != null && held.title().equals(c.label()) && held.template().equals(c.sample());
            Workspace updated = described ? ws.documentRevised(doc, next)
                : ws.withDocument(doc, new Workspace.Document(c.label(), c.sample(), next, c.at()), c.at());
            Steps s = new Steps(c);
            write(s, Family.DOCUMENT, Graphs.document(ws.id(), doc), c.expect(), graph);
            if (!described) {
                describe(s, updated, false);
            }
            s.commit(Graphs.receipts(ws.id()), next);
            workspaces.put(ws.id(), Optional.of(updated));
            String id = ws.id();
            return planned(index, c, Reply.ok(next), () -> {
                Workspace now = ops.workspace(store, id);
                if (now == null) {
                    return Reply.notFound();
                }
                // A deleted document's row stays tombstoned, so its id cannot be created again.
                return now.documentRevision(doc) == c.expect() ? Reply.refused("the document was deleted, so its id cannot be used again")
                    : Reply.stale(now.documentRevision(doc));
            });
        }

        /** The description without the document, then the document tombstoned and its patch log dropped. */
        private Reply deleteDocument(int index, Command c) {
            String doc = c.part();
            if (!Graphs.isId(doc) || named(c).hasNext() || !c.body().getDefaultModel().isEmpty()) {
                return Reply.refused("a document's deletion names the document and carries no graph");
            }
            Optional<Workspace> found = workspace(c.workspace());
            if (found.isEmpty() || !found.get().documents().containsKey(doc)) {
                return Reply.notFound();
            }
            Workspace ws = found.get();
            Steps s = new Steps(c);
            describe(s, ws.withDocument(doc, null, ws.modifiedAt()), false);
            retire(s, c, Family.DOCUMENT, Graphs.document(ws.id(), doc), ws.documentRevision(doc), Graphs.documentGraph(ws.id(), doc));
            s.commit(Graphs.receipts(ws.id()), null);
            workspaces.put(ws.id(), Optional.of(ws.withDocument(doc, null, ws.modifiedAt())));
            return planned(index, c, Reply.ok(), () -> changed(ws.id()));
        }

        /** Tombstones a part or document that has a version row, at {@code revision}, then drops its patch log graphs, up to the tombstone's. */
        private void retire(Steps s, Command c, Family f, String root, long revision, String graph) {
            if (revision == 0) {
                return;
            }
            s.op(graph, txn -> ops.tombstone(f, root, revision, txn, Graphs.receipt(c.id()), actor(c)));
            retireLog(s, f, root, revision);
        }

        private void retireLog(Steps s, Family f, String root, long revision) {
            for (long k = 1; k <= revision + 1; k++) {
                s.raw(StudioStore.drop(ops.revision(f, root, k) + "/add"));
                s.raw(StudioStore.drop(ops.revision(f, root, k) + "/del"));
            }
        }

        /** An import's graphs are named by their roots, under the new workspace's id, which {@code ImportedWorkspace} gave them. */
        private Reply importing(int index, Command c) {
            String id = c.workspace();
            if (c.at() == null || c.label() == null || c.label().isBlank() || c.label().length() > MAX_LABEL
                || !c.body().getDefaultModel().isEmpty()) {
                return Reply.refused("an import carries a label, a time and named graphs only");
            }
            if (workspace(id).isPresent()) {
                return Reply.refused("the workspace exists");
            }
            Workspace ws = Workspace.from(id, c.body().getNamedModel(Graphs.workspace(id)));
            if (ws == null) {
                return Reply.refused("the import holds no workspace description");
            }
            Map<String, Model> parts = new LinkedHashMap<>();
            Map<String, Model> documents = new LinkedHashMap<>();
            for (Iterator<Resource> it = named(c); it.hasNext(); ) {
                String name = it.next().getURI();
                String part = partOf(id, name, ws);
                if (part == null) {
                    return Reply.refused("the import holds a graph that is not one of its workspace's: " + name);
                }
                Model graph = c.body().getNamedModel(name);
                if (part.equals("document")) {
                    String problem = documentProblem(graph, Graphs.documentId(id, name));
                    if (problem != null) {
                        return Reply.refused(problem);
                    }
                    documents.put(Graphs.documentId(id, name), graph);
                } else if (!part.equals("workspace")) {
                    List<String> strangers = Parts.strangers(graph, part, 5);
                    if (!strangers.isEmpty()) {
                        return Reply.refused("the " + part + " graph holds terms of another part: " + String.join(", ", strangers));
                    }
                    parts.put(part, graph);
                }
            }
            // An export leaves out a graph with no triple, and a workspace always has its baseline.
            parts.putIfAbsent("baseline", ModelFactory.createDefaultModel());
            Steps s = new Steps(c);
            Map<String, Long> partRevisions = new HashMap<>();
            Map<String, Long> documentRevisions = new HashMap<>();
            for (String name : Workspace.GRAPHS) {
                if (parts.containsKey(name)) {
                    write(s, Family.PART, Graphs.partRoot(id, name), 0, parts.get(name));
                    partRevisions.put(name, 1L);
                }
            }
            documents.forEach((doc, graph) -> {
                write(s, Family.DOCUMENT, Graphs.document(id, doc), 0, graph);
                documentRevisions.put(doc, 1L);
            });
            Workspace stamped = ws.as(id, c.label(), c.at(), c.principal());
            describe(s, stamped, true);
            s.commit(Graphs.receipts(id), null);
            workspaces.put(id, Optional.of(stamped.withRevisions(partRevisions, documentRevisions)));
            return planned(index, c, Reply.ok(), () -> Reply.refused("the workspace exists"));
        }

        /**
         * The description is tombstoned first, so the receipt, which is guarded on its claim, says the workspace is gone. Then each part
         * and document with a version row is tombstoned and its patch log dropped, and the jobs and the workspace's receipts are
         * cleared. The receipt is kept in the store's own receipt graph.
         */
        private Reply deleteWorkspace(int index, Command c) {
            String id = c.workspace();
            Optional<Workspace> found = workspace(id);
            if (found.isEmpty()) {
                return Reply.notFound();
            }
            Workspace ws = found.get();
            Steps s = new Steps(c);
            String root = Graphs.workspace(id);
            long described = seq(Family.DESCRIPTION, root);
            s.op(Graphs.description(id), txn -> ops.tombstone(Family.DESCRIPTION, root, described, txn, Graphs.receipt(c.id()), actor(c)));
            retireLog(s, Family.DESCRIPTION, root, described);
            for (String name : Workspace.GRAPHS) {
                retire(s, c, Family.PART, Graphs.partRoot(id, name), ws.revision(name), Graphs.config(id, name));
            }
            ws.documents().forEach((doc, d) -> retire(s, c, Family.DOCUMENT, Graphs.document(id, doc), d.revision(), Graphs.documentGraph(id, doc)));
            List<String> cleared = new ArrayList<>();
            store.jobsOf(Graphs.workspace(id)).listSubjects().forEachRemaining(job -> {
                String jobId = job.getURI().substring(Graphs.JOB_PREFIX.length());
                cleared.add(Graphs.job(jobId));
                cleared.add(Graphs.jobInput(jobId));
                cleared.add(Graphs.jobRecord(jobId));
                cleared.add(Graphs.jobReceipts(jobId));
                jobs.put(jobId, Optional.empty());
            });
            cleared.add(Graphs.receipts(id));
            s.wrote.addAll(cleared);
            s.commit(Graphs.STORE_RECEIPTS, s.first, null);
            cleared.forEach(g -> request.add(clear(g, mine(c, Graphs.STORE_RECEIPTS))));
            workspaces.put(id, Optional.empty());
            seqs.remove(root);
            return planned(index, c, Reply.ok(), () -> changed(id));
        }

        private Reply submitJob(int index, Command c) {
            String jobIri = Graphs.job(c.job());
            String input = Graphs.jobInput(c.job());
            if (!names(c).equals(Set.of(jobIri, input)) || !c.body().getDefaultModel().isEmpty()) {
                return Reply.refused("a job's submission carries its job graph and its input graph only");
            }
            Optional<Workspace> found = workspace(c.workspace());
            if (found.isEmpty()) {
                return Reply.notFound();
            }
            Workspace ws = found.get();
            Model description = c.body().getNamedModel(jobIri);
            Resource job = description.createResource(jobIri);
            if (!description.contains(job, RDF.type, Cst.Job)
                || !description.contains(job, Cst.workspace, description.createResource(Graphs.workspace(ws.id())))
                || !description.contains(job, Cst.configGraph, description.createResource(input))
                || !description.contains(job, Cst.baselineGraph, description.createResource(ws.baselineGraph()))
                || !description.contains(job, Cst.status, Cst.Queued)) {
                return Reply.refused("a job names its workspace, its own input, the workspace's baseline and the status Queued");
            }
            Set<RDFNode> contexts = Set.copyOf(description.listObjectsOfProperty(job, Cst.contextGraph).toList());
            Set<RDFNode> parts = CONFIGS.stream().map(part -> (RDFNode) description.createResource(Graphs.config(ws.id(), part))).collect(java.util.stream.Collectors.toSet());
            Set<String> held = ws.imports().keySet().stream().map(Graphs::importedGraphOf).collect(java.util.stream.Collectors.toSet());
            if (!contexts.stream().allMatch(g -> parts.contains(g) || (g.isURIResource() && Graphs.isVersionGraph(g.asResource().getURI()))
                || (g.isURIResource() && held.contains(g.asResource().getURI())))) {
                return Reply.refused("a job's context graphs are configuration parts of its workspace, versions in the registry, or imports the workspace holds");
            }
            if (job(c.job()).isPresent()) {
                return Reply.refused("the job exists");
            }
            String receipts = Graphs.jobReceipts(c.job());
            Element guard = group(exists(ws.id()), notExists(quad(jobIri, iri(jobIri), RDF.type.asNode(), Cst.Job.asNode())));
            receipt(c, receipts, guard, List.of(jobIri, input), null);
            request.add(insert(jobIri, description, mine(c, receipts)));
            request.add(insert(input, c.body().getNamedModel(input), mine(c, receipts)));
            jobs.put(c.job(), Optional.of(description));
            return planned(index, c, Reply.ok(), () -> Reply.refused("the workspace is gone, or the job exists"));
        }

        /**
         * A job's status and results, from the worker or from the service when the job could not be handed over. A job
         * deleted meanwhile stays deleted. Everything on the job node but what {@link #WORKER_PREDICATES} names must be as
         * the service wrote it, so an update cannot move a job to another workspace or point it at another graph.
         */
        private Reply jobUpdate(int index, Command c) {
            String jobIri = Graphs.job(c.job());
            String recordIri = Graphs.jobRecord(c.job());
            Set<String> names = names(c);
            if (!(names.equals(Set.of(jobIri)) || names.equals(Set.of(jobIri, recordIri))) || !c.body().getDefaultModel().isEmpty()) {
                return Reply.refused("a job's update carries its job graph, and an assemble job's its record graph, only");
            }
            Optional<Model> found = job(c.job());
            if (found.isEmpty()) {
                return Reply.notFound();
            }
            Model existing = found.get();
            if (!existing.contains(existing.createResource(jobIri), Cst.workspace, existing.createResource(Graphs.workspace(c.workspace())))) {
                return Reply.refused("the job is not this workspace's");
            }
            Model update = c.body().getNamedModel(jobIri);
            if (!sameValues(serviceTriples(existing, jobIri), serviceTriples(update, jobIri))) {
                return Reply.refused("a job's update may change only its status and results");
            }
            Model record = names.contains(recordIri) ? c.body().getNamedModel(recordIri) : null;
            if (record != null) {
                if (!existing.contains(existing.createResource(jobIri), Cst.kind, Cst.Assemble)) {
                    return Reply.refused("only an assemble job's update carries a record graph");
                }
                String term = foreignTerm(record);
                if (term != null) {
                    return Reply.refused("a record graph holds a term that is not Wording's, PROV's or Foundation's: " + term);
                }
            }
            String receipts = Graphs.jobReceipts(c.job());
            receipt(c, receipts, quad(jobIri, iri(jobIri), Cst.workspace.asNode(), iri(Graphs.workspace(c.workspace()))),
                record == null ? List.of(jobIri) : List.of(jobIri, recordIri), null);
            request.add(clear(jobIri, mine(c, receipts)));
            request.add(insert(jobIri, update, mine(c, receipts)));
            if (record != null) {
                request.add(clear(recordIri, mine(c, receipts)));
                request.add(insert(recordIri, record, mine(c, receipts)));
            }
            jobs.put(c.job(), Optional.of(update));
            return planned(index, c, Reply.ok(), Reply::notFound);
        }

        /**
         * One version of a lineage into the registry. The version's graph is immutable and stored once by its digest. The
         * lineage's graph holds its identity, its versions, the current one and the chain of publication events. The
         * guard is the current version the writer read, so a publication that lost a race is refused and the chain
         * never forks. A version that is already current changes nothing and answers "current".
         */
        private Reply publish(int index, Command c) {
            String lineage = c.part();
            String version = c.label();
            if (!Graphs.isUnitIri(lineage) || version == null || named(c).hasNext()) {
                return Reply.refused("a publication names a lineage that is an absolute http, https or urn IRI the studio did not mint, a version, and carries the version's graph alone");
            }
            if (!version.matches(Pattern.quote(lineage) + "/rev/1-[0-9a-f]{16}")) {
                return Reply.refused("a version is its lineage's IRI, /rev/1- and 16 lower-case hexadecimal digits");
            }
            Model content = c.body().getDefaultModel();
            if (!content.contains(content.createResource(version), Cst.Fnd.hasIdentity, content.createResource(lineage))) {
                return Reply.refused("a version's graph states that the version has the lineage as its identity");
            }
            if (workspace(c.workspace()).isEmpty()) {
                return Reply.notFound();
            }
            String lineageGraph = Graphs.lineage(lineage);
            Model registry = lineages.computeIfAbsent(lineage, k -> store.graph(lineageGraph));
            Resource unit = registry.createResource(lineage);
            Resource previous = registry.listObjectsOfProperty(unit, Cst.current).toList().stream()
                .filter(RDFNode::isURIResource).map(RDFNode::asResource).findFirst().orElse(null);
            long last = 0;
            Resource lastEvent = null;
            for (Statement s : registry.listStatements(null, Cst.sequence, (RDFNode) null).toList()) {
                if (s.getObject().isLiteral() && s.getObject().asLiteral().getLong() > last) {
                    last = s.getObject().asLiteral().getLong();
                    lastEvent = s.getSubject();
                }
            }
            if (previous != null && previous.getURI().equals(version)) {
                return new Reply(200, last, "current");
            }
            long next = last + 1;
            String digest = version.substring(version.length() - 16);
            String versionGraph = Graphs.version(lineage, digest);
            String event = lineage + "/evt/e1/" + String.format("%06d", next);
            Model add = ModelFactory.createDefaultModel();
            Resource unitAdd = add.createResource(lineage).addProperty(RDF.type, Cst.Fnd.PersistentIdentity)
                .addProperty(Cst.Fnd.hasVersion, add.createResource(version)).addProperty(Cst.current, add.createResource(version));
            Resource e = add.createResource(event).addProperty(RDF.type, Cst.Publication).addProperty(RDF.type, Cst.Prov.Activity)
                .addLiteral(Cst.sequence, add.createTypedLiteral(next))
                .addProperty(Cst.Prov.generated, add.createResource(version))
                .addProperty(Cst.fromWorkspace, add.createResource(Graphs.workspace(c.workspace())))
                .addProperty(Cst.publishedAt, add.createTypedLiteral(clock.instant().toString(), XSDDatatype.XSDdateTime));
            if (c.principal() != null) {
                e.addProperty(Cst.principal, c.principal());
            }
            if (lastEvent != null) {
                e.addProperty(Cst.previousPublication, add.createResource(lastEvent.getURI()));
            }
            if (previous != null) {
                add.createResource(previous.getURI()).addProperty(Cst.Fnd.supersededBy, add.createResource(version));
            }
            String receipts = Graphs.receipts(c.workspace());
            Node unitNode = iri(lineage);
            Element guard = previous == null
                ? group(notExists(quad(lineageGraph, unitNode, Cst.current.asNode(), Var.alloc("current"))))
                : quad(lineageGraph, unitNode, Cst.current.asNode(), previous.asNode());
            receipt(c, receipts, guard, List.of(versionGraph, lineageGraph), next);
            // The same digest is the same content, so a version graph that exists is left as it is.
            request.add(insert(versionGraph, content, group(mine(c, receipts), notExists(quad(versionGraph, S, P, O)))));
            request.add(deleteOf(lineageGraph, unitNode, Cst.current.asNode(), mine(c, receipts)));
            // A version published again after being superseded is no longer superseded.
            request.add(deleteOf(lineageGraph, iri(version), Cst.Fnd.supersededBy.asNode(), mine(c, receipts)));
            request.add(insert(lineageGraph, add, mine(c, receipts)));
            registry.removeAll(unit, Cst.current, null);
            registry.removeAll(registry.createResource(version), Cst.Fnd.supersededBy, null);
            registry.add(add);
            return planned(index, c, Reply.ok(next), () -> {
                lineages.remove(lineage);
                return Reply.refused("the lineage was published meanwhile, so publish again");
            });
        }

        private Reply deleteJob(int index, Command c) {
            String jobIri = Graphs.job(c.job());
            Optional<Model> found = job(c.job());
            if (found.isEmpty()) {
                return Reply.notFound();
            }
            Model existing = found.get();
            if (!existing.contains(existing.createResource(jobIri), Cst.workspace, existing.createResource(Graphs.workspace(c.workspace())))) {
                return Reply.refused("the job is not this workspace's");
            }
            List<String> graphs = List.of(jobIri, Graphs.jobInput(c.job()), Graphs.jobRecord(c.job()), Graphs.jobReceipts(c.job()));
            String receipts = Graphs.receipts(c.workspace());
            receipt(c, receipts, quad(jobIri, iri(jobIri), Cst.workspace.asNode(), iri(Graphs.workspace(c.workspace()))), graphs, null);
            graphs.forEach(g -> request.add(clear(g, mine(c, receipts))));
            jobs.put(c.job(), Optional.empty());
            return planned(index, c, Reply.ok(), Reply::notFound);
        }

        private Reply planned(int index, Command c, Reply reply, Supplier<Reply> unapplied) {
            planned.put(c.id(), new Plan(index, reply, unapplied));
            return null;
        }

        /** Inserts the command's receipt where {@code guard} holds. Every other operation of the command needs it. */
        private void receipt(Command c, String graph, Element guard, Iterable<String> wrote, Long revision) {
            Node g = iri(graph);
            Node r = iri(Graphs.receipt(c.id()));
            UpdateModify u = new UpdateModify();
            add(u, g, r, RDF.type.asNode(), Cst.Receipt.asNode());
            add(u, g, r, Cst.commandId.asNode(), NodeFactory.createLiteralString(c.id()));
            add(u, g, r, Cst.command.asNode(), NodeFactory.createLiteralString(c.type().wire));
            add(u, g, r, Cst.workspace.asNode(), iri(Graphs.workspace(c.workspace())));
            if (c.job() != null) {
                add(u, g, r, Cst.job.asNode(), iri(Graphs.job(c.job())));
            }
            if (c.sender() != null) {
                add(u, g, r, Cst.sender.asNode(), NodeFactory.createLiteralString(c.sender()));
            }
            if (c.principal() != null) {
                add(u, g, r, Cst.principal.asNode(), NodeFactory.createLiteralString(c.principal()));
            }
            if (c.at() != null) {
                add(u, g, r, Cst.requestedAt.asNode(), NodeFactory.createLiteralDT(c.at().toString(), XSDDatatype.XSDdateTime));
            }
            add(u, g, r, Cst.committedAt.asNode(), NodeFactory.createLiteralDT(clock.instant().toString(), XSDDatatype.XSDdateTime));
            for (String w : wrote) {
                add(u, g, r, Cst.wrote.asNode(), iri(w));
            }
            if (revision != null) {
                add(u, g, r, Cst.receiptRevision.asNode(), NodeFactory.createLiteralDT(Long.toString(revision), XSDDatatype.XSDinteger));
            }
            u.setHasInsertClause(true);
            u.setElement(guard);
            request.add(u);
        }
    }

    // --- the operations, built with Jena's typed API, never from strings (PRI-55) -----------------------------------

    /** The command's own receipt, which every operation after its first requires. */
    private static Element mine(Command c, String receipts) {
        return quad(receipts, iri(Graphs.receipt(c.id())), Cst.commandId.asNode(), NodeFactory.createLiteralString(c.id()));
    }

    private static Element exists(String ws) {
        return quad(Graphs.description(ws), iri(Graphs.workspace(ws)), RDF.type.asNode(), Cst.Workspace.asNode());
    }

    /** Who asked, as an IRI, for a tombstone's actor. */
    private static String actor(Command c) {
        return c.principal() != null ? "urn:lattice:studio:principal:" + Graphs.encodeForUri(c.principal())
            : "urn:lattice:studio:sender:" + Graphs.encodeForUri(c.sender() == null ? "unknown" : c.sender());
    }

    /** INSERT where {@code when} holds. Its one solution mints each blank node of the graph once. */
    private static UpdateModify insert(String graph, Model m, Element when) {
        UpdateModify u = new UpdateModify();
        Node g = iri(graph);
        m.getGraph().find().forEachRemaining(t -> u.getInsertAcc().addQuad(Quad.create(g, t)));
        u.setHasInsertClause(true);
        u.setElement(when);
        return u;
    }

    /** Deletes every triple of a graph, where {@code when} holds. */
    private static UpdateModify clear(String graph, Element when) {
        UpdateModify u = new UpdateModify();
        u.getDeleteAcc().addQuad(Quad.create(iri(graph), S, P, O));
        u.setHasDeleteClause(true);
        u.setElement(group(when, quad(graph, S, P, O)));
        return u;
    }

    /** Deletes every {@code s p ?o} of a graph, where {@code when} holds. */
    private static UpdateModify deleteOf(String graph, Node s, Node p, Element when) {
        UpdateModify u = new UpdateModify();
        u.getDeleteAcc().addQuad(Quad.create(iri(graph), s, p, O));
        u.setHasDeleteClause(true);
        u.setElement(group(when, quad(graph, s, p, O)));
        return u;
    }

    /** Replaces a graph that holds no blank node, where {@code when} holds: one solution per old triple, one template. */
    private static UpdateModify replace(String graph, Model m, Element when) {
        UpdateModify u = clear(graph, when);
        Node g = iri(graph);
        m.getGraph().find().forEachRemaining(t -> u.getInsertAcc().addQuad(Quad.create(g, t)));
        u.setHasInsertClause(true);
        return u;
    }

    private static void add(UpdateModify u, Node g, Node s, Node p, Node o) {
        u.getInsertAcc().addQuad(Quad.create(g, s, p, o));
    }

    private static Element quad(String graph, Node s, Node p, Node o) {
        ElementPathBlock block = new ElementPathBlock();
        block.addTriple(Triple.create(s, p, o));
        return new ElementNamedGraph(iri(graph), block);
    }

    private static Element group(Element... elements) {
        ElementGroup group = new ElementGroup();
        for (Element e : elements) {
            group.addElement(e);
        }
        return group;
    }

    /** Wrapped in a group, since Jena writes a bare {@code GRAPH} inside {@code NOT EXISTS} without the braces SPARQL needs. */
    private static Element notExists(Element e) {
        return new ElementFilter(new E_NotExists(e instanceof ElementGroup ? e : group(e)));
    }

    private static Node iri(String iri) {
        return NodeFactory.createURI(iri);
    }

    // --- checks ------------------------------------------------------------------------------------------------------

    /** "workspace", a part's name or "document" for a graph, named by its root, of workspace {@code id}, or null. */
    private static String partOf(String id, String graph, Workspace ws) {
        if (graph.equals(Graphs.workspace(id))) {
            return "workspace";
        }
        for (String name : Workspace.GRAPHS) {
            if (graph.equals(Graphs.partRoot(id, name))) {
                return name;
            }
        }
        String doc = Graphs.documentId(id, graph);
        return doc != null && ws.documents().containsKey(doc) ? "document" : null;
    }

    private static final Set<String> RECORD_NAMESPACES = Set.of(
        "https://www.nebularis.org/neuro-semantic/lattice/wording#", "https://www.nebularis.org/neuro-semantic/lattice/foundation#",
        "http://www.w3.org/ns/prov#", RDF.getURI(), RDFS.getURI());

    /** A predicate, or a type, of {@code record} outside Wording, Foundation, PROV, RDF and RDFS, or null. */
    private static String foreignTerm(Model record) {
        for (Statement s : record.listStatements().toList()) {
            String p = s.getPredicate().getURI();
            if (RECORD_NAMESPACES.stream().noneMatch(p::startsWith)) {
                return p;
            }
            if (s.getPredicate().equals(RDF.type) && s.getObject().isURIResource()
                && RECORD_NAMESPACES.stream().noneMatch(s.getObject().asResource().getURI()::startsWith)) {
                return s.getObject().asResource().getURI();
            }
        }
        return null;
    }

    private static final Set<String> DOCUMENT_NAMESPACES = Set.of(
        "https://www.nebularis.org/neuro-semantic/lattice/wording#",
        "https://www.nebularis.org/neuro-semantic/lattice/poc/word-authoring#",
        "http://purl.org/dc/terms/", RDF.getURI(), RDFS.getURI());

    /**
     * Why a document's graph is not one, or null: every subject is a named node under the document's own IRIs, every
     * predicate and type is Wording's, the authoring vocabulary's, Dublin Core's, RDF's or RDFS's, and the document's
     * node holds its markup once, as {@code cst:markup}.
     */
    static String documentProblem(Model graph, String doc) {
        if (doc == null) {
            return "a document's graph is named by its document's id";
        }
        String own = Graphs.documentNode(doc);
        for (Statement s : graph.listStatements().toList()) {
            if (!s.getSubject().isURIResource() || !s.getSubject().getURI().startsWith(own)) {
                return "a document's graph describes its own nodes only, under " + own;
            }
            if (s.getPredicate().equals(Cst.markup)) {
                continue;
            }
            if (DOCUMENT_NAMESPACES.stream().noneMatch(ns -> s.getPredicate().getURI().startsWith(ns))
                || (s.getPredicate().equals(RDF.type) && (!s.getObject().isURIResource()
                    || DOCUMENT_NAMESPACES.stream().noneMatch(ns -> s.getObject().asResource().getURI().startsWith(ns))))) {
                return "a document's graph holds a term that is not Wording's: " + s.getPredicate().getURI();
            }
        }
        List<Statement> markup = graph.listStatements(graph.createResource(own), Cst.markup, (RDFNode) null).toList();
        if (markup.size() != 1 || !markup.get(0).getObject().isLiteral() || graph.listStatements(null, Cst.markup, (RDFNode) null).toList().size() != 1) {
            return "a document's node holds its markup once, as cst:markup";
        }
        return null;
    }

    private static Model serviceTriples(Model m, String jobIri) {
        Model out = ModelFactory.createDefaultModel();
        m.listStatements(m.createResource(jobIri), null, (RDFNode) null).forEachRemaining((Statement s) -> {
            if (!WORKER_PREDICATES.contains(s.getPredicate())) {
                out.add(s);
            }
        });
        return out;
    }

    /**
     * The job node's own statements, compared by value: rdflib writes an {@code xsd:dateTime} that Jena wrote with
     * {@code Z} back with {@code +00:00}, which is the same value under another lexical form (TSD-63).
     */
    private static boolean sameValues(Model a, Model b) {
        if (a.size() != b.size()) {
            return false;
        }
        for (Statement s : a.listStatements().toList()) {
            boolean found = false;
            for (Statement o : b.listStatements(s.getSubject(), s.getPredicate(), (RDFNode) null).toList()) {
                found |= o.getObject().asNode().sameValueAs(s.getObject().asNode());
            }
            if (!found) {
                return false;
            }
        }
        return true;
    }

    private static Iterator<Resource> named(Command c) {
        return c.body().listModelNames();
    }

    private static Set<String> names(Command c) {
        Set<String> out = new HashSet<>();
        named(c).forEachRemaining(r -> out.add(r.getURI()));
        return out;
    }

    private static Property p(String name) {
        return org.apache.jena.rdf.model.ResourceFactory.createProperty(Cst.NS + name);
    }
}
