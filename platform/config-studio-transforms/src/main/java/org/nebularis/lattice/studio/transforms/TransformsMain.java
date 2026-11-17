// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import java.time.Clock;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.Function;
import org.nebularis.lattice.studio.jobs.Amqp;
import org.nebularis.lattice.studio.jobs.Topology;
import org.nebularis.lattice.studio.settings.Secrets;
import org.nebularis.lattice.studio.store.StudioStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The Configuration Studio's run worker, the transforms worker of ADR-A148 generalised by ADR-A154. It consumes three queues, each on a
 * channel and a pool of threads of its own so that a long sample run never delays a simulator's step and the deprecated transforms
 * route keeps its behaviour: {@code lattice.studio.transforms} (a sample source answered on the sender's reply queue),
 * {@code lattice.studio.runs.interactive} and {@code lattice.studio.runs}, whose runs it answers as frames on the events exchange. It stays
 * running so the engines and the stylesheets they compiled stay warm. It reads the store and never writes it.
 */
public final class TransformsMain {
    private static final Logger LOG = LoggerFactory.getLogger(TransformsMain.class);
    static final String INTERACTIVE_CONCURRENCY = "LATTICE_RUNS_INTERACTIVE_CONCURRENCY";
    static final String SAMPLE_CONCURRENCY = "LATTICE_RUNS_CONCURRENCY";
    private static final int DEFAULT_CONCURRENCY = 2;

    private TransformsMain() {
    }

    /** The requests a run queue handles at once, from the setting {@code name}, at least 1. */
    static int concurrency(Map<String, String> env, String name) {
        String v = env.get(name);
        if (v == null || v.isBlank()) {
            return DEFAULT_CONCURRENCY;
        }
        try {
            int n = Integer.parseInt(v.trim());
            if (n >= 1) {
                return n;
            }
        } catch (NumberFormatException e) {
            // Falls through to the refusal below.
        }
        throw new IllegalArgumentException(name + " is a whole number from 1");
    }

    public static void main(String[] args) throws Exception {
        Map<String, String> env = System.getenv();
        String fuseki = env.get("LATTICE_FUSEKI_URL");
        if (fuseki == null || fuseki.isBlank()) {
            throw new IllegalArgumentException("LATTICE_FUSEKI_URL is required");
        }
        int interactive = concurrency(env, INTERACTIVE_CONCURRENCY);
        int samples = concurrency(env, SAMPLE_CONCURRENCY);
        StudioStore store = StudioStore.fuseki(fuseki.trim(), env.getOrDefault("LATTICE_FUSEKI_DATASET", "studio"),
            env.get("LATTICE_FUSEKI_USER"), Secrets.secret(env, "LATTICE_FUSEKI_PASSWORD"));
        Connection connection = Amqp.connect(Secrets.required(env, "LATTICE_AMQP_URI"), "config-studio-transforms");
        Channel setup = connection.createChannel();
        Topology.declare(setup);
        setup.close();
        List<AutoCloseable> closeables = new ArrayList<>();
        Clock clock = Clock.systemUTC();
        // Each queue has a channel to consume and settle on, and each run queue a channel of its own to publish its frames on.
        Channel transformsChannel = connection.createChannel();
        consume(transformsChannel, Topology.TRANSFORMS_QUEUE, 1, new LegacyTransforms(store::graph, LegacyTransforms.onChannel(transformsChannel)), closeables);
        for (Object[] q : new Object[][] {{Topology.RUNS_INTERACTIVE_QUEUE, "simulate", interactive}, {Topology.RUNS_QUEUE, "sample", samples}}) {
            RunWorker worker = new RunWorker((String) q[1], store::graph, new AmqpFrameSink(connection.createChannel(), clock, UUID::randomUUID), clock);
            closeables.add(worker);
            consume(connection.createChannel(), (String) q[0], (Integer) q[2], worker, closeables);
        }
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            try {
                connection.close();
            } catch (Exception e) {
                LOG.debug("closing the RabbitMQ connection failed", e);
            }
            for (AutoCloseable c : closeables) {
                try {
                    c.close();
                } catch (Exception e) {
                    LOG.debug("closing a worker failed", e);
                }
            }
            store.close();
        }));
        LOG.info("Configuration Studio run worker running");
    }

    /** Consumes {@code queue} on {@code channel}, taking at most {@code threads} messages at once, each handled on a pool of that many threads. */
    private static void consume(Channel channel, String queue, int threads, Function<Message, Outcome> handler, List<AutoCloseable> closeables)
        throws Exception {
        channel.basicQos(threads);
        QueueWorker worker = new QueueWorker(queue, threads, handler, QueueWorker.onChannel(channel));
        closeables.add(worker);
        channel.basicConsume(queue, false, (tag, delivery) -> worker.deliver(Message.of(delivery)),
            tag -> LOG.warn("the queue {} cancelled this consumer", queue));
    }
}
