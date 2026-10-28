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
    /** A consistent-hash exchange: a write's routing key, its workspace id, picks one partition queue. */
    public static final String WRITES_EXCHANGE = "lattice.studio.writes";
    public static final String WRITES_EXCHANGE_TYPE = "x-consistent-hash";
    public static final String WRITES_QUEUE_PREFIX = "lattice.studio.writes.";
    /** Fixed by the contract. Changing it moves workspaces between partitions, so drain the queues first. */
    public static final int PARTITIONS = 8;

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
        channel.exchangeDeclare(WRITES_EXCHANGE, WRITES_EXCHANGE_TYPE, true);
        for (int i = 0; i < PARTITIONS; i++) {
            // One active consumer per partition, however many writers consume it, so its writes apply in order.
            channel.queueDeclare(writesQueue(i), true, false, false,
                Map.of("x-dead-letter-exchange", DEAD_LETTER_EXCHANGE, "x-single-active-consumer", true));
            // The binding key of a consistent-hash exchange is the partition's weight.
            channel.queueBind(writesQueue(i), WRITES_EXCHANGE, "1");
        }
    }

    public static String writesQueue(int partition) {
        return WRITES_QUEUE_PREFIX + partition;
    }
}
