// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Pattern;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.ResourceFactory;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.Projections;
import org.nebularis.lattice.studio.store.StudioStore;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.DirectWrites;

/**
 * Stands in for the Python worker in the service's tests: it runs a refresh job the bus hands it, computing the five projections
 * from the store and sending the job's updates through the writer, as the worker does. The promotions are restated here in a few
 * lines each, and {@code ProjectionsTest} holds them equal to what the real worker computes.
 */
final class RefreshWorker {
    private static final Pattern JOB_GRAPH = Pattern.compile("urn:lattice:studio:job:[0-9a-f-]{36}");
    private static final String SKOS = "http://www.w3.org/2004/02/skos/core#";
    private static final Resource CONCEPT = ResourceFactory.createResource(SKOS + "Concept");
    private static final Property PREF_LABEL = ResourceFactory.createProperty(SKOS + "prefLabel");
    private static final Property IN_SCHEME = ResourceFactory.createProperty(SKOS + "inScheme");
    private static final Resource PERSISTENT_IDENTITY = Cst.Fnd.PersistentIdentity;

    private final StudioStore store;
    private final DirectWrites writes;
    private final String summariesQuery;
    private final java.util.concurrent.atomic.AtomicInteger runs = new java.util.concurrent.atomic.AtomicInteger();

    RefreshWorker(StudioStore store, DirectWrites writes) {
        this.store = store;
        this.writes = writes;
        try {
            this.summariesQuery = Files.readString(Path.of(System.getProperty("studio.assets"), "projections", "workspace-summaries.rq"));
        } catch (java.io.IOException e) {
            throw new java.io.UncheckedIOException(e);
        }
    }

    /** How many refresh jobs it has run. */
    int runs() {
        return runs.get();
    }

    /** Runs the job if it is a refresh job and says so. */
    boolean handle(String jobIri) {
        Resource job = ResourceFactory.createResource(jobIri);
        Model written = store.graph(jobIri);
        if (!written.contains(job, Cst.kind, Cst.Refresh)) {
            return false;
        }
        String id = jobIri.substring(Graphs.JOB_PREFIX.length());
        Model running = ModelFactory.createDefaultModel().add(written);
        running.removeAll(job, Cst.status, null);
        running.add(job, Cst.status, Cst.Running);
        send(id, running, Map.of());
        Model done = ModelFactory.createDefaultModel().add(running);
        done.removeAll(job, Cst.status, null);
        done.add(job, Cst.status, Cst.Succeeded);
        done.add(job, Cst.finishedAt, done.createTypedLiteral("2026-10-27T10:00:00Z", XSDDatatype.XSDdateTime));
        send(id, done, compute(store, summariesQuery, jobIri, Instant.parse("2026-10-27T10:00:00Z")));
        runs.incrementAndGet();
        return true;
    }

    private void send(String id, Model job, Map<String, Model> projections) {
        Dataset graphs = DatasetFactory.create();
        graphs.addNamedModel(Graphs.job(id), job);
        projections.forEach(graphs::addNamedModel);
        writes.send(Command.jobUpdate(null, id, graphs));
    }

    /** The five projections of {@code store}, each with its refresh node, by graph name. */
    static Map<String, Model> compute(StudioStore store, String summariesQuery, String jobIri, Instant readAt) {
        Property current = Cst.current;
        Map<String, Model> out = new LinkedHashMap<>();
        for (String key : Graphs.PROJECTIONS) {
            out.put(Graphs.projection(key), ModelFactory.createDefaultModel());
        }
        Model registry = out.get(Graphs.projection("registry"));
        Model jobs = out.get(Graphs.projection("jobs"));
        Model holders = out.get(Graphs.projection("holders"));
        Model terms = out.get(Graphs.projection("terms"));
        for (String name : store.graphNames()) {
            if (name.startsWith(Graphs.LINEAGE_PREFIX)) {
                restate(store.graph(name), PERSISTENT_IDENTITY, current, "current", registry);
            } else if (JOB_GRAPH.matcher(name).matches()) {
                Model graph = store.graph(name);
                if (!graph.contains(graph.createResource(name), Cst.kind, Cst.Refresh)) {
                    restate(graph, Cst.Job, Cst.workspace, "workspace", jobs);
                }
            } else if (name.startsWith(Graphs.DESCRIPTION_PREFIX)) {
                Model graph = store.graph(name);
                restate(graph, Cst.Workspace, Cst.dependsOn, "dependsOn", holders);
                restate(graph, Cst.Workspace, Cst.holdsImport, "holdsImport", holders);
            } else if (name.startsWith(Graphs.VERSION_PREFIX)) {
                Model graph = store.graph(name);
                restate(graph, CONCEPT, PREF_LABEL, "prefLabel", terms);
                restate(graph, CONCEPT, IN_SCHEME, "inScheme", terms);
            }
        }
        Model summaries = out.get(Graphs.projection("summaries"));
        try (var query = QueryExecutionFactory.create(QueryFactory.create(summariesQuery), store.snapshot())) {
            summaries.add(query.execConstruct());
        }
        out.forEach((name, graph) -> {
            Resource node = graph.createResource(name);
            node.addProperty(RDF.type, graph.createResource(Projections.NS + "Refresh"));
            node.addProperty(graph.createProperty(Projections.NS + "job"), graph.createResource(jobIri));
            node.addProperty(graph.createProperty(Projections.NS + "readAt"), graph.createTypedLiteral(readAt.toString(), XSDDatatype.XSDdateTime));
        });
        return out;
    }

    private static void restate(Model source, Resource carrier, Property read, String promoted, Model into) {
        Property to = into.createProperty(Projections.NS + promoted);
        source.listSubjectsWithProperty(RDF.type, carrier).forEachRemaining(s -> s.listProperties(read).forEachRemaining(st -> {
            if (!st.getObject().isAnon()) {
                into.add(st.getSubject(), to, st.getObject());
            }
        }));
    }
}
