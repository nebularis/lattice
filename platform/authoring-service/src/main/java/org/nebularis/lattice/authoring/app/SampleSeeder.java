// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.app;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.List;
import org.nebularis.lattice.authoring.api.AuthoringApi;
import org.nebularis.lattice.authoring.json.Json;
import org.nebularis.lattice.authoring.store.DocumentRegistry;
import org.nebularis.lattice.authoring.template.SampleCatalog;
import org.nebularis.lattice.authoring.template.SampleSummary;

/** Submits every sample the registry does not already hold, as revision 1 (decision WA-D10). */
public final class SampleSeeder {
    private final SampleCatalog samples;
    private final DocumentRegistry registry;
    private final AuthoringApi api;

    public SampleSeeder(SampleCatalog samples, DocumentRegistry registry, AuthoringApi api) {
        this.samples = samples;
        this.registry = registry;
        this.api = api;
    }

    public int seed() {
        List<String> existing = registry.documentIds();
        int seeded = 0;
        for (SampleSummary summary : samples.list()) {
            JsonNode raw = samples.raw(summary.sampleId()).orElseThrow();
            String documentId = raw.get("documentId").asText();
            if (existing.contains(documentId)) {
                continue;
            }
            ObjectNode submission = Json.MAPPER.createObjectNode();
            submission.putNull("baseRevision");
            submission.set("snapshot", raw);
            api.submitSnapshot(documentId, submission);
            seeded++;
        }
        return seeded;
    }
}
