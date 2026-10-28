// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writes;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.studio.api.Parts;
import org.nebularis.lattice.studio.api.Workspace;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.StudioStore;

/**
 * Applies one {@link Command} to the store. The writer of a partition is the only code that writes the graphs of the
 * workspaces routed to it, so a revision it reads cannot change before its own update, and it needs no lock. It checks
 * every command it receives, whatever its sender checked, since it cannot know the command was not forged (STD-279).
 */
public final class Writer {
    private static final Pattern SAMPLE_ID = Pattern.compile("[a-z0-9][a-z0-9-]*");
    private static final int MAX_LABEL = 500;
    /** What a job update may change. Anything else on the job node is the service's and must stay as it wrote it. */
    private static final Set<Property> WORKER_PREDICATES = Set.of(
        Cst.status, Cst.startedAt, Cst.finishedAt, Cst.failureMessage, p("conforms"), p("report"), p("artefact"),
        p("gap"), p("resolution"), p("expansion"), p("testResult"));
    private static final List<String> CONFIGS = Workspace.GRAPHS.subList(1, Workspace.GRAPHS.size());

    private final StudioStore store;

    public Writer(StudioStore store) {
        this.store = store;
    }

    public Reply apply(Command c) {
        if (c == null || c.type() == null || !Graphs.isId(c.workspace())) {
            return Reply.refused("a write names a workspace by its id");
        }
        if (c.job() != null && !Graphs.isId(c.job())) {
            return Reply.refused("a write names a job by its id");
        }
        return switch (c.type()) {
            case CREATE -> create(c);
            case SAVE -> save(c);
            case IMPORT -> importing(c);
            case DELETE_WORKSPACE -> deleteWorkspace(c.workspace());
            case SUBMIT_JOB -> submitJob(c);
            case JOB_UPDATE -> jobUpdate(c);
            case DELETE_JOB -> deleteJob(c);
        };
    }

    private Reply create(Command c) {
        if (c.label() == null || c.label().isBlank() || c.label().length() > MAX_LABEL || c.at() == null) {
            return Reply.refused("a creation carries a label of at most " + MAX_LABEL + " characters and a time");
        }
        if (c.sample() != null && !SAMPLE_ID.matcher(c.sample()).matches()) {
            return Reply.refused("a sample id is lower-case letters, digits and hyphens");
        }
        if (named(c).hasNext()) {
            return Reply.refused("a creation carries the baseline alone, in the default graph");
        }
        if (load(c.workspace()) != null) {
            return Reply.refused("the workspace exists");
        }
        Workspace ws = Workspace.created(c.workspace(), c.label(), c.at(), c.sample());
        store.write(List.of(), Map.of(Graphs.workspace(ws.id()), ws.toModel(), ws.baselineGraph(), c.body().getDefaultModel()));
        return Reply.ok(1);
    }

    private Reply save(Command c) {
        String part = c.part();
        if (part == null || !Workspace.GRAPHS.contains(part) || c.expect() == null || c.at() == null || named(c).hasNext()) {
            return Reply.refused("a save names a graph of the workspace, the revision it expects and a time, and carries the graph alone");
        }
        Model graph = c.body().getDefaultModel();
        List<String> strangers = Parts.strangers(graph, part, 5);
        if (!strangers.isEmpty()) {
            return Reply.refused("the graph holds terms of another part: " + String.join(", ", strangers));
        }
        Workspace ws = load(c.workspace());
        if (ws == null) {
            return Reply.notFound();
        }
        if (ws.revision(part) != c.expect()) {
            return Reply.stale(ws.revision(part));
        }
        long next = ws.revision(part) + 1;
        Workspace updated = ws.revised(part, next, c.at());
        String target = part.equals("baseline") ? updated.baselineGraph() : Graphs.config(ws.id(), part);
        // The graph and the revision move in one update request, so they never disagree.
        store.write(List.of(), Map.of(target, graph, Graphs.workspace(ws.id()), updated.toModel()));
        return Reply.ok(next);
    }

    /** An import's graphs are already under the new workspace's names, which {@code ImportedWorkspace} gave them. */
    private Reply importing(Command c) {
        String id = c.workspace();
        if (c.at() == null || c.label() == null || c.label().isBlank() || c.label().length() > MAX_LABEL
            || !c.body().getDefaultModel().isEmpty()) {
            return Reply.refused("an import carries a label, a time and named graphs only");
        }
        if (load(id) != null) {
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
            if (!part.equals("workspace")) {
                List<String> strangers = Parts.strangers(graph, part, 5);
                if (!strangers.isEmpty()) {
                    return Reply.refused("the " + part + " graph holds terms of another part: " + String.join(", ", strangers));
                }
            }
            graphs.put(name, graph);
        }
        Workspace stamped = ws.as(id, c.label(), c.at());
        graphs.put(Graphs.workspace(id), stamped.toModel());
        store.write(List.of(), graphs);
        return Reply.ok();
    }

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
        return null;
    }

    private Reply deleteWorkspace(String id) {
        Workspace ws = load(id);
        if (ws == null) {
            return Reply.notFound();
        }
        List<String> graphs = new ArrayList<>();
        for (long n = 1; n <= ws.revision("baseline"); n++) {
            graphs.add(Graphs.baseline(id, n));
        }
        for (String name : CONFIGS) {
            graphs.add(Graphs.config(id, name));
        }
        store.jobsOf(Graphs.workspace(id)).listSubjects().forEachRemaining(job -> {
            graphs.add(job.getURI());
            graphs.add(job.getURI() + ":input");
        });
        graphs.add(Graphs.workspace(id));
        store.drop(graphs);
        return Reply.ok();
    }

    private Reply submitJob(Command c) {
        String jobIri = Graphs.job(c.job());
        String input = Graphs.jobInput(c.job());
        Set<String> names = names(c);
        if (!names.equals(Set.of(jobIri, input)) || !c.body().getDefaultModel().isEmpty()) {
            return Reply.refused("a job's submission carries its job graph and its input graph only");
        }
        Workspace ws = load(c.workspace());
        if (ws == null) {
            return Reply.notFound();
        }
        Model description = c.body().getNamedModel(jobIri);
        Resource job = description.createResource(jobIri);
        if (!description.contains(job, RDF.type, Cst.Job)
            || !description.contains(job, Cst.workspace, description.createResource(Graphs.workspace(ws.id())))
            || !description.contains(job, Cst.configGraph, description.createResource(input))
            || !description.contains(job, Cst.baselineGraph, description.createResource(ws.baselineGraph()))
            || !description.contains(job, Cst.status, Cst.Queued)) {
            return Reply.refused("a job names its workspace, its own input, the workspace's baseline and the status Queued");
        }
        if (!store.graph(jobIri).isEmpty()) {
            return Reply.refused("the job exists");
        }
        store.write(List.of(), Map.of(jobIri, description, input, c.body().getNamedModel(input)));
        return Reply.ok();
    }

    /**
     * A job's status and results, from the worker or from the service when the job could not be handed over. A job
     * deleted meanwhile stays deleted. Everything on the job node but what {@link #WORKER_PREDICATES} names must be as
     * the service wrote it, so an update cannot move a job to another workspace or point it at another graph.
     */
    private Reply jobUpdate(Command c) {
        String jobIri = Graphs.job(c.job());
        if (!names(c).equals(Set.of(jobIri)) || !c.body().getDefaultModel().isEmpty()) {
            return Reply.refused("a job's update carries its job graph only");
        }
        Model existing = store.graph(jobIri);
        if (existing.isEmpty()) {
            return Reply.notFound();
        }
        Resource job = existing.createResource(jobIri);
        if (!existing.contains(job, Cst.workspace, existing.createResource(Graphs.workspace(c.workspace())))) {
            return Reply.refused("the job is not this workspace's");
        }
        Model update = c.body().getNamedModel(jobIri);
        if (!serviceTriples(existing, jobIri).isIsomorphicWith(serviceTriples(update, jobIri))) {
            return Reply.refused("a job's update may change only its status and results");
        }
        store.write(List.of(), Map.of(jobIri, update));
        return Reply.ok();
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

    private Reply deleteJob(Command c) {
        String jobIri = Graphs.job(c.job());
        Model existing = store.graph(jobIri);
        if (existing.isEmpty()) {
            return Reply.notFound();
        }
        if (!existing.contains(existing.createResource(jobIri), Cst.workspace, existing.createResource(Graphs.workspace(c.workspace())))) {
            return Reply.refused("the job is not this workspace's");
        }
        store.drop(List.of(jobIri, Graphs.jobInput(c.job())));
        return Reply.ok();
    }

    private Workspace load(String id) {
        return Workspace.from(id, store.graph(Graphs.workspace(id)));
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
