// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.app;

import java.time.Clock;
import org.nebularis.lattice.authoring.api.AuthoringApi;
import org.nebularis.lattice.authoring.detection.ConstructDetector;
import org.nebularis.lattice.authoring.http.AuthoringHttpServer;
import org.nebularis.lattice.authoring.json.ContractSchemas;
import org.nebularis.lattice.authoring.jobs.JobRegistry;
import org.nebularis.lattice.authoring.messaging.RabbitMqAnalysisBus;
import org.nebularis.lattice.authoring.model.DocumentSnapshot;
import org.nebularis.lattice.authoring.rdf.IriMinter;
import org.nebularis.lattice.authoring.rdf.WordingMapper;
import org.nebularis.lattice.authoring.store.DocumentRegistry;
import org.nebularis.lattice.authoring.store.FusekiAuthoringStore;
import org.nebularis.lattice.authoring.template.ConformanceChecker;
import org.nebularis.lattice.authoring.template.SampleCatalog;
import org.nebularis.lattice.authoring.template.TemplateCatalog;
import org.nebularis.lattice.authoring.template.TemplateFindings;
import org.nebularis.lattice.authoring.validation.ValidationReportView;
import org.nebularis.lattice.authoring.validation.WordingValidator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** The service's entry point: `--self-check` for a quick offline check, otherwise runs the service. */
public final class AuthoringServiceMain {
    private static final Logger LOG = LoggerFactory.getLogger(AuthoringServiceMain.class);

    private AuthoringServiceMain() {
    }

    public static void main(String[] args) throws InterruptedException {
        if (args.length == 1 && "--self-check".equals(args[0])) {
            selfCheck();
            return;
        }
        run();
    }

    /** Loads everything shipped with the jar and validates each sample, with no network access. */
    private static void selfCheck() {
        ContractSchemas schemas = new ContractSchemas();
        WordingValidator validator = new WordingValidator();
        SampleCatalog samples = new SampleCatalog(schemas);
        new TemplateCatalog(schemas);
        WordingMapper mapper = new WordingMapper("https://example.org/lattice/authoring/");

        for (var summary : samples.list()) {
            DocumentSnapshot snapshot = samples.get(summary.sampleId()).orElseThrow();
            ValidationReportView report = validator.validate(mapper.map(snapshot, 1));
            if (!report.conforms()) {
                throw new IllegalStateException("self-check: sample '" + summary.sampleId() + "' does not conform");
            }
        }
        System.out.println("self-check ok");
    }

    private static void run() throws InterruptedException {
        AuthoringConfig config = AuthoringConfig.from(System.getenv());
        ContractSchemas schemas = new ContractSchemas();
        TemplateCatalog templates = new TemplateCatalog(schemas);
        SampleCatalog samples = new SampleCatalog(schemas);
        IriMinter minter = new IriMinter(config.baseIri());
        WordingMapper mapper = new WordingMapper(config.baseIri());

        FusekiAuthoringStore store = new FusekiAuthoringStore(config.fusekiUrl(), config.fusekiDataset(),
            config.fusekiAdminUser(), config.fusekiAdminPassword());
        store.ensureReady();
        DocumentRegistry registry = new DocumentRegistry(store, minter);
        RabbitMqAnalysisBus bus = new RabbitMqAnalysisBus(config.amqpUri());

        AuthoringApi api = new AuthoringApi(schemas, templates, samples, minter, mapper, new WordingValidator(),
            new ConstructDetector(), new TemplateFindings(), new ConformanceChecker(), store, registry, bus,
            new JobRegistry(), Clock.systemUTC());
        bus.onResult(api::onAnalysisResult);

        if (config.seedSamples()) {
            int seeded = new SampleSeeder(samples, registry, api).seed();
            LOG.info("seeded {} sample document(s)", seeded);
        }

        AuthoringHttpServer server = new AuthoringHttpServer(api);
        server.start(config.port());
        LOG.info("word authoring POC service listening on port {}", server.port());

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            server.stop();
            bus.close();
        }, "authoring-service-shutdown"));

        Thread.currentThread().join();
    }
}
