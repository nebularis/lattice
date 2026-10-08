// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import org.nebularis.lattice.authoring.api.AuthoringApi;
import org.nebularis.lattice.authoring.detection.ConstructDetector;
import org.nebularis.lattice.authoring.json.ContractSchemas;
import org.nebularis.lattice.authoring.json.Json;
import org.nebularis.lattice.authoring.jobs.JobRegistry;
import org.nebularis.lattice.authoring.messaging.InMemoryAnalysisBus;
import org.nebularis.lattice.authoring.rdf.IriMinter;
import org.nebularis.lattice.authoring.rdf.WordingMapper;
import org.nebularis.lattice.authoring.store.DocumentRegistry;
import org.nebularis.lattice.authoring.store.InMemoryAuthoringStore;
import org.nebularis.lattice.authoring.template.ConformanceChecker;
import org.nebularis.lattice.authoring.template.SampleCatalog;
import org.nebularis.lattice.authoring.template.TemplateCatalog;
import org.nebularis.lattice.authoring.template.TemplateFindings;
import org.nebularis.lattice.authoring.validation.WordingValidator;

/**
 * One full in-memory wiring of {@link AuthoringApi}, built fresh for each test (plan WA4 "the
 * in-memory wiring"). The clock is fixed so {@code requestedAt} is reproducible.
 */
public final class ApiFixture {
    public final ContractSchemas schemas = new ContractSchemas();
    public final TemplateCatalog templates = new TemplateCatalog(schemas);
    public final SampleCatalog samples = new SampleCatalog(schemas);
    public final IriMinter minter = new IriMinter("https://example.org/lattice/authoring/");
    public final WordingMapper mapper = new WordingMapper(minter.base());
    public final WordingValidator validator = new WordingValidator();
    public final ConstructDetector detector = new ConstructDetector();
    public final TemplateFindings templateFindings = new TemplateFindings();
    public final ConformanceChecker conformanceChecker = new ConformanceChecker();
    public final InMemoryAuthoringStore store = new InMemoryAuthoringStore();
    public final DocumentRegistry registry = new DocumentRegistry(store, minter);
    public final InMemoryAnalysisBus bus = new InMemoryAnalysisBus();
    public final JobRegistry jobs = new JobRegistry();
    public final Clock clock = Clock.fixed(Instant.parse("2026-10-01T12:00:00Z"), ZoneOffset.UTC);
    public final AuthoringApi api;

    public ApiFixture() {
        this.api = new AuthoringApi(schemas, templates, samples, minter, mapper, validator, detector,
            templateFindings, conformanceChecker, store, registry, bus, jobs, clock);
        bus.onResult(api::onAnalysisResult);
    }

    /** A {@code snapshot-submission} body for the given base revision (null for none) and snapshot. */
    public JsonNode submission(Integer baseRevision, JsonNode snapshot) {
        ObjectNode body = Json.MAPPER.createObjectNode();
        if (baseRevision == null) {
            body.putNull("baseRevision");
        } else {
            body.put("baseRevision", baseRevision);
        }
        body.set("snapshot", snapshot);
        return body;
    }
}
