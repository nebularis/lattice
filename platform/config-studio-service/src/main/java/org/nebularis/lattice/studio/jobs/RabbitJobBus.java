// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.TimeoutException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Publishes job IRIs to RabbitMQ, persistent and confirmed by the broker. */
public final class RabbitJobBus implements JobBus {
    private static final Logger LOG = LoggerFactory.getLogger(RabbitJobBus.class);
    private static final int CONNECT_ATTEMPTS = 15;
    private static final Duration CONNECT_INTERVAL = Duration.ofSeconds(2);
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

    /** Connects, retrying for half a minute while the broker starts. */
    public static Connection connect(String uri) {
        ConnectionFactory factory = new ConnectionFactory();
        try {
            factory.setUri(uri);
        } catch (Exception e) {
            throw new IllegalArgumentException("LATTICE_AMQP_URI is not a valid AMQP URI");
        }
        factory.setAutomaticRecoveryEnabled(true);
        Exception last = null;
        for (int attempt = 1; attempt <= CONNECT_ATTEMPTS; attempt++) {
            try {
                return factory.newConnection("config-studio-service");
            } catch (IOException | TimeoutException e) {
                last = e;
                LOG.warn("RabbitMQ is not reachable yet (attempt {} of {})", attempt, CONNECT_ATTEMPTS);
            }
            try {
                Thread.sleep(CONNECT_INTERVAL.toMillis());
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException("interrupted while connecting to RabbitMQ", interrupted);
            }
        }
        throw new IllegalStateException("could not connect to RabbitMQ", last);
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
