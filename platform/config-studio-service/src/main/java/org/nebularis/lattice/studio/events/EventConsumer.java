// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.events;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import java.io.IOException;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.nebularis.lattice.outbox.CloudEvent;
import org.nebularis.lattice.studio.writes.StudioEvents;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Hands every studio event on the exchange to the notifier. Each service instance has a queue of its own, named by the broker and gone
 * with its connection, so each instance's sessions hear every event, and an event published while no instance listens is dropped,
 * which a session that reads the job again on reconnecting does not need.
 */
public final class EventConsumer {
    private static final Logger LOG = LoggerFactory.getLogger(EventConsumer.class);
    private static final String PREFIX = "cloudEvents:";

    private EventConsumer() {
    }

    public static void start(Connection connection, Notifier notifier) throws IOException {
        Channel channel = connection.createChannel();
        channel.exchangeDeclare(StudioEvents.EXCHANGE, "topic", true);
        String queue = channel.queueDeclare().getQueue();
        channel.queueBind(queue, StudioEvents.EXCHANGE, "org.nebularis.lattice.studio.#");
        channel.basicConsume(queue, true, (tag, delivery) -> {
            CloudEvent event = read(delivery.getProperties(), delivery.getBody());
            if (event == null) {
                LOG.warn("an event on {} lacked a CloudEvents attribute, and was dropped", StudioEvents.EXCHANGE);
            } else {
                notifier.deliver(event);
            }
        }, tag -> { });
    }

    /** The event a message carries in the CloudEvents AMQP binding's binary mode, or null when an attribute is missing. */
    public static CloudEvent read(AMQP.BasicProperties properties, byte[] body) {
        Map<String, Object> h = properties.getHeaders();
        if (h == null) {
            return null;
        }
        String id = text(h, "id");
        String source = text(h, "source");
        String type = text(h, "type");
        String subject = text(h, "subject");
        String time = text(h, "time");
        if (id == null || source == null || type == null || subject == null || time == null) {
            return null;
        }
        try {
            return new CloudEvent(UUID.fromString(id), URI.create(source), type, subject, Instant.parse(time), Map.of(),
                new String(body, StandardCharsets.UTF_8));
        } catch (RuntimeException e) {
            return null;
        }
    }

    private static String text(Map<String, Object> headers, String name) {
        Object v = headers.get(PREFIX + name);
        return v == null ? null : v.toString();
    }
}
