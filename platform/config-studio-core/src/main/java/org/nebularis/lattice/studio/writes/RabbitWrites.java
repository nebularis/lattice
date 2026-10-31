// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writes;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import org.nebularis.lattice.studio.jobs.Topology;
import org.nebularis.lattice.studio.store.StudioStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Publishes each write to its workspace's partition of the writes super stream, with a broker confirm, and waits for the
 * writer's reply on RabbitMQ's direct reply-to, so a save answers the browser at once. A stream keeps a write until a
 * writer reaches it, however long that takes, so a write the writer has not answered in time may still apply. The store
 * then settles it: a receipt for the command means it applied, and without one the answer is that it has not yet.
 */
public final class RabbitWrites implements Writes {
    private static final Logger LOG = LoggerFactory.getLogger(RabbitWrites.class);
    private static final String REPLY_TO = "amq.rabbitmq.reply-to";
    private static final long CONFIRM_TIMEOUT_MILLIS = 5_000;

    private final Channel channel;
    private final StudioStore store;
    private final Duration timeout;
    private final ConcurrentHashMap<String, CompletableFuture<Reply>> pending = new ConcurrentHashMap<>();

    public RabbitWrites(Connection connection, StudioStore store, Duration timeout) {
        this.store = store;
        this.timeout = timeout;
        try {
            this.channel = connection.createChannel();
            Topology.declare(channel);
            channel.confirmSelect();
            // Direct reply-to needs its consumer on the publishing channel, with automatic acknowledgement.
            channel.basicConsume(REPLY_TO, true, (tag, delivery) -> {
                CompletableFuture<Reply> waiting = pending.remove(String.valueOf(delivery.getProperties().getCorrelationId()));
                if (waiting != null) {
                    waiting.complete(Codec.reply(delivery.getProperties().getHeaders()));
                }
            }, tag -> { });
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    @Override
    public Reply send(Command command) {
        CompletableFuture<Reply> reply = new CompletableFuture<>();
        pending.put(command.id(), reply);
        AMQP.BasicProperties properties = new AMQP.BasicProperties.Builder()
            .contentType(Codec.CONTENT_TYPE).deliveryMode(2).correlationId(command.id()).replyTo(REPLY_TO)
            .headers(Codec.headers(command)).build();
        try {
            // A channel is not thread safe, so publishes and their confirms take turns.
            synchronized (channel) {
                channel.basicPublish(Topology.WRITES, Topology.routingKey(command.routingId()), true, properties, Codec.body(command));
                channel.waitForConfirmsOrDie(CONFIRM_TIMEOUT_MILLIS);
            }
            return reply.get(timeout.toMillis(), TimeUnit.MILLISECONDS);
        } catch (TimeoutException e) {
            Map<String, Long> applied = store.receipts(List.of(command.id()));
            if (applied.containsKey(command.id())) {
                return Reply.ok(applied.get(command.id()));
            }
            LOG.warn("no writer answered a {} of workspace {} within {}", command.type().wire, command.workspace(), timeout);
            return new Reply(503, 0, "the write is not applied yet, and may still apply: no store writer answered");
        } catch (IOException | ExecutionException e) {
            LOG.error("handing a write to the writers failed", e);
            return new Reply(503, 0, "the write could not be handed to a writer");
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return new Reply(503, 0, "interrupted");
        } finally {
            pending.remove(command.id());
        }
    }
}
