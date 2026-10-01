// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.app;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.apache.jena.rdf.model.Model;
import org.nebularis.lattice.authoring.json.Json;
import org.nebularis.lattice.authoring.model.DocumentSnapshot;
import org.nebularis.lattice.authoring.model.SnapshotReader;
import org.nebularis.lattice.authoring.rdf.CanonicalHash;
import org.nebularis.lattice.authoring.rdf.WordingMapper;

/**
 * Regenerates the POC's generated wording fixtures from the samples: {@code mise run
 * build:authoring-fixtures}, or {@code java -cp authoring-service.jar
 * org.nebularis.lattice.authoring.app.FixtureWriter &lt;contracts/authoring dir&gt;}.
 */
public final class FixtureWriter {
    private static final String DEFAULT_BASE = "https://example.org/lattice/authoring/";
    private static final List<String> SAMPLE_IDS =
        List.of("facility-agreement", "software-licence", "property-policy");

    private FixtureWriter() {
    }

    public static void main(String[] args) throws IOException {
        if (args.length != 1) {
            throw new IllegalArgumentException("usage: FixtureWriter <contracts/authoring directory>");
        }
        write(Path.of(args[0]));
    }

    public static void write(Path authoringDir) throws IOException {
        Path samplesDir = authoringDir.resolve("samples");
        Path outputDir = authoringDir.resolve("fixtures").resolve("wording");
        Files.createDirectories(outputDir);
        WordingMapper mapper = new WordingMapper(DEFAULT_BASE);
        for (String sampleId : SAMPLE_IDS) {
            Path samplePath = samplesDir.resolve(sampleId + ".json");
            JsonNode node = Json.MAPPER.readTree(samplePath.toFile());
            DocumentSnapshot snapshot = SnapshotReader.read(node);
            Model model = mapper.map(snapshot, 1);
            Path outputPath = outputDir.resolve(sampleId + ".nt");
            Files.writeString(outputPath, CanonicalHash.canonicalText(model), StandardCharsets.UTF_8);
            System.out.println("wrote " + outputPath);
        }
    }
}
