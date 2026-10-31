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
import org.apache.jena.sparql.expr.E_NotEquals;
import org.apache.jena.sparql.expr.E_NotExists;
import org.apache.jena.sparql.expr.ExprVar;
import org.apache.jena.sparql.expr.NodeValue;
import org.apache.jena.sparql.modify.request.UpdateModify;
import org.apache.jena.sparql.syntax.Element;
import org.apache.jena.sparql.syntax.ElementFilter;
import org.apache.jena.sparql.syntax.ElementGroup;
import org.apache.jena.sparql.syntax.ElementNamedGraph;
import org.apache.jena.sparql.syntax.ElementPathBlock;
import org.apache.jena.update.UpdateRequest;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.RDFS;
import org.nebularis.lattice.studio.model.Parts;
import org.nebularis.lattice.studio.model.Workspace;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.StudioStore;

/**
 * Applies {@link Command}s to the store, a batch in one SPARQL Update request, so the batch costs one commit (TSD-44).
 * The writer of a partition is the only code that writes the graphs of the workspaces routed to it, and it checks every
 * command it receives, whatever its sender checked (STD-298).
 *
 * <p>Each command's first operation inserts its receipt, a {@code cst:Receipt} with its cause, sender and transaction
 * time (PRI-54), only where the command's precondition holds in the store, such as a save's expected revision (PAT-21).
 * Its other operations are conditional on that receipt. So a command applies whole or not at all even if another writer
 * were to hold its workspace, and after the commit the receipts present are exactly the commands applied. A command whose
 * receipt already exists was applied before, and is answered from the receipt rather than applied again.
 */
public final class Writer {
    private static final Pattern SAMPLE_ID = Pattern.compile("[a-z0-9][a-z0-9-]*");
    private static final int MAX_LABEL = 500;
    private static final int MAX_TITLE = 200;
    /** What a job update may change. Anything else on the job node is the service's and must stay as it wrote it. */
    private static final Set<Property> WORKER_PREDICATES = Set.of(
        Cst.status, Cst.startedAt, Cst.finishedAt, Cst.failureMessage, p("conforms"), p("report"), p("artefact"),
        p("gap"), p("resolution"), p("expansion"), p("testResult"));
    private static final List<String> CONFIGS = Workspace.CONFIGS;
    private static final Var S = Var.alloc("s");
    private static final Var P = Var.alloc("p");
    private static final Var O = Var.alloc("o");

    private final StudioStore store;
    private final Clock clock;

    public Writer(StudioStore store, Clock clock) {
        this.store = store;
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

        Optional<Workspace> workspace(String id) {
            return workspaces.computeIfAbsent(id, k -> Optional.ofNullable(Workspace.from(k, store.graph(Graphs.workspace(k)))));
        }

        Optional<Model> job(String id) {
            return jobs.computeIfAbsent(id, k -> {
                Model m = store.graph(Graphs.job(k));
                return m.isEmpty() ? Optional.empty() : Optional.of(m);
            });
        }

        /** Null when the command is planned, otherwise the reply it gets without being applied. */
        Reply plan(int index, Command c) {
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
            };
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
            Workspace ws = Workspace.created(c.workspace(), c.label(), c.at(), c.sample());
            Map<String, Model> graphs = new LinkedHashMap<>();
            graphs.put(Graphs.workspace(ws.id()), ws.toModel());
            graphs.put(ws.baselineGraph(), baseline);
            String receipts = Graphs.receipts(ws.id());
            receipt(c, receipts, absent(ws.id()), graphs.keySet(), 1L);
            graphs.forEach((g, m) -> request.add(insert(g, m, mine(c, receipts))));
            workspaces.put(ws.id(), Optional.of(ws));
            return planned(index, c, Reply.ok(1), () -> Reply.refused("the workspace exists"));
        }

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
            Workspace updated = ws.revised(part, next, c.at());
            String target = part.equals("baseline") ? updated.baselineGraph() : Graphs.config(ws.id(), part);
            String receipts = Graphs.receipts(ws.id());
            receipt(c, receipts, revisionIs(ws.id(), part, c.expect()), List.of(target, Graphs.workspace(ws.id())), next);
            // The graph and the revision move in one request, so they never disagree.
            request.add(clear(target, mine(c, receipts)));
            request.add(insert(target, graph, mine(c, receipts)));
            request.add(replace(Graphs.workspace(ws.id()), updated.toModel(), mine(c, receipts)));
            workspaces.put(ws.id(), Optional.of(updated));
            String id = ws.id();
            return planned(index, c, Reply.ok(next), () -> {
                Workspace now = Workspace.from(id, store.graph(Graphs.workspace(id)));
                return now == null ? Reply.notFound() : Reply.stale(now.revision(part));
            });
        }

        /** A document's graph and its node in the description move in one request, guarded by its revision. */
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
            Workspace updated = ws.withDocument(doc, new Workspace.Document(c.label(), c.sample(), next, c.at()), c.at());
            String target = Graphs.document(ws.id(), doc);
            String receipts = Graphs.receipts(ws.id());
            receipt(c, receipts, documentRevisionIs(ws.id(), doc, c.expect()), List.of(target, Graphs.workspace(ws.id())), next);
            request.add(clear(target, mine(c, receipts)));
            request.add(insert(target, graph, mine(c, receipts)));
            request.add(replace(Graphs.workspace(ws.id()), updated.toModel(), mine(c, receipts)));
            workspaces.put(ws.id(), Optional.of(updated));
            String id = ws.id();
            return planned(index, c, Reply.ok(next), () -> {
                Workspace now = Workspace.from(id, store.graph(Graphs.workspace(id)));
                return now == null ? Reply.notFound() : Reply.stale(now.documentRevision(doc));
            });
        }

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
            Workspace updated = ws.withDocument(doc, null, ws.modifiedAt());
            String target = Graphs.document(ws.id(), doc);
            String receipts = Graphs.receipts(ws.id());
            Element guard = quad(Graphs.workspace(ws.id()), iri(Graphs.workspace(ws.id())), Cst.document.asNode(), iri(target));
            receipt(c, receipts, guard, List.of(target, Graphs.workspace(ws.id())), null);
            request.add(clear(target, mine(c, receipts)));
            request.add(replace(Graphs.workspace(ws.id()), updated.toModel(), mine(c, receipts)));
            workspaces.put(ws.id(), Optional.of(updated));
            return planned(index, c, Reply.ok(), Reply::notFound);
        }

        /** An import's graphs are already under the new workspace's names, which {@code ImportedWorkspace} gave them. */
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
            Map<String, Model> graphs = new LinkedHashMap<>();
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
                } else if (!part.equals("workspace")) {
                    List<String> strangers = Parts.strangers(graph, part, 5);
                    if (!strangers.isEmpty()) {
                        return Reply.refused("the " + part + " graph holds terms of another part: " + String.join(", ", strangers));
                    }
                }
                graphs.put(name, graph);
            }
            Workspace stamped = ws.as(id, c.label(), c.at());
            graphs.put(Graphs.workspace(id), stamped.toModel());
            String receipts = Graphs.receipts(id);
            receipt(c, receipts, absent(id), graphs.keySet(), null);
            graphs.forEach((g, m) -> request.add(insert(g, m, mine(c, receipts))));
            workspaces.put(id, Optional.of(stamped));
            return planned(index, c, Reply.ok(), () -> Reply.refused("the workspace exists"));
        }

        /** Its graphs and its jobs go, and the receipt of the deletion is kept in the store's own receipt graph. */
        private Reply deleteWorkspace(int index, Command c) {
            String id = c.workspace();
            Optional<Workspace> found = workspace(id);
            if (found.isEmpty()) {
                return Reply.notFound();
            }
            List<String> graphs = new ArrayList<>();
            for (long n = 1; n <= found.get().revision("baseline"); n++) {
                graphs.add(Graphs.baseline(id, n));
            }
            for (String name : CONFIGS) {
                graphs.add(Graphs.config(id, name));
            }
            for (String doc : found.get().documents().keySet()) {
                graphs.add(Graphs.document(id, doc));
            }
            store.jobsOf(Graphs.workspace(id)).listSubjects().forEachRemaining(job -> {
                String jobId = job.getURI().substring(Graphs.JOB_PREFIX.length());
                graphs.add(Graphs.job(jobId));
                graphs.add(Graphs.jobInput(jobId));
                graphs.add(Graphs.jobRecord(jobId));
                graphs.add(Graphs.jobReceipts(jobId));
                jobs.put(jobId, Optional.empty());
            });
            graphs.add(Graphs.receipts(id));
            graphs.add(Graphs.workspace(id));
            receipt(c, Graphs.STORE_RECEIPTS, exists(id), graphs, null);
            graphs.forEach(g -> request.add(clear(g, mine(c, Graphs.STORE_RECEIPTS))));
            workspaces.put(id, Optional.empty());
            return planned(index, c, Reply.ok(), Reply::notFound);
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
            if (!CONFIGS.stream().map(part -> (RDFNode) description.createResource(Graphs.config(ws.id(), part))).collect(java.util.stream.Collectors.toSet()).containsAll(contexts)) {
                return Reply.refused("a job's context graphs are configuration parts of its workspace");
            }
            if (job(c.job()).isPresent()) {
                return Reply.refused("the job exists");
            }
            String receipts = Graphs.jobReceipts(c.job());
            Element guard = group(
                quad(Graphs.workspace(ws.id()), iri(Graphs.workspace(ws.id())), Cst.baselineGraph.asNode(), iri(ws.baselineGraph())),
                notExists(quad(jobIri, iri(jobIri), RDF.type.asNode(), Cst.Job.asNode())));
            receipt(c, receipts, guard, List.of(jobIri, input), null);
            request.add(insert(jobIri, description, mine(c, receipts)));
            request.add(insert(input, c.body().getNamedModel(input), mine(c, receipts)));
            jobs.put(c.job(), Optional.of(description));
            return planned(index, c, Reply.ok(), () -> Reply.refused("the workspace's baseline moved, or the job exists"));
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

    /** The stored revision of a part is {@code expect}. A description without one reads as 0, as {@link Workspace} reads it. */
    private static Element revisionIs(String ws, String part, long expect) {
        Node revision = Cst.revision(part).asNode();
        if (expect > 0) {
            return quad(Graphs.workspace(ws), iri(Graphs.workspace(ws)), revision,
                NodeFactory.createLiteralDT(Long.toString(expect), XSDDatatype.XSDinteger));
        }
        Var r = Var.alloc("revision");
        return group(exists(ws), notExists(group(quad(Graphs.workspace(ws), iri(Graphs.workspace(ws)), revision, r),
            new ElementFilter(new E_NotEquals(new ExprVar(r), NodeValue.makeInteger(0))))));
    }

    /** Document {@code doc}'s stored revision is {@code expect}, where 0 means the workspace holds no such document. */
    private static Element documentRevisionIs(String ws, String doc, long expect) {
        Node node = iri(Graphs.document(ws, doc));
        if (expect > 0) {
            return quad(Graphs.workspace(ws), node, Cst.documentRevision.asNode(),
                NodeFactory.createLiteralDT(Long.toString(expect), XSDDatatype.XSDinteger));
        }
        return group(exists(ws), notExists(quad(Graphs.workspace(ws), iri(Graphs.workspace(ws)), Cst.document.asNode(), node)));
    }

    private static Element exists(String ws) {
        return quad(Graphs.workspace(ws), iri(Graphs.workspace(ws)), RDF.type.asNode(), Cst.Workspace.asNode());
    }

    private static Element absent(String ws) {
        return group(notExists(exists(ws)));
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

    /** "workspace", "baseline" or a configuration's name for a graph of workspace {@code id}, or null. */
    private static String partOf(String id, String graph, Workspace ws) {
        if (graph.equals(Graphs.workspace(id))) {
            return "workspace";
        }
        for (long n = 1; n <= ws.revision("baseline"); n++) {
            if (graph.equals(Graphs.baseline(id, n))) {
                return "baseline";
            }
        }
        for (String name : CONFIGS) {
            if (graph.equals(Graphs.config(id, name))) {
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
