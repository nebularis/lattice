// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.template;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.nebularis.lattice.authoring.json.ContractSchemas;

/** The templates shipped with the service, validated at construction so a bad file fails fast. */
public final class TemplateCatalog {
    public static final List<String> TEMPLATE_IDS =
        List.of("facility-agreement", "software-licence", "property-policy");

    private final Map<String, JsonNode> rawById = new LinkedHashMap<>();
    private final Map<String, AuthoringTemplate> byId = new LinkedHashMap<>();

    public TemplateCatalog(ContractSchemas schemas) {
        this(schemas, TEMPLATE_IDS.stream().map(id -> "contracts/authoring/templates/" + id + ".json").toList());
    }

    TemplateCatalog(ContractSchemas schemas, List<String> resources) {
        for (String resource : resources) {
            JsonNode node = schemas.readValidated("authoring-template", resource);
            AuthoringTemplate template = AuthoringTemplate.from(node);
            rawById.put(template.templateId(), node);
            byId.put(template.templateId(), template);
        }
    }

    public List<TemplateSummary> list() {
        return byId.values().stream().map(AuthoringTemplate::summary).toList();
    }

    public Optional<AuthoringTemplate> get(String templateId) {
        return Optional.ofNullable(byId.get(templateId));
    }

    public Optional<JsonNode> raw(String templateId) {
        return Optional.ofNullable(rawById.get(templateId));
    }
}
