// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.probes.msa;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.stream.Environment;
import com.rabbitmq.stream.EnvironmentBuilder;
import com.rabbitmq.stream.Message;
import com.rabbitmq.stream.OffsetSpecification;
import com.rabbitmq.stream.Producer;
import com.rabbitmq.stream.ProducerBuilder;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicLong;

/** Publisher deduplication of the stream protocol with a named producer, and the same stream read back and counted. */
final class Dedup {
    private Dedup() {
    }

    private static EnvironmentBuilder environment(Main.Args a) {
        List<String> uris = a.list("uris", "rabbitmq-stream://guest:guest@msa-i9-rmq1:5552,rabbitmq-stream://guest:guest@msa-i9-rmq2:5552,rabbitmq-stream://guest:guest@msa-i9-rmq3:5552");
        return Environment.builder().uris(uris);
    }

    /** A super stream producer, routed by the binding key held in the message's {@code k} property. */
    static void publishMain(Main.Args a) throws Exception {
        String superStream = a.str("super", "msa-i9-dedup");
        int partitions = a.num("partitions", 4);
        String name = a.str("name", "");
        long from = a.lng("from", 0);
        long to = a.lng("to", 999);
        long step = a.lng("step", 1);
        long delayMs = a.lng("delay-ms", 0);
        AtomicLong confirmed = new AtomicLong();
        AtomicLong failed = new AtomicLong();
        try (Environment env = environment(a).build()) {
            ProducerBuilder pb = env.producerBuilder().superStream(superStream)
                .routing(m -> m.getApplicationProperties().get("k").toString()).key().producerBuilder();
            if (!name.isEmpty()) {
                pb.name(name).confirmTimeout(Duration.ZERO);
            }
            try (Producer producer = pb.build()) {
                if (!name.isEmpty()) {
                    Log.ev("last-publishing-id", "name", name, "value", producer.getLastPublishingId());
                    if (a.flag("use-last")) {
                        from = producer.getLastPublishingId() + 1;
                        Log.ev("resume-from", "id", from);
                    }
                }
                Log.ev("dedup-start", "name", name, "from", from, "to", to, "step", step);
                for (long seq = from; seq <= to; seq += step) {
                    final long s = seq;
                    var builder = name.isEmpty() ? producer.messageBuilder() : producer.messageBuilder().publishingId(seq);
                    Message m = builder.applicationProperties().entry("k", Long.toString(seq % partitions)).entry("seq", Long.toString(seq))
                        .messageBuilder().addData(Long.toString(seq).getBytes(StandardCharsets.UTF_8)).build();
                    producer.send(m, status -> {
                        if (status.isConfirmed()) {
                            confirmed.incrementAndGet();
                            Log.ev("cf", "q", s);
                        } else {
                            failed.incrementAndGet();
                            Log.ev("nf", "q", s, "code", status.getCode());
                        }
                    });
                    if (delayMs > 0) {
                        Thread.sleep(delayMs);
                    }
                }
                long deadline = System.currentTimeMillis() + 30_000;
                while (confirmed.get() + failed.get() < (to - from) / step + 1 && System.currentTimeMillis() < deadline) {
                    Thread.sleep(100);
                }
                Log.ev("dedup-done", "name", name, "confirmed", confirmed.get(), "failed", failed.get());
            }
        }
    }

    /** Reads every partition from the first offset, with no name and so no tracking, until it is idle, and counts each sequence number. */
    static void countMain(Main.Args a) throws Exception {
        String superStream = a.str("super", "msa-i9-dedup");
        long idleMs = a.lng("idle-s", 6) * 1000;
        long from = a.lng("from", 0);
        long to = a.lng("to", -1);
        Map<Long, Integer> seen = new TreeMap<>();
        AtomicLong last = new AtomicLong(System.currentTimeMillis());
        try (Environment env = environment(a).build()) {
            var consumer = env.consumerBuilder().superStream(superStream).offset(OffsetSpecification.first())
                .messageHandler((ctx, m) -> {
                    synchronized (seen) {
                        seen.merge(Sac.seqOf(m), 1, Integer::sum);
                    }
                    last.set(System.currentTimeMillis());
                }).build();
            while (System.currentTimeMillis() - last.get() < idleMs) {
                Thread.sleep(250);
            }
            consumer.close();
        }
        long total = 0;
        long dups = 0;
        StringBuilder dupList = new StringBuilder();
        StringBuilder ranges = new StringBuilder();
        long runStart = Long.MIN_VALUE;
        long prev = Long.MIN_VALUE;
        for (Map.Entry<Long, Integer> e : seen.entrySet()) {
            total += e.getValue();
            if (e.getValue() > 1) {
                dups += e.getValue() - 1;
                if (dupList.length() < 200) {
                    dupList.append(e.getKey()).append('x').append(e.getValue()).append(' ');
                }
            }
            long k = e.getKey();
            if (runStart == Long.MIN_VALUE) {
                runStart = k;
            } else if (k != prev + 1) {
                ranges.append(runStart).append('-').append(prev).append(',');
                runStart = k;
            }
            prev = k;
        }
        if (runStart != Long.MIN_VALUE) {
            ranges.append(runStart).append('-').append(prev);
        }
        long missing = 0;
        if (to >= from) {
            for (long s = from; s <= to; s++) {
                if (!seen.containsKey(s)) {
                    missing++;
                }
            }
        }
        Log.ev("count", "super", superStream, "entries", total, "distinct", seen.size(), "extra_copies", dups, "missing_in_range", missing,
            "from", from, "to", to, "duplicated", dupList.toString().trim());
        Log.ev("seen-ranges", "ranges", ranges.toString());
    }

    /** What the studio does, and what a retry of a write does: the same message published twice over AMQP 0.9.1, each confirmed. */
    static void amqpDupMain(Main.Args a) throws Exception {
        String superStream = a.str("super", "msa-i9-dedup");
        int partitions = a.num("partitions", 4);
        int n = a.num("n", 100);
        try (Connection c = Topo.amqp(a.list("amqp", "msa-i9-rmq1"), "msa-i9 amqp-dup"); Channel ch = c.createChannel()) {
            ch.confirmSelect();
            for (int seq = 0; seq < n; seq++) {
                AMQP.BasicProperties props = new AMQP.BasicProperties.Builder().deliveryMode(2).messageId(Integer.toString(seq))
                    .correlationId(Integer.toString(seq)).build();
                for (int attempt = 0; attempt < 2; attempt++) {
                    ch.basicPublish(superStream, Integer.toString(seq % partitions), true, props, Integer.toString(seq).getBytes(StandardCharsets.UTF_8));
                    ch.waitForConfirmsOrDie(5_000);
                }
            }
            Log.ev("amqp-dup-done", "messages", n, "publishes", n * 2);
        }
    }
}
