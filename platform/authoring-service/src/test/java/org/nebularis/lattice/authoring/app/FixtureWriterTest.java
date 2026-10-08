// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.app;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.authoring.RepoPaths;

class FixtureWriterTest {
    // --- S2-15 ------------------------------------------------------------------------------------

    @Test
    void regenerating_the_fixtures_reproduces_the_committed_files(@TempDir Path tempDir) throws IOException {
        Path authoringDir = RepoPaths.contracts().resolve("authoring");
        Path tempAuthoringDir = tempDir.resolve("authoring");
        Files.createDirectories(tempAuthoringDir.resolve("samples"));
        for (String sampleId : List.of("facility-agreement", "software-licence", "property-policy")) {
            Files.copy(
                authoringDir.resolve("samples").resolve(sampleId + ".json"),
                tempAuthoringDir.resolve("samples").resolve(sampleId + ".json"));
        }

        FixtureWriter.write(tempAuthoringDir);

        for (String sampleId : List.of("facility-agreement", "software-licence", "property-policy")) {
            Path expected = authoringDir.resolve("fixtures").resolve("wording").resolve(sampleId + ".nt");
            Path actual = tempAuthoringDir.resolve("fixtures").resolve("wording").resolve(sampleId + ".nt");
            assertEquals(Files.readString(expected), Files.readString(actual), sampleId);
        }
    }
}
