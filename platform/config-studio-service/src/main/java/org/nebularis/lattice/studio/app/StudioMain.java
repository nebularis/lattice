// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.app;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Duration;
import java.util.UUID;
import org.nebularis.lattice.studio.api.StudioApi;
import org.nebularis.lattice.studio.auth.Authenticator;
import org.nebularis.lattice.studio.auth.LocalAuthenticator;
import org.nebularis.lattice.studio.http.StudioHttpServer;
import org.nebularis.lattice.studio.jobs.Amqp;
import org.nebularis.lattice.studio.jobs.JobBus;
import org.nebularis.lattice.studio.jobs.RabbitJobBus;
import org.nebularis.lattice.studio.jobs.RecordingJobBus;
import org.nebularis.lattice.studio.store.StudioStore;
import org.nebularis.lattice.studio.writes.DirectWrites;
import org.nebularis.lattice.studio.writes.RabbitWrites;
import org.nebularis.lattice.studio.writes.Writer;
import org.nebularis.lattice.studio.writes.Writes;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Wires the Configuration Studio service. {@code --self-check} serves one request in memory and exits. */
public final class StudioMain {
    private static final Logger LOG = LoggerFactory.getLogger(StudioMain.class);
    private static final Duration WRITE_TIMEOUT = Duration.ofSeconds(10);

    private StudioMain() {
    }

    public static void main(String[] args) throws Exception {
        if (args.length > 0 && args[0].equals("--self-check")) {
            System.exit(selfCheck() ? 0 : 1);
        }
        StudioConfig config = StudioConfig.fromEnv(System.getenv());
        Authenticator auth = Authenticator.fromEnv(System.getenv(), config.bind());
        StudioStore store = config.fusekiUrl() == null ? StudioStore.inMemory()
            : StudioStore.fuseki(config.fusekiUrl(), config.fusekiDataset(), config.fusekiUser(), config.fusekiPassword());
        if (config.fusekiUrl() == null) {
            LOG.warn("LATTICE_FUSEKI_URL is not set, so workspaces live in memory and are lost on exit");
        }
        JobBus bus;
        Writes writes;
        if (config.amqpUri() == null) {
            // Tests and a demonstration without a broker only: the service writes the store through a writer of its own.
            LOG.warn("LATTICE_AMQP_URI is not set, so jobs are recorded but never reach a worker, and this service writes the store itself");
            bus = new RecordingJobBus();
            writes = new DirectWrites(new Writer(store, Clock.systemUTC()));
        } else {
            // Jobs and writes are published on connections of their own, so a broker holding one back does not stall the other.
            bus = new RabbitJobBus(Amqp.connect(config.amqpUri(), "config-studio-service jobs"));
            writes = new RabbitWrites(Amqp.connect(config.amqpUri(), "config-studio-service writes"), store, WRITE_TIMEOUT);
        }
        StudioHttpServer server = serve(config, store, writes, bus, auth);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            server.close();
            bus.close();
            store.close();
        }));
        LOG.info("Configuration Studio service listening on http://{}:{}/", config.bind(), server.port());
    }

    private static StudioHttpServer serve(StudioConfig config, StudioStore store, Writes writes, JobBus bus, Authenticator auth) throws Exception {
        StudioApi api = new StudioApi(store, writes, bus, Clock.systemUTC(), UUID::randomUUID, config.assets(), config.features(), auth);
        StudioHttpServer server = new StudioHttpServer(api, config.bind(), config.port(), config.staticDir());
        server.start();
        return server;
    }

    private static boolean selfCheck() throws Exception {
        StudioConfig config = new StudioConfig(0, "127.0.0.1", Path.of(".build/config-studio"), null, null,
            "studio", null, null, null, java.util.Set.of());
        try (StudioStore store = StudioStore.inMemory();
             StudioHttpServer server = serve(config, store, new DirectWrites(new Writer(store, Clock.systemUTC())), new RecordingJobBus(), LocalAuthenticator.developers())) {
            HttpResponse<String> response = HttpClient.newHttpClient().send(
                HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + server.port() + "/api/health")).build(),
                HttpResponse.BodyHandlers.ofString());
            boolean ok = response.statusCode() == 200 && response.body().equals("ok");
            LOG.info("self-check {}", ok ? "passed" : "failed");
            return ok;
        }
    }
}
