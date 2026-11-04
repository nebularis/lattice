// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Publishes job IRIs to RabbitMQ, persistent and confirmed by the broker, and asks the transforms worker for a run on a
 * channel of its own, whose replies come on RabbitMQ's direct reply-to.
 */
public final class RabbitJobBus implements JobBus {
    private static final Logger LOG = LoggerFactory.getLogger(RabbitJobBus.class);
    private static final long CONFIRM_TIMEOUT_MILLIS = 5_000;
    private static final AMQP.BasicProperties PROPERTIES = new AMQP.BasicProperties.Builder()
        .contentType("text/plain").deliveryMode(2).build();

    private static final String REPLY_TO = "amq.rabbitmq.reply-to";

    private final Connection connection;
    private final Channel channel;
    private final Channel rpc;
    private final ConcurrentHashMap<String, CompletableFuture<byte[]>> pending = new ConcurrentHashMap<>();

    public RabbitJobBus(Connection connection) {
        this.connection = connection;
        try {
            this.channel = connection.createChannel();
            Topology.declare(channel);
            channel.confirmSelect();
            rpc = connection.createChannel();
            // Direct reply-to needs its consumer on the publishing channel, with automatic acknowledgement.
            rpc.basicConsume(REPLY_TO, true, (tag, delivery) -> {
                CompletableFuture<byte[]> waiting = pending.remove(String.valueOf(delivery.getProperties().getCorrelationId()));
                if (waiting != null) {
                    waiting.complete(delivery.getBody());
                }
            }, tag -> { });
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    /** A channel is not thread safe, so publishes take turns. */
    @Override
    public synchronized void publish(String jobIri) throws IOException, InterruptedException, TimeoutException {
        channel.basicPublish(Topology.EXCHANGE, Topology.JOBS_ROUTING_KEY, PROPERTIES,
            jobIri.getBytes(StandardCharsets.UTF_8));
        channel.waitForConfirmsOrDie(CONFIRM_TIMEOUT_MILLIS);
    }

    @Override
    public byte[] transform(String id, String jobIri, String mediaType, byte[] sample, Duration timeout) throws Exception {
        CompletableFuture<byte[]> reply = new CompletableFuture<>();
        pending.put(id, reply);
        // A request expires when the service stops waiting for it, so a worker that is down leaves nothing behind.
        AMQP.BasicProperties properties = new AMQP.BasicProperties.Builder().contentType(mediaType).correlationId(id)
            .replyTo(REPLY_TO).expiration(Long.toString(timeout.toMillis())).headers(Map.of("job", jobIri)).build();
        try {
            synchronized (rpc) {
                rpc.basicPublish(Topology.EXCHANGE, Topology.TRANSFORMS_ROUTING_KEY, properties, sample);
            }
            return reply.get(timeout.toMillis(), TimeUnit.MILLISECONDS);
        } catch (TimeoutException e) {
            return null;
        } finally {
            pending.remove(id);
        }
    }

    @Override
    public void close() {
        try {
            connection.close();
        } catch (IOException e) {
            LOG.debug("closing the RabbitMQ connection failed", e);
        }
    }
}
