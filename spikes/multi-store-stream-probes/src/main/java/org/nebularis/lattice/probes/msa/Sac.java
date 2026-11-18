// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.probes.msa;

import com.rabbitmq.stream.Consumer;
import com.rabbitmq.stream.ConsumerFlowStrategy;
import com.rabbitmq.stream.Environment;
import com.rabbitmq.stream.EnvironmentBuilder;
import com.rabbitmq.stream.Message;
import com.rabbitmq.stream.MessageHandler;
import com.rabbitmq.stream.OffsetSpecification;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.atomic.AtomicLong;

/**
 * A copy of the studio's {@code StreamWriter} with the store replaced by a sleep and a log line. Same builder calls, same group
 * name, same batching, and the same order in a batch: apply, then the offset of each stream stored, then {@code processed()}.
 * A failure in the worker is not caught, as in the studio. Three things are added: a log line for each delivery and each
 * apply, a way to stop the process abruptly at a chosen point of a batch, and an optional requested heartbeat.
 */
final class Sac {
    static final String GROUP = "lattice.studio.writers";

    private record Item(MessageHandler.Context context, long seq, int partition) {
    }

    private Sac() {
    }

    static void main(Main.Args a) throws Exception {
        String id = a.str("id", "c?");
        String superStream = a.str("super", "lattice.studio.writes");
        List<String> uris = a.list("uris", "rabbitmq-stream://guest:guest@msa-i9-rmq1:5552");
        int maxBatch = a.num("max-batch", 64);
        long batchMs = a.lng("batch-ms", 0);
        long perMessageMs = a.lng("message-ms", 0);
        int dieAtBatch = a.num("die-at-batch", 0);
        String diePoint = a.str("die-point", "");
        long pauseBeforeHaltMs = a.lng("pause-before-halt-ms", 0);
        boolean storeViaEnvironment = "env".equals(a.str("store-via", "context"));
        BlockingQueue<Item> waiting = new LinkedBlockingQueue<>();
        AtomicLong received = new AtomicLong();
        AtomicLong applied = new AtomicLong();
        Thread.setDefaultUncaughtExceptionHandler((t, e) -> Log.ev("thread-died", "thread", t.getName(), "err", e.toString()));

        EnvironmentBuilder eb = Environment.builder();
        if (uris.size() == 1) {
            eb.uri(uris.get(0));
        } else {
            eb.uris(uris);
        }
        if (a.map().containsKey("heartbeat-s")) {
            eb.requestedHeartbeat(Duration.ofSeconds(a.num("heartbeat-s", 60)));
        }
        Environment environment = eb.build();
        Consumer consumer = environment.consumerBuilder()
            .superStream(superStream)
            .singleActiveConsumer()
            .name(GROUP)
            .offset(OffsetSpecification.first())
            .manualTrackingStrategy().builder()
            .flow().strategy(ConsumerFlowStrategy.creditWhenHalfMessagesProcessed()).builder()
            .subscriptionListener(ctx -> Log.ev("subscribe", "s", ctx.stream(), "spec", String.valueOf(ctx.offsetSpecification())))
            .messageHandler((context, message) -> {
                long seq = seqOf(message);
                int partition = partitionOf(context.stream());
                received.incrementAndGet();
                Log.ev("rx", "s", partition, "o", context.offset(), "q", seq);
                waiting.add(new Item(context, seq, partition));
            })
            .build();
        Log.ev("joined", "group", GROUP, "super", superStream);

        Thread ticker = Thread.ofPlatform().daemon().name("tick").start(() -> {
            while (true) {
                try {
                    Thread.sleep(1_000);
                } catch (InterruptedException e) {
                    return;
                }
                Log.ev("tick", "rx", received.get(), "ap", applied.get(), "waiting", waiting.size());
            }
        });
        Thread worker = Thread.ofPlatform().name("store-writer").start(() -> {
            List<Item> batch = new ArrayList<>();
            int batches = 0;
            while (!Thread.currentThread().isInterrupted()) {
                try {
                    batch.add(waiting.take());
                    waiting.drainTo(batch, maxBatch - 1);
                    if (batches + 1 == dieAtBatch && "before-apply".equals(diePoint)) {
                        Log.ev("halt", "point", diePoint, "batch", batches + 1, "waiting", waiting.size(), "taken", batch.size());
                        Thread.sleep(pauseBeforeHaltMs);
                        Runtime.getRuntime().halt(137);
                    }
                    long begin = System.currentTimeMillis();
                    Thread.sleep(batchMs + perMessageMs * batch.size());
                    batches++;
                    for (Item item : batch) {
                        Log.ev("ap", "s", item.partition(), "o", item.context().offset(), "q", item.seq(), "bt", begin);
                    }
                    applied.addAndGet(batch.size());
                    Map<String, Item> last = new HashMap<>();
                    for (Item item : batch) {
                        last.put(item.context().stream(), item);
                    }
                    if (batches == dieAtBatch && "before-store".equals(diePoint)) {
                        Log.ev("halt", "point", diePoint, "batch", batches);
                        Thread.sleep(pauseBeforeHaltMs);
                        Runtime.getRuntime().halt(137);
                    }
                    for (Item item : last.values()) {
                        if (storeViaEnvironment) {
                            environment.storeOffset(GROUP, item.context().stream(), item.context().offset());
                        } else {
                            item.context().storeOffset();
                        }
                        Log.ev("store", "s", item.partition(), "o", item.context().offset());
                    }
                    if (batches == dieAtBatch && "after-store".equals(diePoint)) {
                        Log.ev("halt", "point", diePoint, "batch", batches);
                        Runtime.getRuntime().halt(137);
                    }
                    batch.forEach(item -> item.context().processed());
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                batch.clear();
            }
        });
        long stopAfter = a.lng("stop-after-s", 0);
        if (stopAfter > 0) {
            Thread.sleep(stopAfter * 1000);
            Log.ev("stopping");
            worker.interrupt();
            ticker.interrupt();
            consumer.close();
            environment.close();
            return;
        }
        worker.join();
        Thread.currentThread().join();
    }

    static long seqOf(Message message) {
        String body = new String(message.getBodyAsBinary(), StandardCharsets.UTF_8);
        int comma = body.indexOf(',');
        return Long.parseLong(comma < 0 ? body : body.substring(0, comma));
    }

    static int partitionOf(String stream) {
        return Integer.parseInt(stream.substring(stream.lastIndexOf('-') + 1));
    }
}
