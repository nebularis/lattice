// SPDX-License-Identifier: MPL-2.0
// NB: This module has been produced using GenAI

package org.nebularis.lattice.benchmark.isolation;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

import org.apache.jena.dboe.base.file.Location;
import org.apache.jena.fuseki.main.FusekiServer;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.TxnType;
import org.apache.jena.sparql.core.DatasetGraph;
import org.apache.jena.sparql.core.Quad;
import org.apache.jena.system.Txn;
import org.apache.jena.tdb2.TDB2Factory;
import org.apache.jena.tdb2.sys.StoreConnection;

/**
 * The Jena arm of {@code benchmark/store-isolation-probes}. It runs each probe on Fuseki over a TDB2 dataset on disk, driven by
 * concurrent HTTP clients, and the two probes that need a transaction held open on TDB2 called in process, and writes what it
 * observed to the JSON file {@code isolation.out} names. It judges nothing. {@code check.py} holds what each store is expected
 * to do, compares, and writes the report.
 *
 * <p>Each repetition writes under IRIs of its own, so no repetition reads another's state. Two clients that must act at the
 * same moment wait on a barrier first. A step that must follow another is made by one thread after the other has returned.
 */
public final class IsolationProbes {

    static final int REPS = Integer.getInteger("isolation.reps", 20);
    static final int STRESS_TARGET = Integer.getInteger("isolation.stress", 40);
    static final int STRESS_THREADS = 4;
    static final int MOVES = 10;
    static final int BULK = 20_000;
    static final List<Tally> ROWS = new ArrayList<>();

    /** What one probe in one form and mode observed over its repetitions. */
    static final class Tally {
        final String probe, store, form, mode;
        int reps, anomalies;
        final Map<String, Integer> outcomes = new LinkedHashMap<>();
        final Map<String, Long> counts = new LinkedHashMap<>();

        Tally(String probe, String store, String form, String mode) {
            this.probe = probe;
            this.store = store;
            this.form = form;
            this.mode = mode;
            ROWS.add(this);
        }

        void add(String outcome, boolean anomaly) {
            reps++;
            anomalies += anomaly ? 1 : 0;
            outcomes.merge(outcome, 1, Integer::sum);
        }

        void count(String name, long value) {
            counts.merge(name, value, Long::sum);
        }
    }

    // ---- Fuseki over HTTP ---------------------------------------------------------------------------------------------

    /** One HTTP client of the Fuseki dataset. Each client has a connection pool of its own, as a separate process would. */
    static final class Client {
        final String base;
        final HttpClient http = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).connectTimeout(Duration.ofSeconds(10)).build();

        Client(String base) {
            this.base = base;
        }

        Client another() {
            return new Client(base);
        }

        /** Sends an update and returns the HTTP status. */
        int update(String text) throws IOException, InterruptedException {
            HttpRequest request = HttpRequest.newBuilder(URI.create(base + "/update")).header("Content-Type", "application/sparql-update")
                .POST(HttpRequest.BodyPublishers.ofString(text, StandardCharsets.UTF_8)).build();
            return http.send(request, HttpResponse.BodyHandlers.discarding()).statusCode();
        }

        void mustUpdate(String text) throws IOException, InterruptedException {
            int status = update(text);
            if (status >= 300) {
                throw new IllegalStateException("HTTP " + status + " for " + text.substring(0, Math.min(120, text.length())));
            }
        }

        /** The rows of a SELECT, read as CSV, without the header. A cell holds an IRI or a literal's lexical form. */
        List<String[]> select(String query) throws IOException, InterruptedException {
            HttpRequest request = HttpRequest.newBuilder(URI.create(base + "/query")).header("Content-Type", "application/sparql-query")
                .header("Accept", "text/csv").POST(HttpRequest.BodyPublishers.ofString(query, StandardCharsets.UTF_8)).build();
            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            if (response.statusCode() >= 300) {
                throw new IllegalStateException("HTTP " + response.statusCode() + " for " + query);
            }
            List<String[]> rows = new ArrayList<>();
            String[] lines = response.body().split("\r?\n");
            for (int i = 1; i < lines.length; i++) {
                if (!lines[i].isEmpty()) {
                    rows.add(lines[i].split(",", -1));
                }
            }
            return rows;
        }

        /** The first cell of the first row as a number, or -1 where there is no row or the cell is empty. */
        long number(String query) throws IOException, InterruptedException {
            List<String[]> rows = select(query);
            if (rows.isEmpty() || rows.get(0)[0].isEmpty()) {
                return -1;
            }
            return Long.parseLong(rows.get(0)[0].trim());
        }
    }

    interface Step {
        void run(int index) throws Exception;
    }

    /** Runs the step on two threads, index 0 and 1, and waits for both. An exception in either fails the run. */
    static void both(Step step) throws Exception {
        runAll(2, step);
    }

    static void runAll(int n, Step step) throws Exception {
        Thread[] threads = new Thread[n];
        Exception[] failed = new Exception[n];
        for (int i = 0; i < n; i++) {
            int index = i;
            threads[i] = new Thread(() -> {
                try {
                    step.run(index);
                } catch (Exception e) {
                    failed[index] = e;
                }
            });
            threads[i].start();
        }
        for (Thread t : threads) {
            t.join();
        }
        for (Exception e : failed) {
            if (e != null) {
                throw e;
            }
        }
    }

    static String iri(String prefix, String local) {
        return "<" + prefix + local + ">";
    }

    /** ISO-01. Two clients read the version, then send at once an update that moves it from what each read. */
    static void casTwoWriters(Client store, String form) throws Exception {
        Tally t = new Tally("ISO-01", "fuseki", form, "two clients");
        for (int rep = 0; rep < REPS; rep++) {
            String p = "urn:iso:01:" + form.replace(' ', '-') + ":" + rep + ":";
            String c = iri(p, "c"), v = iri(p, "v"), at = iri(p, "at");
            store.mustUpdate("INSERT DATA { " + c + " " + v + " 0 }");
            Client[] clients = {store.another(), store.another()};
            CyclicBarrier barrier = new CyclicBarrier(2);
            both(i -> {
                long n = clients[i].number("SELECT ?n WHERE { " + c + " " + v + " ?n }");
                barrier.await();
                String marker = iri(p, "m" + i);
                String insert = " INSERT { " + c + " " + v + " " + (n + 1) + " . " + marker + " " + at + " " + (n + 1) + " } ";
                clients[i].mustUpdate(form.equals("guarded")
                    ? "DELETE { " + c + " " + v + " " + n + " }" + insert + "WHERE { " + c + " " + v + " " + n + " }"
                    : "DELETE { " + c + " " + v + " ?x }" + insert + "WHERE { " + c + " " + v + " ?x }");
            });
            long markers = store.number("SELECT (COUNT(*) AS ?n) WHERE { ?m " + at + " 1 }");
            long versions = store.number("SELECT (COUNT(*) AS ?n) WHERE { " + c + " " + v + " ?x }");
            t.add(markers == 1 ? "one applied, the other wrote nothing" : markers == 2 ? "both applied from the same version" : "markers " + markers, markers != 1 || versions != 1);
        }
    }

    /** ISO-02. Four clients each loop: read the version, send the guarded update with a marker of their own, until the target. */
    static void casStress(Client store) throws Exception {
        Tally t = new Tally("ISO-02", "fuseki", "guarded", "four clients");
        String p = "urn:iso:02:";
        String c = iri(p, "c"), v = iri(p, "v"), at = iri(p, "at");
        store.mustUpdate("INSERT DATA { " + c + " " + v + " 0 }");
        AtomicLong lost = new AtomicLong();
        runAll(STRESS_THREADS, i -> {
            Client client = store.another();
            for (int k = 0; ; k++) {
                long n = client.number("SELECT ?n WHERE { " + c + " " + v + " ?n }");
                if (n >= STRESS_TARGET) {
                    return;
                }
                String marker = iri(p, "w" + i + "-" + k);
                client.mustUpdate("DELETE { " + c + " " + v + " " + n + " } INSERT { " + c + " " + v + " " + (n + 1) + " . " + marker + " " + at + " " + (n + 1)
                    + " } WHERE { " + c + " " + v + " " + n + " }");
                if (client.number("SELECT (COUNT(*) AS ?n) WHERE { " + marker + " " + at + " ?x }") == 0) {
                    lost.incrementAndGet();
                }
            }
        });
        long markers = store.number("SELECT (COUNT(*) AS ?n) WHERE { ?m " + at + " ?x }");
        long doubled = store.number("SELECT (COUNT(*) AS ?n) WHERE { SELECT ?x WHERE { ?m " + at + " ?x } GROUP BY ?x HAVING (COUNT(?m) > 1) }");
        t.count("target", STRESS_TARGET);
        t.count("markers", markers);
        t.count("versions with more than one marker", doubled);
        t.count("races lost", lost.get());
        t.add(markers == STRESS_TARGET && doubled == 0 ? "one marker at each version" : "markers " + markers + ", versions with more than one " + doubled,
            markers != STRESS_TARGET || doubled != 0);
    }

    /** ISO-03. Two clients deliver the same command, each after reading that it has no receipt. */
    static void duplicateDelivery(Client store, String form) throws Exception {
        Tally t = new Tally("ISO-03", "fuseki", form, "two clients");
        for (int rep = 0; rep < REPS; rep++) {
            String p = "urn:iso:03:" + (form.contains("earlier") ? "earlier" : "request") + ":" + rep + ":";
            String cmd = iri(p, "cmd"), receipt = iri(p, "receipt"), of = iri(p, "of");
            Client[] clients = {store.another(), store.another()};
            CyclicBarrier barrier = new CyclicBarrier(2);
            both(i -> {
                long seen = clients[i].number("SELECT (COUNT(*) AS ?n) WHERE { " + cmd + " " + receipt + " ?w }");
                barrier.await();
                String effect = iri(p, "effect" + i) + " " + of + " " + cmd + " . " + cmd + " " + receipt + " " + iri(p, "w" + i);
                if (form.contains("earlier")) {
                    if (seen == 0) {
                        clients[i].mustUpdate("INSERT DATA { " + effect + " }");
                    }
                } else {
                    clients[i].mustUpdate("INSERT { " + effect + " } WHERE { FILTER NOT EXISTS { " + cmd + " " + receipt + " ?any } }");
                }
            });
            long effects = store.number("SELECT (COUNT(*) AS ?n) WHERE { ?e " + of + " " + cmd + " }");
            t.add(effects == 1 ? "applied once" : "applied " + effects + " times", effects != 1);
        }
    }

    /** ISO-04 over HTTP. A request inserts a marker and 20,000 triples into a graph and then fails, while another client reads the marker as often as it can. */
    static void failedRequestBesideReader(Client store) throws Exception {
        Tally t = new Tally("ISO-04", "fuseki", "reader polling while the request runs", "two clients");
        for (int rep = 0; rep < REPS; rep++) {
            String p = "urn:iso:04:" + rep + ":";
            String marker = iri(p, "m"), at = iri(p, "at");
            StringBuilder text = new StringBuilder("INSERT DATA { GRAPH ").append(iri(p, "g")).append(" { ").append(marker).append(' ').append(at).append(" 1 . ");
            for (int k = 0; k < BULK; k++) {
                text.append(iri(p, "s" + k)).append(' ').append(at).append(' ').append(k).append(" . ");
            }
            // The second operation fails when it runs, after the insert: CLEAR GRAPH of a graph that holds nothing, without SILENT, which ARQ refuses.
            // CREATE GRAPH of the graph the insert made does not fail on TDB2, so it cannot serve.
            text.append("} } ; CLEAR GRAPH ").append(iri(p, "absent"));
            AtomicBoolean done = new AtomicBoolean();
            AtomicInteger status = new AtomicInteger();
            AtomicLong samples = new AtomicLong(), seen = new AtomicLong();
            Client writer = store.another(), reader = store.another();
            both(i -> {
                if (i == 0) {
                    try {
                        status.set(writer.update(text.toString()));
                    } finally {
                        done.set(true);
                    }
                } else {
                    while (!done.get()) {
                        samples.incrementAndGet();
                        if (reader.number("SELECT (COUNT(*) AS ?n) WHERE { GRAPH ?g { " + marker + " " + at + " ?x } }") > 0) {
                            seen.incrementAndGet();
                        }
                    }
                }
            });
            long after = store.number("SELECT (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s " + at + " ?x } }");
            t.count("reads while the request ran", samples.get());
            t.count("reads that saw the marker", seen.get());
            boolean failed = status.get() >= 400;
            t.add((failed ? "refused with HTTP " + status.get() : "HTTP " + status.get()) + (after == 0 ? ", nothing left" : ", " + after + " triples left"),
                !failed || after != 0 || seen.get() != 0);
        }
    }

    static String move(String p, String row, String writer) {
        String x = iri(p, row), rev = iri(p, "rev"), by = iri(p, "by");
        return "DELETE { " + x + " " + rev + " 0 } INSERT { " + x + " " + rev + " 1 . " + x + " " + by + " " + iri(p, writer) + " } WHERE { " + x + " " + rev + " 0 }";
    }

    /** ISO-05. Two requests each move rows a and b, in opposite orders, each step guarded on its own row, sent at once. */
    static void twoRowsOppositeOrder(Client store) throws Exception {
        Tally t = new Tally("ISO-05", "fuseki", "per-step guards", "two clients");
        for (int rep = 0; rep < REPS; rep++) {
            String p = "urn:iso:05:" + rep + ":";
            String rev = iri(p, "rev"), by = iri(p, "by");
            store.mustUpdate("INSERT DATA { " + iri(p, "a") + " " + rev + " 0 . " + iri(p, "b") + " " + rev + " 0 }");
            Client[] clients = {store.another(), store.another()};
            CyclicBarrier barrier = new CyclicBarrier(2);
            both(i -> {
                String text = i == 0 ? move(p, "a", "w0") + " ; " + move(p, "b", "w0") : move(p, "b", "w1") + " ; " + move(p, "a", "w1");
                barrier.await();
                clients[i].mustUpdate(text);
            });
            List<String[]> a = store.select("SELECT ?w WHERE { " + iri(p, "a") + " " + by + " ?w }");
            List<String[]> b = store.select("SELECT ?w WHERE { " + iri(p, "b") + " " + by + " ?w }");
            boolean whole = a.size() == 1 && b.size() == 1 && a.get(0)[0].equals(b.get(0)[0]);
            t.add(whole ? "one request applied both steps, the other neither" : "the rows were moved by different requests", !whole);
        }
    }

    /** ISO-06 over HTTP. A client moves the version and adds its receipt in one request, ten times, while another reads both. */
    static void readBesideCommit(Client store, String form) throws Exception {
        Tally t = new Tally("ISO-06", "fuseki", form, "two clients");
        for (int rep = 0; rep < REPS; rep++) {
            String p = "urn:iso:06:" + (form.startsWith("one") ? "one" : "two") + ":" + rep + ":";
            String c = iri(p, "c"), v = iri(p, "v"), rc = iri(p, "receipt");
            store.mustUpdate("INSERT DATA { " + c + " " + v + " 0 . " + iri(p, "r0") + " " + rc + " 0 }");
            Client writer = store.another(), reader = store.another();
            if (form.startsWith("one")) {
                AtomicBoolean done = new AtomicBoolean();
                AtomicLong samples = new AtomicLong(), torn = new AtomicLong();
                both(i -> {
                    if (i == 0) {
                        try {
                            for (int n = 0; n < MOVES; n++) {
                                writer.mustUpdate("DELETE { " + c + " " + v + " " + n + " } INSERT { " + c + " " + v + " " + (n + 1) + " . " + iri(p, "r" + (n + 1)) + " " + rc + " " + (n + 1)
                                    + " } WHERE { " + c + " " + v + " " + n + " }");
                            }
                        } finally {
                            done.set(true);
                        }
                    } else {
                        while (!done.get()) {
                            List<String[]> rows = reader.select("SELECT ?n (MAX(?q) AS ?m) WHERE { " + c + " " + v + " ?n . ?r " + rc + " ?q } GROUP BY ?n");
                            samples.incrementAndGet();
                            if (rows.size() != 1 || !rows.get(0)[0].equals(rows.get(0)[1])) {
                                torn.incrementAndGet();
                            }
                        }
                    }
                });
                t.count("reads while the writes ran", samples.get());
                t.count("reads that saw a version and a receipt that differ", torn.get());
                t.add(torn.get() == 0 ? "every read saw the version and its receipt together" : torn.get() + " reads saw them apart", torn.get() != 0);
            } else {
                long n = reader.number("SELECT ?n WHERE { " + c + " " + v + " ?n }");
                writer.mustUpdate("DELETE { " + c + " " + v + " " + n + " } INSERT { " + c + " " + v + " " + (n + 1) + " . " + iri(p, "r" + (n + 1)) + " " + rc + " " + (n + 1)
                    + " } WHERE { " + c + " " + v + " " + n + " }");
                long m = reader.number("SELECT (MAX(?q) AS ?m) WHERE { ?r " + rc + " ?q }");
                t.add(m == n ? "the two reads agree" : "the version read first and the receipt read second differ", m != n);
            }
        }
    }

    /** ISO-07. A client inserts a marker, and as soon as the reply has come another client reads it. */
    static void visibleAfterReply(Client store) throws Exception {
        Tally t = new Tally("ISO-07", "fuseki", "a new request from another client", "two clients");
        Client writer = store.another(), reader = store.another();
        for (int rep = 0; rep < REPS; rep++) {
            String p = "urn:iso:07:" + rep + ":";
            writer.mustUpdate("INSERT DATA { " + iri(p, "m") + " " + iri(p, "at") + " 1 }");
            long seen = reader.number("SELECT (COUNT(*) AS ?n) WHERE { " + iri(p, "m") + " " + iri(p, "at") + " ?x }");
            t.add(seen == 1 ? "seen" : "not seen", seen != 1);
        }
    }

    /** ISO-08. Receipts take positions. A relay that has seen every position up to its mark must never see a lower one appear later. */
    static void positions(Client store, String form) throws Exception {
        Tally t = new Tally("ISO-08", "fuseki", form, form.startsWith("position computed") ? "four clients" : "two clients");
        int reps = form.startsWith("position computed") ? Math.max(1, REPS / 4) : REPS;
        for (int rep = 0; rep < reps; rep++) {
            String p = "urn:iso:08:" + (form.startsWith("position computed") ? "in" : "own") + ":" + rep + ":";
            String pos = iri(p, "pos");
            if (form.startsWith("position computed")) {
                int per = 5;
                AtomicBoolean done = new AtomicBoolean();
                AtomicInteger writersLeft = new AtomicInteger(STRESS_THREADS);
                AtomicLong samples = new AtomicLong(), gaps = new AtomicLong();
                runAll(STRESS_THREADS + 1, i -> {
                    if (i < STRESS_THREADS) {
                        Client client = store.another();
                        try {
                            for (int k = 0; k < per; k++) {
                                client.mustUpdate("INSERT { " + iri(p, "r" + i + "-" + k) + " " + pos + " ?n } WHERE { { SELECT ((COALESCE(MAX(?q), 0) + 1) AS ?n) WHERE { OPTIONAL { ?x " + pos + " ?q } } } }");
                            }
                        } finally {
                            if (writersLeft.decrementAndGet() == 0) {
                                done.set(true);
                            }
                        }
                    } else {
                        Client reader = store.another();
                        while (!done.get()) {
                            TreeSet<Long> seen = new TreeSet<>();
                            for (String[] row : reader.select("SELECT ?q WHERE { ?x " + pos + " ?q }")) {
                                seen.add(Long.parseLong(row[0].trim()));
                            }
                            samples.incrementAndGet();
                            if (!seen.isEmpty() && seen.last() != seen.size()) {
                                gaps.incrementAndGet();
                            }
                        }
                    }
                });
                long receipts = store.number("SELECT (COUNT(*) AS ?n) WHERE { ?x " + pos + " ?q }");
                long distinct = store.number("SELECT (COUNT(DISTINCT ?q) AS ?n) WHERE { ?x " + pos + " ?q }");
                long max = store.number("SELECT (MAX(?q) AS ?n) WHERE { ?x " + pos + " ?q }");
                t.count("reads while the writes ran", samples.get());
                t.count("reads that saw a gap below the highest position", gaps.get());
                boolean ok = gaps.get() == 0 && receipts == (long) STRESS_THREADS * per && distinct == receipts && max == receipts;
                t.add(ok ? "positions 1 to " + receipts + ", no gap seen" : "receipts " + receipts + ", distinct " + distinct + ", gaps seen " + gaps.get(), !ok);
            } else {
                String ctr = iri(p, "ctr"), n = iri(p, "n");
                store.mustUpdate("INSERT DATA { " + ctr + " " + n + " 0 }");
                Client w1 = store.another(), w2 = store.another(), relay = store.another();
                long p1 = take(w1, ctr, n), p2 = take(w2, ctr, n);
                w2.mustUpdate("INSERT DATA { " + iri(p, "r2") + " " + pos + " " + p2 + " }");
                long mark = relay.number("SELECT (MAX(?q) AS ?n) WHERE { ?x " + pos + " ?q }");
                w1.mustUpdate("INSERT DATA { " + iri(p, "r1") + " " + pos + " " + p1 + " }");
                long below = relay.number("SELECT (COUNT(*) AS ?n) WHERE { ?x " + pos + " ?q . FILTER(?q < " + mark + ") }");
                t.add(below > 0 ? "a position below the relay's mark appeared after it" : "no position appeared below the mark", below > 0);
            }
        }
    }

    /** Takes the next position from a counter with a guarded update, retrying where another client moved it. */
    static long take(Client client, String ctr, String n) throws Exception {
        while (true) {
            long current = client.number("SELECT ?x WHERE { " + ctr + " " + n + " ?x }");
            client.mustUpdate("DELETE { " + ctr + " " + n + " " + current + " } INSERT { " + ctr + " " + n + " " + (current + 1) + " } WHERE { " + ctr + " " + n + " " + current + " }");
            if (client.number("SELECT ?x WHERE { " + ctr + " " + n + " ?x }") == current + 1) {
                return current + 1;
            }
        }
    }

    /** ISO-09. A writer reads that no fence is set, the fence is set and a copy is taken, then the writer writes. */
    static void fence(Client store, String form) throws Exception {
        Tally t = new Tally("ISO-09", "fuseki", form, "three clients");
        for (int rep = 0; rep < REPS; rep++) {
            String p = "urn:iso:09:" + (form.contains("earlier") ? "earlier" : "request") + ":" + rep + ":";
            String auth = iri(p, "authority"), fenced = iri(p, "fenced"), in = iri(p, "in");
            Client writer = store.another(), migrator = store.another();
            long before = writer.number("SELECT (COUNT(*) AS ?n) WHERE { " + auth + " " + fenced + " ?f }");
            migrator.mustUpdate("INSERT DATA { " + auth + " " + fenced + " true }");
            long copied = migrator.number("SELECT (COUNT(*) AS ?n) WHERE { ?w " + in + " " + auth + " }");
            String write = iri(p, "w") + " " + in + " " + auth;
            if (form.contains("earlier")) {
                if (before == 0) {
                    writer.mustUpdate("INSERT DATA { " + write + " }");
                }
            } else {
                writer.mustUpdate("INSERT { " + write + " } WHERE { FILTER NOT EXISTS { " + auth + " " + fenced + " ?f } }");
            }
            long applied = store.number("SELECT (COUNT(*) AS ?n) WHERE { ?w " + in + " " + auth + " }");
            boolean lost = applied > 0 && copied == 0;
            t.add(lost ? "applied after the fence and missing from the copy" : applied == 0 ? "refused" : "in the copy", lost);
        }
    }

    /** ISO-10. Two clients send the same guarded move at once. The one refused reads the version afterwards. */
    static void refusalRevision(Client store) throws Exception {
        Tally t = new Tally("ISO-10", "fuseki", "version read after the refusal", "two clients");
        for (int rep = 0; rep < REPS; rep++) {
            String p = "urn:iso:10:" + rep + ":";
            String c = iri(p, "c"), v = iri(p, "v"), at = iri(p, "at");
            store.mustUpdate("INSERT DATA { " + c + " " + v + " 0 }");
            Client[] clients = {store.another(), store.another()};
            CyclicBarrier barrier = new CyclicBarrier(2);
            long[] found = {-2, -2};
            both(i -> {
                barrier.await();
                String marker = iri(p, "m" + i);
                clients[i].mustUpdate("DELETE { " + c + " " + v + " 0 } INSERT { " + c + " " + v + " 1 . " + marker + " " + at + " 1 } WHERE { " + c + " " + v + " 0 }");
                if (clients[i].number("SELECT (COUNT(*) AS ?n) WHERE { " + marker + " " + at + " ?x }") == 0) {
                    found[i] = clients[i].number("SELECT ?n WHERE { " + c + " " + v + " ?n }");
                }
            });
            long refusedFound = found[0] != -2 ? found[0] : found[1];
            boolean oneRefused = (found[0] == -2) != (found[1] == -2);
            t.add(!oneRefused ? "not exactly one refused" : refusedFound == 1 ? "the refused client read version 1" : "the refused client read version " + refusedFound,
                !oneRefused || refusedFound == 0);
        }
    }

    /** ISO-11. Rows a and b are both on. Each client reads that both are, then takes one off, so that at least one stays on. */
    static void writeSkew(Client store, String form) throws Exception {
        Tally t = new Tally("ISO-11", "fuseki", form, "two clients");
        for (int rep = 0; rep < REPS; rep++) {
            String p = "urn:iso:11:" + (form.contains("earlier") ? "earlier" : "request") + ":" + rep + ":";
            String on = iri(p, "on"), a = iri(p, "a"), b = iri(p, "b");
            store.mustUpdate("INSERT DATA { " + a + " " + on + " true . " + b + " " + on + " true }");
            Client[] clients = {store.another(), store.another()};
            CyclicBarrier barrier = new CyclicBarrier(2);
            both(i -> {
                String mine = i == 0 ? a : b, other = i == 0 ? b : a;
                long count = clients[i].number("SELECT (COUNT(*) AS ?n) WHERE { ?x " + on + " true }");
                barrier.await();
                if (form.contains("earlier")) {
                    if (count >= 2) {
                        clients[i].mustUpdate("DELETE DATA { " + mine + " " + on + " true } ; INSERT DATA { " + mine + " " + on + " false }");
                    }
                } else {
                    clients[i].mustUpdate("DELETE { " + mine + " " + on + " true } INSERT { " + mine + " " + on + " false } WHERE { " + mine + " " + on + " true . " + other + " " + on + " true }");
                }
            });
            long left = store.number("SELECT (COUNT(*) AS ?n) WHERE { ?x " + on + " true }");
            t.add(left == 0 ? "both taken off" : left + " left on", left == 0);
        }
    }

    // ---- TDB2 in process ----------------------------------------------------------------------------------------------

    static Node uri(String s) {
        return NodeFactory.createURI(s);
    }

    /** ISO-04 in process. A write transaction adds a marker, a read transaction on another thread reads it, and the writer aborts. */
    static void dirtyReadInProcess(Dataset ds) throws Exception {
        Tally t = new Tally("ISO-04", "tdb2", "reader transaction during the write transaction", "in process");
        DatasetGraph dsg = ds.asDatasetGraph();
        for (int rep = 0; rep < REPS; rep++) {
            Node g = Quad.defaultGraphIRI, m = uri("urn:iso:04t:" + rep + ":m"), at = uri("urn:iso:04t:at"), one = uri("urn:iso:04t:one");
            CyclicBarrier written = new CyclicBarrier(2), read = new CyclicBarrier(2), aborted = new CyclicBarrier(2);
            boolean[] seen = new boolean[2];
            both(i -> {
                if (i == 0) {
                    ds.begin(TxnType.WRITE);
                    try {
                        dsg.add(Quad.create(g, m, at, one));
                        written.await();
                        read.await();
                        ds.abort();
                    } finally {
                        ds.end();
                    }
                    aborted.await();
                } else {
                    written.await();
                    seen[0] = Txn.calculateRead(ds, () -> dsg.contains(g, m, at, one));
                    read.await();
                    aborted.await();
                    seen[1] = Txn.calculateRead(ds, () -> dsg.contains(g, m, at, one));
                }
            });
            t.add(seen[0] || seen[1] ? "the reader saw the marker" : "the reader saw nothing, during or after", seen[0] || seen[1]);
        }
    }

    /** ISO-06 in process. A reader reads the version, a writer moves it and adds its receipt and commits, and the reader reads the receipts. */
    static void snapshotInProcess(Dataset ds, String form) throws Exception {
        Tally t = new Tally("ISO-06", "tdb2", form, "in process");
        DatasetGraph dsg = ds.asDatasetGraph();
        for (int rep = 0; rep < REPS; rep++) {
            String p = "urn:iso:06t:" + (form.startsWith("one") ? "one" : "two") + ":" + rep + ":";
            Node g = Quad.defaultGraphIRI, c = uri(p + "c"), v = uri(p + "v"), rc = uri(p + "receipt"), n0 = uri(p + "n0"), n1 = uri(p + "n1");
            Txn.executeWrite(ds, () -> {
                dsg.add(Quad.create(g, c, v, n0));
                dsg.add(Quad.create(g, uri(p + "r0"), rc, n0));
            });
            CyclicBarrier readFirst = new CyclicBarrier(2), committed = new CyclicBarrier(2);
            boolean[] torn = new boolean[1];
            both(i -> {
                if (i == 0) {
                    readFirst.await();
                    Txn.executeWrite(ds, () -> {
                        dsg.delete(Quad.create(g, c, v, n0));
                        dsg.add(Quad.create(g, c, v, n1));
                        dsg.add(Quad.create(g, uri(p + "r1"), rc, n1));
                    });
                    committed.await();
                } else if (form.startsWith("one")) {
                    ds.begin(TxnType.READ);
                    try {
                        boolean atOne = dsg.contains(g, c, v, n1);
                        readFirst.await();
                        committed.await();
                        boolean receiptOne = dsg.contains(g, uri(p + "r1"), rc, n1);
                        torn[0] = atOne != receiptOne;
                    } finally {
                        ds.end();
                    }
                } else {
                    boolean atOne = Txn.calculateRead(ds, () -> dsg.contains(g, c, v, n1));
                    readFirst.await();
                    committed.await();
                    boolean receiptOne = Txn.calculateRead(ds, () -> dsg.contains(g, uri(p + "r1"), rc, n1));
                    torn[0] = atOne != receiptOne;
                }
            });
            t.add(torn[0] ? "the version read first and the receipt read second differ" : "the two reads agree", torn[0]);
        }
    }

    // ---- the run ------------------------------------------------------------------------------------------------------

    static void deleteTree(Path dir) {
        try (var walk = Files.walk(dir)) {
            walk.sorted(Comparator.reverseOrder()).forEach(path -> path.toFile().delete());
        } catch (IOException e) {
            // a temporary directory left behind is harmless
        }
    }

    static String jarOf(Class<?> type) {
        try {
            return Path.of(type.getProtectionDomain().getCodeSource().getLocation().toURI()).getFileName().toString();
        } catch (Exception e) {
            return "unknown";
        }
    }

    static String json(String s) {
        StringBuilder out = new StringBuilder("\"");
        for (char ch : s.toCharArray()) {
            switch (ch) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                case '\n' -> out.append("\\n");
                case '\r' -> out.append("\\r");
                case '\t' -> out.append("\\t");
                default -> {
                    if (ch < 0x20) {
                        out.append(String.format("\\u%04x", (int) ch));
                    } else {
                        out.append(ch);
                    }
                }
            }
        }
        return out.append('"').toString();
    }

    static String write(Map<String, String> env) {
        StringBuilder out = new StringBuilder("{\n  \"environment\": {");
        Iterator<Map.Entry<String, String>> it = env.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry<String, String> e = it.next();
            out.append(json(e.getKey())).append(": ").append(json(e.getValue())).append(it.hasNext() ? ", " : "");
        }
        out.append("},\n  \"rows\": [\n");
        for (int r = 0; r < ROWS.size(); r++) {
            Tally t = ROWS.get(r);
            out.append("    {\"probe\": ").append(json(t.probe)).append(", \"store\": ").append(json(t.store)).append(", \"form\": ").append(json(t.form))
                .append(", \"mode\": ").append(json(t.mode)).append(", \"reps\": ").append(t.reps).append(", \"anomalies\": ").append(t.anomalies).append(", \"outcomes\": {");
            int k = 0;
            for (Map.Entry<String, Integer> e : t.outcomes.entrySet()) {
                out.append(k++ > 0 ? ", " : "").append(json(e.getKey())).append(": ").append(e.getValue());
            }
            out.append("}, \"counts\": {");
            k = 0;
            for (Map.Entry<String, Long> e : t.counts.entrySet()) {
                out.append(k++ > 0 ? ", " : "").append(json(e.getKey())).append(": ").append(e.getValue());
            }
            out.append("}}").append(r + 1 < ROWS.size() ? ",\n" : "\n");
        }
        return out.append("  ]\n}\n").toString();
    }

    public static void main(String[] args) throws Exception {
        Path out = Path.of(System.getProperty("isolation.out", "results.json"));
        Path served = Files.createTempDirectory("isolation-fuseki-");
        Path local = Files.createTempDirectory("isolation-tdb2-");
        Location servedAt = Location.create(served.toString()), localAt = Location.create(local.toString());
        Dataset servedDs = TDB2Factory.connectDataset(servedAt);
        Dataset localDs = TDB2Factory.connectDataset(localAt);
        FusekiServer server = FusekiServer.create().loopback(true).port(0).add("/ds", servedDs.asDatasetGraph()).build().start();
        long started = System.nanoTime();
        try {
            Client store = new Client("http://localhost:" + server.getPort() + "/ds");
            casTwoWriters(store, "guarded");
            casTwoWriters(store, "unguarded");
            casStress(store);
            duplicateDelivery(store, "receipt checked by an earlier read");
            duplicateDelivery(store, "receipt checked in the request");
            failedRequestBesideReader(store);
            twoRowsOppositeOrder(store);
            readBesideCommit(store, "one query");
            readBesideCommit(store, "two queries");
            visibleAfterReply(store);
            positions(store, "position computed in the request");
            positions(store, "position taken by a request of its own");
            fence(store, "fence checked by an earlier read");
            fence(store, "fence checked in the write's request");
            refusalRevision(store);
            writeSkew(store, "check by an earlier read");
            writeSkew(store, "check in the request");
            dirtyReadInProcess(localDs);
            snapshotInProcess(localDs, "one read transaction");
            snapshotInProcess(localDs, "two read transactions");
        } finally {
            server.stop();
            servedDs.close();
            localDs.close();
            StoreConnection.release(servedAt);
            StoreConnection.release(localAt);
            deleteTree(served);
            deleteTree(local);
        }
        Map<String, String> env = new LinkedHashMap<>();
        env.put("jena", org.apache.jena.Jena.VERSION);
        env.put("tdb2", jarOf(TDB2Factory.class));
        env.put("fuseki", jarOf(FusekiServer.class));
        env.put("java", System.getProperty("java.version"));
        env.put("os", System.getProperty("os.name") + " " + System.getProperty("os.arch"));
        env.put("reps", Integer.toString(REPS));
        env.put("seconds", String.format("%.1f", (System.nanoTime() - started) / 1e9));
        Files.createDirectories(out.toAbsolutePath().getParent());
        Files.writeString(out, write(env), StandardCharsets.UTF_8);
        System.out.println("jena arm: " + ROWS.size() + " rows written to " + out);
    }
}
