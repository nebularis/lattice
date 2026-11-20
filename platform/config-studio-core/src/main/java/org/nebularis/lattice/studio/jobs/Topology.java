// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

import com.rabbitmq.client.Channel;
import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.List;
import java.util.Map;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.atlas.json.JsonValue;

/**
 * The AMQP topology of `contracts/config-studio/amqp-topology.json`. The names are constants for the code that
 * publishes and consumes, and {@link #declare} declares the exchanges and queues from the contract itself.
 */
public final class Topology {
    public static final String EXCHANGE = "lattice.studio";
    public static final String DEAD_LETTER_EXCHANGE = "lattice.studio.dlx";
    public static final String JOBS_QUEUE = "lattice.studio.jobs";
    public static final String JOBS_ROUTING_KEY = "lattice.studio.jobs";
    /**
     * Jobs that take minutes, a proposal by a language model and a publication, on a queue of their own and a worker of their own, so a
     * validation or a compilation never waits behind one (plan studio-worker-liveness, WL-Q3). See {@link Lanes}.
     */
    public static final String JOBS_LONG_QUEUE = "lattice.studio.jobs.long";
    public static final String JOBS_LONG_ROUTING_KEY = "lattice.studio.jobs.long";
    /**
     * Runs of a compiled transform (ADR-A148), each a request answered on its sender's direct reply-to. A request expires
     * when its sender stops waiting, so it is never dead-lettered.
     */
    public static final String TRANSFORMS_QUEUE = "lattice.studio.transforms";
    public static final String TRANSFORMS_ROUTING_KEY = "lattice.studio.transforms";
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

    /** The contract, `contracts/config-studio/amqp-topology.json`, which the build puts beside this class. */
    static JsonObject contract() {
        try (InputStream in = Topology.class.getResourceAsStream("amqp-topology.json")) {
            if (in == null) {
                throw new IllegalStateException("amqp-topology.json is not on the classpath beside Topology");
            }
            return JSON.parse(in);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    /**
     * Idempotent, so the service, the writer and the worker may each declare it. The exchanges and queues are the
     * contract's: each queue bound to the exchange its {@code bindsTo} names and dead-lettering to the one its
     * {@code deadLettersTo} names, or nowhere when that is null, as the worker's {@code declare_topology} does (MSAI12-01).
     */
    public static void declare(Channel channel) throws IOException {
        declare(channel, contract());
    }

    /**
     * Declares the exchanges and queues of {@code contract}, which has the form of the contract file, then the super stream.
     * A queue whose {@code bindsTo} or {@code deadLettersTo} names an exchange the contract does not declare is refused
     * before it is declared, as the worker's {@code declare_topology} refuses it.
     */
    public static void declare(Channel channel, JsonObject contract) throws IOException {
        List<String> exchanges = List.of(contract.getString("exchange"), contract.getString("deadLetterExchange"));
        for (String exchange : exchanges) {
            channel.exchangeDeclare(exchange, "topic", true);
        }
        for (JsonValue entry : contract.get("queues").getAsArray()) {
            JsonObject queue = entry.getAsObject();
            for (String field : List.of("bindsTo", "deadLettersTo")) {
                JsonValue named = queue.get(field);
                if (!named.isNull() && !exchanges.contains(named.getAsString().value())) {
                    throw new IllegalArgumentException("queue " + queue.getString("name") + ": " + field + " names "
                        + named.getAsString().value() + ", which the topology does not declare");
                }
            }
            JsonValue deadLettersTo = queue.get("deadLettersTo");
            Map<String, Object> arguments = deadLettersTo.isNull() ? Map.of()
                : Map.of("x-dead-letter-exchange", deadLettersTo.getAsString().value());
            channel.queueDeclare(queue.getString("name"), true, false, false, arguments);
            channel.queueBind(queue.getString("name"), queue.getString("bindsTo"), queue.getString("routingKey"));
        }
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
