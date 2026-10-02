// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.messaging;

import com.rabbitmq.client.Channel;
import java.io.IOException;
import java.util.Map;

/** The AMQP topology of `contracts/authoring/amqp-topology.json`, as declared constants. */
public final class Topology {
    public static final String EXCHANGE = "lattice.authoring";
    public static final String DEAD_LETTER_EXCHANGE = "lattice.authoring.dlx";
    public static final String REQUESTED_QUEUE = "lattice.authoring.analysis.requested";
    public static final String REQUESTED_ROUTING_KEY = "lattice.authoring.analysis.requested";
    public static final String COMPLETED_QUEUE = "lattice.authoring.analysis.completed";
    public static final String COMPLETED_ROUTING_KEY = "lattice.authoring.analysis.completed";
    public static final String DEAD_QUEUE = "lattice.authoring.dead";
    public static final String DEAD_ROUTING_KEY = "#";

    private Topology() {
    }

    /** Idempotent: declares the exchanges, queues and bindings, safe to call more than once. */
    public static void declare(Channel channel) throws IOException {
        channel.exchangeDeclare(EXCHANGE, "topic", true);
        channel.exchangeDeclare(DEAD_LETTER_EXCHANGE, "topic", true);

        declareDeadLetteredQueue(channel, REQUESTED_QUEUE, REQUESTED_ROUTING_KEY);
        declareDeadLetteredQueue(channel, COMPLETED_QUEUE, COMPLETED_ROUTING_KEY);

        channel.queueDeclare(DEAD_QUEUE, true, false, false, Map.of());
        channel.queueBind(DEAD_QUEUE, DEAD_LETTER_EXCHANGE, DEAD_ROUTING_KEY);
    }

    private static void declareDeadLetteredQueue(Channel channel, String queue, String routingKey) throws IOException {
        channel.queueDeclare(queue, true, false, false, Map.of("x-dead-letter-exchange", DEAD_LETTER_EXCHANGE));
        channel.queueBind(queue, EXCHANGE, routingKey);
    }
}
