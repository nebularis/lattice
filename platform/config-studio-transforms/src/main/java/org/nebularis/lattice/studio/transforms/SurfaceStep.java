// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.concurrent.TimeUnit;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonArray;
import org.apache.jena.atlas.json.JsonException;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.atlas.json.JsonValue;
import org.apache.jena.graph.Graph;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.graph.Triple;
import org.apache.jena.query.Query;
import org.apache.jena.query.QueryCancelledException;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.sparql.core.DatasetGraph;
import org.apache.jena.sparql.core.DatasetGraphFactory;
import org.apache.jena.sparql.core.Quad;
import org.apache.jena.sparql.exec.QueryExec;
import org.apache.jena.sparql.exec.UpdateExec;
import org.apache.jena.system.Txn;
import org.apache.jena.update.Update;
import org.apache.jena.update.UpdateRequest;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.Maintenance;

/**
 * One step of the surface simulator (ADR-A154 decisions 1 and 11, contract Runs, "A surface step"). A step is a function of its compile job
 * and its input alone, and the time it runs at is the one the input states (PRI-56). The input is a sample world and an edit of it, the
 * quads a write added and removed. The step keeps the rows of each source the edit changed as the studio's writer keeps them, with the
 * writer's own {@link Maintenance}, which sends the partition clear and then each contract's fill over the whole source, and it does so over
 * the world before the edit and over the world after it, each in a dataset of its own. A fill reads the world, each hop in the graph that
 * holds it, so the edit also reaches the other sources whose carriers' read paths pass through a node it changed, and the step keeps those
 * too, the sources the job's reach queries name over the world before the edit, as the writer does within the write. It also says which
 * contracts read what the edit changed, by the query the compiler's read set is defined by. The operations are those the compile job holds, since this worker has no
 * compiler. Nothing is shared with another step, and nothing is stored.
 */
final class SurfaceStep {
    /** The family the job's contracts are kept under. A contract of a compile job names none, so every contract reads every source. */
    static final String FAMILY = "source";
    private static final String MANIFEST = "maintenance/manifest.json";
    private static final String CLEAR = "maintenance/partition-clear.rq";

    private SurfaceStep() {
    }

    private static final class Failed extends Exception {
        private static final long serialVersionUID = 1L;

        Failed(String message) {
            super(message);
        }
    }

    /** One contract of the compile job, from its manifest. {@code fill}, {@code reach}, {@code readSet} and {@code reason} are each null where the job has none. */
    private record Contract(String key, String iri, String kind, String fill, String reach, Query readSet, String reason) {
    }

    /** The parts of a step in order, or the reason the step could not be run, in words an author reads. */
    static PersistenceStep.Result execute(Model job, String jobIri, String trig, long budgetMillis) {
        try {
            return new PersistenceStep.Result(null, run(job, jobIri, trig, budgetMillis));
        } catch (Failed | StepRequest.StepFormatException e) {
            return PersistenceStep.Result.failed(e.getMessage());
        }
    }

    private static List<PersistenceStep.Part> run(Model job, String jobIri, String trig, long budgetMillis) throws Failed, StepRequest.StepFormatException {
        Resource compile = job.createResource(jobIri);
        if (!compile.hasProperty(Cst.kind, Cst.Compile) || !compile.hasProperty(Cst.target, Cst.target("surface"))
            || !compile.hasProperty(Cst.status, Cst.Succeeded)) {
            throw new Failed("The job is not a finished compilation of the surface part, so this step was not run.");
        }
        Map<String, String> artefacts = new HashMap<>();
        for (Statement s : compile.listProperties(Cst.artefact).toList()) {
            Statement path = s.getResource().getProperty(Cst.path);
            Statement content = s.getResource().getProperty(Cst.content);
            if (path != null && content != null && path.getObject().isLiteral() && content.getObject().isLiteral()) {
                artefacts.put(path.getString(), content.getString());
            }
        }
        SurfaceStepRequest step = SurfaceStepRequest.parse(trig);
        List<Contract> contracts = contracts(artefacts);
        Maintenance maintenance = maintenance(contracts, artefacts);
        List<String> edited = step.sources();
        Node time = step.transactionTime();

        DatasetGraph after = step.after();
        List<String> reached = reached(maintenance, step, edited, budgetMillis);
        List<String> sources = new ArrayList<>(edited);
        sources.addAll(reached);
        sources.sort(PersistenceStep.BYTES);
        Map<String, Set<Quad>> rowsBefore = keep(step.world(), sources, maintenance, contracts, time, budgetMillis);
        Map<String, Set<Quad>> rowsAfter = keep(after, sources, maintenance, contracts, time, budgetMillis);
        Set<String> touched = touched(contracts, step.world(), after, budgetMillis);

        List<PersistenceStep.Part> parts = new ArrayList<>();
        JsonArray changes = new JsonArray();
        JsonArray table = new JsonArray();
        for (Contract c : contracts) {
            if (c.fill() == null) {
                table.add(row(c, false, touched.contains(c.key()), 0, 0));
                continue;
            }
            Set<Quad> before = rowsBefore.getOrDefault(c.key(), Set.of());
            Set<Quad> now = rowsAfter.getOrDefault(c.key(), Set.of());
            Set<Quad> asserted = new HashSet<>(now);
            asserted.removeAll(before);
            Set<Quad> retracted = new HashSet<>(before);
            retracted.removeAll(now);
            parts.add(new PersistenceStep.Part("artefact", "application/trig", c.key(), c.key() + "/rows-before.trig", trig(before)));
            parts.add(new PersistenceStep.Part("artefact", "application/trig", c.key(), c.key() + "/rows-after.trig", trig(now)));
            changes.add(change(c, asserted, retracted));
            table.add(row(c, true, touched.contains(c.key()), asserted.size(), retracted.size()));
        }
        JsonObject delta = new JsonObject();
        delta.put("contracts", changes);
        parts.add(new PersistenceStep.Part("delta", "application/json", JSON.toString(delta)));
        JsonObject outcome = new JsonObject();
        outcome.put("engine", PersistenceStep.ENGINE);
        outcome.put("sources", PersistenceStep.strings(edited));
        outcome.put("reached", PersistenceStep.strings(reached));
        outcome.put("contracts", table);
        parts.add(new PersistenceStep.Part("outcome", "application/json", JSON.toString(outcome)));
        return parts;
    }

    // ---- reading the job

    /** The contracts of the job's maintenance manifest, in the order of their keys, each with the operation files the job holds for it. */
    private static List<Contract> contracts(Map<String, String> artefacts) throws Failed {
        String text = artefacts.get(MANIFEST);
        if (text == null) {
            throw new Failed("The job holds no maintenance manifest (" + MANIFEST + "), so this step was not run. Compile the surface part again.");
        }
        JsonArray manifest;
        try {
            manifest = JSON.parseAny(text).getAsArray();
        } catch (JsonException | ClassCastException e) {
            throw new Failed("The job's maintenance manifest could not be read, so this step was not run.");
        }
        TreeMap<String, Contract> byKey = new TreeMap<>(PersistenceStep.BYTES);
        for (JsonValue value : manifest) {
            if (!value.isObject() || !string(value.getAsObject(), "key") || !string(value.getAsObject(), "contract") || !string(value.getAsObject(), "kind")) {
                throw new Failed("The job's maintenance manifest has an entry without a key, a contract and a kind, so this step was not run.");
            }
            JsonObject entry = value.getAsObject();
            String key = entry.getString("key");
            String fill = file(artefacts, entry, "fill");
            String reach = file(artefacts, entry, "reach");
            String readSet = file(artefacts, entry, "readSet");
            Query query = null;
            if (readSet != null) {
                try {
                    query = QueryFactory.create(readSet);
                } catch (RuntimeException e) {
                    throw new Failed("The read set of the contract " + key + " is not a query Jena reads, so this step was not run.");
                }
                if (NowPinning.remaining(query) > 0) {
                    throw new Failed("The read set of the contract " + key + " reads the clock, and a step reads none.");
                }
            }
            String reason = entry.hasKey("reason") && entry.get("reason").isString() ? entry.getString("reason") : null;
            if (byKey.put(key, new Contract(key, entry.getString("contract"), entry.getString("kind"), fill, reach, query, reason)) != null) {
                throw new Failed("The job's maintenance manifest names the contract " + key + " more than once, so this step was not run.");
            }
        }
        return List.copyOf(byKey.values());
    }

    private static boolean string(JsonObject o, String key) {
        return o.hasKey(key) && o.get(key).isString() && !o.getString(key).isEmpty();
    }

    /** The text of the file the entry names under {@code field}, null where it names none, or throws where the job lacks the file. */
    private static String file(Map<String, String> artefacts, JsonObject entry, String field) throws Failed {
        if (!entry.hasKey(field)) {
            return null;
        }
        String path = entry.get(field).isString() ? "maintenance/" + entry.getString(field) : null;
        String text = path == null ? null : artefacts.get(path);
        if (text == null) {
            throw new Failed("The maintenance manifest names " + field + " of the contract " + entry.getString("key") + ", which the job does not hold, so this step was not run.");
        }
        return text;
    }

    private static Maintenance maintenance(List<Contract> contracts, Map<String, String> artefacts) throws Failed {
        List<Maintenance.Fill> fills = contracts.stream().filter(c -> c.fill() != null).map(c -> new Maintenance.Fill(c.key(), c.fill(), c.reach())).toList();
        String clear = artefacts.get(CLEAR);
        if (!fills.isEmpty() && clear == null) {
            throw new Failed("The job holds the fills of its contracts and no partition clear (" + CLEAR + "), so this step was not run.");
        }
        return Maintenance.of(clear, Map.of(FAMILY, fills));
    }

    // ---- the sources an edit reaches

    /**
     * The sources, beside those the edit changed, whose rows the edit reaches, in the order of their bytes. They are named by the job's reach
     * queries, run over the world before the edit with the triples the edit added and removed in the named graphs. The default graph is read by
     * no fill. A partition is no source, and a source the edit changed is kept already.
     */
    private static List<String> reached(Maintenance maintenance, SurfaceStepRequest step, List<String> edited, long budgetMillis) throws Failed {
        // what the edit changes, which is what it adds that the world lacks and what it removes that the world holds
        Set<org.apache.jena.graph.Triple> delta = new HashSet<>();
        step.added().stream().filter(q -> !Quad.isDefaultGraph(q.getGraph()) && !step.world().contains(q)).forEach(q -> delta.add(q.asTriple()));
        step.removed().stream().filter(q -> !Quad.isDefaultGraph(q.getGraph()) && step.world().contains(q)).forEach(q -> delta.add(q.asTriple()));
        Set<String> found = new TreeSet<>(PersistenceStep.BYTES);
        for (Query query : maintenance.reach(FAMILY, delta)) {
            try {
                QueryExec.dataset(step.world()).query(query).timeout(Math.max(budgetMillis, 1), TimeUnit.MILLISECONDS).build().select()
                    .forEachRemaining(row -> found.add(row.get("src").getURI()));
            } catch (QueryCancelledException e) {
                throw new Failed("The reach of the edit was still being read at the run's deadline, so it was stopped.");
            } catch (RuntimeException e) {
                throw new Failed("Jena could not read which sources the edit reaches. " + e.getMessage());
            }
        }
        found.removeIf(g -> g.startsWith(Graphs.PROMOTED_PREFIX) || edited.contains(g));
        return List.copyOf(found);
    }

    // ---- keeping the rows

    /**
     * The rows each contract holds for {@code sources} once the writer's maintenance has run over {@code world}, as quads in the partition of
     * their source. The updates are the writer's, one source at a time, and a fill's rows are the quads it added to the partition, so each row
     * is attributed to the contract whose fill wrote it. A row two contracts write is attributed to the one whose fill ran first.
     */
    private static Map<String, Set<Quad>> keep(DatasetGraph world, List<String> sources, Maintenance maintenance, List<Contract> contracts, Node time,
                                               long budgetMillis) throws Failed {
        Map<String, Set<Quad>> rows = new TreeMap<>(PersistenceStep.BYTES);
        DatasetGraph dataset = DatasetGraphFactory.createTxnMem();
        Txn.executeWrite(dataset, () -> world.find().forEachRemaining(dataset::add));
        for (String source : sources) {
            Node derived = NodeFactory.createURI(Graphs.promoted(source));
            Set<Quad> previous = Txn.calculateRead(dataset, () -> partition(dataset, derived));
            List<Maintenance.Operation> operations;
            try {
                operations = maintenance.operations(FAMILY, source);
            } catch (RuntimeException e) {
                throw new Failed("An operation of the job's maintenance did not parse once its source was bound, so this step was not run. " + e.getMessage());
            }
            for (Maintenance.Operation op : operations) {
                UpdateRequest pinned = NowPinning.pin(new UpdateRequest(op.update()), time).request();
                try {
                    Txn.executeWrite(dataset, () -> UpdateExec.dataset(dataset).update(pinned).timeout(Math.max(budgetMillis, 1), TimeUnit.MILLISECONDS).build().execute());
                } catch (QueryCancelledException e) {
                    throw new Failed("The maintenance was still running at the run's deadline, so it was stopped.");
                } catch (RuntimeException e) {
                    throw new Failed("Jena could not run the maintenance of " + (op.contract() == null ? "the partition clear" : "the contract " + op.contract()) + ". " + e.getMessage());
                }
                Set<Quad> now = Txn.calculateRead(dataset, () -> partition(dataset, derived));
                if (op.contract() != null) {
                    Set<Quad> written = new HashSet<>(now);
                    written.removeAll(previous);
                    rows.computeIfAbsent(op.contract(), k -> new HashSet<>()).addAll(written);
                }
                previous = now;
            }
        }
        return rows;
    }

    private static Set<Quad> partition(DatasetGraph dataset, Node graph) {
        Set<Quad> out = new HashSet<>();
        dataset.find(graph, Node.ANY, Node.ANY, Node.ANY).forEachRemaining(out::add);
        return out;
    }

    // ---- the read sets

    /**
     * The contracts the edit touched, as the compiler's invalidation names them. The compiler records a contract's instance graph whether or not
     * the source holds an instance, with the empty graph's digest where it holds none, and calls the contract stale when the graph it reads now
     * differs from the one recorded. So the first instance of a class touches its contracts, and so does the loss of the last. The graph is read over every graph of the world, the
     * default graph included, since the compiler reads one merged source.
     */
    private static Set<String> touched(List<Contract> contracts, DatasetGraph before, DatasetGraph after, long budgetMillis) throws Failed {
        Graph unionBefore = union(before);
        Graph unionAfter = union(after);
        Set<String> out = new TreeSet<>(PersistenceStep.BYTES);
        for (Contract c : contracts) {
            if (c.readSet() == null) {
                continue;
            }
            Set<Triple> recorded = read(c, unionBefore, budgetMillis);
            if (!recorded.equals(read(c, unionAfter, budgetMillis))) {
                out.add(c.key());
            }
        }
        return out;
    }

    /** Every triple of every graph of the world, but the derived rows, which a source's own triples never are. */
    private static Graph union(DatasetGraph world) {
        Model m = ModelFactory.createDefaultModel();
        world.find().forEachRemaining(q -> {
            if (!(q.getGraph().isURI() && q.getGraph().getURI().startsWith(Graphs.PROMOTED_PREFIX))) {
                m.getGraph().add(q.asTriple());
            }
        });
        return m.getGraph();
    }

    private static Set<Triple> read(Contract c, Graph graph, long budgetMillis) throws Failed {
        Set<Triple> out = new HashSet<>();
        try {
            QueryExec.graph(graph).query(c.readSet()).timeout(Math.max(budgetMillis, 1), TimeUnit.MILLISECONDS).build().construct().find().forEachRemaining(out::add);
        } catch (QueryCancelledException e) {
            throw new Failed("The read set of the contract " + c.key() + " was still being read at the run's deadline, so it was stopped.");
        } catch (RuntimeException e) {
            throw new Failed("Jena could not read the read set of the contract " + c.key() + ". " + e.getMessage());
        }
        return out;
    }

    // ---- the parts

    /** The quads as TriG, a block for each partition in the order of the partitions' bytes, and each block's lines in the order of their bytes. */
    private static String trig(Set<Quad> quads) {
        StringBuilder out = new StringBuilder();
        for (Map.Entry<String, List<String>> g : PersistenceStep.byGraph(quads).entrySet()) {
            out.append('<').append(g.getKey()).append("> {\n");
            g.getValue().forEach(line -> out.append("    ").append(line).append('\n'));
            out.append("}\n");
        }
        return out.toString();
    }

    private static JsonObject change(Contract c, Set<Quad> asserted, Set<Quad> retracted) {
        Map<String, List<String>> add = PersistenceStep.byGraph(asserted);
        Map<String, List<String>> del = PersistenceStep.byGraph(retracted);
        Set<String> graphs = new TreeSet<>(PersistenceStep.BYTES);
        graphs.addAll(add.keySet());
        graphs.addAll(del.keySet());
        JsonArray list = new JsonArray();
        for (String graph : graphs) {
            JsonObject entry = new JsonObject();
            entry.put("graph", graph);
            entry.put("asserted", PersistenceStep.strings(add.getOrDefault(graph, List.of())));
            entry.put("retracted", PersistenceStep.strings(del.getOrDefault(graph, List.of())));
            list.add(entry);
        }
        JsonObject o = new JsonObject();
        o.put("contract", c.iri());
        o.put("key", c.key());
        o.put("graphs", list);
        return o;
    }

    private static JsonObject row(Contract c, boolean kept, boolean touched, int asserted, int retracted) {
        JsonObject o = new JsonObject();
        o.put("contract", c.iri());
        o.put("key", c.key());
        o.put("kind", c.kind());
        o.put("kept", kept);
        if (c.reason() != null) {
            o.put("reason", c.reason());
        }
        o.put("readSetTouched", touched);
        o.put("asserted", asserted);
        o.put("retracted", retracted);
        return o;
    }
}
