// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import java.io.IOException;
import java.time.Duration;
import java.util.concurrent.TimeoutException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Connections to RabbitMQ, named so the broker shows which component holds each. */
public final class Amqp {
    private static final Logger LOG = LoggerFactory.getLogger(Amqp.class);
    private static final int CONNECT_ATTEMPTS = 15;
    private static final Duration CONNECT_INTERVAL = Duration.ofSeconds(2);

    private Amqp() {
    }

    /** Connects, retrying for half a minute while the broker starts. */
    public static Connection connect(String uri, String name) {
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
                return factory.newConnection(name);
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

}
