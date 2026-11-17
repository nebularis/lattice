// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.probes.msa;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * Publishes as {@code RabbitWrites} of the studio does: AMQP 0.9.1, to the super stream's exchange, persistent, mandatory,
 * routing key the partition number, and a broker confirm awaited after every {@code --confirm-every} messages (1 in the
 * studio). A failure ends the batch as unknown, the publisher opens a new connection to the next node and goes on with the next
 * sequence number, as the studio does not republish. Message {@code n} goes to partition {@code n mod partitions}.
 */
final class Pub {
    private Pub() {
    }

    static void main(Main.Args a) throws Exception {
        String superStream = a.str("super", "lattice.studio.writes");
        int partitions = a.num("partitions", 8);
        List<String> hosts = a.list("amqp", "msa-i9-rmq1");
        int rate = a.num("rate", 100);
        long durationMs = a.lng("duration-s", 30) * 1000;
        long start = a.lng("start", 0);
        long count = a.lng("count", 0);
        int every = a.num("confirm-every", 1);
        long t0 = System.currentTimeMillis();
        long seq = start;
        long rangeFrom = -1;
        long rangeTo = -1;
        long lastFlush = t0;
        Connection connection = null;
        Channel channel = null;
        Log.ev("pub-start", "super", superStream, "rate", rate, "start", start, "every", every);
        while (System.currentTimeMillis() - t0 < durationMs && (count == 0 || seq - start < count)) {
            long batchFrom = seq;
            try {
                if (channel == null || !channel.isOpen()) {
                    connection = Topo.amqp(hosts, "msa-i9 publisher");
                    channel = connection.createChannel();
                    channel.confirmSelect();
                    channel.addReturnListener(r -> Log.ev("returned", "seq", new String(r.getBody(), StandardCharsets.UTF_8).split(",")[0]));
                    Log.ev("pub-connected", "node", connection.getAddress().getHostName());
                }
                for (int i = 0; i < every && (count == 0 || seq - start < count); i++) {
                    byte[] body = (seq + "," + System.currentTimeMillis()).getBytes(StandardCharsets.UTF_8);
                    AMQP.BasicProperties props = new AMQP.BasicProperties.Builder()
                        .contentType("application/octet-stream").deliveryMode(2).messageId(Long.toString(seq)).build();
                    channel.basicPublish(superStream, Long.toString(seq % partitions), true, props, body);
                    seq++;
                }
                channel.waitForConfirmsOrDie(5_000);
                if (rangeFrom < 0) {
                    rangeFrom = batchFrom;
                }
                rangeTo = seq - 1;
            } catch (Exception e) {
                if (rangeFrom >= 0) {
                    Log.ev("conf", "from", rangeFrom, "to", rangeTo);
                    rangeFrom = -1;
                }
                Log.ev("unk", "from", batchFrom, "to", seq - 1, "err", e.getClass().getSimpleName() + " " + e.getMessage());
                closeQuietly(connection);
                channel = null;
                Thread.sleep(500);
            }
            long now = System.currentTimeMillis();
            if (rangeFrom >= 0 && now - lastFlush >= 1_000) {
                Log.ev("conf", "from", rangeFrom, "to", rangeTo);
                rangeFrom = -1;
                lastFlush = now;
            }
            if (rate > 0) {
                long due = t0 + (seq - start) * 1000L / rate;
                long wait = due - System.currentTimeMillis();
                if (wait > 0) {
                    TimeUnit.MILLISECONDS.sleep(wait);
                }
            }
        }
        if (rangeFrom >= 0) {
            Log.ev("conf", "from", rangeFrom, "to", rangeTo);
        }
        Log.ev("pub-done", "next", seq);
        closeQuietly(connection);
    }

    private static void closeQuietly(Connection c) {
        try {
            if (c != null) {
                c.close(1_000);
            }
        } catch (Exception ignored) {
            // the connection is gone already
        }
    }
}
