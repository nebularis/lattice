// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.messaging;

import com.fasterxml.jackson.databind.JsonNode;
import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import com.rabbitmq.client.DeliverCallback;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.time.Duration;
import java.util.concurrent.TimeoutException;
import java.util.function.Consumer;
import org.nebularis.lattice.authoring.json.Json;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** An {@link AnalysisBus} over a real RabbitMQ connection, with automatic recovery on. */
public final class RabbitMqAnalysisBus implements AnalysisBus, AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(RabbitMqAnalysisBus.class);
    private static final int CONNECT_ATTEMPTS = 30;
    private static final Duration CONNECT_INTERVAL = Duration.ofSeconds(2);

    private final Connection connection;
    private final Channel channel;

    public RabbitMqAnalysisBus(String uri) {
        this.connection = connect(uri);
        try {
            this.channel = connection.createChannel();
            Topology.declare(channel);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static Connection connect(String uri) {
        ConnectionFactory factory = new ConnectionFactory();
        try {
            factory.setUri(uri);
        } catch (Exception e) {
            throw new IllegalArgumentException("LATTICE_AMQP_URI is not a valid AMQP URI", e);
        }
        factory.setAutomaticRecoveryEnabled(true);

        Exception lastError = null;
        for (int attempt = 1; attempt <= CONNECT_ATTEMPTS; attempt++) {
            try {
                return factory.newConnection();
            } catch (IOException | TimeoutException e) {
                lastError = e;
            }
            try {
                Thread.sleep(CONNECT_INTERVAL.toMillis());
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException("interrupted while connecting to RabbitMQ", interrupted);
            }
        }
        throw new IllegalStateException("could not connect to RabbitMQ after " + CONNECT_ATTEMPTS + " attempts",
            lastError);
    }

    @Override
    public void publish(JsonNode request) {
        String jobId = request.get("jobId").asText();
        AMQP.BasicProperties properties = new AMQP.BasicProperties.Builder()
            .contentType("application/json")
            .messageId(jobId)
            .correlationId(jobId)
            .deliveryMode(2)
            .type(Topology.REQUESTED_ROUTING_KEY)
            .build();
        try {
            channel.basicPublish(Topology.EXCHANGE, Topology.REQUESTED_ROUTING_KEY, properties,
                Json.MAPPER.writeValueAsBytes(request));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    @Override
    public void onResult(Consumer<JsonNode> handler) {
        DeliverCallback callback = (consumerTag, delivery) -> {
            long deliveryTag = delivery.getEnvelope().getDeliveryTag();
            try {
                JsonNode result = Json.MAPPER.readTree(delivery.getBody());
                handler.accept(result);
                channel.basicAck(deliveryTag, false);
            } catch (RuntimeException | IOException e) {
                LOG.warn("dead-lettering an unprocessable analysis result: {}", e.toString());
                channel.basicNack(deliveryTag, false, false);
            }
        };
        try {
            channel.basicConsume(Topology.COMPLETED_QUEUE, false, callback, consumerTag -> { });
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    @Override
    public boolean ping() {
        return connection.isOpen();
    }

    @Override
    public void close() {
        try {
            channel.close();
        } catch (IOException | TimeoutException ignored) {
            // best effort
        }
        try {
            connection.close();
        } catch (IOException ignored) {
            // best effort
        }
    }
}
