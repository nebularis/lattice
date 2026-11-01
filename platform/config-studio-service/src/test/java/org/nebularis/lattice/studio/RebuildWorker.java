// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.ResourceFactory;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.Promotions;
import org.nebularis.lattice.studio.store.Promotions;
import org.nebularis.lattice.studio.store.StudioStore;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.DirectWrites;

/**
 * Stands in for the Python worker in the service's tests: it runs a rebuild job the bus hands it, computing every source's promoted
 * partition and the record from the store and sending the job's update through the writer, as the worker does. The promotions are
 * restated here in a few lines each, and {@code PromotionsTest} holds them equal to what the real worker computes.
 */
final class RebuildWorker {
    private static final String SKOS = "http://www.w3.org/2004/02/skos/core#";

    /** A promotion restated, the carrier's type, the property read and the property of the promotion namespace it is promoted to. */
    private record Promotion(Resource carrier, Property read, String promoted) {
    }

    private static final Map<String, List<Promotion>> BY_FAMILY = Map.of(
        "lineage", List.of(new Promotion(Cst.Fnd.PersistentIdentity, Cst.current, "current")),
        "job", List.of(new Promotion(Cst.Job, Cst.workspace, "workspace")),
        "description", List.of(new Promotion(Cst.Workspace, Cst.dependsOn, "dependsOn"), new Promotion(Cst.Workspace, Cst.holdsImport, "holdsImport")),
        "version", List.of(
            new Promotion(ResourceFactory.createResource(SKOS + "Concept"), ResourceFactory.createProperty(SKOS + "prefLabel"), "prefLabel"),
            new Promotion(ResourceFactory.createResource(SKOS + "Concept"), ResourceFactory.createProperty(SKOS + "inScheme"), "inScheme")));

    private final StudioStore store;
    private final DirectWrites writes;
    private final java.util.concurrent.atomic.AtomicInteger runs = new java.util.concurrent.atomic.AtomicInteger();

    RebuildWorker(StudioStore store, DirectWrites writes) {
        this.store = store;
        this.writes = writes;
    }

    /** How many rebuild jobs it has run. */
    int runs() {
        return runs.get();
    }

    /** Runs the job if it is a rebuild job and says so. */
    boolean handle(String jobIri) {
        Resource job = ResourceFactory.createResource(jobIri);
        Model written = store.graph(jobIri);
        if (!written.contains(job, Cst.kind, Cst.Rebuild)) {
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
        send(id, done, compute(store));
        runs.incrementAndGet();
        return true;
    }

    private void send(String id, Model job, Map<String, Model> partitions) {
        Dataset graphs = DatasetFactory.create();
        graphs.addNamedModel(Graphs.job(id), job);
        partitions.forEach(graphs::addNamedModel);
        writes.send(Command.jobUpdate(null, id, graphs));
    }

    /** Every source's promoted partition of {@code store}, an empty one for each whose source is gone, and the record, by graph name. */
    static Map<String, Model> compute(StudioStore store) {
        Map<String, Model> out = new LinkedHashMap<>();
        for (String name : store.graphNames()) {
            String family = Graphs.familyOf(name);
            if (family != null) {
                Model graph = store.graph(name);
                Model rows = ModelFactory.createDefaultModel();
                for (Promotion p : BY_FAMILY.get(family)) {
                    restate(graph, p, rows);
                }
                out.put(Graphs.promoted(name), rows);
            }
        }
        for (String name : store.graphNames()) {
            if (Graphs.isPromoted(name)) {
                out.putIfAbsent(name, ModelFactory.createDefaultModel());
            }
        }
        try {
            byte[] contracts = Files.readAllBytes(Path.of(System.getProperty("studio.assets"), "promotions", "promotions.ttl"));
            out.put(Graphs.PROMOTED_RECORD, Promotions.record(Promotions.digests(contracts)));
        } catch (java.io.IOException e) {
            throw new java.io.UncheckedIOException(e);
        }
        return out;
    }

    private static void restate(Model source, Promotion p, Model into) {
        Property to = into.createProperty(Promotions.NS + p.promoted());
        source.listSubjectsWithProperty(RDF.type, p.carrier()).forEachRemaining(s -> s.listProperties(p.read()).forEachRemaining(st -> {
            if (!st.getObject().isAnon()) {
                into.add(st.getSubject(), to, st.getObject());
            }
        }));
    }
}
