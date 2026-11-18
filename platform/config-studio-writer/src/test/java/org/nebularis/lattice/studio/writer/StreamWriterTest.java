// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTimeoutPreemptively;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.rabbitmq.stream.Consumer;
import com.rabbitmq.stream.MessageHandler;
import java.net.ConnectException;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
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
