// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

import com.rabbitmq.client.Channel;
import java.io.IOException;
import java.util.Map;

/** The AMQP topology of `contracts/config-studio/amqp-topology.json`, as declared constants. */
public final class Topology {
    public static final String EXCHANGE = "lattice.studio";
    public static final String DEAD_LETTER_EXCHANGE = "lattice.studio.dlx";
    public static final String JOBS_QUEUE = "lattice.studio.jobs";
    public static final String JOBS_ROUTING_KEY = "lattice.studio.jobs";
    public static final String DEAD_QUEUE = "lattice.studio.dead";
    public static final String DEAD_ROUTING_KEY = "#";

    private Topology() {
    }

    /** Idempotent, so the service and the worker may both declare it. */
    public static void declare(Channel channel) throws IOException {
        channel.exchangeDeclare(EXCHANGE, "topic", true);
        channel.exchangeDeclare(DEAD_LETTER_EXCHANGE, "topic", true);
        channel.queueDeclare(JOBS_QUEUE, true, false, false, Map.of("x-dead-letter-exchange", DEAD_LETTER_EXCHANGE));
        channel.queueBind(JOBS_QUEUE, EXCHANGE, JOBS_ROUTING_KEY);
        channel.queueDeclare(DEAD_QUEUE, true, false, false, Map.of());
        channel.queueBind(DEAD_QUEUE, DEAD_LETTER_EXCHANGE, DEAD_ROUTING_KEY);
    }
}
