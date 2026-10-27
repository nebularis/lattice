// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.app;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Path;
import java.time.Clock;
import java.util.UUID;
import org.nebularis.lattice.studio.api.StudioApi;
import org.nebularis.lattice.studio.http.StudioHttpServer;
import org.nebularis.lattice.studio.jobs.JobBus;
import org.nebularis.lattice.studio.jobs.RabbitJobBus;
import org.nebularis.lattice.studio.jobs.RecordingJobBus;
import org.nebularis.lattice.studio.store.StudioStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Wires the Configuration Studio service. {@code --self-check} serves one request in memory and exits. */
public final class StudioMain {
    private static final Logger LOG = LoggerFactory.getLogger(StudioMain.class);

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
        if (config.amqpUri() == null) {
            LOG.warn("LATTICE_AMQP_URI is not set, so jobs are recorded but never reach a worker and stay queued");
            bus = new RecordingJobBus();
        } else {
            bus = new RabbitJobBus(config.amqpUri());
        }
        StudioHttpServer server = serve(config, store, bus);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            server.close();
            bus.close();
            store.close();
        }));
        LOG.info("Configuration Studio service listening on http://{}:{}/", config.bind(), server.port());
    }

    private static StudioHttpServer serve(StudioConfig config, StudioStore store, JobBus bus) throws Exception {
        StudioApi api = new StudioApi(store, bus, Clock.systemUTC(), UUID::randomUUID, config.assets());
        StudioHttpServer server = new StudioHttpServer(api, config.bind(), config.port(), config.staticDir());
        server.start();
        return server;
    }

    private static boolean selfCheck() throws Exception {
        StudioConfig config = new StudioConfig(0, "127.0.0.1", Path.of(".build/config-studio"), null, null,
            "studio", null, null, null);
        try (StudioStore store = StudioStore.inMemory(); StudioHttpServer server = serve(config, store, new RecordingJobBus())) {
            HttpResponse<String> response = HttpClient.newHttpClient().send(
                HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + server.port() + "/api/health")).build(),
                HttpResponse.BodyHandlers.ofString());
            boolean ok = response.statusCode() == 200 && response.body().equals("ok");
            LOG.info("self-check {}", ok ? "passed" : "failed");
            return ok;
        }
    }
}
