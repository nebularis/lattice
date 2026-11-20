// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTimeoutPreemptively;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.AlreadyClosedException;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.ShutdownSignalException;
import com.rabbitmq.stream.Consumer;
import com.rabbitmq.stream.Message;
import com.rabbitmq.stream.MessageHandler;
import com.rabbitmq.stream.Properties;
import com.rabbitmq.stream.StreamException;
import java.net.ConnectException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.function.BooleanSupplier;
import java.util.function.Supplier;
import org.apache.jena.atlas.web.HttpException;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.sparql.engine.http.QueryExceptionHTTP;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.store.Maintenance;
import org.nebularis.lattice.studio.store.StudioOperations;
import org.nebularis.lattice.studio.store.StudioStore;
import org.nebularis.lattice.studio.writes.Codec;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Reply;
import org.nebularis.lattice.studio.writes.Writer;

class StreamWriterTest {
    @Test
    void aReplyToKeptAsAnAmqp10AddressNamesItsQueue() {
        // As RabbitMQ 4.4 stores the service's reply_to in the stream, observed on the live stack.
        assertEquals("amq.rabbitmq.reply-to.g1h2AA5yZXBseUA0MjM1NTc4MAAAA4EAAAAAauDz0A==.LqwAPs8fRHKo/CMG+E+NJw==",
            StreamWriter.queue("/queues/amq.rabbitmq.reply-to.g1h2AA5yZXBseUA0MjM1NTc4MAAAA4EAAAAAauDz0A%3D%3D.LqwAPs8fRHKo%2FCMG%2BE%2BNJw%3D%3D"));
        assertEquals("plain", StreamWriter.queue("plain"));
        assertNull(StreamWriter.queue(null));
    }

    /**
     * MSA-F1, MSAI9-06. A message received but waiting for the next batch is not applied, so no offset at or past it may be
     * stored. The fake context behaves as the stream client's super-stream context does in 1.12.0: its storeOffset() also
     * stores, for every other partition the consumer holds, the offset that partition last received.
     */
    @Test
    void aBatchStoresTheOffsetItAppliedOnEachPartitionAndNothingItHasOnlyReceived() throws InterruptedException {
        Partitions partitions = new Partitions();
        List<StreamWriter.Item> batch = List.of(
            partitions.received("lattice.studio.writes-0", 10),
            partitions.received("lattice.studio.writes-0", 11),
            partitions.received("lattice.studio.writes-1", 5));
        // Received after the batch was taken, so applied by the next batch, or by the next writer if this one stops.
        partitions.received("lattice.studio.writes-0", 12);
        partitions.received("lattice.studio.writes-2", 40);

        List<String> replied = new ArrayList<>();
        StreamWriter.apply(batch, items -> items.stream().map(i -> Reply.ok(1)).toList(),
            (item, reply) -> replied.add(item.context().stream() + "@" + item.context().offset()), partitions.stored::put);

        assertEquals(Map.of("lattice.studio.writes-0", 11L, "lattice.studio.writes-1", 5L), partitions.stored);
        assertEquals(List.of("lattice.studio.writes-0@10", "lattice.studio.writes-0@11", "lattice.studio.writes-1@5"), replied);
        assertEquals(3, partitions.processed);
    }

    /**
     * MSA-F2, MSAI11-05. A batch the store refuses as malformed is not retried for ever. Its commands are tried one at a time,
     * so the one the store refuses is answered as refused and the others apply, and the partitions move on.
     */
    @Test
    void aBatchTheStoreRefusesIsAnsweredCommandByCommandAndThePartitionMovesOn() {
        Partitions partitions = new Partitions();
        StreamWriter.Item first = partitions.received("lattice.studio.writes-0", 1);
        StreamWriter.Item poison = partitions.received("lattice.studio.writes-0", 2);
        StreamWriter.Item last = partitions.received("lattice.studio.writes-0", 3);
        List<Integer> sizes = new ArrayList<>();
        List<Integer> statuses = new ArrayList<>();
        assertTimeoutPreemptively(Duration.ofSeconds(10), () -> StreamWriter.apply(List.of(first, poison, last), items -> {
            sizes.add(items.size());
            if (items.contains(poison)) {
                throw new HttpException(400, "Bad Request", "Parse error");
            }
            return items.stream().map(i -> Reply.ok(1)).toList();
        }, (item, reply) -> statuses.add(reply.status()), partitions.stored::put, Duration.ofMillis(10)));
        assertEquals(List.of(200, 400, 200), statuses);
        assertEquals(List.of(3, 1, 1, 1), sizes);
        assertEquals(Map.of("lattice.studio.writes-0", 3L), partitions.stored);
    }

    /** MSA-F2. A store that cannot be reached is retried with the whole batch, which holds its partitions in order. */
    @Test
    void aStoreThatCannotBeReachedIsRetriedWithTheWholeBatch() throws InterruptedException {
        Partitions partitions = new Partitions();
        List<StreamWriter.Item> batch = List.of(partitions.received("lattice.studio.writes-0", 1), partitions.received("lattice.studio.writes-1", 1));
        int[] calls = {0};
        List<Integer> statuses = new ArrayList<>();
        StreamWriter.apply(batch, items -> {
            if (++calls[0] < 3) {
                throw calls[0] == 1 ? new HttpException("connect", new ConnectException("refused")) : new HttpException(503);
            }
            return items.stream().map(i -> Reply.ok(1)).toList();
        }, (item, reply) -> statuses.add(reply.status()), partitions.stored::put, Duration.ofMillis(10));
        assertEquals(3, calls[0]);
        assertEquals(List.of(200, 200), statuses);
    }

    /** MSA-F2. Which failures are retried: those that say nothing about the request, as against a request the store refused. */
    @Test
    void onlyAFailureThatSaysNothingAboutTheRequestIsRetried() {
        assertTrue(StreamWriter.retried(new HttpException("connect", new ConnectException("refused"))));
        assertTrue(StreamWriter.retried(new RuntimeException(new java.io.UncheckedIOException(new java.io.IOException("reset")))));
        assertTrue(StreamWriter.retried(new HttpException(503)));
        assertTrue(StreamWriter.retried(new HttpException(500)));
        assertTrue(StreamWriter.retried(new HttpException(401)));
        assertTrue(StreamWriter.retried(new HttpException(404)));
        assertTrue(StreamWriter.retried(new HttpException(429)));
        assertTrue(StreamWriter.retried(new QueryExceptionHTTP(502)));
        assertFalse(StreamWriter.retried(new HttpException(400)));
        assertFalse(StreamWriter.retried(new HttpException(413)));
        assertFalse(StreamWriter.retried(new QueryExceptionHTTP(400)));
        assertFalse(StreamWriter.retried(new IllegalArgumentException("a payload with a blank node")));
    }

    /**
     * MSA-F8. A failure of the writer's own code is not retried, as MSA-F2 has it, and is answered as the writer's fault, a 500,
     * not as a request the store refused, a 400. The other commands of the batch apply and the partition moves on.
     */
    @Test
    void aFailureOfTheWritersOwnCodeIsAnsweredAsTheWritersFaultAndThePartitionMovesOn() {
        Partitions partitions = new Partitions();
        StreamWriter.Item first = partitions.received("lattice.studio.writes-0", 1);
        StreamWriter.Item failing = partitions.received("lattice.studio.writes-0", 2);
        StreamWriter.Item refused = partitions.received("lattice.studio.writes-0", 3);
        List<Reply> replies = new ArrayList<>();
        assertTimeoutPreemptively(Duration.ofSeconds(10), () -> StreamWriter.apply(List.of(first, failing, refused), items -> {
            if (items.contains(failing)) {
                throw new IllegalStateException("a bug in the writer");
            }
            if (items.contains(refused)) {
                throw new HttpException(400, "Bad Request", "Parse error");
            }
            return items.stream().map(i -> Reply.ok(1)).toList();
        }, (item, reply) -> replies.add(reply), partitions.stored::put, Duration.ofMillis(10)));
        assertEquals(List.of(200, 500, 400), replies.stream().map(Reply::status).toList());
        assertEquals("the writer failed on this write, which was not applied", replies.get(1).message(), "the exception's text stays in the log (MSA-F12)");
        assertEquals(Map.of("lattice.studio.writes-0", 3L), partitions.stored);
    }

    private static final String WS = "00000000-0000-4000-8000-000000000001";
    private static final Instant AT = Instant.parse("2026-11-19T10:00:00Z");

    /**
     * MSA-F12, MSAF8-01. A store's refusal and a failure of the writer's own code are answered with a fixed message that
     * names the command's id, and the exception's text, which can name an endpoint, a query or a class, goes to the log
     * with that id. A message the writer's own checks author for a refusal is answered as it is.
     */
    @Test
    void aRefusalOrAFailureIsAnsweredWithAFixedMessageAndTheExceptionGoesToTheLogWithTheCommandsId() {
        Partitions partitions = new Partitions();
        String refusedId = "00000000-0000-4000-8000-000000000012";
        String failingId = "00000000-0000-4000-8000-000000000013";
        StreamWriter.Item first = partitions.received(P0, 1, message(Map.of("id", "00000000-0000-4000-8000-000000000011"), new byte[0], null));
        StreamWriter.Item refused = partitions.received(P0, 2, message(Map.of("id", refusedId), new byte[0], null));
        StreamWriter.Item failing = partitions.received(P0, 3, message(Map.of("id", failingId), new byte[0], null));
        StreamWriter.Item authored = partitions.received(P0, 4, message(Map.of("id", "00000000-0000-4000-8000-000000000014"), new byte[0], null));
        StreamWriter.Item unnamed = partitions.received(P0, 5, message(Map.of("id", "not an id <script>"), new byte[0], null));
        String storeText = "Parse error in the update sent to http://store.internal:3030/studio/update";
        String codeText = "org.nebularis.lattice.studio.writes.Writer$Batch failed on SELECT ?row WHERE { GRAPH <urn:lattice:studio:rows> }";
        List<Reply> replies = new ArrayList<>();
        String log = logged(() -> assertTimeoutPreemptively(Duration.ofSeconds(10), () -> StreamWriter.apply(
            List.of(first, refused, failing, authored, unnamed), items -> {
                if (items.contains(refused)) {
                    throw new HttpException(400, "Bad Request", storeText);
                }
                if (items.contains(failing) || items.contains(unnamed)) {
                    throw new IllegalStateException(codeText);
                }
                return items.stream().map(i -> i == authored ? Reply.refused("the document was deleted, so its id cannot be used again") : Reply.ok(1)).toList();
            }, (item, reply) -> replies.add(reply), partitions.stored::put, Duration.ofMillis(10))));
        assertEquals(List.of(200, 400, 500, 400, 500), replies.stream().map(Reply::status).toList());
        assertEquals("the store refused this write, which was not applied. The writer's log holds the reason under command " + refusedId,
            replies.get(1).message());
        assertEquals("the writer failed on this write, which was not applied. The writer's log holds the reason under command " + failingId,
            replies.get(2).message());
        assertEquals("the document was deleted, so its id cannot be used again", replies.get(3).message(), "a message our own code authors stays");
        assertEquals("the writer failed on this write, which was not applied", replies.get(4).message(), "an id that is not an id is not echoed");
        assertEquals(Map.of(P0, 5L), partitions.stored);
        assertTrue(log.lines().anyMatch(line -> line.contains(refusedId)), "the log names the refused command: " + log);
        assertTrue(log.lines().anyMatch(line -> line.contains(failingId)), "the log names the failed command: " + log);
        assertTrue(log.contains(storeText) && log.contains(codeText), "the exceptions' text is in the log: " + log);
    }

    private static final StudioOperations OPS = StudioOperations.load(Path.of(System.getProperty("studio.assets"), "persistence"), 1L);
    private static final Maintenance MAINTENANCE = Maintenance.load(Path.of(System.getProperty("studio.assets"), "maintenance"));

    /**
     * MSA-F12. A message that is not a command, since its N-Quads do not parse, its body is not binary or its command is
     * unknown, is the request's fault: it is answered 400 where it carries a reply-to, the others of its batch apply, and
     * the partition moves on. The batch runs through the decoding the production writer uses, and a real {@link Writer}.
     */
    @Test
    void aMessageThatIsNotACommandIsAnswered400WhereItHasAReplyToAndThePartitionMovesOn() {
        Writer writer = new Writer(StudioStore.inMemory(), OPS, MAINTENANCE, Clock.fixed(AT, ZoneOffset.UTC));
        Map<String, Reply> published = new ConcurrentHashMap<>();
        Channel channel = channel(published);
        Partitions partitions = new Partitions();
        Command create = Command.create(WS, "Plan", AT, null, ModelFactory.createDefaultModel());
        Command garbled = Command.save(WS, "surface", 0, AT, ModelFactory.createDefaultModel());
        Command unreadable = Command.save(WS, "surface", 0, AT, ModelFactory.createDefaultModel());
        Command save = Command.save(WS, "surface", 0, AT, ModelFactory.createDefaultModel());
        List<StreamWriter.Item> batch = List.of(
            partitions.received(P0, 1, message(Codec.headers(create), Codec.body(create), "/queues/q1")),
            partitions.received(P0, 2, message(Codec.headers(garbled), "<urn:a> <urn:b> this is not N-Quads".getBytes(StandardCharsets.UTF_8), "/queues/q2")),
            // As the stream client's message answers for a body that is not AMQP data.
            partitions.received(P0, 3, message(Codec.headers(unreadable), () -> {
                throw new IllegalStateException("Body cannot by returned as array of bytes. Use #getBody() to get native representation.");
            }, "/queues/q3")),
            partitions.received(P0, 4, message(Map.of("command", "frobnicate"), new byte[0], null)),
            partitions.received(P0, 5, message(Codec.headers(save), Codec.body(save), "/queues/q5")));
        List<Reply> answered = new ArrayList<>();
        assertTimeoutPreemptively(Duration.ofSeconds(10), () -> StreamWriter.apply(batch, StreamWriter.decoding(writer::apply), (item, reply) -> {
            answered.add(reply);
            StreamWriter.reply(channel, item.message(), reply);
        }, partitions.stored::put, Duration.ofMillis(10)));
        assertEquals(List.of(200, 400, 400, 400, 200), answered.stream().map(Reply::status).toList());
        assertEquals(Map.of("q1", 200, "q2", 400, "q3", 400, "q5", 200),
            published.entrySet().stream().collect(java.util.stream.Collectors.toMap(Map.Entry::getKey, e -> e.getValue().status())),
            "each message with a reply-to is answered, and the one without is not");
        assertEquals("the message is not a studio command, so it was not applied. The writer's log holds the reason under command " + garbled.id(),
            published.get("q2").message());
        assertEquals("the message is not a studio command, so it was not applied. The writer's log holds the reason under command " + unreadable.id(),
            published.get("q3").message());
        assertEquals("the message is not a studio command, so it was not applied", answered.get(3).message());
        assertEquals(Map.of(P0, 5L), partitions.stored);
        assertEquals(5, partitions.processed);
    }

    /** A message as the stream client gives one, with its application properties, body and reply-to. */
    private static Message message(Map<String, Object> headers, byte[] body, String replyTo) {
        return message(headers, () -> body, replyTo);
    }

    private static Message message(Map<String, Object> headers, Supplier<byte[]> body, String replyTo) {
        Properties properties = proxy(Properties.class, (method, args) -> switch (method) {
            case "getReplyTo" -> replyTo;
            case "getCorrelationIdAsString" -> headers.get("id") == null ? null : headers.get("id").toString();
            default -> null;
        });
        return proxy(Message.class, (method, args) -> switch (method) {
            case "getApplicationProperties" -> headers;
            case "getBodyAsBinary" -> body.get();
            case "getProperties" -> properties;
            default -> null;
        });
    }

    /** A reply channel that keeps each reply published, by the queue it was sent to. */
    private static Channel channel(Map<String, Reply> published) {
        return proxy(Channel.class, (method, args) -> {
            if (method.equals("basicPublish") && args.length == 4) {
                published.put((String) args[1], Codec.reply(((AMQP.BasicProperties) args[2]).getHeaders()));
            }
            return null;
        });
    }

    @SuppressWarnings("unchecked")
    private static <T> T proxy(Class<T> type, java.util.function.BiFunction<String, Object[], Object> answer) {
        return (T) java.lang.reflect.Proxy.newProxyInstance(type.getClassLoader(), new Class<?>[] {type}, (self, method, args) -> switch (method.getName()) {
            case "equals" -> self == args[0];
            case "hashCode" -> System.identityHashCode(self);
            case "toString" -> type.getSimpleName();
            default -> answer.apply(method.getName(), args == null ? new Object[0] : args);
        });
    }

    /** What {@code run} writes to the log, which slf4j-simple writes to standard error. */
    private static String logged(Runnable run) {
        java.io.PrintStream err = System.err;
        java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
        System.setErr(new java.io.PrintStream(out, true, StandardCharsets.UTF_8));
        try {
            run.run();
        } finally {
            System.setErr(err);
        }
        return out.toString(StandardCharsets.UTF_8);
    }

    private static final String P0 = "lattice.studio.writes-0";

    /**
     * MSA-F10, MSAF2-01. A reply sent on a closed channel throws, and the writer's thread goes on: the partition's next write
     * is applied by the same writer, and its offset is stored.
     */
    @Test
    void aReplyThatCannotBeSentIsLoggedAndThePartitionsNextWriteIsApplied() {
        Partitions partitions = new Partitions();
        BlockingQueue<StreamWriter.Item> waiting = new LinkedBlockingQueue<>();
        List<Long> applied = new CopyOnWriteArrayList<>();
        List<Long> replied = new CopyOnWriteArrayList<>();
        Map<String, Long> broker = new ConcurrentHashMap<>();
        FakeConsumer consumer = new FakeConsumer();
        StreamWriter writer = new StreamWriter(waiting, consumer, items -> {
            items.forEach(i -> applied.add(i.context().offset()));
            return items.stream().map(i -> Reply.ok(1)).toList();
        }, (item, reply) -> {
            replied.add(item.context().offset());
            if (item.context().offset() == 1) {
                throw new AlreadyClosedException(new ShutdownSignalException(false, false, null, null));
            }
        }, broker::put, Duration.ofMillis(10));
        try {
            waiting.add(partitions.received(P0, 1));
            await(() -> replied.contains(1L), "the first write was not replied to");
            waiting.add(partitions.received(P0, 2));
            await(() -> applied.contains(2L), "the partition's next write was not applied after a reply could not be sent");
            await(() -> Long.valueOf(2).equals(broker.get(P0)), "the next write's offset was not stored");
            assertTrue(writer.threadAlive(), "the writer's thread ended");
            assertEquals(Map.of(P0, 2L), writer.storedOffsets());
            assertFalse(consumer.closed);
        } finally {
            writer.close();
        }
    }

    /**
     * MSA-F10, MSAF2-01. An offset that cannot be stored is logged and the writer goes on: the partition's next write is applied
     * by the same writer, which stores the later offset.
     */
    @Test
    void anOffsetThatCannotBeStoredIsLoggedAndThePartitionsNextWriteIsApplied() {
        Partitions partitions = new Partitions();
        BlockingQueue<StreamWriter.Item> waiting = new LinkedBlockingQueue<>();
        List<Long> applied = new CopyOnWriteArrayList<>();
        List<Long> attempted = new CopyOnWriteArrayList<>();
        Map<String, Long> broker = new ConcurrentHashMap<>();
        FakeConsumer consumer = new FakeConsumer();
        StreamWriter writer = new StreamWriter(waiting, consumer, items -> {
            items.forEach(i -> applied.add(i.context().offset()));
            return items.stream().map(i -> Reply.ok(1)).toList();
        }, (item, reply) -> { }, (stream, offset) -> {
            attempted.add(offset);
            if (offset == 1) {
                throw new StreamException("the offset could not be stored");
            }
            broker.put(stream, offset);
        }, Duration.ofMillis(10));
        try {
            waiting.add(partitions.received(P0, 1));
            await(() -> attempted.contains(1L), "the first write's offset was not tried");
            waiting.add(partitions.received(P0, 2));
            await(() -> applied.contains(2L), "the partition's next write was not applied after an offset could not be stored");
            await(() -> Long.valueOf(2).equals(broker.get(P0)), "the next write's offset was not stored");
            assertTrue(writer.threadAlive(), "the writer's thread ended");
            assertEquals(Map.of(P0, 2L), writer.storedOffsets());
            assertFalse(consumer.closed);
        } finally {
            writer.close();
        }
    }

    /**
     * MSA-F10, MSAF2-01. Anything else that escapes the loop, here a writer that answers fewer replies than it was given,
     * ends the thread and closes the consumer, so the group gives the partition to another member, which applies its next
     * write. The writer's state shows its thread is not alive.
     */
    @Test
    void aFailureThatEscapesTheLoopClosesTheConsumerSoTheGroupMovesThePartition() {
        Partitions partitions = new Partitions();
        BlockingQueue<StreamWriter.Item> waiting = new LinkedBlockingQueue<>();
        FakeConsumer consumer = new FakeConsumer();
        StreamWriter writer = new StreamWriter(waiting, consumer, items -> List.of(), (item, reply) -> { }, (stream, offset) -> { },
            Duration.ofMillis(10));
        try {
            waiting.add(partitions.received(P0, 1));
            await(() -> !writer.threadAlive(), "the writer's thread did not end");
            assertTrue(consumer.closed, "the consumer was not closed, so the writer keeps its partitions with no thread applying");
            assertFalse(writer.threadAlive());
        } finally {
            writer.close();
        }
    }

    private static void await(BooleanSupplier condition, String message) {
        long deadline = System.nanoTime() + Duration.ofSeconds(5).toNanos();
        while (!condition.getAsBoolean()) {
            if (System.nanoTime() > deadline) {
                fail(message);
            }
            try {
                Thread.sleep(10);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                fail(message);
            }
        }
    }

    /** A member of the group: closing it leaves the group, which gives its partitions to another member. */
    private static final class FakeConsumer implements Consumer {
        volatile boolean closed;

        @Override
        public void store(long offset) {
        }

        @Override
        public void close() {
            closed = true;
        }

        @Override
        public long storedOffset() {
            return 0;
        }
    }

    /** The offsets the broker holds, and what the consumer has received, shared by every context of one consumer. */
    private static final class Partitions {
        final Map<String, Long> lastReceived = new HashMap<>();
        final Map<String, Long> stored = new HashMap<>();
        int processed;

        StreamWriter.Item received(String stream, long offset) {
            return received(stream, offset, null);
        }

        StreamWriter.Item received(String stream, long offset, Message message) {
            lastReceived.merge(stream, offset, Math::max);
            return new StreamWriter.Item(new Context(this, stream, offset), message);
        }
    }

    private record Context(Partitions partitions, String stream, long offset) implements MessageHandler.Context {
        @Override
        public void storeOffset() {
            partitions.lastReceived.forEach((s, o) -> partitions.stored.put(s, s.equals(stream) ? offset : o));
        }

        @Override
        public void processed() {
            partitions.processed++;
        }

        @Override
        public long timestamp() {
            return 0;
        }

        @Override
        public long committedChunkId() {
            return 0;
        }

        @Override
        public Consumer consumer() {
            return null;
        }
    }
}
