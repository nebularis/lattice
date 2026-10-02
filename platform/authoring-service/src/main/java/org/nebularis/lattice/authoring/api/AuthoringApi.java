// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.api;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.nebularis.lattice.authoring.detection.ConstructDetector;
import org.nebularis.lattice.authoring.detection.Detection;
import org.nebularis.lattice.authoring.jobs.JobRegistry;
import org.nebularis.lattice.authoring.jobs.JobView;
import org.nebularis.lattice.authoring.json.ContractSchemas;
import org.nebularis.lattice.authoring.json.Json;
import org.nebularis.lattice.authoring.messaging.AnalysisBus;
import org.nebularis.lattice.authoring.model.DocumentSnapshot;
import org.nebularis.lattice.authoring.model.GraphRef;
import org.nebularis.lattice.authoring.model.SnapshotReader;
import org.nebularis.lattice.authoring.rdf.CanonicalHash;
import org.nebularis.lattice.authoring.rdf.IriMinter;
import org.nebularis.lattice.authoring.rdf.Vocab;
import org.nebularis.lattice.authoring.rdf.WordingMapper;
import org.nebularis.lattice.authoring.store.AuthoringStore;
import org.nebularis.lattice.authoring.store.DocumentRegistry;
import org.nebularis.lattice.authoring.template.AuthoringTemplate;
import org.nebularis.lattice.authoring.template.ConformanceChecker;
import org.nebularis.lattice.authoring.template.Finding;
import org.nebularis.lattice.authoring.template.SampleCatalog;
import org.nebularis.lattice.authoring.template.SampleSummary;
import org.nebularis.lattice.authoring.template.TemplateCatalog;
import org.nebularis.lattice.authoring.template.TemplateFindings;
import org.nebularis.lattice.authoring.template.TemplateSummary;
import org.nebularis.lattice.authoring.validation.ValidationReportView;
import org.nebularis.lattice.authoring.validation.WordingValidator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Everything the word authoring POC service does, with no knowledge of HTTP: one method per route
 * of plan WA4, plus {@link #onAnalysisResult(JsonNode)} for the worker's result event.
 * {@code http.AuthoringHttpServer} is the only class that knows this runs behind Javalin.
 */
public final class AuthoringApi {
    private static final Logger LOG = LoggerFactory.getLogger(AuthoringApi.class);
    private static final List<String> GRAPH_KINDS = List.of("wording", "proposal");

    private final ContractSchemas schemas;
    private final TemplateCatalog templates;
    private final SampleCatalog samples;
    private final IriMinter minter;
    private final WordingMapper mapper;
    private final WordingValidator validator;
    private final ConstructDetector detector;
    private final TemplateFindings templateFindings;
    private final ConformanceChecker conformanceChecker;
    private final AuthoringStore store;
    private final DocumentRegistry registry;
    private final AnalysisBus bus;
    private final JobRegistry jobs;
    private final Clock clock;
    private final Map<String, AnalysisView> analysisCache = new HashMap<>();

    public AuthoringApi(ContractSchemas schemas, TemplateCatalog templates, SampleCatalog samples, IriMinter minter,
                        WordingMapper mapper, WordingValidator validator, ConstructDetector detector,
                        TemplateFindings templateFindings, ConformanceChecker conformanceChecker,
                        AuthoringStore store, DocumentRegistry registry, AnalysisBus bus, JobRegistry jobs,
                        Clock clock) {
        this.schemas = schemas;
        this.templates = templates;
        this.samples = samples;
        this.minter = minter;
        this.mapper = mapper;
        this.validator = validator;
        this.detector = detector;
        this.templateFindings = templateFindings;
        this.conformanceChecker = conformanceChecker;
        this.store = store;
        this.registry = registry;
        this.bus = bus;
        this.jobs = jobs;
        this.clock = clock;
    }

    public ApiResponse<HealthView> health() {
        boolean storeUp = store.ping();
        boolean busUp = bus.ping();
        HealthView view = HealthView.of(storeUp, busUp);
        return storeUp && busUp ? ApiResponse.ok(view) : ApiResponse.unavailable(view);
    }

    public ApiResponse<List<TemplateSummary>> listTemplates() {
        return ApiResponse.ok(templates.list());
    }

    public ApiResponse<?> getTemplate(String templateId) {
        if (!PathParams.isKey(templateId)) {
            return ApiResponse.badRequest("templateId is not a Key", List.of());
        }
        return templates.raw(templateId)
            .<ApiResponse<?>>map(ApiResponse::ok)
            .orElseGet(() -> ApiResponse.notFound("no such template: " + templateId));
    }

    public ApiResponse<List<SampleSummary>> listSamples() {
        return ApiResponse.ok(samples.list());
    }

    public ApiResponse<?> getSample(String sampleId) {
        if (!PathParams.isKey(sampleId)) {
            return ApiResponse.badRequest("sampleId is not a Key", List.of());
        }
        return samples.raw(sampleId)
            .<ApiResponse<?>>map(ApiResponse::ok)
            .orElseGet(() -> ApiResponse.notFound("no such sample: " + sampleId));
    }

    public ApiResponse<?> getDocument(String documentId) {
        if (!PathParams.isUuid(documentId)) {
            return ApiResponse.badRequest("documentId is not a Uuid", List.of());
        }
        return registry.find(documentId)
            .<ApiResponse<?>>map(ApiResponse::ok)
            .orElseGet(() -> ApiResponse.notFound("no such document: " + documentId));
    }

    /** Plan WA4 "submitSnapshot, in this order". */
    public ApiResponse<?> submitSnapshot(String documentId, JsonNode body) {
        if (!PathParams.isUuid(documentId)) {
            return ApiResponse.badRequest("documentId is not a Uuid", List.of());
        }

        List<String> submissionMessages = schemas.validate("snapshot-submission", body);
        if (!submissionMessages.isEmpty()) {
            return ApiResponse.badRequest("snapshot-submission does not validate", submissionMessages);
        }

        JsonNode snapshotNode = body.get("snapshot");
        if (!documentId.equals(snapshotNode.get("documentId").asText())) {
            return ApiResponse.badRequest("documentId in the path and body must match", List.of());
        }
        DocumentSnapshot snapshot = SnapshotReader.read(snapshotNode);

        Optional<AuthoringTemplate> template = templates.get(snapshot.templateId());
        if (template.isEmpty()) {
            return ApiResponse.notFound("no such template: " + snapshot.templateId());
        }

        int latest = registry.latestRevision(documentId);
        JsonNode baseRevisionNode = body.get("baseRevision");
        Integer baseRevision = baseRevisionNode.isNull() ? null : baseRevisionNode.asInt();
        boolean conflict = (baseRevision == null && latest > 0) || (baseRevision != null && baseRevision != latest);
        if (conflict) {
            return ApiResponse.conflict("the latest revision is " + latest);
        }

        int revision = latest + 1;
        Model model = mapper.map(snapshot, revision);
        String hash = CanonicalHash.of(model);
        String wordingGraphIri = minter.wordingGraph(documentId, revision);
        store.putGraph(wordingGraphIri, model);
        GraphRef wordingGraph = GraphRef.of(wordingGraphIri, hash);

        ValidationReportView validation = validator.validate(model);
        List<Detection> detections = detector.detect(snapshot);
        List<Finding> findings = templateFindings.check(snapshot, template.get());

        registry.record(documentId, revision, snapshot.title(), snapshot.templateId(), wordingGraph);

        String jobId = UUID.randomUUID().toString();
        jobs.queue(jobId, documentId, revision);
        publishAnalysisRequest(jobId, documentId, revision, wordingGraph);
        JobView job = jobs.get(jobId).orElseThrow();

        return ApiResponse.ok(new SnapshotAccepted(documentId, revision, wordingGraph, validation, detections,
            findings, job.summary()));
    }

    private void publishAnalysisRequest(String jobId, String documentId, int revision, GraphRef wordingGraph) {
        ObjectNode request = Json.MAPPER.createObjectNode();
        request.put("jobId", jobId);
        request.put("correlationId", jobId);
        request.put("documentId", documentId);
        request.put("revision", revision);
        request.set("wordingGraph", Json.MAPPER.valueToTree(wordingGraph));
        request.put("wordingIri", minter.wording(documentId));
        request.put("proposalGraphIri", minter.proposalGraph(documentId, revision));
        request.put("requestedAt", clock.instant().toString());

        List<String> requestMessages = schemas.validate("wording-analysis-request", request);
        if (!requestMessages.isEmpty()) {
            throw new IllegalStateException("built an invalid wording-analysis-request: " + requestMessages);
        }
        try {
            bus.publish(request);
        } catch (RuntimeException e) {
            LOG.warn("could not publish the analysis request for job {}: {}", jobId, e.toString());
            jobs.fail(jobId, "analysis queue unavailable");
        }
    }

    public ApiResponse<?> getJob(String jobId) {
        if (!PathParams.isUuid(jobId)) {
            return ApiResponse.badRequest("jobId is not a Uuid", List.of());
        }
        return jobs.get(jobId)
            .<ApiResponse<?>>map(ApiResponse::ok)
            .orElseGet(() -> ApiResponse.notFound("no such job: " + jobId));
    }

    public ApiResponse<?> getAnalysis(String documentId, String revisionParam) {
        if (!PathParams.isUuid(documentId)) {
            return ApiResponse.badRequest("documentId is not a Uuid", List.of());
        }
        if (!PathParams.isRevision(revisionParam)) {
            return ApiResponse.badRequest("revision is not a valid revision number", List.of());
        }
        int revision = Integer.parseInt(revisionParam);

        AnalysisView cached = analysisCache.get(analysisKey(documentId, revision));
        if (cached != null) {
            return ApiResponse.ok(cached);
        }

        Optional<Model> graph = store.getGraph(minter.analysisGraph(documentId, revision));
        if (graph.isEmpty()) {
            return ApiResponse.notFound("analysis not available");
        }
        Resource revisionResource = graph.get().createResource(minter.revision(documentId, revision));
        if (!revisionResource.hasProperty(Vocab.WAP_ANALYSIS_JSON)) {
            return ApiResponse.notFound("analysis not available");
        }
        String json = revisionResource.getRequiredProperty(Vocab.WAP_ANALYSIS_JSON).getString();
        try {
            return ApiResponse.ok(Json.MAPPER.readTree(json));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    public ApiResponse<?> getGraph(String documentId, String revisionParam, String kind) {
        if (!PathParams.isUuid(documentId)) {
            return ApiResponse.badRequest("documentId is not a Uuid", List.of());
        }
        if (!PathParams.isRevision(revisionParam)) {
            return ApiResponse.badRequest("revision is not a valid revision number", List.of());
        }
        if (!GRAPH_KINDS.contains(kind)) {
            return ApiResponse.badRequest("kind must be wording or proposal", List.of());
        }
        int revision = Integer.parseInt(revisionParam);
        String graphIri = "wording".equals(kind)
            ? minter.wordingGraph(documentId, revision)
            : minter.proposalGraph(documentId, revision);
        return store.getGraph(graphIri)
            .<ApiResponse<?>>map(model -> ApiResponse.ok(turtleOf(model), ApiResponse.TEXT_TURTLE))
            .orElseGet(() -> ApiResponse.notFound("no such graph"));
    }

    /** Plan WA4 "onAnalysisResult". */
    public void onAnalysisResult(JsonNode result) {
        List<String> messages = schemas.validate("wording-analysis-result", result);
        if (!messages.isEmpty()) {
            LOG.warn("dropping an invalid wording-analysis-result: {}", messages);
            return;
        }
        String jobId = result.get("jobId").asText();
        if (jobs.get(jobId).isEmpty()) {
            LOG.warn("dropping a wording-analysis-result for an unknown job: {}", jobId);
            return;
        }
        if ("failed".equals(result.get("status").asText())) {
            jobs.fail(jobId, result.get("error").asText());
            return;
        }
        completeAnalysis(jobId, result);
    }

    private void completeAnalysis(String jobId, JsonNode result) {
        String documentId = result.get("documentId").asText();
        int revision = result.get("revision").asInt();

        Optional<AuthoringTemplate> template = registry.find(documentId)
            .flatMap(view -> templates.get(view.templateId()));
        if (template.isEmpty()) {
            LOG.warn("dropping a completed wording-analysis-result for an unknown document: {}", documentId);
            return;
        }

        JsonNode analysis = result.get("analysis");
        GraphRef proposalGraph = readGraphRef(result.get("proposalGraph"));
        List<Finding> conformance = conformanceChecker.check(analysis, template.get());
        AnalysisView view = new AnalysisView(documentId, revision, analysis, conformance, proposalGraph);

        Model model = ModelFactory.createDefaultModel();
        Resource revisionResource = model.createResource(minter.revision(documentId, revision));
        revisionResource.addProperty(Vocab.WAP_ANALYSIS_JSON, writeJson(view));
        store.putGraph(minter.analysisGraph(documentId, revision), model);

        analysisCache.put(analysisKey(documentId, revision), view);
        jobs.complete(jobId);
    }

    private static GraphRef readGraphRef(JsonNode node) {
        return new GraphRef(node.get("tenantId").asText(), node.get("projectId").asText(),
            node.get("graphIri").asText(), node.get("revisionHash").asText());
    }

    private static String writeJson(Object value) {
        try {
            return Json.MAPPER.writeValueAsString(value);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static String analysisKey(String documentId, int revision) {
        return documentId + "@" + revision;
    }

    private static String turtleOf(Model model) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        RDFDataMgr.write(out, model, Lang.TURTLE);
        return out.toString(StandardCharsets.UTF_8);
    }
}
