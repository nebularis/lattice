// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writes;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.Delivery;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.ArrayList;
import java.util.List;
import org.nebularis.lattice.studio.jobs.Topology;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * {@code writers} consumers over the {@link Topology#PARTITIONS} partition queues, partition i going to writer
 * i mod writers. Each writer has its own channel, and a channel delivers one message at a time, so the writes of a
 * partition apply in order. Each queue has a single active consumer, so a second instance's writers stand by until this
 * one's go away.
 */
public final class WriterPool implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(WriterPool.class);
    private static final long STORE_RETRY_MILLIS = 1_000;

    private final List<Channel> channels = new ArrayList<>();

    public WriterPool(Connection connection, Writer writer, int writers) {
        if (writers < 1 || writers > Topology.PARTITIONS) {
            throw new IllegalArgumentException("LATTICE_STUDIO_WRITERS is from 1 to " + Topology.PARTITIONS);
        }
        try {
            for (int w = 0; w < writers; w++) {
                Channel channel = connection.createChannel();
                Topology.declare(channel);
                channel.basicQos(1);
                channels.add(channel);
            }
            for (int p = 0; p < Topology.PARTITIONS; p++) {
                Channel channel = channels.get(p % writers);
                channel.basicConsume(Topology.writesQueue(p), false, (tag, d) -> handle(channel, writer, d), tag -> { });
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        LOG.info("{} store writer(s) over {} partitions", writers, Topology.PARTITIONS);
    }

    // ponytail: one SPARQL Update per write. Merge a partition's queued writes into one request when throughput needs it.
    private static void handle(Channel channel, Writer writer, Delivery d) throws IOException {
        long tag = d.getEnvelope().getDeliveryTag();
        Command command = Codec.decode(d.getProperties().getHeaders(), d.getBody());
        Reply reply;
        try {
            reply = command == null ? Reply.refused("the message is not a write") : writer.apply(command);
        } catch (RuntimeException e) {
            // The store is unreachable or refused the update. The write is retried, after a pause so it does not spin.
            LOG.error("a write could not be applied, and is retried", e);
            sleep();
            channel.basicNack(tag, false, true);
            return;
        }
        String replyTo = d.getProperties().getReplyTo();
        if (replyTo != null) {
            AMQP.BasicProperties props = new AMQP.BasicProperties.Builder()
                .correlationId(d.getProperties().getCorrelationId()).headers(Codec.reply(reply)).build();
            channel.basicPublish("", replyTo, props, new byte[0]);
        }
        if (reply.status() == 400) {
            LOG.warn("refused a write: {}", reply.message());
            channel.basicNack(tag, false, false);
        } else {
            channel.basicAck(tag, false);
        }
    }

    private static void sleep() {
        try {
            Thread.sleep(STORE_RETRY_MILLIS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    @Override
    public void close() {
        for (Channel channel : channels) {
            try {
                channel.close();
            } catch (Exception e) {
                LOG.debug("closing a writer's channel failed", e);
            }
        }
    }
}
