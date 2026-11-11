// SPDX-License-Identifier: MPL-2.0
// NB: This module has been produced using GenAI
package org.nebularis.lattice.benchmark.creditkinds;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.function.Supplier;
import java.util.stream.Stream;

import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonArray;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.atlas.json.JsonValue;
import org.apache.jena.query.ARQ;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSetFactory;
import org.apache.jena.query.ResultSetRewindable;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.system.Txn;
import org.apache.jena.tdb2.TDB2Factory;

/**
 * What a credit's kind, a stepwise credit ceiling, checkpoints and a shortcut cost an ancestor's balance read on Jena, called from Java.
 *
 * <p>The corpora and every read's expected balance and posting count are written by {@code benchmark/ledger-credit-kinds/check.py --emit}, so the history and the model are the Python
 * benchmark's. This runs the same reads (plain, kind-filtered, stepwise, and the shortcut, each from the start of history and from the last checkpoint) on Jena in memory and on
 * TDB2 on disk in a temporary directory that is removed afterwards. The stepwise fold is an ordered SELECT folded here, so its rows do not cross a pipe. The timings go to a JSON file
 * the Python report merges.
 *
 * <p><b>A wrong balance or posting count fails this benchmark, with a non-zero exit. Time never does (ADR-A124).</b>
 */
public final class CreditKinds {

    static final String L = "https://example.org/ledger-kinds#";
    static final String PREFIX = "PREFIX l: <" + L + "> ";
    static final String[] LEVELS = {"contract", "sublimit", "section", "root"};
    static final String[] FOLDS = {"plain", "kind-filtered", "stepwise"};
    static final Map<String, String> KIND_JOIN = Map.of(
            "optional", "OPTIONAL { ?p l:kind ?k } ",
            "union", "{ ?p l:direction l:Debit } UNION { ?p l:kind ?k } UNION { ?p l:direction l:Credit . FILTER NOT EXISTS { ?p l:kind ?z2 } } ");
    static final String SIGNED = "BIND(IF(?d = l:Debit, -?a, ?a) AS ?signed)";

    /** A wrong balance, posting count or stored count. The one way the run fails. */
    static final class WrongResult extends RuntimeException {
        WrongResult(String message) {
            super(message);
        }
    }

    record Acct(String iri, int level, long stated, List<String> graphPrefixes, List<String> contracts) {}

    /** What a read returned and how long its parts took, in seconds. */
    record Res(long balance, long rows, double query, double transfer, double loop, boolean fellBack) {}

    /** Totals over the reads of one kind at one level. */
    static final class Total {
        long reads, rows, fallbacks;
        double seconds, query, transfer, loop;

        void add(Res r, double elapsed) {
            reads++;
            rows += r.rows;
            seconds += elapsed;
            query += r.query;
            transfer += r.transfer;
            loop += r.loop;
            if (r.fellBack) {
                fallbacks++;
            }
        }
    }

    static int every;
    static final Map<String, Acct> ACCTS = new HashMap<>();

    // ---- queries, the same text as check.py builds ----

    static String graphsFor(Acct a, int point, int first) {
        int last = (point - 1) / every;
        StringBuilder out = new StringBuilder();
        for (String prefix : a.graphPrefixes()) {
            for (int n = first; n <= last; n++) {
                out.append('<').append(prefix).append(n).append("> ");
            }
        }
        return out.toString();
    }

    static String scan(Acct a, int point, boolean withKind, String form, int first, String extra) {
        String kind = withKind ? KIND_JOIN.get(form) : "";
        return "{ VALUES ?g { " + graphsFor(a, point, first) + "} GRAPH ?g { ?p l:position ?pos ; l:microPosition ?mp ; l:direction ?d ; l:amount ?a . " + extra
                + "FILTER(?pos <= " + point + ") " + kind + "} }";
    }

    static String kindFilter(Acct a) {
        return "FILTER(?d = l:Debit || NOT EXISTS { <" + a.iri() + "> l:accepts ?z } || EXISTS { <" + a.iri() + "> l:accepts ?k })";
    }

    static ResultSetRewindable select(Dataset ds, String text) {
        try (QueryExecution execution = QueryExecution.dataset(ds).query(text).build()) {
            return ResultSetFactory.copyResults(execution.execSelect());
        }
    }

    static long number(QuerySolution row, String name) {
        return row.contains(name) ? row.getLiteral(name).getLong() : 0;
    }

    static long stated(Dataset ds, Acct a) {
        return number(select(ds, PREFIX + "SELECT ?s WHERE { <" + a.iri() + "> l:statedAmount ?s }").next(), "s");
    }

    /** The first period graph to fold and the balances (plain, kind-filtered, stepwise) the fold starts from. */
    record Start(int first, long[] balance) {}

    static Start startOf(Dataset ds, Acct a, int point, boolean checkpointed, long base) {
        int k = point / every - 1;
        if (checkpointed && k >= 0) {
            QuerySolution row = select(ds, PREFIX + "SELECT ?pl ?kd ?st WHERE { GRAPH <urn:graph:checkpoint:" + k + "> { ?c l:account <" + a.iri()
                    + "> ; l:plainBalance ?pl ; l:kindBalance ?kd ; l:stepBalance ?st } }").next();
            return new Start(k + 1, new long[] {number(row, "pl"), number(row, "kd"), number(row, "st")});
        }
        return new Start(0, new long[] {base, base, base});
    }

    static long[] aggregate(Dataset ds, Acct a, int point, int first, boolean withKind, String form) {
        String text = PREFIX + "SELECT (SUM(?signed) AS ?sum) (COUNT(?p) AS ?folded) WHERE { " + scan(a, point, withKind, form, first, "") + " "
                + (withKind ? kindFilter(a) : "") + " " + SIGNED + " }";
        QuerySolution row = select(ds, text).next();
        return new long[] {number(row, "sum"), number(row, "folded")};
    }

    static Res read(Dataset ds, String fold, Acct a, int point, boolean checkpointed, String form) {
        return Txn.calculateRead(ds, () -> readIn(ds, fold, a, point, checkpointed, form));
    }

    static Res readIn(Dataset ds, String fold, Acct a, int point, boolean checkpointed, String form) {
        long base = stated(ds, a);
        Start start = startOf(ds, a, point, checkpointed, base);
        if (!fold.equals("stepwise")) {
            boolean withKind = fold.equals("kind-filtered");
            long[] total = aggregate(ds, a, point, start.first(), withKind, form);
            return new Res(start.balance()[withKind ? 1 : 0] + total[0], total[1], 0, 0, 0, false);
        }
        String text = PREFIX + "SELECT ?pos ?mp ?d ?a ?ap WHERE { " + scan(a, point, true, form, start.first(), "OPTIONAL { ?p l:applied ?ap } ") + " " + kindFilter(a)
                + " } ORDER BY ?pos ?mp";
        long t0 = System.nanoTime();
        ResultSetRewindable rows = select(ds, text);
        long t1 = System.nanoTime();
        int n = rows.size();
        boolean[] debit = new boolean[n];
        long[] amount = new long[n], applied = new long[n];
        for (int i = 0; i < n; i++) {
            QuerySolution row = rows.next();
            debit[i] = row.getResource("d").getURI().endsWith("#Debit");
            amount[i] = number(row, "a");
            applied[i] = number(row, "ap");
        }
        long t2 = System.nanoTime();
        long balance = start.balance()[2];
        for (int i = 0; i < n; i++) {
            balance = debit[i] ? balance - amount[i] : Math.min(balance + applied[i], base);
        }
        long t3 = System.nanoTime();
        return new Res(balance, n, (t1 - t0) / 1e9, (t2 - t1) / 1e9, (t3 - t2) / 1e9, false);
    }

    /** Sound when each contract's credits of any kind in the range total no more than its outstanding draw at the range's start, and the balance is within the ceiling. See check.py. */
    static boolean shortcutSound(long balance, long base, Map<String, Long> credits, Map<String, Long> outstanding) {
        return balance <= base && credits.entrySet().stream().allMatch(e -> e.getValue() <= outstanding.getOrDefault(e.getKey(), 0L));
    }

    static Res readShortcut(Dataset ds, Acct a, int point, boolean checkpointed, String form) {
        return Txn.calculateRead(ds, () -> {
            long base = stated(ds, a);
            Start start = startOf(ds, a, point, checkpointed, base);
            long[] total = aggregate(ds, a, point, start.first(), true, form);
            long balance = start.balance()[2] + total[0];
            Map<String, Long> credits = new HashMap<>();
            ResultSetRewindable grouped = select(ds, PREFIX + "SELECT ?c (SUM(?a) AS ?cr) WHERE { " + scan(a, point, false, form, start.first(), "?p l:account ?c . ")
                    + " FILTER(?d = l:Credit) } GROUP BY ?c");
            while (grouped.hasNext()) {
                QuerySolution row = grouped.next();
                credits.put(row.getResource("c").getURI(), number(row, "cr"));
            }
            Map<String, Long> outstanding = new HashMap<>();
            int k = point / every - 1;
            if (checkpointed && k >= 0) {
                ResultSetRewindable stepped = select(ds, PREFIX + "SELECT ?c ?st WHERE { GRAPH <urn:graph:checkpoint:" + k + "> { ?x l:account ?c ; l:stepBalance ?st } }");
                while (stepped.hasNext()) {
                    QuerySolution row = stepped.next();
                    String iri = row.getResource("c").getURI();
                    outstanding.put(iri, ACCTS.get(iri).stated() - number(row, "st"));
                }
            }
            if (shortcutSound(balance, base, credits, outstanding)) {
                return new Res(balance, total[1], 0, 0, 0, false);
            }
            Res step = readIn(ds, "stepwise", a, point, checkpointed, form);
            return new Res(step.balance(), total[1] + step.rows(), step.query(), step.transfer(), step.loop(), true);
        });
    }

    // ---- the run ----

    static String key(String prefix, String name, String level) {
        return prefix + name + "/" + level;
    }

    static JsonObject obj(JsonValue v) {
        return v.getAsObject();
    }

    static String text(JsonObject o, String name) {
        return o.get(name).getAsString().value();
    }

    static long num(JsonObject o, String name) {
        return o.get(name).getAsNumber().value().longValue();
    }

    static boolean flag(JsonObject o, String name) {
        return o.get(name).getAsBoolean().value();
    }

    record Run(String engine, String form, Map<String, Total> totals, long stored, double loadSeconds) {}

    static Run runReads(Dataset ds, String engine, String form, JsonObject corpus, long stored, double load) {
        Map<String, Total> totals = new LinkedHashMap<>();
        String where = engine + " " + num(corpus, "events") + " share " + corpus.get("credit_share").getAsNumber().value();
        for (JsonValue v : corpus.get("reads").getAsArray()) {
            JsonObject r = obj(v);
            boolean cp = flag(r, "checkpointed");
            String fold = text(r, "fold"), account = text(r, "account");
            int point = (int) num(r, "point");
            long start = System.nanoTime();
            Res res = read(ds, fold, ACCTS.get(account), point, cp, form);
            double elapsed = (System.nanoTime() - start) / 1e9;
            String label = where + " " + (cp ? "checkpointed" : "full") + " " + fold + ": " + account + " as of " + point;
            if (res.balance() != num(r, "balance")) {
                throw new WrongResult(label + " reads " + res.balance() + ", the model gives " + num(r, "balance"));
            }
            if (res.rows() != num(r, "rows")) {
                throw new WrongResult(label + " counts " + res.rows() + " postings, the model gives " + num(r, "rows"));
            }
            totals.computeIfAbsent(key(cp ? "cp:" : "", fold, LEVELS[(int) num(r, "level")]), x -> new Total()).add(res, elapsed);
        }
        for (JsonValue v : corpus.get("shortcut").getAsArray()) {
            JsonObject r = obj(v);
            boolean cp = flag(r, "checkpointed");
            String account = text(r, "account");
            int point = (int) num(r, "point");
            long start = System.nanoTime();
            Res res = readShortcut(ds, ACCTS.get(account), point, cp, form);
            double elapsed = (System.nanoTime() - start) / 1e9;
            if (res.balance() != num(r, "balance")) {
                throw new WrongResult(where + " " + (cp ? "checkpointed" : "full") + " shortcut: " + account + " as of " + point + " reads " + res.balance()
                        + ", the model gives " + num(r, "balance"));
            }
            totals.computeIfAbsent(key("shortcut:", cp ? "checkpointed" : "full", LEVELS[(int) num(r, "level")]), x -> new Total()).add(res, elapsed);
        }
        return new Run(engine, form, totals, stored, load);
    }

    static long countQuads(Dataset ds) {
        return Txn.calculateRead(ds, () -> number(select(ds, "SELECT (COUNT(*) AS ?n) WHERE { { ?s ?p ?o } UNION { GRAPH ?g { ?s ?p ?o } } }").next(), "n"));
    }

    static void deleteTree(Path path) throws IOException {
        try (Stream<Path> walk = Files.walk(path)) {
            for (Path entry : (Iterable<Path>) walk.sorted(java.util.Comparator.reverseOrder())::iterator) {
                Files.deleteIfExists(entry);
            }
        }
    }

    /** Loads the corpus into the engine, runs the reads in each form and checks them, and removes the store. */
    static List<Run> runEngine(String engine, Path directory, JsonObject corpus, List<String> forms) throws IOException {
        Path file = directory.resolve(text(corpus, "file"));
        Path location = engine.equals("tdb2") ? Files.createTempDirectory("ledger-credit-kinds-tdb2-") : null;
        Dataset ds = location == null ? DatasetFactory.createTxnMem() : TDB2Factory.connectDataset(location.toString());
        try {
            long start = System.nanoTime();
            Txn.executeWrite(ds, () -> RDFDataMgr.read(ds, file.toString(), Lang.NQUADS));
            double load = (System.nanoTime() - start) / 1e9;
            long stored = countQuads(ds);
            if (stored != num(corpus, "stored")) {
                throw new WrongResult(engine + " " + num(corpus, "events") + ": stored " + stored + " triples, expected " + num(corpus, "stored"));
            }
            List<Run> runs = new ArrayList<>();
            for (String form : forms) {
                runs.add(runReads(ds, engine, form, corpus, stored, load));
            }
            return runs;
        } finally {
            ds.close();
            if (location != null) {
                deleteTree(location);
            }
        }
    }

    static String jenaVersion() throws IOException {
        try (InputStream in = ARQ.class.getResourceAsStream("/META-INF/maven/org.apache.jena/jena-arq/pom.properties")) {
            Properties p = new Properties();
            p.load(in);
            return p.getProperty("version");
        }
    }

    static String entry(Total t) {
        double n = t.reads;
        return String.format("{\"reads\": %d, \"mean_ms\": %.4f, \"mean_rows\": %.2f, \"fetch_ms\": %.4f, \"query_ms\": %.4f, \"transfer_ms\": %.4f, \"loop_ms\": %.4f, \"fallbacks\": %d}",
                t.reads, 1000 * t.seconds / n, t.rows / n, 1000 * (t.query + t.transfer) / n, 1000 * t.query / n, 1000 * t.transfer / n, 1000 * t.loop / n, t.fallbacks);
    }

    static void writeReport(Path report, String jena, List<JsonObject> corpora, List<Run> runs) throws IOException {
        StringBuilder out = new StringBuilder();
        out.append("{\"environment\": {\"date\": \"").append(LocalDate.now()).append("\", \"java\": \"").append(System.getProperty("java.version")).append("\", \"machine\": \"")
                .append(System.getProperty("os.name")).append(' ').append(System.getProperty("os.arch")).append("\", \"jena\": \"").append(jena)
                .append("\", \"heap\": \"").append(Runtime.getRuntime().maxMemory() >> 20).append(" MiB\"}, \"measurements\": [\n");
        for (int i = 0; i < runs.size(); i++) {
            Run run = runs.get(i);
            JsonObject corpus = corpora.get(i);
            out.append(i == 0 ? "" : ",\n").append("{\"backend\": \"jena-").append(run.engine().equals("tdb2") ? "tdb2" : "memory").append(" (java)\", \"events\": ").append(num(corpus, "events"))
                    .append(", \"credit_share\": ").append(corpus.get("credit_share").getAsNumber().value()).append(", \"stored_triples\": ").append(run.stored())
                    .append(", \"kind_join\": \"").append(run.form()).append("\", \"write_seconds\": ").append(String.format("%.4f", run.loadSeconds())).append(", \"reads\": {");
            boolean first = true;
            for (Map.Entry<String, Total> e : run.totals().entrySet()) {
                out.append(first ? "" : ", ").append('"').append(e.getKey()).append("\": ").append(entry(e.getValue()));
                first = false;
            }
            out.append("}}");
        }
        out.append("\n]}\n");
        Files.writeString(report, out.toString());
    }

    public static void main(String[] args) throws IOException {
        Path directory = Path.of(System.getProperty("kinds.dir", "target/corpus"));
        Path report = Path.of(System.getProperty("kinds.report", "report.json"));
        List<String> forms = List.of(System.getProperty("kinds.forms", "optional,union").split(","));
        JsonObject expected = JSON.read(directory.resolve("expected.json").toString()).getAsObject();
        every = (int) num(expected, "every");
        for (JsonValue v : expected.get("tree").getAsArray()) {
            JsonObject t = obj(v);
            List<String> prefixes = new ArrayList<>(), contracts = new ArrayList<>();
            t.get("graphPrefixes").getAsArray().forEach(p -> prefixes.add(p.getAsString().value()));
            t.get("contracts").getAsArray().forEach(c -> contracts.add(c.getAsString().value()));
            ACCTS.put(text(t, "iri"), new Acct(text(t, "iri"), (int) num(t, "level"), num(t, "stated"), prefixes, contracts));
        }
        String jena = jenaVersion();
        System.out.println("Jena " + jena + ", Java " + Runtime.version().feature() + ", heap cap " + (Runtime.getRuntime().maxMemory() >> 20) + " MiB");
        List<JsonObject> all = new ArrayList<>();
        expected.get("corpora").getAsArray().forEach(c -> all.add(obj(c)));
        List<JsonObject> reported = new ArrayList<>();
        List<Run> runs = new ArrayList<>();
        try {
            runEngine("memory", directory, all.get(0), forms); // a warm-up that is not reported, so the smallest size does not pay for loading classes and the JIT
            for (JsonObject corpus : all) {
                for (String engine : List.of("memory", "tdb2")) {
                    for (Run run : runEngine(engine, directory, corpus, forms)) {
                        runs.add(run);
                        reported.add(corpus);
                        Total plain = run.totals().get("plain/root"), step = run.totals().get("stepwise/root"), cp = run.totals().get("cp:stepwise/root");
                        System.out.printf("%-6s %-8s events %6d credits %4.0f%%  plain root %8.2f ms  stepwise root %8.2f ms (query %.2f, transfer %.2f, loop %.2f)  checkpointed stepwise root %8.2f ms%n",
                                run.engine(), run.form(), num(corpus, "events"), 100 * corpus.get("credit_share").getAsNumber().value().doubleValue(),
                                1000 * plain.seconds / plain.reads, 1000 * step.seconds / step.reads, 1000 * step.query / step.reads, 1000 * step.transfer / step.reads,
                                1000 * step.loop / step.reads, 1000 * cp.seconds / cp.reads);
                    }
                }
            }
        } catch (WrongResult error) {
            System.err.println("WRONG RESULT: " + error.getMessage());
            System.exit(1);
        }
        writeReport(report, jena, reported, runs);
        System.out.println("report written to " + report.toAbsolutePath());
    }
}
