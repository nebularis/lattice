// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import com.rabbitmq.client.Channel;
import java.io.IOException;
import java.net.URI;
import java.time.Clock;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.TimeoutException;
import java.util.function.Supplier;
import org.nebularis.lattice.outbox.CloudEvent;
import org.nebularis.lattice.outbox.RabbitMqEventPublisher;
import org.nebularis.lattice.studio.writes.StudioEvents;

/**
 * Publishes each frame to the events exchange as a CloudEvent in the AMQP binding's binary mode, with the publisher the store writer
 * publishes a job's event with. The channel is in confirm mode, and the frames of a run are published in order and then confirmed
 * together, so a frame the broker did not take fails the run's publish rather than going missing.
 *
 * <p>A channel is not safe for concurrent use. This sink owns its channel and every publish and confirm on it holds {@link #lock}, so
 * the frames of two runs never interleave on it and no two threads use it at once.
 */
final class AmqpFrameSink implements FrameSink {
    static final String FRAME_TYPE = "org.nebularis.lattice.studio.run.frame";
    static final URI SOURCE = URI.create("urn:lattice:studio:run-worker");
    private static final long CONFIRM_MILLIS = 10_000;

    private final Channel channel;
    private final RabbitMqEventPublisher events;
    private final Clock clock;
    private final Supplier<UUID> ids;
    private final Object lock = new Object();

    AmqpFrameSink(Channel channel, Clock clock, Supplier<UUID> ids) throws IOException {
        this.channel = channel;
        this.clock = clock;
        this.ids = ids;
        channel.exchangeDeclare(StudioEvents.EXCHANGE, "topic", true);
        channel.confirmSelect();
        this.events = new RabbitMqEventPublisher(channel, StudioEvents.EXCHANGE);
    }

    @Override
    public void publish(String run, List<String> frames) throws IOException {
        synchronized (lock) {
            for (String frame : frames) {
                events.publish(new CloudEvent(ids.get(), SOURCE, FRAME_TYPE, run, clock.instant(), java.util.Map.of(), frame));
            }
            try {
                channel.waitForConfirmsOrDie(CONFIRM_MILLIS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IOException("interrupted while the broker confirmed a run's frames", e);
            } catch (TimeoutException e) {
                throw new IOException("the broker did not confirm a run's frames in time", e);
            }
        }
    }
}
