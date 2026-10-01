// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.messaging;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import com.fasterxml.jackson.databind.JsonNode;
import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import com.rabbitmq.client.GetResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.TimeoutException;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.authoring.json.Json;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testcontainers.utility.DockerImageName;

/** S5-03, S5-04: {@link RabbitMqAnalysisBus} against a real RabbitMQ container. */
class RabbitMqAnalysisBusIT {
    private static GenericContainer<?> rabbit;
    private static String uri;

    @BeforeAll
    static void startRabbit() {
        rabbit = new GenericContainer<>(DockerImageName.parse("rabbitmq:3.13-management-alpine"))
            .withEnv("RABBITMQ_DEFAULT_USER", "lattice")
            .withEnv("RABBITMQ_DEFAULT_PASS", "lattice")
            .withExposedPorts(5672)
            .waitingFor(Wait.forLogMessage(".*Server startup complete.*\\n", 1));
        rabbit.start();
        uri = "amqp://lattice:lattice@" + rabbit.getHost() + ":" + rabbit.getMappedPort(5672);
    }

    @AfterAll
    static void stopRabbit() {
        rabbit.stop();
    }

    /** S5-03: declaring twice does not error, and a published request carries the four properties. */
    @Test
    void declaresIdempotentlyAndPublishesWithTheFourProperties() throws Exception {
        try (RabbitMqAnalysisBus bus = new RabbitMqAnalysisBus(uri)) {
            RabbitMqAnalysisBus redeclared = new RabbitMqAnalysisBus(uri);
            redeclared.close();

            JsonNode request = Json.MAPPER.readTree(
                "{\"jobId\": \"00000009-0000-4000-8000-000000000001\"}");
            bus.publish(request);

            try (Connection connection = adminConnection(); Channel channel = connection.createChannel()) {
                GetResponse response = pollForMessage(channel, Topology.REQUESTED_QUEUE);
                assertNotNull(response, "expected a message on " + Topology.REQUESTED_QUEUE);
                AMQP.BasicProperties properties = response.getProps();
                assertEquals("application/json", properties.getContentType());
                assertEquals("00000009-0000-4000-8000-000000000001", properties.getMessageId());
                assertEquals("00000009-0000-4000-8000-000000000001", properties.getCorrelationId());
                assertEquals(Integer.valueOf(2), properties.getDeliveryMode());
                assertEquals(request, Json.MAPPER.readTree(response.getBody()));
            }
        }
    }

    /** S5-04: a valid result reaches the handler, a malformed one is dead-lettered. */
    @Test
    void deadLettersAMalformedResultButHandlesAValidOne() throws Exception {
        try (RabbitMqAnalysisBus bus = new RabbitMqAnalysisBus(uri)) {
            List<JsonNode> received = new CopyOnWriteArrayList<>();
            bus.onResult(received::add);

            JsonNode valid = Json.MAPPER.readTree("{\"jobId\": \"00000009-0000-4000-8000-000000000002\"}");
            publishRaw(Topology.COMPLETED_ROUTING_KEY, Json.MAPPER.writeValueAsBytes(valid));
            publishRaw(Topology.COMPLETED_ROUTING_KEY, "not json".getBytes(StandardCharsets.UTF_8));

            waitUntil(() -> received.size() == 1);
            assertEquals(List.of(valid), received);

            try (Connection connection = adminConnection(); Channel channel = connection.createChannel()) {
                GetResponse dead = pollForMessage(channel, Topology.DEAD_QUEUE);
                assertNotNull(dead, "expected the malformed message to land on " + Topology.DEAD_QUEUE);
                assertEquals("not json", new String(dead.getBody(), StandardCharsets.UTF_8));
            }
        }
    }

    private static Connection adminConnection() throws IOException, TimeoutException {
        ConnectionFactory factory = new ConnectionFactory();
        try {
            factory.setUri(uri);
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
        return factory.newConnection();
    }

    private static void publishRaw(String routingKey, byte[] body) throws Exception {
        try (Connection connection = adminConnection(); Channel channel = connection.createChannel()) {
            channel.basicPublish(Topology.EXCHANGE, routingKey, null, body);
        }
    }

    private static GetResponse pollForMessage(Channel channel, String queue) throws IOException, InterruptedException {
        for (int attempt = 0; attempt < 50; attempt++) {
            GetResponse response = channel.basicGet(queue, true);
            if (response != null) {
                return response;
            }
            Thread.sleep(100);
        }
        return null;
    }

    private static void waitUntil(java.util.function.BooleanSupplier condition) throws InterruptedException, TimeoutException {
        for (int attempt = 0; attempt < 100; attempt++) {
            if (condition.getAsBoolean()) {
                return;
            }
            Thread.sleep(100);
        }
        throw new TimeoutException("condition not met within 10 seconds");
    }
}
