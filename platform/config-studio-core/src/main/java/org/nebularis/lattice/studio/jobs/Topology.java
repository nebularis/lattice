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
    /**
     * The writes super stream: a direct exchange whose binding keys "0" to "7" route to the partition streams. A write's
     * routing key is its workspace's partition, so every write of a workspace lands in one partition, in order.
     */
    public static final String WRITES = "lattice.studio.writes";
    /** Fixed by the contract. Changing it moves workspaces between partitions, so stop the writers and drain first. */
    public static final int PARTITIONS = 8;
    /** A partition keeps a week of writes or 1 GiB, whichever is less. The receipts in the store are the lasting record. */
    public static final Map<String, Object> PARTITION_ARGUMENTS = Map.of(
        "x-queue-type", "stream", "x-max-age", "7D", "x-max-length-bytes", 1_073_741_824L);

    private Topology() {
    }

    /** Idempotent, so the service, the writer and the worker may each declare it. */
    public static void declare(Channel channel) throws IOException {
        channel.exchangeDeclare(EXCHANGE, "topic", true);
        channel.exchangeDeclare(DEAD_LETTER_EXCHANGE, "topic", true);
        channel.queueDeclare(JOBS_QUEUE, true, false, false, Map.of("x-dead-letter-exchange", DEAD_LETTER_EXCHANGE));
        channel.queueBind(JOBS_QUEUE, EXCHANGE, JOBS_ROUTING_KEY);
        channel.queueDeclare(DEAD_QUEUE, true, false, false, Map.of());
        channel.queueBind(DEAD_QUEUE, DEAD_LETTER_EXCHANGE, DEAD_ROUTING_KEY);
        // A super stream, declared as `rabbitmq-streams add_super_stream` would: the exchange marked as one, and each
        // partition bound with its order, which is how the stream protocol finds the partitions.
        channel.exchangeDeclare(WRITES, "direct", true, false, Map.of("x-super-stream", true));
        for (int i = 0; i < PARTITIONS; i++) {
            channel.queueDeclare(partition(i), true, false, false, PARTITION_ARGUMENTS);
            channel.queueBind(partition(i), WRITES, Integer.toString(i), Map.of("x-stream-partition-order", i));
        }
    }

    /** The stream of partition {@code i}. */
    public static String partition(int i) {
        return WRITES + "-" + i;
    }

    /**
     * The routing key of a workspace's writes: its id's first 32 bits, an unsigned number, modulo the partitions. A
     * workspace id is a random UUID, so the partitions fill evenly, and the Python worker computes the same key.
     */
    public static String routingKey(String workspace) {
        return Long.toString(Long.parseLong(workspace.substring(0, 8), 16) % PARTITIONS);
    }
}
