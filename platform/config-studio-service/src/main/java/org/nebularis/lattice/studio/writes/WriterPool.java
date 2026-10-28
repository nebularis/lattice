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
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;
import org.nebularis.lattice.studio.jobs.Topology;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * {@code writers} writers over the {@link Topology#PARTITIONS} partition queues, partition i going to writer
 * i mod writers. Each writer has its own channel and one thread, which takes every delivery waiting for it, up to
 * {@link #MAX_BATCH}, and applies them in one request, since a commit costs far more than the operations in it
 * (TSD-44). A queue delivers in order and the writer applies a batch in order, so a workspace's writes apply in the order
 * they were sent. Each queue has a single active consumer, so a second instance's writers stand by until this one's go.
 */
public final class WriterPool implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(WriterPool.class);
    public static final int MAX_BATCH = 64;
    private static final long STORE_RETRY_MILLIS = 1_000;

    private final List<Channel> channels = new ArrayList<>();
    private final List<Thread> threads = new ArrayList<>();

    public WriterPool(Connection connection, Writer writer, int writers) {
        if (writers < 1 || writers > Topology.PARTITIONS) {
            throw new IllegalArgumentException("LATTICE_STUDIO_WRITERS is from 1 to " + Topology.PARTITIONS);
        }
        try {
            for (int w = 0; w < writers; w++) {
                Channel channel = connection.createChannel();
                Topology.declare(channel);
                channel.basicQos(MAX_BATCH);
                BlockingQueue<Delivery> waiting = new LinkedBlockingQueue<>();
                for (int p = w; p < Topology.PARTITIONS; p += writers) {
                    channel.basicConsume(Topology.writesQueue(p), false, (tag, d) -> waiting.add(d), tag -> { });
                }
                channels.add(channel);
                threads.add(Thread.ofPlatform().name("store-writer-" + w).daemon().start(() -> run(channel, writer, waiting)));
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        LOG.info("{} store writer(s) over {} partitions", writers, Topology.PARTITIONS);
    }

    private static void run(Channel channel, Writer writer, BlockingQueue<Delivery> waiting) {
        List<Delivery> batch = new ArrayList<>();
        while (!Thread.currentThread().isInterrupted()) {
            try {
                batch.add(waiting.take());
                waiting.drainTo(batch, MAX_BATCH - 1);
                apply(channel, writer, batch);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } catch (IOException | RuntimeException e) {
                LOG.error("a writer's channel failed, and its unacknowledged writes are redelivered", e);
            }
            batch.clear();
        }
    }

    private static void apply(Channel channel, Writer writer, List<Delivery> batch) throws IOException, InterruptedException {
        List<Command> commands = new ArrayList<>(batch.size());
        for (Delivery d : batch) {
            commands.add(Codec.decode(d.getProperties().getHeaders(), d.getBody()));
        }
        List<Reply> replies;
        try {
            replies = writer.apply(commands);
        } catch (RuntimeException e) {
            // The store is unreachable or refused the request, which ran as one transaction, so none of it applied. The
            // batch is retried after a pause, and a command applied before is answered from its receipt.
            LOG.error("a batch of {} write(s) could not be applied, and is retried", batch.size(), e);
            Thread.sleep(STORE_RETRY_MILLIS);
            for (Delivery d : batch) {
                channel.basicNack(d.getEnvelope().getDeliveryTag(), false, true);
            }
            return;
        }
        for (int i = 0; i < batch.size(); i++) {
            Delivery d = batch.get(i);
            Reply reply = replies.get(i);
            String replyTo = d.getProperties().getReplyTo();
            if (replyTo != null) {
                AMQP.BasicProperties props = new AMQP.BasicProperties.Builder()
                    .correlationId(d.getProperties().getCorrelationId()).headers(Codec.reply(reply)).build();
                channel.basicPublish("", replyTo, props, new byte[0]);
            }
            if (reply.status() == 400) {
                LOG.warn("refused a write: {}", reply.message());
                channel.basicNack(d.getEnvelope().getDeliveryTag(), false, false);
            } else {
                channel.basicAck(d.getEnvelope().getDeliveryTag(), false);
            }
        }
    }

    @Override
    public void close() {
        threads.forEach(Thread::interrupt);
        for (Channel channel : channels) {
            try {
                channel.close();
            } catch (Exception e) {
                LOG.debug("closing a writer's channel failed", e);
            }
        }
    }
}
