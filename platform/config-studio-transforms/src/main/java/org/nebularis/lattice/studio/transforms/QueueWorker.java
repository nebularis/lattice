// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import com.rabbitmq.client.Channel;
import java.io.IOException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Function;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * One queue's consumer: a pool of threads of its own that handles the deliveries of its channel, so a slow run on one queue never
 * holds a thread of another. A handler runs on one of the pool's threads and returns what to do with the message, and the message is
 * acknowledged or rejected only after that, so after the handler published what it publishes.
 */
final class QueueWorker implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(QueueWorker.class);

    /** Acknowledges and rejects on one channel. */
    interface Acks {
        void ack(long tag) throws IOException;

        void reject(long tag, boolean requeue) throws IOException;
    }

    /**
     * The acknowledgements of a consumer's channel. A channel is not safe for concurrent use, and the pool's threads settle messages
     * at once, so every acknowledgement and rejection holds the channel's own monitor.
     */
    static Acks onChannel(Channel channel) {
        return new Acks() {
            @Override
            public void ack(long tag) throws IOException {
                synchronized (channel) {
                    channel.basicAck(tag, false);
                }
            }

            @Override
            public void reject(long tag, boolean requeue) throws IOException {
                synchronized (channel) {
                    channel.basicReject(tag, requeue);
                }
            }
        };
    }

    private final String name;
    private final Function<Message, Outcome> handler;
    private final Acks acks;
    private final ExecutorService pool;

    QueueWorker(String name, int threads, Function<Message, Outcome> handler, Acks acks) {
        this.name = name;
        this.handler = handler;
        this.acks = acks;
        AtomicInteger n = new AtomicInteger();
        this.pool = Executors.newFixedThreadPool(threads, r -> {
            Thread t = new Thread(r, name + "-" + n.incrementAndGet());
            t.setDaemon(true);
            return t;
        });
    }

    /** Hands the delivery to the pool and returns at once, so the broker's callback thread is free for the next. */
    void deliver(Message message) {
        pool.execute(() -> {
            Outcome outcome;
            try {
                outcome = handler.apply(message);
            } catch (RuntimeException e) {
                // The message and what it says are not logged. The service sends the run's failed frame at its deadline.
                LOG.error("handling a message of {} failed", name, e);
                outcome = Outcome.REJECT;
            }
            try {
                switch (outcome) {
                    case ACK -> acks.ack(message.tag());
                    case REJECT -> acks.reject(message.tag(), false);
                    case REQUEUE -> acks.reject(message.tag(), true);
                }
            } catch (IOException | RuntimeException e) {
                LOG.warn("settling a message of {} failed", name, e);
            }
        });
    }

    @Override
    public void close() {
        pool.shutdownNow();
    }
}
