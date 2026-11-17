// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.probes.msa;

import com.rabbitmq.client.Address;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * The writes super stream declared as {@code Topology.declare} of the studio declares it: a direct exchange marked as a super
 * stream, and for each partition a stream queue with the studio's arguments, bound with its order.
 */
final class Topo {
    static final Map<String, Object> PARTITION_ARGUMENTS = Map.of(
        "x-queue-type", "stream", "x-max-age", "7D", "x-max-length-bytes", 1_073_741_824L);

    private Topo() {
    }

    static String partition(String superStream, int i) {
        return superStream + "-" + i;
    }

    static Connection amqp(List<String> hosts, String name) throws Exception {
        ConnectionFactory factory = new ConnectionFactory();
        factory.setUsername("guest");
        factory.setPassword("guest");
        factory.setConnectionTimeout(5_000);
        List<Address> addresses = new ArrayList<>();
        for (String h : hosts) {
            addresses.add(new Address(h, 5672));
        }
        return factory.newConnection(addresses, name);
    }

    static void declare(Channel channel, String superStream, int partitions) throws IOException {
        channel.exchangeDeclare(superStream, "direct", true, false, Map.of("x-super-stream", true));
        for (int i = 0; i < partitions; i++) {
            channel.queueDeclare(partition(superStream, i), true, false, false, PARTITION_ARGUMENTS);
            channel.queueBind(partition(superStream, i), superStream, Integer.toString(i), Map.of("x-stream-partition-order", i));
        }
    }

    static void delete(Channel channel, String superStream, int partitions) throws IOException {
        for (int i = 0; i < partitions; i++) {
            channel.queueDelete(partition(superStream, i));
        }
        channel.exchangeDelete(superStream);
    }

    static void declareMain(Main.Args a) throws Exception {
        if (a.flag("spread")) {
            // The broker puts a stream's leader on the node of the declaring connection, so each partition is declared over a
            // connection to node (partition mod number of nodes), which spreads the leaders over the cluster.
            String superStream = a.str("super", "lattice.studio.writes");
            int partitions = a.num("partitions", 8);
            List<String> nodes = a.list("amqp", "msa-i9-rmq1,msa-i9-rmq2,msa-i9-rmq3");
            try (Connection c = amqp(List.of(nodes.get(0)), "msa-i9 declare"); Channel ch = c.createChannel()) {
                ch.exchangeDeclare(superStream, "direct", true, false, Map.of("x-super-stream", true));
            }
            for (int i = 0; i < partitions; i++) {
                try (Connection c = amqp(List.of(nodes.get(i % nodes.size())), "msa-i9 declare"); Channel ch = c.createChannel()) {
                    ch.queueDeclare(partition(superStream, i), true, false, false, PARTITION_ARGUMENTS);
                    ch.queueBind(partition(superStream, i), superStream, Integer.toString(i), Map.of("x-stream-partition-order", i));
                }
            }
            Log.ev("declared", "super", superStream, "partitions", partitions, "spread", true);
            return;
        }
        try (Connection c = amqp(a.list("amqp", "msa-i9-rmq1"), "msa-i9 declare"); Channel ch = c.createChannel()) {
            declare(ch, a.str("super", "lattice.studio.writes"), a.num("partitions", 8));
            Log.ev("declared", "super", a.str("super", "lattice.studio.writes"), "partitions", a.num("partitions", 8));
        }
    }

    static void deleteMain(Main.Args a) throws Exception {
        try (Connection c = amqp(a.list("amqp", "msa-i9-rmq1"), "msa-i9 delete"); Channel ch = c.createChannel()) {
            delete(ch, a.str("super", "lattice.studio.writes"), a.num("partitions", 8));
            Log.ev("deleted", "super", a.str("super", "lattice.studio.writes"));
        }
    }
}
