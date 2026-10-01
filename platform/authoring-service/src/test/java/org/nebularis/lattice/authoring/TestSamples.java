// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Path;
import org.nebularis.lattice.authoring.json.Json;
import org.nebularis.lattice.authoring.model.DocumentSnapshot;
import org.nebularis.lattice.authoring.model.SnapshotReader;

/** Reads the three committed samples under {@code contracts/authoring/samples}, for tests. */
public final class TestSamples {
    public static final String FACILITY_AGREEMENT = "facility-agreement";
    public static final String SOFTWARE_LICENCE = "software-licence";
    public static final String PROPERTY_POLICY = "property-policy";

    private TestSamples() {
    }

    public static JsonNode rawNode(String sampleId) {
        Path path = RepoPaths.contracts().resolve("authoring").resolve("samples").resolve(sampleId + ".json");
        try {
            return Json.MAPPER.readTree(path.toFile());
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    public static DocumentSnapshot read(String sampleId) {
        return SnapshotReader.read(rawNode(sampleId));
    }
}
