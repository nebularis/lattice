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
import org.nebularis.lattice.studio.events.Relay;
import org.nebularis.lattice.studio.events.Notifier;
import org.nebularis.lattice.studio.api.StudioApi;
import org.nebularis.lattice.studio.auth.Authenticator;
import org.nebularis.lattice.studio.auth.LocalAuthenticator;
import org.nebularis.lattice.studio.http.StudioHttpServer;
import org.nebularis.lattice.studio.jobs.Amqp;
import org.nebularis.lattice.studio.jobs.JobBus;
import org.nebularis.lattice.studio.jobs.RabbitJobBus;
import org.nebularis.lattice.studio.jobs.RecordingJobBus;
import org.nebularis.lattice.studio.runs.RunRegistry;
import org.nebularis.lattice.studio.runs.TabEvents;
import org.nebularis.lattice.studio.store.StudioOperations;
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
    /** Fires the deadline of each pending run. A daemon thread, since a run is lost with the service anyway. */
    private static final java.util.concurrent.ScheduledExecutorService RUN_DEADLINES = java.util.concurrent.Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = new Thread(r, "studio-run-deadlines");
        t.setDaemon(true);
        return t;
    });

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
        StudioOperations ops = StudioOperations.load(config.assets().resolve("persistence"), config.epoch());
        JobBus bus;
        Writes writes;
        com.rabbitmq.client.Connection events = null;
        if (config.amqpUri() == null) {
            // Tests and a demonstration without a broker only: the service writes the store through a writer of its own.
            LOG.warn("LATTICE_AMQP_URI is not set, so jobs are recorded but never reach a worker, and this service writes the store itself");
            bus = new RecordingJobBus();
            writes = new DirectWrites(new Writer(store, ops, org.nebularis.lattice.studio.store.Maintenance.load(config.assets().resolve("maintenance")), Clock.systemUTC()));
        } else {
            // Jobs and writes are published on connections of their own, so a broker holding one back does not stall the other.
            bus = new RabbitJobBus(Amqp.connect(config.amqpUri(), "config-studio-service jobs"));
            writes = new RabbitWrites(Amqp.connect(config.amqpUri(), "config-studio-service writes"), store, WRITE_TIMEOUT);
            events = Amqp.connect(config.amqpUri(), "config-studio-service events");
        }
        StudioApi api = new StudioApi(store, ops, writes, bus, Clock.systemUTC(), UUID::randomUUID, config.assets(), config.features(), auth);
        Plan plan = plan(config);
        if (config.eventsUrl() != null && config.brokerSecret() == null) {
            LOG.warn("LATTICE_STUDIO_EVENTS_URL is set without LATTICE_STUDIO_BROKER_SECRET, so the broker's checks are not served and the browser polls for jobs");
        } else if (config.eventsUrl() != null && events == null) {
            LOG.warn("LATTICE_STUDIO_EVENTS_URL is set without LATTICE_AMQP_URI, so the browser polls for jobs");
        }
        if (plan.runs()) {
            // A run's frames are read wherever there is a broker, and forwarded only by the instance that accepted the run (ADR-A154 decisions 4 and 10).
            RunRegistry runs = new RunRegistry(Clock.systemUTC(), RunRegistry.timers(RUN_DEADLINES), api::mayReadWorkspace);
            Relay.startRuns(events, runs);
            TabEvents tabs = null;
            if (plan.tabs()) {
                // Events reach a browser over the broker's MQTT, which asks this service who connected, and the relay decides what each tab hears (PM-Q20 (d)).
                api.events(config.eventsUrl(), config.brokerSecret());
                tabs = Relay.start(events, new Notifier(api::authenticate, api::mayRead));
            }
            api.runs(runs, tabs);
        }
        StudioHttpServer server = serve(config, api);
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            server.close();
            bus.close();
            store.close();
        }));
        LOG.info("Configuration Studio service listening on http://{}:{}/", config.bind(), server.port());
    }

    /** What to start: {@code runs} reads the frames of runs and needs a broker, {@code tabs} serves events to browsers and needs the broker, an events address and the broker's secret. */
    public record Plan(boolean runs, boolean tabs) {
    }

    public static Plan plan(StudioConfig config) {
        boolean broker = config.amqpUri() != null;
        return new Plan(broker, broker && config.eventsUrl() != null && config.brokerSecret() != null);
    }

    private static StudioHttpServer serve(StudioConfig config, StudioApi api) throws Exception {
        StudioHttpServer server = new StudioHttpServer(api, config.bind(), config.port(), config.staticDir());
        server.start();
        if (config.amqpUri() != null) {
            // Writes keep their promotions, so a start rebuilds them only when the contracts grew since the last rebuild (PM-Q3).
            api.startUp();
        }
        return server;
    }

    private static boolean selfCheck() throws Exception {
        StudioConfig config = new StudioConfig(0, "127.0.0.1", Path.of(".build/config-studio"), null, null,
            "studio", null, null, null, java.util.Set.of(), 1L, null, null);
        StudioOperations ops = StudioOperations.load(config.assets().resolve("persistence"), config.epoch());
        try (StudioStore store = StudioStore.inMemory();
             StudioHttpServer server = serve(config, new StudioApi(store, ops, new DirectWrites(new Writer(store, ops, org.nebularis.lattice.studio.store.Maintenance.load(config.assets().resolve("maintenance")), Clock.systemUTC())), new RecordingJobBus(), Clock.systemUTC(), UUID::randomUUID, config.assets(), config.features(), LocalAuthenticator.developers()))) {
            HttpResponse<String> response = HttpClient.newHttpClient().send(
                HttpRequest.newBuilder(URI.create("http://127.0.0.1:" + server.port() + "/api/health")).build(),
                HttpResponse.BodyHandlers.ofString());
            boolean ok = response.statusCode() == 200 && response.body().equals("ok");
            LOG.info("self-check {}", ok ? "passed" : "failed");
            return ok;
        }
    }
}
