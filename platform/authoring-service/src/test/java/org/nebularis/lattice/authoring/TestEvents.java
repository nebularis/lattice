// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring;

import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Path;
import org.nebularis.lattice.authoring.json.Json;

/** Builds {@code wording-analysis-result} events for a test, from the committed valid fixtures. */
public final class TestEvents {
    private TestEvents() {
    }

    public static ObjectNode completedResult(ApiFixture fx, String jobId, String documentId, int revision) {
        ObjectNode node = fixture("wording-analysis-result--completed-minimal");
        node.put("jobId", jobId);
        node.put("correlationId", jobId);
        node.put("documentId", documentId);
        node.put("revision", revision);
        ((ObjectNode) node.get("proposalGraph")).put("graphIri", fx.minter.proposalGraph(documentId, revision));
        return node;
    }

    public static ObjectNode failedResult(String jobId, String documentId, int revision, String error) {
        ObjectNode node = fixture("wording-analysis-result--failed-minimal");
        node.put("jobId", jobId);
        node.put("correlationId", jobId);
        node.put("documentId", documentId);
        node.put("revision", revision);
        node.put("error", error);
        return node;
    }

    private static ObjectNode fixture(String id) {
        Path path = RepoPaths.contracts().resolve("authoring/fixtures/valid").resolve(id + ".json");
        try {
            return (ObjectNode) Json.MAPPER.readTree(path.toFile());
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
