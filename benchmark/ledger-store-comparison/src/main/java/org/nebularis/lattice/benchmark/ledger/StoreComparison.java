// SPDX-License-Identifier: MPL-2.0
// NB: This module has been produced using GenAI
package org.nebularis.lattice.benchmark.ledger;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Random;
import java.util.stream.Stream;

import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.QueryExecution;
import org.apache.jena.query.QuerySolution;
import org.apache.jena.query.ResultSet;
import org.apache.jena.sparql.core.Quad;
import org.apache.jena.system.Txn;
import org.apache.jena.tdb2.TDB2Factory;

/**
 * Whether the ledger's period-graph partition bounds an aggregate read on Jena TDB2 as it does on Oxigraph.
 *
 * <p>The claim under test is the shape of the cost, not its absolute value. On Oxigraph a programme read behind a
 * position filter grows with the history (2.66 ms to 261 ms from 1,000 to 100,000 events) while the same read over
 * named period graphs stays flat (0.40 ms to 0.54 ms). This asks whether a store of a different architecture, with
 * B+tree indexes on disk rather than RocksDB, behaves the same way.
 *
 * <p>The account tree, the event mix and the strategies mirror {@code benchmark/ledger-posting-cost}. The event stream
 * does not: Java's generator is not Python's, so the two engines see the same volume and structure but not the same
 * draws, and only the shape of each engine's curve is comparable. Each run checks itself against a model computed
 * here by plain arithmetic, so a wrong balance fails the run on either engine.
 *
 * <p><b>A wrong balance fails this benchmark. Time never does (ADR-A124).</b>
 */
public final class StoreComparison {

    static final String L = "https://example.org/ledger-cost#";
    static final int PROGRAMMES = 2, LAYERS_PER_PROGRAMME = 5, CONTRACTS_PER_LAYER = 10;
    static final int CHECKPOINT_EVERY = 500;
    static final long SEED = 20261024L;
    static final long[] STATED = {1_000_000_000L, 10_000_000_000L, 100_000_000_000L};
    static final int[] SIZES = {1_000, 5_000, 20_000};
    static final int REPS = 7;

    /** An account in the tree: its IRI, its level (0 contract, 1 layer, 2 programme) and its parent's index. */
    record Account(String iri, int level, int parent) {}

    /** One event: the contract account drawn on, whether it is a debit, and the amount. */
    record Event(int contract, boolean debit, long amount) {}

    /** What one strategy cost at one size. */
    record Measurement(String strategy, int events, long quads, double writeSeconds, double readMillis, long folded) {}

    static List<Account> tree() {
        List<Account> accounts = new ArrayList<>();
        for (int p = 0; p < PROGRAMMES; p++) {
            accounts.add(new Account("urn:acct:prog" + p, 2, -1));
        }
        for (int p = 0; p < PROGRAMMES; p++) {
            for (int l = 0; l < LAYERS_PER_PROGRAMME; l++) {
                accounts.add(new Account("urn:acct:lyr" + p + "-" + l, 1, p));
            }
        }
        int firstLayer = PROGRAMMES;
        for (int index = 0; index < PROGRAMMES * LAYERS_PER_PROGRAMME; index++) {
            for (int c = 0; c < CONTRACTS_PER_LAYER; c++) {
                accounts.add(new Account("urn:acct:con" + index + "-" + c, 0, firstLayer + index));
            }
        }
        return accounts;
    }

    /** The account and every ancestor, contract first. */
    static List<Integer> ancestors(List<Account> accounts, int index) {
        List<Integer> chain = new ArrayList<>();
        for (int at = index; at >= 0; at = accounts.get(at).parent()) {
            chain.add(at);
        }
        return chain;
    }

    static List<Event> events(int count, List<Account> accounts) {
        List<Integer> contracts = new ArrayList<>();
        for (int i = 0; i < accounts.size(); i++) {
            if (accounts.get(i).level() == 0) {
                contracts.add(i);
            }
        }
        Random rng = new Random(SEED);
        List<Event> stream = new ArrayList<>(count);
        for (int i = 0; i < count; i++) {
            stream.add(new Event(contracts.get(rng.nextInt(contracts.size())), rng.nextDouble() >= 0.2,
                                 1 + rng.nextInt(1000)));
        }
        return stream;
    }

    /**
     * The balance of every account after each event, and the balance at each close, by the plainest arithmetic.
     * This is what the store's answers are checked against.
     */
    static final class Model {
        final long[] atPoint;
        final java.util.Map<Integer, long[]> atCloses = new java.util.TreeMap<>();

        Model(int count, int point, List<Account> accounts, List<Event> stream, int every) {
            long[] snapshot = null;
            long[] balance = new long[accounts.size()];
            for (int i = 0; i < accounts.size(); i++) {
                balance[i] = STATED[accounts.get(i).level()];
            }
            for (int e = 1; e <= count; e++) {
                Event event = stream.get(e - 1);
                for (int i : ancestors(accounts, event.contract())) {
                    balance[i] += event.debit() ? -event.amount() : event.amount();
                }
                if (e % every == 0) {
                    atCloses.put(e, balance.clone());
                }
                if (e == point) {
                    snapshot = balance.clone();
                }
            }
            this.atPoint = point == 0 ? balance.clone() : snapshot;
        }
    }

    static Node iri(String value) {
        return NodeFactory.createURI(value);
    }

    static Node num(long value) {
        return NodeFactory.createLiteralByValue(value);
    }

    static String periodGraph(String layerIri, int period) {
        return "urn:graph:" + layerIri.substring(layerIri.lastIndexOf(':') + 1) + ":" + period;
    }

    /** The layers whose contracts lie in the account's subtree, read from the tree structure. */
    static List<String> layersOf(List<Account> accounts, int index) {
        Account account = accounts.get(index);
        if (account.level() == 0) {
            return List.of(accounts.get(account.parent()).iri());
        }
        if (account.level() == 1) {
            return List.of(account.iri());
        }
        List<String> layers = new ArrayList<>();
        for (Account candidate : accounts) {
            if (candidate.level() == 1 && accounts.get(candidate.parent()).iri().equals(account.iri())) {
                layers.add(candidate.iri());
            }
        }
        return layers;
    }

    static void writeHistory(Dataset dataset, boolean periodGraphs, List<Account> accounts, List<Event> stream,
                             Model model, int every) {
        Txn.executeWrite(dataset, () -> {
            var dsg = dataset.asDatasetGraph();
            Node defaultGraph = Quad.defaultGraphIRI;
            for (Account account : accounts) {
                dsg.add(new Quad(defaultGraph, iri(account.iri()), iri(L + "type"), iri(L + "Account")));
                dsg.add(new Quad(defaultGraph, iri(account.iri()), iri(L + "statedAmount"), num(STATED[account.level()])));
                if (account.parent() >= 0) {
                    dsg.add(new Quad(defaultGraph, iri(account.iri()), iri(L + "partOf"),
                                     iri(accounts.get(account.parent()).iri())));
                }
            }
            for (int e = 1; e <= stream.size(); e++) {
                Event event = stream.get(e - 1);
                Account account = accounts.get(event.contract());
                String suffix = account.iri().substring(account.iri().lastIndexOf(':') + 1);
                Node posting = iri("urn:posting:" + e + ":" + suffix);
                Node graph = defaultGraph;
                if (periodGraphs) {
                    graph = iri(periodGraph(accounts.get(account.parent()).iri(), (e - 1) / every));
                }
                dsg.add(new Quad(graph, posting, iri(L + "type"), iri(L + "Posting")));
                dsg.add(new Quad(graph, posting, iri(L + "account"), iri(account.iri())));
                dsg.add(new Quad(graph, posting, iri(L + "owner"), iri("urn:owner:1")));
                dsg.add(new Quad(graph, posting, iri(L + "key"), NodeFactory.createLiteralString("k" + e)));
                dsg.add(new Quad(graph, posting, iri(L + "position"), num(e)));
                dsg.add(new Quad(graph, posting, iri(L + "microPosition"), num(0)));
                dsg.add(new Quad(graph, posting, iri(L + "direction"), iri(L + (event.debit() ? "Debit" : "Credit"))));
                dsg.add(new Quad(graph, posting, iri(L + "amount"), num(event.amount())));
            }
            if (periodGraphs) {
                for (var close : model.atCloses.entrySet()) {
                    for (int i = 0; i < accounts.size(); i++) {
                        Account account = accounts.get(i);
                        String suffix = account.iri().substring(account.iri().lastIndexOf(':') + 1);
                        Node checkpoint = iri("urn:checkpoint:" + close.getKey() + ":" + suffix);
                        dsg.add(new Quad(defaultGraph, checkpoint, iri(L + "type"), iri(L + "Checkpoint")));
                        dsg.add(new Quad(defaultGraph, checkpoint, iri(L + "account"), iri(account.iri())));
                        dsg.add(new Quad(defaultGraph, checkpoint, iri(L + "position"), num(close.getKey())));
                        dsg.add(new Quad(defaultGraph, checkpoint, iri(L + "balance"), num(close.getValue()[i])));
                    }
                }
            }
        });
    }

    static final String PREFIX = "PREFIX l: <" + L + "> ";

    /** The whole-history fold behind a position filter, the form whose cost grows on Oxigraph. */
    static String subtreeFold(String accountIri, int point) {
        return PREFIX + "SELECT (SUM(?signed) AS ?sum) (COUNT(?p) AS ?folded) WHERE { "
               + "?acc l:partOf* <" + accountIri + "> . ?p l:account ?acc ; l:position ?pos ; l:direction ?d ; "
               + "l:amount ?a . FILTER(?pos > -1 && ?pos <= " + point + ") "
               + "BIND(IF(?d = l:Debit, -?a, ?a) AS ?signed) }";
    }

    /** The fold over exactly the named graphs of the periods since the last close. */
    static String graphFold(List<Account> accounts, int index, int after, int point, int every) {
        int first = Math.max(after, 0) / every;
        int last = (point - 1) / every;
        StringBuilder values = new StringBuilder();
        for (int period = first; period <= last; period++) {
            for (String layer : layersOf(accounts, index)) {
                values.append('<').append(periodGraph(layer, period)).append("> ");
            }
        }
        // the only position bound left is the period holding the read point, and none at all when the point is a close
        String bound = point % every == 0 ? "" : "FILTER(?pos <= " + point + ") ";
        String scope = accounts.get(index).level() == 0
                ? "?p l:account <" + accounts.get(index).iri() + "> . " : "";
        return PREFIX + "SELECT (SUM(?signed) AS ?sum) (COUNT(?p) AS ?folded) WHERE { "
               + "VALUES ?g { " + values + "} GRAPH ?g { " + scope
               + "?p l:position ?pos ; l:direction ?d ; l:amount ?a . " + bound + "} "
               + "BIND(IF(?d = l:Debit, -?a, ?a) AS ?signed) }";
    }

    record Folded(long sum, long count) {}

    static Folded runFold(Dataset dataset, String query) {
        return Txn.calculateRead(dataset, () -> {
            try (QueryExecution execution = QueryExecution.dataset(dataset).query(query).build()) {
                ResultSet results = execution.execSelect();
                QuerySolution row = results.next();
                long sum = row.get("sum") == null ? 0 : row.getLiteral("sum").getLong();
                return new Folded(sum, row.getLiteral("folded").getLong());
            }
        });
    }

    /** The latest checkpoint at or before the point, addressed by a derived IRI rather than searched for (TSD-36). */
    static long[] checkpointAt(Dataset dataset, Account account, int point, int every, long base) {
        int position = (point / every) * every;
        if (position < every) {
            return new long[] {-1, base};
        }
        String suffix = account.iri().substring(account.iri().lastIndexOf(':') + 1);
        String query = PREFIX + "SELECT ?b WHERE { <urn:checkpoint:" + position + ":" + suffix + "> l:balance ?b }";
        long balance = Txn.calculateRead(dataset, () -> {
            try (QueryExecution execution = QueryExecution.dataset(dataset).query(query).build()) {
                return execution.execSelect().next().getLiteral("b").getLong();
            }
        });
        return new long[] {position, balance};
    }

    static Measurement measure(String strategy, int count, Path root) throws IOException {
        List<Account> accounts = tree();
        List<Event> stream = events(count, accounts);
        // read mid-period: on a close the checkpoint answers alone and the graph fold is never exercised
        int point = count - Math.max(1, CHECKPOINT_EVERY / 2);
        Model model = new Model(count, point, accounts, stream, CHECKPOINT_EVERY);
        boolean periodGraphs = strategy.equals("post-once-period-graphs");
        int programme = 0;  // the first programme, a top-level aggregate
        Account account = accounts.get(programme);

        Path location = Files.createTempDirectory(root, "tdb2-");
        try {
            Dataset dataset = TDB2Factory.connectDataset(location.toString());
            long start = System.nanoTime();
            writeHistory(dataset, periodGraphs, accounts, stream, model, CHECKPOINT_EVERY);
            double write = (System.nanoTime() - start) / 1e9;
            long quads = Txn.calculateRead(dataset, () -> dataset.asDatasetGraph().stream().count());

            long expected = model.atPoint[programme];
            long folded;
            double millis;
            if (periodGraphs) {
                long[] at = checkpointAt(dataset, account, point, CHECKPOINT_EVERY, STATED[account.level()]);
                String query = graphFold(accounts, programme, (int) at[0], point, CHECKPOINT_EVERY);
                Folded result = runFold(dataset, query);
                check(strategy, count, at[1] + result.sum(), expected);
                folded = result.count();
                millis = time(() -> {
                    long[] again = checkpointAt(dataset, account, point, CHECKPOINT_EVERY, STATED[account.level()]);
                    runFold(dataset, graphFold(accounts, programme, (int) again[0], point, CHECKPOINT_EVERY));
                });
            } else {
                String query = subtreeFold(account.iri(), point);
                Folded result = runFold(dataset, query);
                check(strategy, count, STATED[account.level()] + result.sum(), expected);
                folded = result.count();
                millis = time(() -> runFold(dataset, query));
            }
            dataset.close();
            return new Measurement(strategy, count, quads, write, millis, folded);
        } finally {
            deleteTree(location);
        }
    }

    static void check(String strategy, int count, long got, long expected) {
        if (got != expected) {
            throw new AssertionError("WRONG RESULT: " + strategy + " " + count + " events: programme reads " + got
                                     + ", the model gives " + expected);
        }
    }

    static double time(Runnable work) {
        List<Double> runs = new ArrayList<>();
        for (int i = 0; i < REPS; i++) {
            long start = System.nanoTime();
            work.run();
            runs.add((System.nanoTime() - start) / 1e6);
        }
        runs.sort(Comparator.naturalOrder());
        return runs.get(runs.size() / 2);
    }

    static void deleteTree(Path path) throws IOException {
        try (Stream<Path> walk = Files.walk(path)) {
            walk.sorted(Comparator.reverseOrder()).forEach(entry -> {
                try {
                    Files.deleteIfExists(entry);
                } catch (IOException ignored) {
                    // a store file already gone is not a failure of the benchmark
                }
            });
        }
    }

    public static void main(String[] args) throws IOException {
        int cap = Integer.getInteger("ledger.store.max", SIZES[SIZES.length - 1]);
        Path root = Files.createTempDirectory("ledger-store-comparison-");
        System.out.printf("Jena TDB2, Java %s, programme read at depth 3%n%n", Runtime.version().feature());
        System.out.printf("%-26s %8s %10s %9s %10s %9s%n",
                          "strategy", "events", "quads", "write s", "read ms", "folded");
        System.out.println("-".repeat(78));
        try {
            for (int size : SIZES) {
                if (size > cap) {
                    continue;
                }
                for (String strategy : new String[] {"post-once", "post-once-period-graphs"}) {
                    Measurement m = measure(strategy, size, root);
                    System.out.printf("%-26s %8d %10d %9.2f %10.3f %9d%n",
                                      m.strategy(), m.events(), m.quads(), m.writeSeconds(), m.readMillis(), m.folded());
                }
            }
        } finally {
            deleteTree(root);
        }
    }
}
