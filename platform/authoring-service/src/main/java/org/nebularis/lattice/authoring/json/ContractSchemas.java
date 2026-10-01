// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.json;

import com.fasterxml.jackson.databind.JsonNode;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.net.URI;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * Loads every JSON Schema the word authoring POC uses from the classpath, keyed by both schema
 * name (the file name without {@code .schema.json}) and {@code $id}, and validates JSON nodes
 * against them. The only place the set of schema resources is listed.
 */
public final class ContractSchemas {
    private static final List<String> SCHEMA_RESOURCES = List.of(
        "contracts/authoring/common.schema.json",
        "contracts/authoring/document-snapshot.schema.json",
        "contracts/authoring/snapshot-submission.schema.json",
        "contracts/authoring/snapshot-accepted.schema.json",
        "contracts/authoring/authoring-template.schema.json",
        "contracts/authoring/template-list.schema.json",
        "contracts/authoring/sample-list.schema.json",
        "contracts/authoring/document-view.schema.json",
        "contracts/authoring/job-view.schema.json",
        "contracts/authoring/analysis-view.schema.json",
        "contracts/authoring/health.schema.json",
        "contracts/authoring/error.schema.json",
        "contracts/events/wording-analysis-request.schema.json",
        "contracts/events/wording-analysis-result.schema.json"
    );

    private static final int MAX_MESSAGES = 20;

    private final Map<String, JsonSchema> schemasByName;

    public ContractSchemas() {
        Map<String, String> contentById = new LinkedHashMap<>();
        Map<String, String> idByName = new LinkedHashMap<>();
        for (String resource : SCHEMA_RESOURCES) {
            JsonNode schema = readResource(resource);
            String id = schema.get("$id").asText();
            contentById.put(id, schema.toString());
            idByName.put(nameOf(resource), id);
        }

        JsonSchemaFactory factory = JsonSchemaFactory
            .builder(JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012))
            .schemaLoaders(loaders -> loaders.schemas(contentById))
            .build();

        Map<String, JsonSchema> schemas = new LinkedHashMap<>();
        for (Map.Entry<String, String> entry : idByName.entrySet()) {
            schemas.put(entry.getKey(), factory.getSchema(URI.create(entry.getValue())));
        }
        this.schemasByName = Map.copyOf(schemas);
    }

    /** Returns at most {@value #MAX_MESSAGES} validation messages, empty when {@code node} is valid. */
    public List<String> validate(String schemaName, JsonNode node) {
        JsonSchema schema = schemasByName.get(schemaName);
        if (schema == null) {
            throw new IllegalArgumentException("unknown schema: " + schemaName);
        }
        Set<ValidationMessage> messages = schema.validate(node);
        return messages.stream().map(ValidationMessage::getMessage).limit(MAX_MESSAGES).collect(Collectors.toList());
    }

    private static String nameOf(String resource) {
        String fileName = resource.substring(resource.lastIndexOf('/') + 1);
        return fileName.substring(0, fileName.length() - ".schema.json".length());
    }

    private static JsonNode readResource(String resource) {
        try (InputStream in = ContractSchemas.class.getClassLoader().getResourceAsStream(resource)) {
            if (in == null) {
                throw new IllegalStateException("missing classpath resource: " + resource);
            }
            return Json.MAPPER.readTree(in);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
