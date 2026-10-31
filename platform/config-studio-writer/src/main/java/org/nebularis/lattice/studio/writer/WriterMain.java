// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writer;

import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.stream.Environment;
import java.time.Clock;
import java.time.Duration;
import org.nebularis.lattice.studio.jobs.Amqp;
import org.nebularis.lattice.studio.jobs.Topology;
import org.nebularis.lattice.studio.store.StudioOperations;
import org.nebularis.lattice.studio.store.StudioStore;
import org.nebularis.lattice.studio.writes.RabbitWrites;
import org.nebularis.lattice.studio.writes.Writer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The Configuration Studio's store writer, the only component that writes the store. Run as many instances as wanted:
 * the writes super stream's partitions spread across them, and one that stops hands its partitions to the others.
 */
public final class WriterMain {
    private static final Logger LOG = LoggerFactory.getLogger(WriterMain.class);
    private static final Duration WRITE_TIMEOUT = Duration.ofSeconds(10);
    private static final Duration SWEEP_EVERY = Duration.ofHours(1);

    private WriterMain() {
    }

    public static void main(String[] args) throws Exception {
        WriterConfig config = WriterConfig.fromEnv(System.getenv());
        StudioStore store = StudioStore.fuseki(config.fusekiUrl(), config.fusekiDataset(), config.fusekiUser(), config.fusekiPassword());
        // Replies go out on a connection of their own, apart from the sweep's publishing, so neither throttles the other.
        Connection replies = Amqp.connect(config.amqpUri(), "config-studio-writer replies");
        Connection publishing = Amqp.connect(config.amqpUri(), "config-studio-writer sweep");
        Channel replyChannel = replies.createChannel();
        Topology.declare(replyChannel);
        Environment environment = Environment.builder().uri(config.streamUri()).build();
        StreamWriter writer = new StreamWriter(environment, replyChannel, new Writer(store, StudioOperations.load(config.assets().resolve("persistence"), config.epoch()), Clock.systemUTC()));
        Sweeper sweeper = new Sweeper(store, new RabbitWrites(publishing, store, WRITE_TIMEOUT), Clock.systemUTC(),
            Duration.ofDays(config.jobRetentionDays())).start(SWEEP_EVERY);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            sweeper.close();
            writer.close();
            environment.close();
            close(publishing);
            close(replies);
            store.close();
        }));
        LOG.info("Configuration Studio store writer running");
    }

    private static void close(Connection connection) {
        try {
            connection.close();
        } catch (Exception e) {
            LOG.debug("closing a RabbitMQ connection failed", e);
        }
    }
}
