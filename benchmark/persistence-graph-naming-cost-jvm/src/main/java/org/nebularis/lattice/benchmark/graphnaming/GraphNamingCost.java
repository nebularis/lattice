// SPDX-License-Identifier: MPL-2.0
// NB: This module has been produced using GenAI

package org.nebularis.lattice.benchmark.graphnaming;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.function.Supplier;

import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonArray;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.dboe.base.file.Location;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.query.ReadWrite;
import org.apache.jena.sparql.core.Quad;
import org.apache.jena.sparql.util.NodeFactoryExtra;
import org.apache.jena.system.Txn;
import org.apache.jena.tdb2.TDB2Factory;
import org.apache.jena.tdb2.sys.StoreConnection;
import org.apache.jena.update.UpdateAction;
import org.eclipse.rdf4j.model.IRI;
import org.eclipse.rdf4j.model.Literal;
import org.eclipse.rdf4j.model.Statement;
import org.eclipse.rdf4j.model.ValueFactory;
import org.eclipse.rdf4j.model.impl.SimpleValueFactory;
import org.eclipse.rdf4j.query.BindingSet;
import org.eclipse.rdf4j.query.QueryLanguage;
import org.eclipse.rdf4j.query.TupleQueryResult;
import org.eclipse.rdf4j.repository.Repository;
import org.eclipse.rdf4j.repository.RepositoryConnection;
import org.eclipse.rdf4j.repository.sail.SailRepository;
import org.eclipse.rdf4j.sail.memory.MemoryStore;

/**
 * What a {@code GRAPH ?g} inside an {@code OPTIONAL}, and the generated named-graph replace, cost on Jena and RDF4J (ADR-A124, TSD-45).
 *
 * <p>The forms, the rendered operations and the checks come from {@code benchmark/persistence-graph-naming-cost/check.py --emit}, so every store runs the same
 * SPARQL text the compiler generates. <b>A wrong result fails the run. Time never does.</b>
 */
public final class GraphNamingCost {

    /** A store under test. Every method opens and closes its own transaction. */
    interface Engine extends AutoCloseable {
        String name();

        void addGraph(String graph, int triples, int offset);

        long count(String selectCount);

        void update(String text);

        @Override
        void close();
    }

    static final class WrongResult extends RuntimeException {
        WrongResult(String message) {
            super(message);
        }
    }

    // ---- Jena -------------------------------------------------------------------------------------------------------

    static final class JenaEngine implements Engine {
        private final String name;
        private final Dataset dataset;
        private final Runnable release;

        JenaEngine(String name, Dataset dataset, Runnable release) {
            this.name = name;
            this.dataset = dataset;
            this.release = release;
        }

        public String name() {
            return name;
        }

        public void addGraph(String graph, int triples, int offset) {
            Txn.executeWrite(dataset, () -> {
                var g = NodeFactory.createURI(graph);
                var p = NodeFactory.createURI("urn:p");
                var dsg = dataset.asDatasetGraph();
                for (int j = 0; j < triples; j++) {
                    dsg.add(new Quad(g, NodeFactory.createURI("urn:s" + offset + ":" + j), p, NodeFactoryExtra.createLiteralNode(Integer.toString(j), null, null)));
                }
            });
        }

        public long count(String selectCount) {
            return Txn.calculateRead(dataset, () -> {
                try (QueryExecution qe = QueryExecutionFactory.create(selectCount, dataset)) {
                    return qe.execSelect().next().getLiteral("n").getLong();
                }
            });
        }

        public void update(String text) {
            Txn.executeWrite(dataset, () -> UpdateAction.parseExecute(text, dataset));
        }

        public void close() {
            dataset.close();
            release.run();
        }
    }

    private static final java.util.concurrent.atomic.AtomicInteger TDB2_STORES = new java.util.concurrent.atomic.AtomicInteger();

    /** A TDB2 in-memory store stays in Jena's global store map until it is released, so a run that built one per measurement would keep every one of them. */
    static Engine tdb2() {
        Location location = Location.mem("graph-naming-" + TDB2_STORES.incrementAndGet());
        return new JenaEngine("jena tdb2 (in-memory)", TDB2Factory.connectDataset(location), () -> StoreConnection.release(location));
    }

    // ---- RDF4J ------------------------------------------------------------------------------------------------------

    static final class Rdf4jEngine implements Engine {
        private static final ValueFactory VF = SimpleValueFactory.getInstance();
        private final Repository repository = new SailRepository(new MemoryStore());
        private final RepositoryConnection connection;

        Rdf4jEngine() {
            repository.init();
            connection = repository.getConnection();
        }

        public String name() {
            return "rdf4j MemoryStore";
        }

        public void addGraph(String graph, int triples, int offset) {
            IRI g = VF.createIRI(graph);
            IRI p = VF.createIRI("urn:p");
            List<Statement> statements = new ArrayList<>(triples);
            for (int j = 0; j < triples; j++) {
                statements.add(VF.createStatement(VF.createIRI("urn:s" + offset + ":" + j), p, VF.createLiteral(Integer.toString(j)), g));
            }
            connection.begin();
            connection.add(statements);
            connection.commit();
        }

        public long count(String selectCount) {
            try (TupleQueryResult result = connection.prepareTupleQuery(QueryLanguage.SPARQL, selectCount).evaluate()) {
                BindingSet row = result.next();
                return ((Literal) row.getValue("n")).longValue();
            }
        }

        public void update(String text) {
            connection.begin();
            connection.prepareUpdate(QueryLanguage.SPARQL, text).execute();
            connection.commit();
        }

        public void close() {
            connection.close();
            repository.shutDown();
        }
    }

    static final Map<String, Supplier<Engine>> ENGINES = new TreeMap<>(Map.of(
        "1 jena in-memory", () -> new JenaEngine("jena in-memory", DatasetFactory.createTxnMem(), () -> { }),
        "2 jena tdb2 (in-memory)", GraphNamingCost::tdb2,
        "3 rdf4j MemoryStore", Rdf4jEngine::new));

    // ---- the measurements -------------------------------------------------------------------------------------------

    static double bestOfThree(Supplier<Long> timed) {
        double best = Double.MAX_VALUE;
        for (int i = 0; i < 3; i++) {
            long start = System.nanoTime();
            timed.get();
            best = Math.min(best, (System.nanoTime() - start) / 1e6);
        }
        return best;
    }

    /** The ratio of the best timing over {@code graphs} graphs to that over one graph. Raises WrongResult on a wrong count. */
    static double formRatio(Supplier<Engine> factory, String query, boolean readsEvery, int graphs, int triples) {
        double manyMs = 0;
        double oneMs = 0;
        for (int n : new int[] {graphs, 1}) {
            try (Engine engine = factory.get()) {
                for (int g = 0; g < n; g++) {
                    engine.addGraph("urn:g:" + g, triples, 0);
                }
                long[] seen = new long[1];
                double ms = bestOfThree(() -> seen[0] = engine.count(query));
                long expected = (long) triples * (readsEvery ? n : 1);
                if (seen[0] != expected) {
                    throw new WrongResult(engine.name() + ": " + query + " counted " + seen[0] + " over " + n + " graph(s), not " + expected);
                }
                if (n == graphs) {
                    manyMs = ms;
                } else {
                    oneMs = ms;
                }
            }
        }
        return manyMs / oneMs;
    }

    static double replace(Supplier<Engine> factory, JsonObject doc, String names, int ballastQuads) {
        int perGraph = doc.get("perGraph").getAsNumber().value().intValue();
        int graphs = ballastQuads / perGraph;
        JsonObject step = doc.get("steps").getAsObject().get(names).getAsObject();
        try (Engine engine = factory.get()) {
            for (int g = 0; g < graphs; g++) {
                engine.addGraph("urn:g:ballast/" + g, perGraph, g);
            }
            engine.update(step.get("create").getAsString().value());
            double best = Double.MAX_VALUE;
            int n = 0;
            for (var item : step.get("replaces").getAsArray()) {
                n++;
                JsonObject replace = item.getAsObject();
                long start = System.nanoTime();
                engine.update(replace.get("text").getAsString().value());
                best = Math.min(best, (System.nanoTime() - start) / 1e6);
                for (var check : replace.get("checks").getAsArray()) {
                    String query = check.getAsObject().get("query").getAsString().value();
                    long expect = check.getAsObject().get("expect").getAsNumber().value().longValue();
                    long seen = engine.count(query);
                    if (seen != expect) {
                        throw new WrongResult(engine.name() + "/" + names + " replace " + n + ": " + query + " counted " + seen + ", not " + expect);
                    }
                }
                long ballast = engine.count(doc.get("ballastQuery").getAsString().value());
                if (ballast != (long) graphs * perGraph) {
                    throw new WrongResult(engine.name() + "/" + names + " replace " + n + ": the ballast holds " + ballast + " quads, not " + (long) graphs * perGraph);
                }
            }
            return best;
        }
    }

    // ---- one JVM per measurement ---------------------------------------------------------------------------------------

    /*
     * A store that runs out of memory does not give its heap back to the JVM that ran it, so a run that measured every store in one JVM lost every store after
     * the first that failed. Each measurement therefore runs in a child JVM with its own heap cap (-Xmx). A child that runs out of memory is recorded as
     * "did not finish" and costs only its own row. That is not a wrong result and does not fail the run.
     */

    private static final int OUT_OF_MEMORY_EXIT = 3;
    private static final String NOT_RUN = "not run: a smaller ballast did not finish";

    private static String heap() {
        return System.getProperty("graphnaming.heap", "4g");
    }

    /** Runs one measurement in a child JVM and returns its cell. Raises WrongResult if the child reports one. */
    static String inChild(String job) {
        try {
            String java = ProcessHandle.current().info().command().orElse("java");
            Process process = new ProcessBuilder(java, "-Xmx" + heap(), "-XX:+ExitOnOutOfMemoryError", "-Dgraphnaming.job=" + job,
                "-Dgraphnaming.operations=" + System.getProperty("graphnaming.operations"),
                "-Dgraphnaming.formGraphs=" + System.getProperty("graphnaming.formGraphs", ""), "-Dgraphnaming.formTriples=" + System.getProperty("graphnaming.formTriples", ""),
                "-classpath", System.getProperty("java.class.path"), GraphNamingCost.class.getName())
                .redirectError(ProcessBuilder.Redirect.DISCARD).start();
            String output = new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            int exit = process.waitFor();
            for (String line : output.split("\n")) {
                if (line.startsWith("WRONG\t")) {
                    throw new WrongResult(line.substring(6));
                }
                if (line.startsWith("RESULT\t")) {
                    return line.substring(7);
                }
            }
            if (exit == OUT_OF_MEMORY_EXIT) {
                return "did not finish: out of memory under -Xmx" + heap();
            }
            throw new IllegalStateException("the measurement " + job + " exited " + exit + " without a result");
        } catch (IOException | InterruptedException e) {
            throw new IllegalStateException(e);
        }
    }

    /** The child's side: runs the one measurement the job names and prints its cell. */
    static void runJob(String job, JsonObject doc) {
        String[] part = job.split("\\|", -1);
        Supplier<Engine> factory = ENGINES.get(part[1]);
        int formGraphs = Integer.parseInt(orDefault(System.getProperty("graphnaming.formGraphs"), doc.get("formGraphs").getAsNumber().value().toString()));
        int formTriples = Integer.parseInt(orDefault(System.getProperty("graphnaming.formTriples"), doc.get("formTriples").getAsNumber().value().toString()));
        try {
            String cell = switch (part[0]) {
                case "form" -> String.format("%.1f", formRatio(factory, doc.get("forms").getAsObject().get(part[2]).getAsString().value(), false, formGraphs, formTriples));
                case "scale" -> String.format("%.1f", formRatio(factory, doc.get("readsEveryGraph").getAsString().value(), true, formGraphs, formTriples));
                case "replace" -> String.format("%.1f", replace(factory, doc, part[2], Integer.parseInt(part[3])));
                default -> throw new IllegalArgumentException(job);
            };
            System.out.println("RESULT\t" + cell);
        } catch (WrongResult e) {
            System.out.println("WRONG\t" + e.getMessage().replace('\n', ' '));
            System.exit(1);
        }
    }

    private static String orDefault(String value, String fallback) {
        return value == null || value.isEmpty() ? fallback : value;
    }

    public static void main(String[] args) throws IOException {
        Path operations = Path.of(System.getProperty("graphnaming.operations", "benchmark/persistence-graph-naming-cost/operations.json"));
        JsonObject doc;
        try (InputStream in = Files.newInputStream(operations)) {
            doc = JSON.parse(in);
        }
        String job = System.getProperty("graphnaming.job");
        if (job != null) {
            runJob(job, doc);
            return;
        }
        long maximum = Long.parseLong(System.getProperty("graphnaming.max", "1000000"));
        boolean quick = "1".equals(System.getProperty("graphnaming.quick"));
        if (quick) {
            System.setProperty("graphnaming.formGraphs", "10");
            System.setProperty("graphnaming.formTriples", "300");
        }
        int formGraphs = quick ? 10 : doc.get("formGraphs").getAsNumber().value().intValue();
        JsonArray ballast = doc.get("ballast").getAsArray();
        Path reportPath = Path.of(System.getProperty("graphnaming.report", "benchmark/persistence-graph-naming-cost-jvm/report.md"));
        StringBuilder header = new StringBuilder("Run ").append(java.time.LocalDate.now()).append(": java ").append(System.getProperty("java.version"))
            .append(", jena 5.1.0, rdf4j 6.1.0, ").append(System.getProperty("os.arch")).append(", heap cap ").append(heap()).append(" for each measurement\n\n");
        StringBuilder forms = new StringBuilder("## Forms, ratio of ").append(formGraphs).append(" graphs to 1\n\n| Store | Form | Ratio |\n|---|---|---|\n");
        StringBuilder replaces = new StringBuilder("## Generated replace, best of three\n\n| Store | Graph naming | Ballast quads | ms |\n|---|---|---|---|\n");
        Runnable flush = () -> {
            try {
                Files.writeString(reportPath, header.toString() + forms + "\n" + replaces, StandardCharsets.UTF_8);
            } catch (IOException e) {
                throw new java.io.UncheckedIOException(e);
            }
        };
        java.util.Set<String> exhausted = new java.util.HashSet<>();
        try {
            for (String key : ENGINES.keySet()) {
                String store = key.substring(2);
                for (String form : doc.get("forms").getAsObject().keys()) {
                    System.err.println("progress: " + store + " " + form);
                    forms.append(String.format("| %s | %s | %s |%n", store, form, inChild("form|" + key + "|" + form)));
                    flush.run();
                }
                System.err.println("progress: " + store + " scale");
                forms.append(String.format("| %s | nothing bound (reads every graph, for scale) | %s |%n", store, inChild("scale|" + key + "|")));
                flush.run();
                for (var item : ballast) {
                    long quads = item.getAsNumber().value().longValue();
                    if (quads > maximum || (quick && quads > 10_000)) {
                        continue;
                    }
                    for (String names : new String[] {"query", "caller"}) {
                        System.err.println("progress: " + store + " " + names + " " + quads);
                        String cell = exhausted.contains(store) ? NOT_RUN : inChild("replace|" + key + "|" + names + "|" + quads);
                        if (cell.startsWith("did not finish")) {
                            exhausted.add(store);
                        }
                        replaces.append(String.format("| %s | %s | %,d | %s |%n", store, names, quads, cell));
                        flush.run();
                    }
                }
            }
        } catch (WrongResult e) {
            System.err.println("WRONG RESULT: " + e.getMessage());
            System.exit(1);
        }
        flush.run();
        System.out.println(Files.readString(reportPath, StandardCharsets.UTF_8));
    }

    private GraphNamingCost() {
    }
}
