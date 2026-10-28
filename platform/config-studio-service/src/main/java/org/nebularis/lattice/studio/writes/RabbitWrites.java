// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writes;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.time.Duration;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import org.nebularis.lattice.studio.jobs.Topology;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Publishes each write to the consistent-hash exchange, keyed by its workspace, and waits for the writer's reply on
 * RabbitMQ's direct reply-to, so a save answers the browser as it did when the service wrote the store itself.
 */
public final class RabbitWrites implements Writes {
    private static final Logger LOG = LoggerFactory.getLogger(RabbitWrites.class);
    private static final String REPLY_TO = "amq.rabbitmq.reply-to";

    private final Channel channel;
    private final Duration timeout;
    private final ConcurrentHashMap<String, CompletableFuture<Reply>> pending = new ConcurrentHashMap<>();

    public RabbitWrites(Connection connection, Duration timeout) {
        this.timeout = timeout;
        try {
            this.channel = connection.createChannel();
            Topology.declare(channel);
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
        String id = UUID.randomUUID().toString();
        CompletableFuture<Reply> reply = new CompletableFuture<>();
        pending.put(id, reply);
        AMQP.BasicProperties properties = new AMQP.BasicProperties.Builder()
            .contentType(Codec.CONTENT_TYPE).deliveryMode(2).correlationId(id).replyTo(REPLY_TO)
            // A write nobody applied in time is dropped rather than applied after the caller was told it failed.
            .expiration(Long.toString(timeout.toMillis()))
            .headers(Codec.headers(command)).build();
        try {
            synchronized (channel) {
                channel.basicPublish(Topology.WRITES_EXCHANGE, command.workspace(), properties, Codec.body(command));
            }
            return reply.get(timeout.toMillis(), TimeUnit.MILLISECONDS);
        } catch (TimeoutException e) {
            LOG.warn("no writer answered a {} of workspace {} within {}", command.type().wire, command.workspace(), timeout);
            return new Reply(503, 0, "no store writer answered");
        } catch (IOException | ExecutionException e) {
            LOG.error("handing a write to the writers failed", e);
            return new Reply(503, 0, "the write could not be handed to a writer");
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return new Reply(503, 0, "interrupted");
        } finally {
            pending.remove(id);
        }
    }
}
