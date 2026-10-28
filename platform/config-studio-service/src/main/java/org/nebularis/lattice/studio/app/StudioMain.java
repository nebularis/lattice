// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.app;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import com.rabbitmq.client.Connection;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Duration;
import java.util.UUID;
import org.nebularis.lattice.studio.api.StudioApi;
import org.nebularis.lattice.studio.http.StudioHttpServer;
import org.nebularis.lattice.studio.jobs.JobBus;
import org.nebularis.lattice.studio.jobs.RabbitJobBus;
import org.nebularis.lattice.studio.jobs.RecordingJobBus;
import org.nebularis.lattice.studio.store.StudioStore;
import org.nebularis.lattice.studio.writes.DirectWrites;
import org.nebularis.lattice.studio.writes.RabbitWrites;
import org.nebularis.lattice.studio.writes.Sweeper;
import org.nebularis.lattice.studio.writes.Writer;
import org.nebularis.lattice.studio.writes.WriterPool;
import org.nebularis.lattice.studio.writes.Writes;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Wires the Configuration Studio service. {@code --self-check} serves one request in memory and exits. */
public final class StudioMain {
    private static final Logger LOG = LoggerFactory.getLogger(StudioMain.class);
    private static final Duration WRITE_TIMEOUT = Duration.ofSeconds(10);
    private static final Duration SWEEP_EVERY = Duration.ofHours(1);

    private StudioMain() {
    }

    public static void main(String[] args) throws Exception {
        if (args.length > 0 && args[0].equals("--self-check")) {
            System.exit(selfCheck() ? 0 : 1);
        }
        StudioConfig config = StudioConfig.fromEnv(System.getenv());
        StudioStore store = config.fusekiUrl() == null ? StudioStore.inMemory()
            : StudioStore.fuseki(config.fusekiUrl(), config.fusekiDataset(), config.fusekiUser(), config.fusekiPassword());
        if (config.fusekiUrl() == null) {
            LOG.warn("LATTICE_FUSEKI_URL is not set, so workspaces live in memory and are lost on exit");
        }
        JobBus bus;
        Writes writes;
        WriterPool pool = null;
        if (config.amqpUri() == null) {
            LOG.warn("LATTICE_AMQP_URI is not set, so jobs are recorded but never reach a worker and stay queued");
            bus = new RecordingJobBus();
            writes = new DirectWrites(new Writer(store));
        } else {
            Connection amqp = RabbitJobBus.connect(config.amqpUri());
            bus = new RabbitJobBus(amqp);
            if (config.writers() > 0) {
                pool = new WriterPool(amqp, new Writer(store), config.writers());
            }
            writes = new RabbitWrites(amqp, WRITE_TIMEOUT);
        }
        Sweeper sweeper = new Sweeper(store, writes, Clock.systemUTC(), Duration.ofDays(config.jobRetentionDays())).start(SWEEP_EVERY);
        StudioHttpServer server = serve(config, store, writes, bus);
        WriterPool writers = pool;
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            server.close();
            sweeper.close();
            if (writers != null) {
                writers.close();
            }
            bus.close();
            store.close();
        }));
        LOG.info("Configuration Studio service listening on http://{}:{}/", config.bind(), server.port());
    }

    private static StudioHttpServer serve(StudioConfig config, StudioStore store, Writes writes, JobBus bus) throws Exception {
        StudioApi api = new StudioApi(store, writes, bus, Clock.systemUTC(), UUID::randomUUID, config.assets());
        StudioHttpServer server = new StudioHttpServer(api, config.bind(), config.port(), config.staticDir());
        server.start();
        return server;
    }

    private static boolean selfCheck() throws Exception {
        StudioConfig config = new StudioConfig(0, "127.0.0.1", Path.of(".build/config-studio"), null, null,
            "studio", null, null, null, 1, 30);
        try (StudioStore store = StudioStore.inMemory();
             StudioHttpServer server = serve(config, store, new DirectWrites(new Writer(store)), new RecordingJobBus())) {
            HttpResponse<String> response = HttpClient.newHttpClient().send(
                HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + server.port() + "/api/health")).build(),
                HttpResponse.BodyHandlers.ofString());
            boolean ok = response.statusCode() == 200 && response.body().equals("ok");
            LOG.info("self-check {}", ok ? "passed" : "failed");
            return ok;
        }
    }
}
