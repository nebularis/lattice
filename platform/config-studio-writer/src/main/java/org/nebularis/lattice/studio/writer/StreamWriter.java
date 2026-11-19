// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writer;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.stream.Consumer;
import com.rabbitmq.stream.ConsumerFlowStrategy;
import com.rabbitmq.stream.Environment;
import com.rabbitmq.stream.Message;
import com.rabbitmq.stream.MessageHandler;
import com.rabbitmq.stream.OffsetSpecification;
import java.io.IOException;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.function.BiConsumer;
import java.util.function.Function;
import org.apache.jena.atlas.web.HttpException;
import org.apache.jena.sparql.engine.http.QueryExceptionHTTP;
import org.nebularis.lattice.studio.jobs.Topology;
import org.nebularis.lattice.studio.writes.Codec;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Reply;
import org.nebularis.lattice.studio.writes.Writer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * One writer instance: a single-active-consumer member of the group {@link #GROUP} on the writes super stream. RabbitMQ
 * gives each partition to one live member and moves it when a member joins or leaves, so the partitions spread across
 * the instances that run. Messages are handed to one thread, which takes the first that waits and every other already
 * waiting, up to {@link #MAX_BATCH}, without waiting for more, and applies them in one request (TSD-44). It replies to
 * each, then stores, for each partition the batch touched, the offset of the last message it applied, so a member that
 * takes a partition over resumes after the last batch applied and skips nothing received but not yet applied. A write
 * delivered again after a failover is answered from its receipt and not applied twice. A store that cannot be reached
 * holds the batch until it can, and a write the store refuses is answered as refused, so it never holds its partition. A write
 * the writer's own code fails on is answered as the writer's fault, a 500, and does not hold its partition either. A reply
 * that cannot be sent or an offset that cannot be stored is logged and the writer goes on. Anything else that ends the
 * thread closes the consumer, so the writer leaves its group and never holds a partition with no thread applying.
 */
public final class StreamWriter implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(StreamWriter.class);
    static final String GROUP = "lattice.studio.writers";
    static final int MAX_BATCH = 64;
    private static final Duration STORE_RETRY = Duration.ofSeconds(1);

    record Item(MessageHandler.Context context, Message message) {
    }

    /** Where the offset of the last message applied on a partition is stored, under the group's reference. */
    interface Offsets {
        void store(String stream, long offset);
    }

    /** The offsets of the group {@link #GROUP}, stored by stream and offset through the environment. */
    static Offsets offsets(Environment environment) {
        return (stream, offset) -> environment.storeOffset(GROUP, stream, offset);
    }

    private final BlockingQueue<Item> waiting;
    private final Consumer consumer;
    private final Thread thread;
    private final Map<String, Long> stored = new ConcurrentHashMap<>();

    public StreamWriter(Environment environment, Channel replies, Writer writer) {
        this(new LinkedBlockingQueue<>(), environment, replies, writer);
        LOG.info("store writer joined {} on {}, {} partitions", GROUP, Topology.WRITES, Topology.PARTITIONS);
    }

    private StreamWriter(BlockingQueue<Item> waiting, Environment environment, Channel replies, Writer writer) {
        this(waiting, environment.consumerBuilder()
            .superStream(Topology.WRITES)
            .singleActiveConsumer()
            .name(GROUP)
            .offset(OffsetSpecification.first())
            .manualTrackingStrategy().builder()
            // Credit is given back as messages are processed, so a slow store holds the stream back rather than memory.
            .flow().strategy(ConsumerFlowStrategy.creditWhenHalfMessagesProcessed()).builder()
            .messageHandler((context, message) -> waiting.add(new Item(context, message)))
            .build(),
            items -> writer.apply(decode(items)), (item, reply) -> reply(replies, item.message(), reply), offsets(environment), STORE_RETRY);
    }

    /** A writer whose consumer fills {@code waiting}, so a test drives the thread with fakes. */
    StreamWriter(BlockingQueue<Item> waiting, Consumer consumer, Function<List<Item>, List<Reply>> writer, BiConsumer<Item, Reply> replies,
        Offsets offsets, Duration retry) {
        this.waiting = waiting;
        this.consumer = consumer;
        Offsets recorded = (stream, offset) -> {
            offsets.store(stream, offset);
            stored.put(stream, offset);
        };
        this.thread = Thread.ofPlatform().name("store-writer").start(() -> run(writer, replies, recorded, retry));
    }

    /** Whether the thread that applies this writer's batches is running. */
    public boolean threadAlive() {
        return thread.isAlive();
    }

    /** For each partition, the offset this writer last stored for it, since it started. */
    public Map<String, Long> storedOffsets() {
        return Map.copyOf(stored);
    }

    /**
     * Applies batches until the writer is closed. A failure that escapes a batch ends the thread, so the consumer is closed
     * and the group gives its partitions to another member, rather than holding them with no thread applying (MSAF2-01).
     */
    private void run(Function<List<Item>, List<Reply>> writer, BiConsumer<Item, Reply> replies, Offsets offsets, Duration retry) {
        List<Item> batch = new ArrayList<>();
        try {
            while (!Thread.currentThread().isInterrupted()) {
                batch.add(waiting.take());
                waiting.drainTo(batch, MAX_BATCH - 1);
                apply(batch, writer, replies, offsets, retry);
                batch.clear();
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        } catch (RuntimeException | Error e) {
            LOG.error("the store writer stops and leaves {}, so another member takes its partitions", GROUP, e);
            try {
                consumer.close();
            } catch (RuntimeException closing) {
                LOG.error("the stopped store writer could not close its consumer", closing);
            }
        }
    }

    private static List<Command> decode(List<Item> batch) {
        List<Command> commands = new ArrayList<>(batch.size());
        for (Item item : batch) {
            commands.add(Codec.decode(item.message().getApplicationProperties(), item.message().getBodyAsBinary()));
        }
        return commands;
    }

    static void apply(List<Item> batch, Function<List<Item>, List<Reply>> writer, BiConsumer<Item, Reply> replies, Offsets offsets)
        throws InterruptedException {
        apply(batch, writer, replies, offsets, STORE_RETRY);
    }

    /** The statuses that say the request itself is at fault, so sending it again cannot succeed. */
    private static final java.util.Set<Integer> REFUSED = java.util.Set.of(400, 413, 414, 415, 422);

    /**
     * Whether a failure says nothing about the request, so the same request may succeed later: the store could not be
     * reached, answered with no status, failed on its side, or refused the writer itself (its credentials or its dataset)
     * rather than the request. A status of {@link #REFUSED} is the request's fault, and a failure of the writer's own code
     * fails the same way for the same input, so neither is retried, and each is answered (MSAI11-05, MSA-F8).
     */
    static boolean retried(RuntimeException e) {
        for (Throwable t = e; t != null; t = t.getCause()) {
            if (t instanceof java.io.IOException || t instanceof java.io.UncheckedIOException) {
                return true;
            }
            int status = status(t);
            if (status != Integer.MIN_VALUE) {
                return !REFUSED.contains(status);
            }
        }
        return false;
    }

    /** Whether a failure that is not retried came from the store, which answered with a status, rather than from the writer's own code. */
    static boolean fromStore(RuntimeException e) {
        for (Throwable t = e; t != null; t = t.getCause()) {
            if (status(t) != Integer.MIN_VALUE) {
                return true;
            }
        }
        return false;
    }

    private static int status(Throwable t) {
        return t instanceof HttpException h ? h.getStatusCode()
            : t instanceof QueryExceptionHTTP q ? q.getStatusCode() : Integer.MIN_VALUE;
    }

    static void apply(List<Item> batch, Function<List<Item>, List<Reply>> writer, BiConsumer<Item, Reply> replies, Offsets offsets,
        Duration retry) throws InterruptedException {
        List<Reply> answers = answer(batch, writer, retry);
        Map<String, Long> last = new HashMap<>();
        for (int i = 0; i < batch.size(); i++) {
            Item item = batch.get(i);
            Reply reply = answers.get(i);
            if (reply.status() == 400 || reply.status() == 500) {
                LOG.warn("answered a write on {} at offset {} with {}: {}", item.context().stream(), item.context().offset(), reply.status(), reply.message());
            }
            try {
                replies.accept(item, reply);
            } catch (RuntimeException e) {
                // A lost reply costs only a wait: its sender reads the receipt (MSAF2-01).
                LOG.warn("the reply to the write on {} at offset {} could not be sent, and its sender will read the receipt",
                    item.context().stream(), item.context().offset(), e);
            }
            last.merge(item.context().stream(), item.context().offset(), Math::max);
        }
        // Through the environment, by stream and offset. A super-stream context's storeOffset() also stores, for every
        // other partition the consumer holds, the offset it last received, which may be waiting unapplied (MSAI9-06).
        last.forEach((stream, offset) -> {
            try {
                offsets.store(stream, offset);
            } catch (RuntimeException e) {
                // The next batch stores a later offset, and a write delivered again is answered from its receipt (MSAF2-01).
                LOG.warn("the offset {} on {} could not be stored, and the writer goes on", offset, stream, e);
            }
        });
        batch.forEach(item -> item.context().processed());
    }

    /**
     * The replies to a batch, applied in one request. The request runs as one transaction, so a failure applied none of it.
     * A store that cannot be reached is tried again with the whole batch, holding its partitions in order, and receipts make
     * that safe. A batch the store refuses is tried one command at a time in its order, so only the command at fault is
     * answered as refused and the partition moves on.
     */
    private static List<Reply> answer(List<Item> batch, Function<List<Item>, List<Reply>> writer, Duration retry)
        throws InterruptedException {
        while (true) {
            try {
                return writer.apply(batch);
            } catch (RuntimeException e) {
                if (retried(e)) {
                    LOG.error("a batch of {} write(s) could not be applied, and is retried in {}", batch.size(), retry, e);
                    Thread.sleep(retry.toMillis());
                } else if (batch.size() > 1) {
                    LOG.warn("a batch of {} write(s) was refused, so each is tried alone", batch.size(), e);
                    List<Reply> answers = new ArrayList<>(batch.size());
                    for (Item item : batch) {
                        answers.addAll(answer(List.of(item), writer, retry));
                    }
                    return answers;
                } else if (fromStore(e)) {
                    LOG.error("the write on {} at offset {} was refused, and is answered as refused", batch.get(0).context().stream(),
                        batch.get(0).context().offset(), e);
                    return List.of(Reply.refused("the store refused the write: " + e.getMessage()));
                } else {
                    // The same input fails the same way, so retrying would hold the partition. It is the writer's fault (MSA-F8).
                    LOG.error("the writer failed on the write on {} at offset {}, and answers it as its own fault", batch.get(0).context().stream(),
                        batch.get(0).context().offset(), e);
                    return List.of(Reply.failed("the writer failed on this write, which was not applied: " + e.getMessage()));
                }
            }
        }
    }

    /** A write sent by the service carries a reply-to, and the worker's carry none. A lost reply costs only a wait. */
    private static void reply(Channel replies, Message message, Reply reply) {
        String replyTo = queue(message.getProperties() == null ? null : message.getProperties().getReplyTo());
        if (replyTo == null) {
            return;
        }
        AMQP.BasicProperties props = new AMQP.BasicProperties.Builder()
            .correlationId(message.getProperties().getCorrelationIdAsString()).headers(Codec.reply(reply)).build();
        try {
            synchronized (replies) {
                replies.basicPublish("", replyTo, props, new byte[0]);
            }
        } catch (IOException e) {
            LOG.warn("a reply could not be sent, and its sender will read the receipt", e);
        }
    }

    /**
     * The queue a reply-to names. RabbitMQ keeps an AMQP 0.9.1 {@code reply_to} in a stream as an AMQP 1.0 address,
     * {@code /queues/} and the percent-encoded queue name, so the name is decoded from it.
     */
    static String queue(String replyTo) {
        if (replyTo == null || !replyTo.startsWith("/queues/")) {
            return replyTo;
        }
        return java.net.URLDecoder.decode(replyTo.substring("/queues/".length()).replace("+", "%2B"), java.nio.charset.StandardCharsets.UTF_8);
    }

    @Override
    public void close() {
        thread.interrupt();
        consumer.close();
    }
}
