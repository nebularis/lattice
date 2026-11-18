// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.probes.msa;

import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.stream.Stream;

/**
 * Reads the JSON lines of one run, the consumers' ({@code rx}, {@code ap}, {@code store}), the publisher's ({@code conf},
 * {@code unk}) and the harness's ({@code cut}, {@code kill}, {@code heal}, in the clock of the containers), and states for each
 * partition who received, who applied, whether two consumers applied at the same time, whether an older write was applied
 * after a newer one, whether a write was applied twice and whether a confirmed write was never applied.
 */
final class Analyze {
    private record Ev(long t, String c, String e, Map<String, String> kv) {
        long num(String key) {
            return Long.parseLong(kv.get(key));
        }
    }

    private record Ap(String c, long t, long bt, long o, long q) {
    }

    private Analyze() {
    }

    static void main(Main.Args a) throws Exception {
        Path dir = Path.of(a.str("dir", "."));
        int partitions = a.num("partitions", 8);
        String resume = a.str("resume", "");
        List<Ev> all = new ArrayList<>();
        try (Stream<Path> files = Files.list(dir)) {
            for (Path p : (Iterable<Path>) files.filter(f -> f.getFileName().toString().endsWith(".log")).sorted()::iterator) {
                for (String line : Files.readAllLines(p, StandardCharsets.UTF_8)) {
                    if (line.startsWith("{") && line.endsWith("}")) {
                        all.add(parse(line));
                    }
                }
            }
        }
        StringBuilder out = new StringBuilder();
        Map<Integer, List<Ap>> aps = new TreeMap<>();
        Map<Integer, Map<String, Long>> firstRx = new TreeMap<>();
        Map<Integer, Map<String, long[]>> rxTimes = new TreeMap<>();
        Map<String, Map<Integer, Long>> lastStored = new TreeMap<>();
        Map<String, Map<Integer, Long>> firstRxOffset = new TreeMap<>();
        Set<Long> confirmed = new TreeSet<>();
        long unknown = 0;
        List<Ev> harness = new ArrayList<>();
        Set<String> consumers = new TreeSet<>();
        Map<String, List<String>> events = new TreeMap<>();
        for (Ev ev : all) {
            switch (ev.e()) {
                case "rx" -> {
                    int s = (int) ev.num("s");
                    consumers.add(ev.c());
                    firstRx.computeIfAbsent(s, k -> new TreeMap<>()).merge(ev.c(), ev.t(), Math::min);
                    rxTimes.computeIfAbsent(s, k -> new TreeMap<>()).merge(ev.c(), new long[] {1, ev.t()},
                        (x, y) -> new long[] {x[0] + 1, Math.max(x[1], y[1])});
                    firstRxOffset.computeIfAbsent(ev.c(), k -> new TreeMap<>()).putIfAbsent(s, ev.num("o"));
                }
                case "ap" -> aps.computeIfAbsent((int) ev.num("s"), k -> new ArrayList<>())
                    .add(new Ap(ev.c(), ev.t(), ev.num("bt"), ev.num("o"), ev.num("q")));
                case "store" -> lastStored.computeIfAbsent(ev.c(), k -> new TreeMap<>()).put((int) ev.num("s"), ev.num("o"));
                case "conf" -> {
                    for (long q = ev.num("from"); q <= ev.num("to"); q++) {
                        confirmed.add(q);
                    }
                }
                case "unk" -> unknown += ev.num("to") - ev.num("from") + 1;
                case "cut", "kill", "heal", "restart", "note" -> harness.add(ev);
                case "halt", "thread-died", "joined", "stopping" -> events.computeIfAbsent(ev.c(), k -> new ArrayList<>())
                    .add(ev.e() + "@" + ev.t() + (ev.kv().containsKey("err") ? " " + ev.kv().get("err") : ""));
                default -> { }
            }
        }
        harness.sort(Comparator.comparingLong(Ev::t));
        long t0 = harness.isEmpty() ? 0 : harness.get(0).t();
        out.append("consumers: ").append(consumers).append('\n');
        events.forEach((c, l) -> out.append("events ").append(c).append(": ").append(l).append('\n'));
        out.append("confirmed seqs: ").append(confirmed.size()).append(", unknown (publisher saw an error): ").append(unknown).append('\n');

        // Initial owner of each partition: the consumer that received first.
        StringBuilder owners = new StringBuilder();
        for (int p = 0; p < partitions; p++) {
            Map<String, Long> f = firstRx.getOrDefault(p, Map.of());
            String first = f.entrySet().stream().min(Map.Entry.comparingByValue()).map(Map.Entry::getKey).orElse("-");
            owners.append(p).append(':').append(first).append(' ');
        }
        out.append("first receiver by partition: ").append(owners.toString().trim()).append('\n');

        // Cuts and kills.
        for (Ev h : harness) {
            if (!h.e().equals("cut") && !h.e().equals("kill")) {
                continue;
            }
            String x = h.c();
            long tc = h.t();
            out.append(String.format("%n%s of %s at t=%d%n", h.e(), x, tc));
            out.append("partition | previous owner rx | takeover by | takeover after (ms) | owner rx after | owner applies after | owner applies after takeover | last owner apply after takeover (ms)\n");
            List<Long> latencies = new ArrayList<>();
            long staleTotal = 0;
            for (int p = 0; p < partitions; p++) {
                Map<String, long[]> rx = rxTimes.getOrDefault(p, Map.of());
                if (!rx.containsKey(x) || firstRx.get(p).get(x) > tc) {
                    continue;
                }
                long take = Long.MAX_VALUE;
                String taker = "-";
                for (Ev ev : all) {
                    if (ev.e().equals("rx") && ev.num("s") == p && !ev.c().equals(x) && ev.t() > tc && ev.t() < take) {
                        take = ev.t();
                        taker = ev.c();
                    }
                }
                final long takeF = take;
                int pp = p;
                long rxAfter = all.stream().filter(e -> e.e().equals("rx") && e.num("s") == pp && e.c().equals(x) && e.t() > tc).count();
                List<Ap> mine = aps.getOrDefault(p, List.of()).stream().filter(ap -> ap.c().equals(x) && ap.t() > tc).toList();
                long stale = mine.stream().filter(ap -> ap.t() > takeF).count();
                long lastStale = mine.stream().filter(ap -> ap.t() > takeF).mapToLong(ap -> ap.t() - takeF).max().orElse(0);
                staleTotal += stale;
                if (take != Long.MAX_VALUE) {
                    latencies.add(take - tc);
                }
                out.append(String.format("%d | yes | %s | %s | %d | %d | %d | %d%n", p, taker, take == Long.MAX_VALUE ? "none" : Long.toString(take - tc),
                    rxAfter, mine.size(), stale, lastStale));
            }
            if (!latencies.isEmpty()) {
                out.append(String.format("takeover after: min %d ms, max %d ms, partitions taken over %d%n",
                    latencies.stream().mapToLong(Long::longValue).min().getAsLong(),
                    latencies.stream().mapToLong(Long::longValue).max().getAsLong(), latencies.size()));
            } else {
                out.append("no partition was taken over\n");
            }
            out.append("applies by ").append(x).append(" after another consumer had begun receiving the same partition: ").append(staleTotal).append('\n');
        }

        // Applies in the same partition by different consumers, in time.
        out.append("\nper partition: applies, extra applies of a seq, older seq applied after a newer one, overlapping batches of different consumers, skipped, not yet applied\n");
        long totalExtra = 0;
        long totalInversions = 0;
        long totalOverlaps = 0;
        long totalOverlapMs = 0;
        long totalSkipped = 0;
        long totalPending = 0;
        for (int p = 0; p < partitions; p++) {
            List<Ap> list = new ArrayList<>(aps.getOrDefault(p, List.of()));
            list.sort(Comparator.comparingLong(Ap::t).thenComparingLong(Ap::o));
            Map<Long, Integer> times = new HashMap<>();
            long max = -1;
            long inversions = 0;
            for (Ap ap : list) {
                times.merge(ap.q(), 1, Integer::sum);
                if (ap.q() < max) {
                    inversions++;
                }
                max = Math.max(max, ap.q());
            }
            long extra = times.values().stream().mapToLong(n -> n - 1).sum();
            // Distinct batches by consumer.
            Set<String> seen = new HashSet<>();
            List<long[]> spans = new ArrayList<>();
            List<String> who = new ArrayList<>();
            for (Ap ap : list) {
                if (seen.add(ap.c() + "/" + ap.bt() + "/" + ap.t())) {
                    spans.add(new long[] {ap.bt(), ap.t()});
                    who.add(ap.c());
                }
            }
            long overlaps = 0;
            long overlapMs = 0;
            for (int i = 0; i < spans.size(); i++) {
                for (int j = i + 1; j < spans.size(); j++) {
                    if (!who.get(i).equals(who.get(j))) {
                        long o = Math.min(spans.get(i)[1], spans.get(j)[1]) - Math.max(spans.get(i)[0], spans.get(j)[0]);
                        if (o > 0) {
                            overlaps++;
                            overlapMs += o;
                        }
                    }
                }
            }
            long skipped = 0;
            long pending = 0;
            for (long q : confirmed) {
                if (q % partitions == p && !times.containsKey(q)) {
                    if (q < max) {
                        skipped++;
                    } else {
                        pending++;
                    }
                }
            }
            totalExtra += extra;
            totalInversions += inversions;
            totalOverlaps += overlaps;
            totalOverlapMs += overlapMs;
            totalSkipped += skipped;
            totalPending += pending;
            out.append(String.format("%d | %d | %d | %d | %d (%d ms) | %d | %d%n", p, list.size(), extra, inversions, overlaps, overlapMs, skipped, pending));
        }
        out.append(String.format("total | extra applies %d | older after newer %d | overlapping batches of different consumers %d (%d ms) | confirmed but skipped %d | confirmed, not yet applied at the end %d%n",
            totalExtra, totalInversions, totalOverlaps, totalOverlapMs, totalSkipped, totalPending));

        // Resume points of a second incarnation.
        if (!resume.isEmpty()) {
            String[] pair = resume.split(",");
            out.append(String.format("%nresume of %s after %s%n", pair[1], pair[0]));
            out.append("partition | last offset stored by first | first offset received by second | offsets between | seqs applied by both\n");
            for (int p = 0; p < partitions; p++) {
                Long stored = lastStored.getOrDefault(pair[0], Map.of()).get(p);
                Long first = firstRxOffset.getOrDefault(pair[1], Map.of()).get(p);
                final int pp = p;
                Set<Long> a1 = new HashSet<>();
                aps.getOrDefault(p, List.of()).stream().filter(ap -> ap.c().equals(pair[0])).forEach(ap -> a1.add(ap.q()));
                long both = aps.getOrDefault(pp, List.of()).stream().filter(ap -> ap.c().equals(pair[1]) && a1.contains(ap.q())).map(Ap::q).distinct().count();
                out.append(String.format("%d | %s | %s | %s | %d%n", p, stored, first, stored == null || first == null ? "-" : Long.toString(first - stored - 1), both));
            }
        }
        // Relative timeline of the harness.
        for (Ev h : harness) {
            out.append(String.format("harness %s %s at +%.1f s %s%n", h.e(), h.c(), (h.t() - t0) / 1000.0, h.kv().getOrDefault("msg", "")));
        }
        String text = out.toString();
        PrintStream stdout = new PrintStream(System.out, true, StandardCharsets.UTF_8);
        stdout.print(text);
        if (a.map().containsKey("out")) {
            try {
                Files.writeString(Path.of(a.str("out", "")), text, StandardCharsets.UTF_8);
            } catch (IOException e) {
                throw new IllegalStateException(e);
            }
        }
    }

    /** The flat objects Log writes. */
    static Ev parse(String line) {
        Map<String, String> kv = new HashMap<>();
        int i = 1;
        int n = line.length() - 1;
        while (i < n) {
            int ks = line.indexOf('"', i) + 1;
            int ke = line.indexOf('"', ks);
            String key = line.substring(ks, ke);
            i = ke + 2;
            String value;
            if (line.charAt(i) == '"') {
                StringBuilder b = new StringBuilder();
                i++;
                while (line.charAt(i) != '"') {
                    if (line.charAt(i) == '\\') {
                        i++;
                    }
                    b.append(line.charAt(i++));
                }
                i++;
                value = b.toString();
            } else {
                int end = i;
                while (end < n && line.charAt(end) != ',') {
                    end++;
                }
                value = line.substring(i, end);
                i = end;
            }
            kv.put(key, value);
            i++;
        }
        return new Ev(Long.parseLong(kv.getOrDefault("t", "0")), kv.getOrDefault("c", "?"), kv.getOrDefault("e", "?"), kv);
    }
}
