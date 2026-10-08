// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.template;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.nebularis.lattice.authoring.json.ContractSchemas;
import org.nebularis.lattice.authoring.model.DocumentSnapshot;
import org.nebularis.lattice.authoring.model.SnapshotReader;

/** The sample documents shipped with the service, so an author can start from a filled document. */
public final class SampleCatalog {
    public static final List<String> SAMPLE_IDS =
        List.of("facility-agreement", "software-licence", "property-policy");

    private final Map<String, JsonNode> rawById = new LinkedHashMap<>();
    private final Map<String, DocumentSnapshot> byId = new LinkedHashMap<>();

    public SampleCatalog(ContractSchemas schemas) {
        this(schemas, SAMPLE_IDS);
    }

    SampleCatalog(ContractSchemas schemas, List<String> sampleIds) {
        for (String sampleId : sampleIds) {
            JsonNode node = schemas.readValidated("document-snapshot",
                "contracts/authoring/samples/" + sampleId + ".json");
            rawById.put(sampleId, node);
            byId.put(sampleId, SnapshotReader.read(node));
        }
    }

    public List<SampleSummary> list() {
        return byId.entrySet().stream()
            .map(entry -> new SampleSummary(entry.getKey(), entry.getValue().title(), entry.getValue().templateId()))
            .toList();
    }

    public Optional<DocumentSnapshot> get(String sampleId) {
        return Optional.ofNullable(byId.get(sampleId));
    }

    public Optional<JsonNode> raw(String sampleId) {
        return Optional.ofNullable(rawById.get(sampleId));
    }
}
