// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.app;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;
import com.rabbitmq.client.DeliverCallback;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.concurrent.TimeoutException;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.authoring.RepoPaths;
import org.nebularis.lattice.authoring.TestSamples;
import org.nebularis.lattice.authoring.api.AuthoringApi;
import org.nebularis.lattice.authoring.detection.ConstructDetector;
import org.nebularis.lattice.authoring.http.AuthoringHttpServer;
import org.nebularis.lattice.authoring.jobs.JobRegistry;
import org.nebularis.lattice.authoring.json.ContractSchemas;
import org.nebularis.lattice.authoring.json.Json;
import org.nebularis.lattice.authoring.messaging.RabbitMqAnalysisBus;
import org.nebularis.lattice.authoring.messaging.Topology;
import org.nebularis.lattice.authoring.rdf.IriMinter;
import org.nebularis.lattice.authoring.rdf.WordingMapper;
import org.nebularis.lattice.authoring.store.DocumentRegistry;
import org.nebularis.lattice.authoring.store.FusekiAuthoringStore;
import org.nebularis.lattice.authoring.template.ConformanceChecker;
import org.nebularis.lattice.authoring.template.SampleCatalog;
import org.nebularis.lattice.authoring.template.TemplateCatalog;
import org.nebularis.lattice.authoring.template.TemplateFindings;
import org.nebularis.lattice.authoring.validation.WordingValidator;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testcontainers.utility.DockerImageName;

/**
 * S5-05: the real store, bus, API and HTTP server over both containers, with an in-test consumer
 * standing in for the WA6/WA7 worker (answering every request with a completed result).
 */
class AuthoringServiceStackIT {
    private static final String BASE_IRI = "https://example.org/lattice/authoring/";

    private static GenericContainer<?> fuseki;
    private static GenericContainer<?> rabbit;
    private static RabbitMqAnalysisBus bus;
    private static AuthoringHttpServer server;
    private static Connection workerConnection;
    private static Channel workerChannel;

    @BeforeAll
    static void startStack() throws Exception {
        fuseki = new GenericContainer<>(DockerImageName.parse("stain/jena-fuseki:5.1.0"))
            .withEnv("ADMIN_PASSWORD", "lattice")
            .withExposedPorts(3030)
            .waitingFor(Wait.forHttp("/$/ping").forStatusCode(200));
        rabbit = new GenericContainer<>(DockerImageName.parse("rabbitmq:3.13-management-alpine"))
            .withEnv("RABBITMQ_DEFAULT_USER", "lattice")
            .withEnv("RABBITMQ_DEFAULT_PASS", "lattice")
            .withExposedPorts(5672)
            .waitingFor(Wait.forLogMessage(".*Server startup complete.*\\n", 1));
        fuseki.start();
        rabbit.start();

        ContractSchemas schemas = new ContractSchemas();
        TemplateCatalog templates = new TemplateCatalog(schemas);
        SampleCatalog samples = new SampleCatalog(schemas);
        IriMinter minter = new IriMinter(BASE_IRI);
        WordingMapper mapper = new WordingMapper(BASE_IRI);

        FusekiAuthoringStore store = new FusekiAuthoringStore(
            "http://" + fuseki.getHost() + ":" + fuseki.getMappedPort(3030), "wa5-stack-it", "admin", "lattice");
        store.ensureReady();
        DocumentRegistry registry = new DocumentRegistry(store, minter);
        String amqpUri = "amqp://lattice:lattice@" + rabbit.getHost() + ":" + rabbit.getMappedPort(5672);
        bus = new RabbitMqAnalysisBus(amqpUri);

        AuthoringApi api = new AuthoringApi(schemas, templates, samples, minter, mapper, new WordingValidator(),
            new ConstructDetector(), new TemplateFindings(), new ConformanceChecker(), store, registry, bus,
            new JobRegistry(), Clock.fixed(Instant.parse("2026-10-01T00:00:00Z"), ZoneOffset.UTC));
        bus.onResult(api::onAnalysisResult);

        server = new AuthoringHttpServer(api);
        server.start(0);

        startWorkerStandIn(amqpUri);
    }

    /** Stands in for the WA6/WA7 worker: answers every request with a completed, fixture-based result. */
    private static void startWorkerStandIn(String amqpUri) throws IOException, TimeoutException {
        ConnectionFactory factory = new ConnectionFactory();
        try {
            factory.setUri(amqpUri);
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
        workerConnection = factory.newConnection();
        workerChannel = workerConnection.createChannel();
        DeliverCallback callback = (consumerTag, delivery) -> {
            JsonNode request = Json.MAPPER.readTree(delivery.getBody());
            JsonNode result = completedResultFor(request);
            workerChannel.basicPublish(Topology.EXCHANGE, Topology.COMPLETED_ROUTING_KEY, null,
                Json.MAPPER.writeValueAsBytes(result));
            workerChannel.basicAck(delivery.getEnvelope().getDeliveryTag(), false);
        };
        workerChannel.basicConsume(Topology.REQUESTED_QUEUE, false, callback, consumerTag -> { });
    }

    private static JsonNode completedResultFor(JsonNode request) throws IOException {
        ObjectNode result = (ObjectNode) Json.MAPPER.readTree(
            RepoPaths.contracts().resolve("authoring/fixtures/valid/wording-analysis-result--completed-minimal.json")
                .toFile());
        result.put("jobId", request.get("jobId").asText());
        result.put("correlationId", request.get("correlationId").asText());
        result.put("documentId", request.get("documentId").asText());
        result.put("revision", request.get("revision").asInt());
        ((ObjectNode) result.get("proposalGraph")).put("graphIri", request.get("proposalGraphIri").asText());
        return result;
    }

    @AfterAll
    static void stopStack() throws Exception {
        if (server != null) {
            server.stop();
        }
        if (workerChannel != null) {
            workerChannel.close();
        }
        if (workerConnection != null) {
            workerConnection.close();
        }
        if (bus != null) {
            bus.close();
        }
        if (rabbit != null) {
            rabbit.stop();
        }
        if (fuseki != null) {
            fuseki.stop();
        }
    }

    @Test
    void completesAJobAndServesTheAnalysisAndTheWordingGraph() throws Exception {
        JsonNode snapshot = TestSamples.rawNode(TestSamples.SOFTWARE_LICENCE);
        String documentId = snapshot.get("documentId").asText();
        ObjectNode submission = Json.MAPPER.createObjectNode();
        submission.putNull("baseRevision");
        submission.set("snapshot", snapshot);

        HttpClient client = HttpClient.newHttpClient();
        URI base = URI.create("http://localhost:" + server.port());

        HttpRequest submitRequest = HttpRequest.newBuilder(base.resolve("/api/documents/" + documentId + "/snapshot"))
            .header("Content-Type", "application/json")
            .PUT(HttpRequest.BodyPublishers.ofString(submission.toString()))
            .build();
        HttpResponse<String> submitResponse = client.send(submitRequest, HttpResponse.BodyHandlers.ofString());
        assertEquals(200, submitResponse.statusCode());
        String jobId = Json.MAPPER.readTree(submitResponse.body()).get("job").get("jobId").asText();

        String status = pollJobStatus(client, base, jobId);
        assertEquals("completed", status);

        HttpRequest analysisRequest = HttpRequest.newBuilder(
            base.resolve("/api/documents/" + documentId + "/revisions/1/analysis")).GET().build();
        assertEquals(200, client.send(analysisRequest, HttpResponse.BodyHandlers.ofString()).statusCode());

        HttpRequest graphRequest = HttpRequest.newBuilder(
            base.resolve("/api/documents/" + documentId + "/revisions/1/graph/wording")).GET().build();
        HttpResponse<String> graphResponse = client.send(graphRequest, HttpResponse.BodyHandlers.ofString());
        assertEquals(200, graphResponse.statusCode());
        assertTrue(graphResponse.body().contains("wording"));
    }

    private static String pollJobStatus(HttpClient client, URI base, String jobId)
        throws IOException, InterruptedException, TimeoutException {
        HttpRequest request = HttpRequest.newBuilder(base.resolve("/api/jobs/" + jobId)).GET().build();
        for (int attempt = 0; attempt < 100; attempt++) {
            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            String status = Json.MAPPER.readTree(response.body()).get("status").asText();
            if (!"queued".equals(status)) {
                return status;
            }
            Thread.sleep(100);
        }
        throw new TimeoutException("job " + jobId + " did not complete within 10 seconds");
    }
}
