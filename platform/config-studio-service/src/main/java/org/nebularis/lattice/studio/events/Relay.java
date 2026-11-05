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
 * Carries the studio's events to the browser tabs over the broker's MQTT (PM-Q20 (d)). It hands every event on the studio's exchange
 * to the notifier, reads each tab's watch frames from {@code studio/u/<name>/<tab>/watch}, and publishes what the notifier allows to
 * the tab's {@code .../events}. Each service instance has queues of its own, named by the broker and gone with its connection, so an
 * event published while no instance listens is dropped, and a tab that misses it reads its job again after its fallback wait.
 */
public final class Relay {
    private static final Logger LOG = LoggerFactory.getLogger(Relay.class);
    private static final String PREFIX = "cloudEvents:";
    private static final AMQP.BasicProperties JSON = new AMQP.BasicProperties.Builder().contentType("application/json").build();

    private Relay() {
    }

    public static void start(Connection connection, Notifier notifier) throws IOException {
        Channel events = connection.createChannel();
        events.exchangeDeclare(StudioEvents.EXCHANGE, "topic", true);
        String queue = events.queueDeclare().getQueue();
        events.queueBind(queue, StudioEvents.EXCHANGE, "org.nebularis.lattice.studio.#");
        events.basicConsume(queue, true, (tag, delivery) -> {
            CloudEvent event = read(delivery.getProperties(), delivery.getBody());
            if (event == null) {
                LOG.warn("an event on {} lacked a CloudEvents attribute, and was dropped", StudioEvents.EXCHANGE);
            } else {
                notifier.deliver(event);
            }
        }, tag -> { });

        Channel publish = connection.createChannel();
        Channel watches = connection.createChannel();
        String watched = watches.queueDeclare().getQueue();
        watches.queueBind(watched, BrokerAuth.EXCHANGE, "studio.u.*.*.watch");
        watches.basicConsume(watched, true, (tag, delivery) -> {
            String[] key = delivery.getEnvelope().getRoutingKey().split("\\.");
            String user = key.length == 5 ? BrokerAuth.principal(key[2]) : null;
            if (user == null || !BrokerAuth.isTab(key[3])) {
                return;
            }
            String to = "studio.u." + key[2] + "." + key[3] + ".events";
            notifier.message(user, key[3], text -> {
                try {
                    // A channel is not safe for concurrent publishes, and both consumers' threads publish on this one.
                    synchronized (publish) {
                        publish.basicPublish(BrokerAuth.EXCHANGE, to, JSON, text.getBytes(StandardCharsets.UTF_8));
                    }
                } catch (IOException e) {
                    throw new java.io.UncheckedIOException(e);
                }
            }, new String(delivery.getBody(), StandardCharsets.UTF_8));
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
