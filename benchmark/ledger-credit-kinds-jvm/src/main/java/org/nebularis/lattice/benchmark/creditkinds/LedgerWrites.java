// SPDX-License-Identifier: MPL-2.0
// NB: This module has been produced using GenAI
package org.nebularis.lattice.benchmark.creditkinds;

import static org.nebularis.lattice.benchmark.creditkinds.CreditKinds.L;
import static org.nebularis.lattice.benchmark.creditkinds.CreditKinds.number;
import static org.nebularis.lattice.benchmark.creditkinds.CreditKinds.select;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.BrokenBarrierException;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.atomic.AtomicReference;
import java.util.zip.GZIPOutputStream;

import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.atlas.json.JsonValue;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSetRewindable;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.system.Txn;
import org.apache.jena.tdb2.TDB2Factory;
import org.apache.jena.update.UpdateExecution;

/**
 * What a write costs the ledger's account tree on Jena called from Java, and whether one revision triple closes the race between concurrent writers (LG-17 part three).
 *
 * <p><b>The probe.</b> A counter triple and nothing else, as the Python probe of TSD-73. Threads in one JVM against one dataset read the counter, send a guarded update with a marker of their own, and ask
 * whether the marker exists. A second form increments in the store. It is reported and never asserted.
 *
 * <p><b>The ledger's live writer.</b> The port of {@code writes.py}'s writer: it reads the revision and the sum with cuts of every account on the posting's path from the last checkpoint, settles the
 * posting with the benchmark's arithmetic, and writes the posting, its applied amount, kind and cuts and the new revision in one guarded update, confirmed by asking for its own posting. The corpus, the
 * request lists and the plan of the runs are written by {@code writes.py --emit-jvm}. After each run the whole dataset is exported as gzipped N-Quads, and Python replays it ({@code writes.py --audit-jvm}),
 * so the audit is the Python benchmark's own and none is written here.
 *
 * <p><b>A wrong result fails this run with a non-zero exit. Time never does (ADR-A124).</b> What the store does with concurrent writers is reported and not asserted here, and Python asserts it.
 */
public final class LedgerWrites {

    static final String LEDGER = "urn:ledger:owner";
    static final String REVISION = L + "revision";
    static final String RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
    static final int MAX_ATTEMPTS = 20_000;
    static final String[] CLASSES = {"debit", "credit", "credit with a cut"};
    static final String[] PARTS = {"reads", "settle", "update", "confirm"};

    // the tree, by position as Python lists it
    static int n;
    static CreditKinds.Acct[] acct;
    static int[] parent;
    static long[] ceiling, stated;
    static List<String>[] accepts;
    static String[] own;

    record Req(int at, boolean debit, long amount, String kind) {}

    static final class Plan {
        Req r;
        String tag;
        long revision;
        boolean refused;
        long applied;
        List<long[]> cuts = new ArrayList<>();
        double reads, settle, update, confirm;
        int queries, path;
        String graph;

        int triples() {
            return 8 + (r.debit() ? 0 : 1 + (r.kind() != null ? 1 : 0) + 3 * cuts.size());
        }
    }

    static List<Integer> chain(int i) {
        List<Integer> out = new ArrayList<>();
        for (int x = i; x >= 0; x = parent[x]) {
            out.add(x);
        }
        return out;
    }

    static boolean acceptsKind(int i, String kind) {
        return accepts[i].isEmpty() || accepts[i].contains(kind);
    }

    /** The writer's step for a credit posted at `at`, which moves `step`. Returns the applied amount and fills `cuts`. */
    static long settleCredit(long[] step, int at, long amount, String kind, List<long[]> cuts) {
        long applied = Math.min(amount, ceiling[at] - step[at]);
        for (int i : chain(at)) {
            if (acceptsKind(i, kind)) {
                long take = Math.min(applied, ceiling[i] - step[i]);
                step[i] += take;
                if (take < applied) {
                    cuts.add(new long[] {i, applied - take});
                }
            }
        }
        return applied;
    }

    /** The live writer of one thread. `k` is the last checkpoint, whose balances are read once. */
    static final class Live {
        final Dataset ds;
        final boolean guarded;
        final int k;
        final Map<Integer, Long> cp = new HashMap<>();
        int queries;

        Live(Dataset ds, int checkpoints, boolean guarded) {
            this.ds = ds;
            this.k = checkpoints - 1;
            this.guarded = guarded;
        }

        ResultSetRewindable q(String text) {
            queries++;
            return select(ds, text);
        }

        long revision() {
            return number(q("SELECT (MAX(?r) AS ?m) WHERE { <" + LEDGER + "> <" + REVISION + "> ?r }").next(), "m");
        }

        long base(int i) {
            if (k < 0) {
                return stated[i];
            }
            Long known = cp.get(i);
            if (known == null) {
                known = number(q(CreditKinds.PREFIX + "SELECT ?st WHERE { GRAPH <urn:graph:checkpoint:" + k + "> { ?c l:account <" + acct[i].iri() + "> ; l:stepBalance ?st } }").next(), "st");
                cp.put(i, known);
            }
            return known;
        }

        /** The sum with cuts of account i as of the point, from the last checkpoint. */
        long balance(int i, long point) {
            int first = k + 1;
            long base = base(i);
            CreditKinds.Acct a = acct[i];
            if (a.level() > 0) {
                QuerySolution row = q(CreditKinds.withCutsPostingsText(a, (int) point, first)).next();
                QuerySolution cut = q(CreditKinds.cutsText(a, (int) point, first)).next();
                return base + number(row, "sum") - number(cut, "cut");
            }
            StringBuilder graphs = new StringBuilder();
            for (long g = first; g <= (point - 1) / CreditKinds.every; g++) {
                graphs.append('<').append(own[i]).append(g).append("> ");
            }
            String head = "?p l:account <" + a.iri() + "> ; l:position ?pos ; l:direction";
            QuerySolution row = q(CreditKinds.PREFIX + "SELECT (SUM(?signed) AS ?sum) WHERE { VALUES ?g { " + graphs + "} GRAPH ?g { { " + head + " l:Debit ; l:amount ?v . BIND(l:Debit AS ?d) FILTER(?pos <= "
                    + point + ") } UNION { " + head + " l:Credit ; l:applied ?v . BIND(l:Credit AS ?d) FILTER(?pos <= " + point + ") } " + CreditKinds.SIGNED_V + " } }").next();
            return base + number(row, "sum");
        }

        /** Reads the revision and the balance of every account on the path in one read transaction, then settles. A debit larger than the balance of any account on its path is refused. */
        Plan prepare(Req r, String tag) {
            Plan p = new Plan();
            p.r = r;
            p.tag = tag;
            int q0 = queries;
            long t0 = System.nanoTime();
            List<Integer> path = chain(r.at());
            long[] step = new long[n];
            Txn.executeRead(ds, () -> {
                p.revision = revision();
                for (int i : path) {
                    step[i] = balance(i, p.revision);
                }
            });
            long t1 = System.nanoTime();
            p.path = path.size();
            if (r.debit()) {
                p.refused = path.stream().anyMatch(i -> step[i] < r.amount());
                if (!p.refused) {
                    path.forEach(i -> step[i] -= r.amount());
                }
            } else {
                p.applied = settleCredit(step, r.at(), r.amount(), r.kind(), p.cuts);
            }
            p.reads = (t1 - t0) / 1e9;
            p.settle = (System.nanoTime() - t1) / 1e9;
            p.queries = queries - q0;
            return p;
        }

        String text(Plan p) {
            Req r = p.r;
            long pos = p.revision + 1;
            p.graph = own[r.at()] + ((pos - 1) / CreditKinds.every);
            String s = "<urn:posting:" + p.tag + ">";
            StringBuilder body = new StringBuilder();
            body.append(s).append(" <").append(RDF_TYPE).append("> <").append(L).append("Posting> . ");
            body.append(s).append(" <").append(L).append("account> <").append(acct[r.at()].iri()).append("> . ");
            body.append(s).append(" <").append(L).append("owner> <urn:owner:1> . ");
            body.append(s).append(" <").append(L).append("key> \"k").append(p.tag).append("\" . ");
            body.append(s).append(" <").append(L).append("position> ").append(pos).append(" . ");
            body.append(s).append(" <").append(L).append("microPosition> 0 . ");
            body.append(s).append(" <").append(L).append("direction> <").append(L).append(r.debit() ? "Debit" : "Credit").append("> . ");
            body.append(s).append(" <").append(L).append("amount> ").append(r.amount()).append(" . ");
            if (!r.debit()) {
                body.append(s).append(" <").append(L).append("applied> ").append(p.applied).append(" . ");
                if (r.kind() != null) {
                    body.append(s).append(" <").append(L).append("kind> <").append(r.kind()).append("> . ");
                }
                for (long[] cut : p.cuts) {
                    String c = "<urn:cut:" + p.tag + ":" + cut[0] + ">";
                    body.append(c).append(" <").append(L).append("cutOf> ").append(s).append(" . ");
                    body.append(c).append(" <").append(L).append("cutAt> <").append(acct[(int) cut[0]].iri()).append("> . ");
                    body.append(c).append(" <").append(L).append("cutValue> ").append(cut[1]).append(" . ");
                }
            }
            String old = "<" + LEDGER + "> <" + REVISION + "> " + p.revision;
            String now = "<" + LEDGER + "> <" + REVISION + "> " + (p.revision + 1);
            String all = now + " . GRAPH <" + p.graph + "> { " + body + "}";
            return guarded ? "DELETE { " + old + " } INSERT { " + all + " } WHERE { " + old + " }" : "DELETE DATA { " + old + " } ; INSERT DATA { " + all + " }";
        }

        /** Writes the plan. A guarded write learns whether it won by asking for its own posting. An unguarded write does not ask, and reports success. */
        boolean commit(Plan p) {
            String text = text(p);
            long t0 = System.nanoTime();
            Txn.executeWrite(ds, () -> UpdateExecution.dataset(ds).update(text).execute());
            long t1 = System.nanoTime();
            boolean won = true;
            if (guarded) {
                queries++;
                won = Txn.calculateRead(ds, () -> select(ds, "SELECT ?x WHERE { GRAPH <" + p.graph + "> { <urn:posting:" + p.tag + "> a <" + L + "Posting> . BIND(1 AS ?x) } } LIMIT 1").hasNext());
                p.confirm = (System.nanoTime() - t1) / 1e9;
            }
            p.update = (t1 - t0) / 1e9;
            return won;
        }
    }

    /** Prepares and commits one request, preparing again after a lost race. Returns the last plan and the attempts. A refused debit is not written. */
    static Plan writeOne(Live live, Req r, String tag, boolean retry, int[] attempts) {
        for (int attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
            Plan p = live.prepare(r, tag + "." + attempt);
            if (p.refused || live.commit(p)) {
                attempts[0] = attempt;
                return p;
            }
            if (!retry) {
                throw new CreditKinds.WrongResult(tag + ": lost a race with no other writer");
            }
        }
        throw new CreditKinds.WrongResult(tag + ": lost " + MAX_ATTEMPTS + " races in a row");
    }

    // ---- stores ----

    record Store(Dataset ds, Path location) {
        void close() throws IOException {
            ds.close();
            if (location != null) {
                CreditKinds.deleteTree(location);
            }
        }
    }

    static Store open(String store) throws IOException {
        if (store.equals("memory")) {
            return new Store(DatasetFactory.createTxnMem(), null);
        }
        Path dir = Files.createTempDirectory("ledger-writes-tdb2-");
        return new Store(TDB2Factory.connectDataset(dir.toString()), dir);
    }

    static void export(Dataset ds, Path file) throws IOException {
        try (OutputStream out = new GZIPOutputStream(Files.newOutputStream(file))) {
            Txn.executeRead(ds, () -> RDFDataMgr.write(out, ds.asDatasetGraph(), Lang.NQUADS));
        }
    }

    static void update(Dataset ds, String text) {
        Txn.executeWrite(ds, () -> UpdateExecution.dataset(ds).update(text).execute());
    }

    // ---- report ----

    static String json(Object o) {
        if (o == null) {
            return "null";
        }
        if (o instanceof Map<?, ?> m) {
            StringBuilder sb = new StringBuilder("{");
            for (Map.Entry<?, ?> e : m.entrySet()) {
                sb.append(sb.length() > 1 ? ", " : "").append('"').append(e.getKey()).append("\": ").append(json(e.getValue()));
            }
            return sb.append('}').toString();
        }
        if (o instanceof List<?> l) {
            StringBuilder sb = new StringBuilder("[");
            for (Object x : l) {
                sb.append(sb.length() > 1 ? ", " : "").append(json(x));
            }
            return sb.append(']').toString();
        }
        if (o instanceof String s) {
            return '"' + s.replace("\\", "\\\\").replace("\"", "\\\"") + '"';
        }
        if (o instanceof Double d) {
            return String.format("%.6f", d);
        }
        return o.toString();
    }

    static Map<String, Object> map(Object... kv) {
        Map<String, Object> m = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            m.put((String) kv[i], kv[i + 1]);
        }
        return m;
    }

    static double mean(List<Double> xs) {
        return xs.stream().mapToDouble(Double::doubleValue).average().orElse(0);
    }

    static double p95(List<Double> xs) {
        double[] a = xs.stream().mapToDouble(Double::doubleValue).sorted().toArray();
        return a[Math.max(0, (int) Math.ceil(0.95 * a.length) - 1)];
    }

    // ---- the probe ----

    static long first(Dataset ds, String text, String var) {
        return Txn.calculateRead(ds, () -> number(select(ds, text).next(), var));
    }

    interface Body {
        void run(int thread) throws Exception;
    }

    /** Runs `body` on `threads` threads released together, and returns the wall time. A failure in a thread is thrown here. */
    static double race(int threads, Body body) throws Exception {
        CyclicBarrier barrier = new CyclicBarrier(threads + 1);
        AtomicReference<Throwable> failure = new AtomicReference<>();
        List<Thread> pool = new ArrayList<>();
        for (int t = 0; t < threads; t++) {
            int id = t;
            Thread th = new Thread(() -> {
                try {
                    barrier.await();
                    body.run(id);
                } catch (BrokenBarrierException | InterruptedException e) {
                    failure.compareAndSet(null, e);
                } catch (Throwable e) {
                    failure.compareAndSet(null, e);
                    barrier.reset();
                }
            });
            pool.add(th);
            th.start();
        }
        barrier.await();
        long t0 = System.nanoTime();
        for (Thread th : pool) {
            th.join();
        }
        double wall = (System.nanoTime() - t0) / 1e9;
        if (failure.get() != null) {
            throw new RuntimeException(failure.get());
        }
        return wall;
    }

    static Map<String, Object> probeGuarded(String store, int threads, int run, int target) throws Exception {
        Store s = open(store);
        try {
            Dataset ds = s.ds();
            update(ds, "INSERT DATA { <urn:c> <urn:v> 0 }");
            long[] lost = new long[threads];
            double wall = race(threads, t -> {
                int i = 0;
                while (true) {
                    long v = first(ds, "SELECT ?n WHERE { <urn:c> <urn:v> ?n }", "n");
                    if (v >= target) {
                        break;
                    }
                    String marker = "<urn:w:" + t + ":" + (i++) + ">";
                    update(ds, "DELETE { <urn:c> <urn:v> " + v + " } INSERT { <urn:c> <urn:v> " + (v + 1) + " . " + marker + " <urn:at> " + (v + 1) + " } WHERE { <urn:c> <urn:v> " + v + " }");
                    if (!Txn.calculateRead(ds, () -> select(ds, "SELECT ?x WHERE { " + marker + " <urn:at> ?x }").hasNext())) {
                        lost[t]++;
                    }
                }
            });
            return map("store", store, "threads", threads, "run", run, "target", target, "markers", first(ds, "SELECT (COUNT(?m) AS ?c) WHERE { ?m <urn:at> ?x }", "c"),
                    "multi_marker_revisions", first(ds, "SELECT (COUNT(*) AS ?c) WHERE { SELECT ?x WHERE { ?m <urn:at> ?x } GROUP BY ?x HAVING (COUNT(?m) > 1) }", "c"),
                    "lost_races", Arrays.stream(lost).sum(), "counter_triples", first(ds, "SELECT (COUNT(*) AS ?c) WHERE { <urn:c> <urn:v> ?n }", "c"),
                    "counter", first(ds, "SELECT (MAX(?n) AS ?m) WHERE { <urn:c> <urn:v> ?n }", "m"), "wall_s", wall);
        } finally {
            s.close();
        }
    }

    static Map<String, Object> probeIncrement(String store, int threads, int run, int each) throws Exception {
        Store s = open(store);
        try {
            Dataset ds = s.ds();
            update(ds, "INSERT DATA { <urn:k> <urn:v> 0 }");
            double wall = race(threads, t -> {
                for (int i = 0; i < each; i++) {
                    update(ds, "DELETE { <urn:k> <urn:v> ?n } INSERT { <urn:k> <urn:v> ?m } WHERE { <urn:k> <urn:v> ?n . BIND(?n + 1 AS ?m) }");
                }
            });
            return map("store", store, "threads", threads, "run", run, "expected", (long) threads * each, "final", first(ds, "SELECT (MAX(?n) AS ?m) WHERE { <urn:k> <urn:v> ?n }", "m"),
                    "counter_triples", first(ds, "SELECT (COUNT(*) AS ?c) WHERE { <urn:k> <urn:v> ?n }", "c"), "wall_s", wall);
        } finally {
            s.close();
        }
    }

    // ---- the ledger ----

    static Req req(JsonValue v) {
        var a = v.getAsArray();
        return new Req((int) a.get(0).getAsNumber().value().longValue(), a.get(1).getAsNumber().value().longValue() == 1, a.get(2).getAsNumber().value().longValue(),
                a.get(3).isNull() ? null : a.get(3).getAsString().value());
    }

    static List<Req> reqs(JsonValue v) {
        List<Req> out = new ArrayList<>();
        v.getAsArray().forEach(x -> out.add(req(x)));
        return out;
    }

    static JsonObject loadPreload(Dataset ds, Path dir, JsonObject preload) {
        Path file = dir.resolve(CreditKinds.text(preload, "file"));
        Txn.executeWrite(ds, () -> RDFDataMgr.read(ds, file.toString(), Lang.NQUADS));
        long stored = CreditKinds.countQuads(ds);
        if (stored != CreditKinds.num(preload, "stored")) {
            throw new CreditKinds.WrongResult("preload " + file.getFileName() + ": stored " + stored + " triples, expected " + CreditKinds.num(preload, "stored"));
        }
        return preload;
    }

    static Map<String, Object> single(String store, JsonObject preload, List<Req> requests, boolean guarded, Path dir, String tag) throws Exception {
        Store s = open(store);
        try {
            loadPreload(s.ds(), dir, preload);
            Live live = new Live(s.ds(), (int) CreditKinds.num(preload, "checkpoints"), guarded);
            long before = CreditKinds.countQuads(s.ds()), added = 0;
            Map<String, Map<String, List<Double>>> seconds = new LinkedHashMap<>();
            Map<String, List<double[]>> meta = new LinkedHashMap<>();
            for (String c : CLASSES) {
                seconds.put(c, new LinkedHashMap<>());
                emptyParts(seconds.get(c));
                meta.put(c, new ArrayList<>());
            }
            int refused = 0, w = 0;
            for (Req r : requests) {
                Plan p = writeOne(live, r, "W" + (w++), false, new int[1]);
                if (p.refused) {
                    refused++;
                    continue;
                }
                String c = r.debit() ? CLASSES[0] : p.cuts.isEmpty() ? CLASSES[1] : CLASSES[2];
                double[] v = {p.reads, p.settle, p.update, p.confirm};
                for (int i = 0; i < PARTS.length; i++) {
                    seconds.get(c).get(PARTS[i]).add(v[i]);
                }
                meta.get(c).add(new double[] {p.path, p.queries, p.triples()});
                added += p.triples();
            }
            long grew = CreditKinds.countQuads(s.ds()) - before;
            if (grew != added) {
                throw new CreditKinds.WrongResult(store + " " + CreditKinds.num(preload, "postings") + ": the store grew by " + grew + " triples, the writes add " + added);
            }
            Map<String, Object> classes = new LinkedHashMap<>();
            for (String c : CLASSES) {
                List<Double> reads = seconds.get(c).get("reads");
                if (reads.isEmpty()) {
                    continue;
                }
                Map<String, Object> m = map("writes", reads.size(), "path_reads", meta.get(c).stream().mapToDouble(x -> x[0]).average().orElse(0),
                        "queries", meta.get(c).stream().mapToDouble(x -> x[1]).average().orElse(0), "triples", meta.get(c).stream().mapToDouble(x -> x[2]).average().orElse(0));
                List<Double> total = new ArrayList<>();
                for (int i = 0; i < reads.size(); i++) {
                    double t = 0;
                    for (String part : PARTS) {
                        t += seconds.get(c).get(part).get(i);
                    }
                    total.add(t);
                }
                for (String part : PARTS) {
                    m.put(part, map("mean_ms", 1000 * mean(seconds.get(c).get(part)), "p95_ms", 1000 * p95(seconds.get(c).get(part))));
                }
                m.put("total", map("mean_ms", 1000 * mean(total), "p95_ms", 1000 * p95(total)));
                classes.put(c, m);
            }
            String exported = tag + ".nq.gz";
            export(s.ds(), dir.resolve(exported));
            return map("store", store, "postings", CreditKinds.num(preload, "postings"), "guarded", guarded, "writes", requests.size(), "refused", refused, "commits", requests.size() - refused,
                    "base", CreditKinds.num(preload, "base"), "classes", classes, "export", exported);
        } finally {
            s.close();
        }
    }

    static void emptyParts(Map<String, List<Double>> m) {
        for (String p : PARTS) {
            m.put(p, new ArrayList<>());
        }
    }

    static Map<String, Object> stress(String store, JsonObject preload, List<List<Req>> lists, boolean guarded, int run, Path dir, String tag) throws Exception {
        Store s = open(store);
        try {
            loadPreload(s.ds(), dir, preload);
            int threads = lists.size();
            long[] commits = new long[threads], refused = new long[threads], lost = new long[threads], longest = new long[threads];
            double wall = race(threads, t -> {
                Live live = new Live(s.ds(), (int) CreditKinds.num(preload, "checkpoints"), guarded);
                int w = 0;
                for (Req r : lists.get(t)) {
                    int[] attempts = new int[1];
                    Plan p = writeOne(live, r, "L" + t + "." + (w++), true, attempts);
                    lost[t] += attempts[0] - 1;
                    longest[t] = Math.max(longest[t], attempts[0] - 1);
                    if (p.refused) {
                        refused[t]++;
                    } else {
                        commits[t]++;
                    }
                }
            });
            long c = Arrays.stream(commits).sum(), rf = Arrays.stream(refused).sum(), ls = Arrays.stream(lost).sum();
            String exported = tag + ".nq.gz";
            export(s.ds(), dir.resolve(exported));
            return map("store", store, "threads", threads, "guarded", guarded, "run", run, "preload", CreditKinds.num(preload, "postings"), "requests", lists.stream().mapToInt(List::size).sum(), "commits", c,
                    "refused", rf, "lost_races", ls, "retries_mean", (double) ls / Math.max(c + rf, 1), "retries_max", Arrays.stream(longest).max().orElse(0), "wall_s", wall, "commits_per_s", c / wall,
                    "base", CreditKinds.num(preload, "base"), "export", exported);
        } finally {
            s.close();
        }
    }

    public static void main(String[] args) throws Exception {
        Path dir = Path.of(System.getProperty("writes.dir", "target/writes"));
        Path report = Path.of(System.getProperty("writes.report", "target/writes/writes-java.json"));
        JsonObject input = JSON.read(dir.resolve("writes-input.json").toString()).getAsObject();
        CreditKinds.every = (int) CreditKinds.num(input, "every");
        CreditKinds.upper = true;
        var tree = input.get("tree").getAsArray();
        n = tree.size();
        acct = new CreditKinds.Acct[n];
        parent = new int[n];
        ceiling = new long[n];
        stated = new long[n];
        @SuppressWarnings("unchecked")
        List<String>[] acc = new List[n];
        accepts = acc;
        own = new String[n];
        for (int i = 0; i < n; i++) {
            JsonObject t = tree.get(i).getAsObject();
            List<String> prefixes = new ArrayList<>(), upper = new ArrayList<>(), kinds = new ArrayList<>();
            t.get("graphPrefixes").getAsArray().forEach(p -> prefixes.add(p.getAsString().value()));
            t.get("upperPrefixes").getAsArray().forEach(p -> upper.add(p.getAsString().value()));
            t.get("accepts").getAsArray().forEach(p -> kinds.add(p.getAsString().value()));
            stated[i] = CreditKinds.num(t, "stated");
            acct[i] = new CreditKinds.Acct(CreditKinds.text(t, "iri"), (int) CreditKinds.num(t, "level"), stated[i], prefixes, upper, List.of());
            parent[i] = (int) CreditKinds.num(t, "parent");
            ceiling[i] = CreditKinds.num(t, "ceiling");
            accepts[i] = kinds;
            own[i] = CreditKinds.text(t, "ownPrefix");
        }
        JsonObject plan = input.get("plan").getAsObject();
        JsonObject preloads = input.get("preloads").getAsObject();
        String jena = CreditKinds.jenaVersion();
        System.out.println("Jena " + jena + ", Java " + Runtime.version().feature() + ", heap cap " + (Runtime.getRuntime().maxMemory() >> 20) + " MiB, " + Runtime.getRuntime().availableProcessors() + " CPUs");
        List<Object> guarded = new ArrayList<>(), increment = new ArrayList<>(), singles = new ArrayList<>(), stresses = new ArrayList<>();
        try {
            // a warm-up that is not reported, so the first writer does not pay for loading classes and the JIT
            JsonObject first = preloads.get(String.valueOf(plan.get("sizes").getAsArray().get(0).getAsNumber().value().longValue())).getAsObject();
            single("memory", first, reqs(input.get("single")).subList(0, Math.min(30, input.get("single").getAsArray().size())), true, dir, "warm-up");
            Files.deleteIfExists(dir.resolve("warm-up.nq.gz"));
            // each store has its own sizes, since a TDB2 commit costs tens of milliseconds and the same counts would take hours
            for (String store : plan.get("stores").getAsObject().keys()) {
                JsonObject cut = plan.get("stores").getAsObject().get(store).getAsObject();
                JsonObject probe = cut.get("probe").getAsObject();
                int target = (int) CreditKinds.num(probe, "target"), each = (int) CreditKinds.num(probe, "increments"), runs = (int) CreditKinds.num(probe, "runs");
                for (JsonValue tv : plan.get("threads").getAsArray()) {
                    int threads = (int) tv.getAsNumber().value().longValue();
                    for (int run = 1; run <= (threads == 1 ? 1 : runs); run++) {
                        Map<String, Object> g = probeGuarded(store, threads, run, target), inc = probeIncrement(store, threads, run, each);
                        guarded.add(g);
                        increment.add(inc);
                        System.out.println("probe " + store + " " + threads + " threads run " + run + ": markers " + g.get("markers") + " of " + target + ", revisions with more than one marker "
                                + g.get("multi_marker_revisions") + ", lost " + g.get("lost_races") + "; increment ended at " + inc.get("final") + " of " + inc.get("expected") + " as " + inc.get("counter_triples") + " triples");
                    }
                }
                JsonObject sp = cut.get("single").getAsObject();
                List<Req> one = reqs(input.get("single"));
                one = one.subList(0, Math.min(one.size(), (int) CreditKinds.num(sp, "writes")));
                for (JsonValue size : plan.get("sizes").getAsArray()) {
                    JsonObject preload = preloads.get(String.valueOf(size.getAsNumber().value().longValue())).getAsObject();
                    for (boolean g : new boolean[] {true, false}) {
                        String tag = "single-" + store + "-" + CreditKinds.num(preload, "postings") + (g ? "-guarded" : "-unguarded");
                        Map<String, Object> r = single(store, preload, one, g, dir, tag);
                        singles.add(r);
                        System.out.println("single " + tag + " done, " + r.get("commits") + " commits, " + r.get("refused") + " refused");
                    }
                }
                JsonObject st = cut.get("stress").getAsObject();
                JsonObject lists = input.get("stress").getAsObject();
                JsonObject preload = preloads.get(String.valueOf(CreditKinds.num(plan, "stressPreload"))).getAsObject();
                for (JsonValue tv : plan.get("threads").getAsArray()) {
                    int threads = (int) tv.getAsNumber().value().longValue();
                    List<List<Req>> asked = new ArrayList<>();
                    lists.get(String.valueOf(threads)).getAsArray().forEach(l -> {
                        List<Req> all = reqs(l);
                        asked.add(all.subList(0, Math.min(all.size(), (int) CreditKinds.num(st, "total") / threads)));
                    });
                    for (boolean g : new boolean[] {true, false}) {
                        int cell = g ? (int) CreditKinds.num(st.get("guardedRuns").getAsObject(), String.valueOf(threads)) : 1;
                        for (int run = 1; run <= cell; run++) {
                            String tag = "stress-" + store + "-" + threads + (g ? "-guarded-" : "-unguarded-") + run;
                            Map<String, Object> r = stress(store, preload, asked, g, run, dir, tag);
                            stresses.add(r);
                            System.out.println("stress " + tag + ": " + r.get("commits") + " commits, " + r.get("refused") + " refused, " + r.get("lost_races") + " lost, wall "
                                    + String.format("%.2f", (Double) r.get("wall_s")) + " s");
                        }
                    }
                }
            }
        } catch (CreditKinds.WrongResult error) {
            System.err.println("WRONG RESULT: " + error.getMessage());
            System.exit(1);
        }
        Map<String, Object> out = map("environment", map("date", java.time.LocalDate.now().toString(), "java", System.getProperty("java.version"), "machine", System.getProperty("os.name") + " " + System.getProperty("os.arch"),
                "jena", jena, "heap", (Runtime.getRuntime().maxMemory() >> 20) + " MiB", "cpus", Runtime.getRuntime().availableProcessors()), "probe", map("guarded", guarded, "increment", increment), "single", singles, "stress", stresses);
        Files.writeString(report, json(out));
        System.out.println("report written to " + report.toAbsolutePath());
    }
}
