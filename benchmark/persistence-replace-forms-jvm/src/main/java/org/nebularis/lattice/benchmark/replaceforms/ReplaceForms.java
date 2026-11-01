// SPDX-License-Identifier: MPL-2.0
// NB: This module has been produced using GenAI

package org.nebularis.lattice.benchmark.replaceforms;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.function.Function;
import java.util.function.Supplier;

import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonArray;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.dboe.base.file.Location;
import org.apache.jena.fuseki.main.FusekiServer;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSet;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.sparql.exec.http.QueryExecutionHTTP;
import org.apache.jena.system.Txn;
import org.apache.jena.tdb2.TDB2Factory;
import org.apache.jena.tdb2.sys.StoreConnection;
import org.apache.jena.update.UpdateAction;
import org.eclipse.rdf4j.model.Literal;
import org.eclipse.rdf4j.model.Value;
import org.eclipse.rdf4j.query.BindingSet;
import org.eclipse.rdf4j.query.QueryLanguage;
import org.eclipse.rdf4j.query.TupleQueryResult;
import org.eclipse.rdf4j.repository.Repository;
import org.eclipse.rdf4j.repository.RepositoryConnection;
import org.eclipse.rdf4j.repository.sail.SailRepository;
import org.eclipse.rdf4j.sail.memory.MemoryStore;

/**
 * What the generated named-graph replace and two candidate linear forms cost on Jena (in memory, TDB2 on disk and Fuseki over HTTP) and RDF4J, and how each store applies an update (ADR-A124, TSD-01, TD-42).
 *
 * <p>The forms, the workload and the checks come from {@code benchmark/persistence-replace-forms/check.py --emit}, so every store runs the same SPARQL text. The probes run first and are printed as a table.
 * <b>A wrong result from a generated form fails the run. Time never does.</b> A candidate form that is wrong is recorded as such.
 */
public final class ReplaceForms {

    /** A store under test. Every method opens and closes its own transaction. */
    interface Engine extends AutoCloseable {
        String name();

        /** Runs the request as one caller would, in its own transaction. Throws if the store refuses it or it fails. */
        void update(String text) throws Exception;

        long count(String selectCount);

        /** The triples of one graph as {@code <s> <p> "o" .} lines, for a comparison as sets. */
        Set<String> rows(String graph);

        /** Every quad in the store, the default graph included. */
        long totalQuads();

        /** What the store said about the last update beyond success, such as an HTTP status. */
        default String status() {
            return "";
        }

        @Override
        void close();
    }

    static final class WrongResult extends RuntimeException {
        WrongResult(String message) {
            super(message);
        }
    }

    // ---- Jena -------------------------------------------------------------------------------------------------------

    abstract static class JenaBase implements Engine {
        abstract <T> T read(String query, Function<QueryExecution, T> use);

        public long count(String selectCount) {
            return read(selectCount, qe -> qe.execSelect().next().getLiteral("n").getLong());
        }

        public Set<String> rows(String graph) {
            return read("SELECT ?s ?p ?o WHERE { GRAPH <" + graph + "> { ?s ?p ?o } }", qe -> {
                Set<String> out = new HashSet<>();
                ResultSet rs = qe.execSelect();
                while (rs.hasNext()) {
                    QuerySolution row = rs.next();
                    out.add(term(row.get("s")) + " " + term(row.get("p")) + " " + term(row.get("o")) + " .");
                }
                return out;
            });
        }

        public long totalQuads() {
            return count("SELECT (COUNT(*) AS ?n) WHERE { { ?s ?p ?o } UNION { GRAPH ?g { ?s ?p ?o } } }");
        }

        private static String term(RDFNode node) {
            if (node.isURIResource()) {
                return "<" + node.asResource().getURI() + ">";
            }
            if (node.isLiteral()) {
                return "\"" + node.asLiteral().getLexicalForm() + "\"";
            }
            return "_:" + node.asResource().getId().getLabelString();
        }
    }

    static final class LocalJena extends JenaBase {
        private final String name;
        private final Dataset dataset;
        private final Runnable release;

        LocalJena(String name, Dataset dataset, Runnable release) {
            this.name = name;
            this.dataset = dataset;
            this.release = release;
        }

        public String name() {
            return name;
        }

        <T> T read(String query, Function<QueryExecution, T> use) {
            return Txn.calculateRead(dataset, () -> {
                try (QueryExecution qe = QueryExecutionFactory.create(query, dataset)) {
                    return use.apply(qe);
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

    static void deleteTree(Path dir) {
        try (var walk = Files.walk(dir)) {
            walk.sorted(Comparator.reverseOrder()).forEach(p -> p.toFile().delete());
        } catch (IOException e) {
            // a temporary directory that stays behind is harmless
        }
    }

    static Engine tdb2Disk() {
        try {
            Path dir = Files.createTempDirectory("replaceforms-tdb2-");
            Location location = Location.create(dir.toString());
            return new LocalJena("jena tdb2 (disk)", TDB2Factory.connectDataset(location), () -> {
                StoreConnection.release(location);
                deleteTree(dir);
            });
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    /** A Fuseki server in this JVM over a TDB2 dataset on disk. Updates go to the dataset's update endpoint as one HTTP request, so a two-operation form travels as one request. */
    static final class FusekiEngine extends JenaBase {
        private final Path dir;
        private final Location location;
        private final Dataset dataset;
        private final FusekiServer server;
        private final HttpClient http = HttpClient.newHttpClient();
        private final String base;
        private int lastStatus;

        FusekiEngine() {
            try {
                dir = Files.createTempDirectory("replaceforms-fuseki-");
            } catch (IOException e) {
                throw new IllegalStateException(e);
            }
            location = Location.create(dir.toString());
            dataset = TDB2Factory.connectDataset(location);
            server = FusekiServer.create().port(0).add("/ds", dataset.asDatasetGraph()).build().start();
            base = "http://localhost:" + server.getPort() + "/ds";
        }

        public String name() {
            return "fuseki http (tdb2 disk)";
        }

        <T> T read(String query, Function<QueryExecution, T> use) {
            try (QueryExecution qe = QueryExecutionHTTP.service(base + "/query").query(query).build()) {
                return use.apply(qe);
            }
        }

        /** Sends the request, with a client timeout when {@code timeout} is not null. Returns the HTTP status. */
        int post(String text, Duration timeout) throws IOException, InterruptedException {
            HttpRequest.Builder request = HttpRequest.newBuilder(URI.create(base + "/update")).header("Content-Type", "application/sparql-update")
                .POST(HttpRequest.BodyPublishers.ofString(text, StandardCharsets.UTF_8));
            if (timeout != null) {
                request.timeout(timeout);
            }
            HttpResponse<String> response = http.send(request.build(), HttpResponse.BodyHandlers.ofString());
            lastStatus = response.statusCode();
            if (lastStatus >= 300) {
                String body = response.body().replace('\n', ' ');
                throw new IllegalStateException("HTTP " + lastStatus + ": " + body.substring(0, Math.min(160, body.length())));
            }
            return lastStatus;
        }

        public void update(String text) throws Exception {
            post(text, null);
        }

        public String status() {
            return "HTTP " + lastStatus;
        }

        public void close() {
            server.stop();
            dataset.close();
            StoreConnection.release(location);
            deleteTree(dir);
        }
    }

    // ---- RDF4J ------------------------------------------------------------------------------------------------------

    static final class Rdf4jEngine implements Engine {
        private final Repository repository = new SailRepository(new MemoryStore());
        private final RepositoryConnection connection;

        Rdf4jEngine() {
            repository.init();
            connection = repository.getConnection();
        }

        public String name() {
            return "rdf4j memory";
        }

        /** In a transaction of its own, as the sibling benchmark does, so the timing is the update's. */
        public void update(String text) {
            connection.begin();
            try {
                connection.prepareUpdate(QueryLanguage.SPARQL, text).execute();
                connection.commit();
            } catch (RuntimeException e) {
                connection.rollback();
                throw e;
            }
        }

        /** The store's own behaviour, with no transaction opened by the caller. Used by the probe of failure atomicity. */
        void updateAutoCommit(String text) {
            connection.prepareUpdate(QueryLanguage.SPARQL, text).execute();
        }

        public long count(String selectCount) {
            try (TupleQueryResult result = connection.prepareTupleQuery(QueryLanguage.SPARQL, selectCount).evaluate()) {
                BindingSet row = result.next();
                return ((Literal) row.getValue("n")).longValue();
            }
        }

        public Set<String> rows(String graph) {
            Set<String> out = new HashSet<>();
            try (TupleQueryResult result = connection.prepareTupleQuery(QueryLanguage.SPARQL, "SELECT ?s ?p ?o WHERE { GRAPH <" + graph + "> { ?s ?p ?o } }").evaluate()) {
                for (BindingSet row : result) {
                    out.add(term(row.getValue("s")) + " " + term(row.getValue("p")) + " " + term(row.getValue("o")) + " .");
                }
            }
            return out;
        }

        public long totalQuads() {
            return connection.size();
        }

        private static String term(Value value) {
            if (value instanceof Literal literal) {
                return "\"" + literal.getLabel() + "\"";
            }
            return value.isIRI() ? "<" + value.stringValue() + ">" : "_:" + value.stringValue();
        }

        public void close() {
            connection.close();
            repository.shutDown();
        }
    }

    static final Map<String, Supplier<Engine>> ENGINES = new LinkedHashMap<>();

    static {
        ENGINES.put("jena in-memory", () -> new LocalJena("jena in-memory", DatasetFactory.createTxnMem(), () -> { }));
        ENGINES.put("jena tdb2 (disk)", ReplaceForms::tdb2Disk);
        ENGINES.put("fuseki http (tdb2 disk)", FusekiEngine::new);
        ENGINES.put("rdf4j memory", Rdf4jEngine::new);
    }

    // ---- the probes -------------------------------------------------------------------------------------------------

    static final String P1_STORED = "INSERT DATA { GRAPH <urn:g> { <urn:s> <urn:p> <urn:o> } }";
    static final String P1_UPDATE = "DELETE { GRAPH <urn:g> { ?d <urn:p> <urn:o> } } INSERT { GRAPH <urn:g> { ?i <urn:p> <urn:o> } } WHERE { VALUES (?i ?d) { %s } }";
    static final String P1_KEPT = "SELECT (COUNT(*) AS ?n) WHERE { GRAPH <urn:g> { <urn:s> <urn:p> ?o } }";

    /** One probe's result, or the error that stopped it. */
    interface Probe {
        String run(Supplier<Engine> factory) throws Exception;
    }

    static boolean p1Kept(Supplier<Engine> factory, String rows) throws Exception {
        try (Engine engine = factory.get()) {
            engine.update(P1_STORED);
            engine.update(String.format(P1_UPDATE, rows));
            return engine.count(P1_KEPT) == 1;
        }
    }

    /** P1, TSD-01: the specification removes every deletion and then adds every insertion, so the triple survives in either row order. */
    static String p1(Supplier<Engine> factory) throws Exception {
        boolean insertFirst = p1Kept(factory, "(<urn:s> UNDEF) (UNDEF <urn:s>)");
        boolean deleteFirst = p1Kept(factory, "(UNDEF <urn:s>) (<urn:s> UNDEF)");
        return (insertFirst && deleteFirst ? "snapshot" : "per-solution") + " (insert row first: " + (insertFirst ? "kept" : "lost") + ", delete row first: " + (deleteFirst ? "kept" : "lost") + ")";
    }

    /** P4: a template quad whose graph variable is unbound. Is it skipped, or written somewhere? */
    static String p4(Supplier<Engine> factory) throws Exception {
        try (Engine engine = factory.get()) {
            long before = engine.totalQuads();
            try {
                engine.update("INSERT { GRAPH ?g { <urn:a> <urn:b> <urn:c> } } WHERE { }");
            } catch (Exception e) {
                return "the update failed: " + brief(e);
            }
            long after = engine.totalQuads();
            return after == before ? "nothing written (quads " + before + " before and after)" : "wrote " + (after - before) + " quad(s) (quads " + before + " before, " + after + " after)";
        }
    }

    /** P2, TSD-06 and TSD-Q13: a request whose second operation fails. Did it fail, and is the first operation's insert kept or rolled back? */
    static String p2(Supplier<Engine> factory) throws Exception {
        try (Engine engine = factory.get()) {
            String failed;
            String request = "INSERT DATA { GRAPH <urn:g> { <urn:s> <urn:p> <urn:o> } } ; LOAD <urn:no-such>";
            try {
                if (engine instanceof Rdf4jEngine rdf4j) {
                    rdf4j.updateAutoCommit(request);
                } else {
                    engine.update(request);
                }
                failed = "the request did not fail";
            } catch (Exception e) {
                failed = "the request failed (" + brief(e) + ")";
            }
            String status = engine.status().isEmpty() ? "" : ", " + engine.status();
            long kept = engine.count(P1_KEPT);
            return failed + status + ", the insert was " + (kept == 1 ? "kept" : "rolled back");
        }
    }

    /** P6, Jena only: blank nodes in a template. The specification mints a fresh blank node per solution, so 3 means once per binding and 1 means once. */
    static String p6(Supplier<Engine> factory) throws Exception {
        try (Engine engine = factory.get()) {
            engine.update("INSERT DATA { GRAPH <urn:b> { <urn:x1> <urn:y> <urn:z1> . <urn:x2> <urn:y> <urn:z2> . <urn:x3> <urn:y> <urn:z3> } }");
            engine.update("DELETE { GRAPH <urn:b> { ?s ?p ?o } } INSERT { GRAPH <urn:b> { <urn:r> <urn:q> [ <urn:v> \"x\" ] } } WHERE { GRAPH <urn:b> { ?s ?p ?o } }");
            long blanks = engine.count("SELECT (COUNT(DISTINCT ?b) AS ?n) WHERE { GRAPH <urn:b> { <urn:r> <urn:q> ?b FILTER(isBlank(?b)) } }");
            long triples = engine.count("SELECT (COUNT(*) AS ?n) WHERE { GRAPH <urn:b> { ?s ?p ?o } }");
            return blanks + " distinct blank node(s), " + triples + " triple(s) in the graph (3 solutions)";
        }
    }

    static String brief(Throwable e) {
        String message = String.valueOf(e.getMessage()).replace('\n', ' ');
        return e.getClass().getSimpleName() + ": " + message.substring(0, Math.min(140, message.length()));
    }

    static Set<String> set(JsonArray array) {
        Set<String> out = new HashSet<>();
        for (var item : array) {
            out.add(item.getAsString().value());
        }
        return out;
    }

    /**
     * P7, Fuseki only: the interrupted large update. Sends {@code R0} at the largest size up to 3,000 with a client timeout of 50 ms so the client abandons the request, waits two seconds and checks whether the
     * graph is at the old state, the new state or anything else. It checks again later, since the server may still be working.
     */
    static String p7(JsonObject doc) throws Exception {
        String size = "3000";
        JsonObject run = loadRun(family(doc, "named-graph"), size);
        JsonObject step = run.get("forms").getAsObject().get("R0").getAsArray().get(0).getAsObject();
        try (FusekiEngine engine = new FusekiEngine()) {
            engine.update(run.get("create").getAsString().value());
            String graph = step.get("rootGraph").getAsString().value();
            Set<String> add = set(step.get("expect").getAsObject().get("add").getAsArray());
            Set<String> del = set(step.get("expect").getAsObject().get("del").getAsArray());
            Set<String> next = set(step.get("expect").getAsObject().get("root").getAsArray());
            Set<String> old = new HashSet<>(next);
            old.removeAll(add);
            old.addAll(del);
            String client;
            long start = System.nanoTime();
            try {
                engine.post(step.get("text").getAsString().value(), Duration.ofMillis(50));
                client = "the request finished within 50 ms (" + engine.status() + ")";
            } catch (java.net.http.HttpTimeoutException e) {
                client = "the client abandoned the request after " + (System.nanoTime() - start) / 1_000_000 + " ms";
            } catch (Exception e) {
                client = "the client stopped with " + brief(e);
            }
            Thread.sleep(2000);
            String atTwo = classify(engine.rows(graph), old, next);
            String later;
            long waited = 2;
            String seen = atTwo;
            while (waited < 120 && seen.equals(atTwo)) {
                Thread.sleep(5000);
                waited += 5;
                seen = classify(engine.rows(graph), old, next);
            }
            later = seen + " after " + waited + " s";
            return client + ", at 2 s the graph is " + atTwo + ", later " + later;
        }
    }

    static String classify(Set<String> got, Set<String> old, Set<String> next) {
        if (got.equals(next)) {
            return "the new state";
        }
        if (got.equals(old)) {
            return "the old state";
        }
        return "neither (" + got.size() + " triples)";
    }

    /** The child's side of a probe job: runs every probe that applies to the engine and prints one line each. */
    static void runProbes(String engineName, JsonObject doc) {
        Supplier<Engine> factory = ENGINES.get(engineName);
        boolean jena = !engineName.startsWith("rdf4j");
        Map<String, Probe> probes = new LinkedHashMap<>();
        probes.put("P1 snapshot semantics", ReplaceForms::p1);
        probes.put("P4 unbound graph variable in a template", ReplaceForms::p4);
        probes.put("P2 failure atomicity", ReplaceForms::p2);
        if (jena) {
            probes.put("P6 blank nodes in a template", ReplaceForms::p6);
        }
        for (var probe : probes.entrySet()) {
            String result;
            try {
                result = probe.getValue().run(factory);
            } catch (Throwable e) {
                result = "error: " + brief(e);
            }
            System.out.println("PROBE\t" + probe.getKey() + "\t" + result);
        }
        if (engineName.startsWith("fuseki")) {
            String result;
            try {
                result = p7(doc);
            } catch (Throwable e) {
                result = "error: " + brief(e);
            }
            System.out.println("PROBE\tP7 interrupted large update (R0, M = 3000)\t" + result);
        }
    }

    // ---- the forms --------------------------------------------------------------------------------------------------

    static JsonObject family(JsonObject doc, String name) {
        return doc.get("families").getAsObject().get(name).getAsObject();
    }

    /** The scenario of one size: a create and the replaces of every form. The sized runs are large, so each is a file of its own, named by the family's {@code runs} entry and read from beside operations.json. */
    static JsonObject loadRun(JsonObject fam, String size) {
        Path operations = Path.of(System.getProperty("replaceforms.operations", "benchmark/persistence-replace-forms/operations.json"));
        try (InputStream in = Files.newInputStream(operations.resolveSibling(fam.get("runs").getAsObject().get(size).getAsString().value()))) {
            return JSON.parse(in);
        } catch (IOException e) {
            throw new java.io.UncheckedIOException(e);
        }
    }

    /** The store refused an update. For a generated form this fails the run, and for a candidate form it is recorded as an error. */
    static final class UpdateFailed extends RuntimeException {
        UpdateFailed(String message) {
            super(message);
        }
    }

    /** The reasons a replace went wrong, empty when nothing did. */
    static List<String> verify(Engine engine, JsonObject step, long outsideBefore) {
        List<String> issues = new ArrayList<>();
        JsonObject expect = step.get("expect").getAsObject();
        for (String[] item : new String[][] {{"the aggregate's graph", "rootGraph", "root"}, {"the add graph", "addGraph", "add"}, {"the delete graph", "delGraph", "del"}}) {
            Set<String> expected = set(expect.get(item[2]).getAsArray());
            Set<String> got = engine.rows(step.get(item[1]).getAsString().value());
            if (!got.equals(expected)) {
                Set<String> missing = new HashSet<>(expected);
                missing.removeAll(got);
                Set<String> extra = new HashSet<>(got);
                extra.removeAll(expected);
                List<String> kept = missing.stream().filter(r -> r.endsWith("\"k\" .")).sorted().toList();
                issues.add(item[0] + " is missing " + missing.size() + " expected triples" + (kept.isEmpty() ? "" : ", " + kept.size() + " of them kept triples (first lost " + kept.get(0).split(" ")[0] + ")")
                    + " and holds " + extra.size() + " unexpected");
            }
        }
        for (var check : step.get("counts").getAsArray()) {
            String query = check.getAsObject().get("query").getAsString().value();
            long expect1 = check.getAsObject().get("expect").getAsNumber().value().longValue();
            long seen = engine.count(query);
            if (seen != expect1) {
                issues.add(query + " counted " + seen + ", not " + expect1);
            }
        }
        long outside = engine.count(step.get("outsideQuery").getAsString().value());
        if (outside != outsideBefore) {
            issues.add("graphs outside the replace's own changed from " + outsideBefore + " to " + outside + " quads");
        }
        return issues;
    }

    /**
     * Runs a scenario, a create and the replaces of one form, on a fresh store and returns the best time of a replace in milliseconds. Raises WrongResult when a check fails and UpdateFailed when the store refuses an update.
     * {@code mentionsRoot}, when not null, is a count query that must give 0 before the first replace. {@code detail}, when not null, collects whether the store lists the aggregate's graph after the last replace.
     */
    static double runScenario(Supplier<Engine> factory, JsonObject fam, JsonObject scenario, String form, String label, String mentionsRoot, StringBuilder detail) {
        JsonArray steps = scenario.get("forms").getAsObject().get(form).getAsArray();
        String preload = fam.get("preload").getAsString().value();
        String prefix = label.isEmpty() ? "" : label + " ";
        try (Engine engine = factory.get()) {
            try {
                if (!preload.isEmpty()) {
                    engine.update(preload);
                }
                engine.update(scenario.get("create").getAsString().value());
            } catch (Exception e) {
                throw new UpdateFailed(prefix + "the create failed, " + brief(e));
            }
            double best = Double.MAX_VALUE;
            int n = 0;
            for (var item : steps) {
                n++;
                JsonObject step = item.getAsObject();
                if (n == 1 && mentionsRoot != null) {
                    long mentions = engine.count(mentionsRoot);
                    if (mentions != 0) {
                        throw new WrongResult(prefix + "the root is in " + mentions + " triples of the data graph before the replace");
                    }
                }
                long before = engine.count(step.get("outsideQuery").getAsString().value());
                long start = System.nanoTime();
                try {
                    engine.update(step.get("text").getAsString().value());
                } catch (Exception e) {
                    throw new UpdateFailed(prefix + "replace " + n + " failed, " + brief(e));
                }
                best = Math.min(best, (System.nanoTime() - start) / 1e6);
                if (detail != null && n == steps.size()) {
                    try {
                        long listed = engine.count("SELECT (COUNT(*) AS ?n) WHERE { GRAPH ?g { } FILTER(?g = <" + step.get("rootGraph").getAsString().value() + ">) }");
                        detail.append("graph listed after: ").append(listed > 0 ? "yes" : "no");
                    } catch (RuntimeException e) {
                        detail.append("graph listed after: unknown (").append(brief(e)).append(")");
                    }
                }
                List<String> issues = verify(engine, step, before);
                if (!issues.isEmpty()) {
                    throw new WrongResult(prefix + "replace " + n + ": " + String.join("; ", issues));
                }
            }
            return best;
        }
    }

    static final String[] EDGE_FULL = {"R0", "R1-candidate", "R2-values-candidate"};

    /** One edge case: pass, wrong with the verify's reasons, or error with the store's message. */
    static String edgeCell(Supplier<Engine> factory, JsonObject fam, String caseId, String form, boolean full, boolean snapshot) {
        if (!form.equals("R0") && !full) {
            return form.equals("R2-values-candidate") ? "not run: per-solution store (P1)" : "not run: R0 only on this engine";
        }
        if (form.equals("R2-values-candidate") && !snapshot) {
            return "not run: per-solution store (P1)";
        }
        StringBuilder detail = caseId.equals("E2") ? new StringBuilder() : null;
        try {
            JsonObject scenario = fam.get("edges").getAsObject().get(caseId).getAsObject();
            runScenario(factory, fam, scenario, form, "", caseId.equals("E5") ? fam.get("mentionsRoot").getAsString().value() : null, detail);
            return "pass" + (detail == null || detail.length() == 0 ? "" : " (" + detail + ")");
        } catch (WrongResult e) {
            return "wrong: " + e.getMessage().replace('\n', ' ');
        } catch (UpdateFailed e) {
            return "error: " + e.getMessage().replace('\n', ' ');
        } catch (Throwable e) {
            return "error: " + brief(e);
        }
    }

    /** The child's side of an edge job: every case and form of one family on one store, then the bare sweep counts with the root in no triple. */
    static void runEdges(String engineName, String familyName, JsonObject doc) {
        Supplier<Engine> factory = ENGINES.get(engineName);
        JsonObject fam = family(doc, familyName);
        boolean snapshot;
        try {
            snapshot = p1(factory).startsWith("snapshot");
        } catch (Throwable e) {
            snapshot = false;
        }
        boolean full = !engineName.startsWith("rdf4j");
        List<String> cases = new ArrayList<>(fam.get("edges").getAsObject().keys());
        java.util.Collections.sort(cases);
        for (String caseId : cases) {
            for (var formItem : fam.get("edgeForms").getAsArray()) {
                String form = formItem.getAsString().value();
                System.out.println("EDGE\t" + caseId + "\t" + form + "\t" + edgeCell(factory, fam, caseId, form, full, snapshot));
            }
        }
        if (!fam.get("sweep").isNull()) {
            JsonObject sweep = fam.get("sweep").getAsObject();
            JsonObject scenario = fam.get("edges").getAsObject().get("E5").getAsObject();
            try (Engine engine = factory.get()) {
                String preload = fam.get("preload").getAsString().value();
                if (!preload.isEmpty()) {
                    engine.update(preload);
                }
                engine.update(scenario.get("create").getAsString().value());
                System.out.println("SWEEP\t" + engine.count(sweep.get("with").getAsString().value()) + "\t" + engine.count(sweep.get("without").getAsString().value()));
            } catch (Throwable e) {
                System.out.println("SWEEP\terror: " + brief(e) + "\t");
            }
        }
    }

    /** The best of three timings of the composite family's bare sweep over the aggregate at one size. Raises WrongResult if it does not count M. */
    static String sweepTime(Supplier<Engine> factory, JsonObject fam, String size) throws Exception {
        JsonObject sweep = fam.get("sweep").getAsObject();
        try (Engine engine = factory.get()) {
            String preload = fam.get("preload").getAsString().value();
            if (!preload.isEmpty()) {
                engine.update(preload);
            }
            engine.update(loadRun(fam, size).get("create").getAsString().value());
            double best = Double.MAX_VALUE;
            long seen = 0;
            for (int i = 0; i < 3; i++) {
                long start = System.nanoTime();
                seen = engine.count(sweep.get("with").getAsString().value());
                best = Math.min(best, (System.nanoTime() - start) / 1e6);
            }
            if (seen != Long.parseLong(size)) {
                throw new WrongResult(engine.name() + ": the bare sweep counted " + seen + " at M=" + size);
            }
            return String.format("%.1f (count %d)", best, seen);
        }
    }

    // ---- one JVM per measurement ---------------------------------------------------------------------------------------

    /*
     * A store that runs out of memory does not give its heap back to the JVM that ran it, so each measurement runs in a child JVM with its own heap cap (-Xmx)
     * and a wall-clock limit. A child that runs out of memory or does not finish is recorded as such and costs only its own row. That is not a wrong result and does not fail the run.
     */

    private static final int OUT_OF_MEMORY_EXIT = 3;
    private static final String[] RESULT_LINES = {"RESULT\t", "WRONG\t", "ERROR\t", "PROBE\t", "EDGE\t", "SWEEP\t"};

    private static String heap() {
        return System.getProperty("replaceforms.heap", "4g");
    }

    /** Runs one job in a child JVM and returns its output lines. Returns a single {@code END} line with the reason when the child did not finish. */
    static List<String> inChild(String job) {
        long timeout = Long.parseLong(System.getProperty("replaceforms.timeout", "900"));
        try {
            String java = ProcessHandle.current().info().command().orElse("java");
            Path errors = Files.createTempFile("replaceforms-child-", ".err");
            Process process = new ProcessBuilder(java, "-Xmx" + heap(), "-XX:+ExitOnOutOfMemoryError", "-Dreplaceforms.job=" + job,
                "-Dreplaceforms.operations=" + System.getProperty("replaceforms.operations"), "-classpath", System.getProperty("java.class.path"), ReplaceForms.class.getName())
                .redirectError(errors.toFile()).start();
            Path out = Files.createTempFile("replaceforms-child-", ".out");
            Thread reader = new Thread(() -> {
                try (InputStream in = process.getInputStream()) {
                    Files.write(out, in.readAllBytes());
                } catch (IOException e) {
                    // the exit code tells
                }
            });
            reader.start();
            if (!process.waitFor(timeout, TimeUnit.SECONDS)) {
                process.destroyForcibly().waitFor();
                reader.join();
                return List.of("END\tdid not finish: no result within " + timeout + " s");
            }
            reader.join();
            List<String> lines = Files.readAllLines(out, StandardCharsets.UTF_8);
            if (lines.stream().noneMatch(l -> Arrays.stream(RESULT_LINES).anyMatch(l::startsWith))) {
                if (process.exitValue() == OUT_OF_MEMORY_EXIT) {
                    return List.of("END\tdid not finish: out of memory under -Xmx" + heap());
                }
                List<String> err = Files.readAllLines(errors, StandardCharsets.UTF_8);
                return List.of("END\tdid not finish: the child exited " + process.exitValue() + (err.isEmpty() ? "" : " (" + err.get(err.size() - 1) + ")"));
            }
            Files.deleteIfExists(errors);
            Files.deleteIfExists(out);
            return lines;
        } catch (IOException | InterruptedException e) {
            throw new IllegalStateException(e);
        }
    }

    /** The child's side: runs the one job and prints its lines. */
    static void runJob(String job, JsonObject doc) {
        String[] part = job.split("\\|", -1);
        switch (part[0]) {
            case "probes" -> runProbes(part[1], doc);
            case "edges" -> runEdges(part[1], part[2], doc);
            default -> {
                try {
                    JsonObject fam = family(doc, part[2]);
                    if (part[0].equals("sweep")) {
                        System.out.println("RESULT\t" + sweepTime(ENGINES.get(part[1]), fam, part[4]));
                    } else {
                        JsonObject scenario = loadRun(fam, part[4]);
                        double ms = runScenario(ENGINES.get(part[1]), fam, scenario, part[3], part[1] + "/" + part[2] + "/" + part[3] + "/M=" + part[4], null, null);
                        System.out.println("RESULT\t" + String.format("%.1f", ms));
                    }
                } catch (WrongResult e) {
                    System.out.println("WRONG\t" + e.getMessage().replace('\n', ' '));
                } catch (UpdateFailed e) {
                    System.out.println("ERROR\t" + e.getMessage().replace('\n', ' '));
                } catch (Exception e) {
                    System.out.println("ERROR\t" + brief(e));
                }
            }
        }
        System.exit(0);
    }

    static String jarOf(Class<?> type) {
        try {
            return Path.of(type.getProtectionDomain().getCodeSource().getLocation().toURI()).getFileName().toString();
        } catch (Exception e) {
            return "unknown";
        }
    }

    static String cell(String line) {
        if (line.startsWith("RESULT\t")) {
            return line.substring(7);
        }
        if (line.startsWith("WRONG\t")) {
            return "wrong: " + line.substring(6);
        }
        if (line.startsWith("ERROR\t")) {
            return "error: " + line.substring(6);
        }
        return line.substring(line.indexOf('\t') + 1);
    }

    public static void main(String[] args) throws IOException {
        Path operations = Path.of(System.getProperty("replaceforms.operations", "benchmark/persistence-replace-forms/operations.json"));
        JsonObject doc;
        try (InputStream in = Files.newInputStream(operations)) {
            doc = JSON.parse(in);
        }
        String job = System.getProperty("replaceforms.job");
        if (job != null) {
            runJob(job, doc);
            return;
        }
        boolean quick = "1".equals(System.getProperty("replaceforms.quick"));
        long maximum = quick ? 1000 : Long.parseLong(System.getProperty("replaceforms.max", "10000"));
        long maxR0 = Long.parseLong(System.getProperty("replaceforms.maxr0", "3000"));
        Path reportPath = Path.of(System.getProperty("replaceforms.report", "benchmark/persistence-replace-forms-jvm/report.md"));
        StringBuilder header = new StringBuilder("Run ").append(java.time.LocalDate.now()).append(": java ").append(System.getProperty("java.version")).append(", jena ")
            .append(org.apache.jena.Jena.VERSION).append(" (").append(jarOf(org.apache.jena.tdb2.TDB2Factory.class)).append("), fuseki ").append(jarOf(FusekiServer.class)).append(", rdf4j ")
            .append(jarOf(SailRepository.class)).append(", ").append(System.getProperty("os.arch")).append(", heap cap ").append(heap()).append(" for each measurement\n\n");
        StringBuilder probeTable = new StringBuilder("## Probes\n\n| Store | Probe | Result |\n|---|---|---|\n");
        StringBuilder edgeSection = new StringBuilder();
        StringBuilder formTables = new StringBuilder();
        StringBuilder sweepSection = new StringBuilder();
        Runnable flush = () -> {
            try {
                Files.writeString(reportPath, header.toString() + probeTable + "\n" + edgeSection + formTables + sweepSection, StandardCharsets.UTF_8);
            } catch (IOException e) {
                throw new java.io.UncheckedIOException(e);
            }
        };
        Map<String, Boolean> snapshot = new LinkedHashMap<>();
        for (String engine : ENGINES.keySet()) {
            System.err.println("progress: probes " + engine);
            for (String line : inChild("probes|" + engine)) {
                if (line.startsWith("PROBE\t")) {
                    String[] cells = line.split("\t", 3);
                    probeTable.append(String.format("| %s | %s | %s |%n", engine, cells[1], cells[2]));
                    if (cells[1].startsWith("P1")) {
                        snapshot.put(engine, cells[2].startsWith("snapshot"));
                    }
                } else if (line.startsWith("END\t")) {
                    probeTable.append(String.format("| %s | all | %s |%n", engine, line.substring(4)));
                }
            }
            snapshot.putIfAbsent(engine, false);
            flush.run();
        }
        System.out.println(probeTable);
        List<String> familyNames = new ArrayList<>(doc.get("families").getAsObject().keys());
        familyNames.sort((a, b) -> Integer.compare(a.equals("named-graph") ? 0 : 1, b.equals("named-graph") ? 0 : 1));
        // the edge cases, one table per family with the engines as columns
        StringBuilder sweepCounts = new StringBuilder();
        for (String familyName : familyNames) {
            JsonObject fam = family(doc, familyName);
            Map<String, Map<String, String>> cells = new LinkedHashMap<>();
            for (String engine : ENGINES.keySet()) {
                System.err.println("progress: edge cases " + familyName + " " + engine);
                for (String line : inChild("edges|" + engine + "|" + familyName)) {
                    if (line.startsWith("EDGE\t")) {
                        String[] c = line.split("\t", 4);
                        cells.computeIfAbsent(c[1] + "\t" + c[2], k -> new LinkedHashMap<>()).put(engine, c[3]);
                    } else if (line.startsWith("SWEEP\t")) {
                        String[] c = line.split("\t", -1);
                        sweepCounts.append(String.format("| %s | %s | %s |%n", engine, c[1], c.length > 2 ? c[2] : ""));
                    } else if (line.startsWith("END\t")) {
                        cells.computeIfAbsent("all\tall", k -> new LinkedHashMap<>()).put(engine, line.substring(4));
                    }
                }
            }
            edgeSection.append("## Edge cases, ").append(familyName).append(" family\n\n| Case | Form | ").append(String.join(" | ", ENGINES.keySet())).append(" |\n|---|---|").append("---|".repeat(ENGINES.size())).append("\n");
            JsonObject edges = fam.get("edges").getAsObject();
            for (var entry : cells.entrySet()) {
                String[] key = entry.getKey().split("\t");
                String title = key[0].equals("all") ? "all" : key[0] + " " + edges.get(key[0]).getAsObject().get("title").getAsString().value();
                StringBuilder row = new StringBuilder("| " + title + " | " + key[1] + " |");
                for (String engine : ENGINES.keySet()) {
                    row.append(' ').append(entry.getValue().getOrDefault(engine, "")).append(" |");
                }
                edgeSection.append(row).append('\n');
            }
            edgeSection.append('\n');
            flush.run();
        }
        if (sweepCounts.length() > 0) {
            edgeSection.append("## Composite family, the bare sweep with the root in no triple\n\n| Store | Solutions of the sweep | Solutions without `?s ?p ?o` |\n|---|---|---|\n").append(sweepCounts).append('\n');
            flush.run();
        }
        List<String> generatedWrong = new ArrayList<>();
        for (String familyName : familyNames) {
            JsonObject fam = family(doc, familyName);
            JsonArray forms = fam.get("forms").getAsArray();
            JsonArray sizes = fam.get("sizes").getAsArray();
            for (String engine : ENGINES.keySet()) {
                formTables.append("## ").append(familyName).append(" family, ").append(engine).append(", best of ").append(doc.get("repeats").getAsNumber().value()).append(" replaces, milliseconds\n\n| Form | M (N equals M) | ms |\n|---|---|---|\n");
                for (var formItem : forms) {
                    JsonObject form = formItem.getAsObject();
                    String id = form.get("id").getAsString().value();
                    boolean generated = form.get("generated").getAsBoolean().value();
                    boolean needsSnapshot = form.get("needsSnapshot").getAsBoolean().value();
                    boolean stopped = false;
                    for (var sizeItem : sizes) {
                        long m = sizeItem.getAsNumber().value().longValue();
                        if (m > maximum) {
                            continue;
                        }
                        String cell;
                        if (generated && m > maxR0) {
                            cell = "not run: above replaceforms.maxr0 (" + maxR0 + ")";
                        } else if (needsSnapshot && !snapshot.get(engine)) {
                            cell = "not run: per-solution store (P1)";
                        } else if (stopped) {
                            cell = "not run: a smaller size did not finish";
                        } else {
                            System.err.println("progress: " + familyName + " " + engine + " " + id + " " + m);
                            String line = inChild("form|" + engine + "|" + familyName + "|" + id + "|" + m).get(0);
                            cell = cell(line);
                            stopped = line.startsWith("END\t");
                            if (generated && (cell.startsWith("wrong:") || cell.startsWith("error:"))) {
                                generatedWrong.add(familyName + "/" + engine + "/" + id + "/M=" + m + ": " + cell);
                            }
                        }
                        formTables.append(String.format("| %s | %,d | %s |%n", form.get("label").getAsString().value(), m, cell));
                        flush.run();
                    }
                }
                formTables.append('\n');
            }
            if (!fam.get("sweep").isNull()) {
                sweepSection.append("## ").append(familyName).append(" family, the bare sweep alone, best of three, milliseconds\n\n| Store | M | ms |\n|---|---|---|\n");
                for (String engine : ENGINES.keySet()) {
                    for (var sizeItem : fam.get("sweep").getAsObject().get("sizes").getAsArray()) {
                        long m = sizeItem.getAsNumber().value().longValue();
                        if (m > maximum) {
                            continue;
                        }
                        System.err.println("progress: " + familyName + " " + engine + " bare sweep " + m);
                        sweepSection.append(String.format("| %s | %,d | %s |%n", engine, m, cell(inChild("sweep|" + engine + "|" + familyName + "|sweep|" + m).get(0))));
                        flush.run();
                    }
                }
                sweepSection.append('\n');
            }
        }
        flush.run();
        System.out.println(Files.readString(reportPath, StandardCharsets.UTF_8));
        if (!generatedWrong.isEmpty()) {
            System.err.println("WRONG RESULT from a generated form:\n" + String.join("\n", generatedWrong));
            System.exit(1);
        }
    }

    private ReplaceForms() {
    }
}
