// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTimeoutPreemptively;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

import com.rabbitmq.client.AlreadyClosedException;
import com.rabbitmq.client.ShutdownSignalException;
import com.rabbitmq.stream.Consumer;
import com.rabbitmq.stream.MessageHandler;
import com.rabbitmq.stream.StreamException;
import java.net.ConnectException;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.function.BooleanSupplier;
import org.apache.jena.atlas.web.HttpException;
import org.apache.jena.sparql.engine.http.QueryExceptionHTTP;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.writes.Reply;

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
        assertTrue(replies.get(1).message().contains("a bug in the writer"), replies.get(1).message());
        assertEquals(Map.of("lattice.studio.writes-0", 3L), partitions.stored);
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
            lastReceived.merge(stream, offset, Math::max);
            return new StreamWriter.Item(new Context(this, stream, offset), null);
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
