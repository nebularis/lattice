// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.json;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import org.nebularis.lattice.authoring.RepoPaths;

class ContractSchemasTest {
    private static final ContractSchemas SCHEMAS = new ContractSchemas();

    static Stream<Path> validFixtures() throws IOException {
        return Files.list(RepoPaths.contracts().resolve("authoring").resolve("fixtures").resolve("valid")).sorted();
    }

    static Stream<Path> invalidFixtures() throws IOException {
        return Files.list(RepoPaths.contracts().resolve("authoring").resolve("fixtures").resolve("invalid")).sorted();
    }

    @ParameterizedTest
    @MethodSource("validFixtures")
    void a_valid_fixture_gives_no_message(Path path) throws IOException {
        List<String> messages = SCHEMAS.validate(schemaName(path), Json.MAPPER.readTree(path.toFile()));
        assertTrue(messages.isEmpty(), path.getFileName() + ": " + messages);
    }

    @ParameterizedTest
    @MethodSource("invalidFixtures")
    void an_invalid_fixture_gives_at_least_one_message(Path path) throws IOException {
        List<String> messages = SCHEMAS.validate(schemaName(path), Json.MAPPER.readTree(path.toFile()));
        assertFalse(messages.isEmpty(), path.getFileName() + ": expected at least one message");
    }

    @Test
    void an_unknown_schema_name_is_rejected() {
        try {
            SCHEMAS.validate("no-such-schema", Json.MAPPER.createObjectNode());
            fail("expected IllegalArgumentException");
        } catch (IllegalArgumentException expected) {
            assertTrue(expected.getMessage().contains("no-such-schema"));
        }
    }

    @Test
    void the_three_samples_validate_against_document_snapshot() throws IOException {
        Path samplesDir = RepoPaths.contracts().resolve("authoring").resolve("samples");
        for (String sampleId : List.of("facility-agreement", "software-licence", "property-policy")) {
            JsonNode node = Json.MAPPER.readTree(samplesDir.resolve(sampleId + ".json").toFile());
            List<String> messages = SCHEMAS.validate("document-snapshot", node);
            assertEquals(List.of(), messages, sampleId);
        }
    }

    private static String schemaName(Path path) {
        String fileName = path.getFileName().toString();
        return fileName.substring(0, fileName.indexOf("--"));
    }
}
