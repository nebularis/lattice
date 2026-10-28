// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.TimeoutException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Publishes job IRIs to RabbitMQ, persistent and confirmed by the broker. */
public final class RabbitJobBus implements JobBus {
    private static final Logger LOG = LoggerFactory.getLogger(RabbitJobBus.class);
    private static final long CONFIRM_TIMEOUT_MILLIS = 5_000;
    private static final AMQP.BasicProperties PROPERTIES = new AMQP.BasicProperties.Builder()
        .contentType("text/plain").deliveryMode(2).build();

    private final Connection connection;
    private final Channel channel;

    public RabbitJobBus(Connection connection) {
        this.connection = connection;
        try {
            this.channel = connection.createChannel();
            Topology.declare(channel);
            channel.confirmSelect();
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
    public void close() {
        try {
            connection.close();
        } catch (IOException e) {
            LOG.debug("closing the RabbitMQ connection failed", e);
        }
    }
}
