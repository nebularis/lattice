// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.api;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.authoring.ApiFixture;
import org.nebularis.lattice.authoring.TestSamples;
import org.nebularis.lattice.authoring.model.JobStatus;

class SubmitSnapshotTest {

    /** S4-01: a new facility snapshot, revision 1, stored, registered, one request published. */
    @Test
    void acceptsANewSnapshotAndPublishesAnAnalysisRequest() {
        ApiFixture fx = new ApiFixture();
        JsonNode snapshot = TestSamples.rawNode(TestSamples.FACILITY_AGREEMENT);
        String documentId = snapshot.get("documentId").asText();

        ApiResponse<?> response = fx.api.submitSnapshot(documentId, fx.submission(null, snapshot));

        assertEquals(200, response.status());
        SnapshotAccepted accepted = (SnapshotAccepted) response.body();
        assertEquals(documentId, accepted.documentId());
        assertEquals(1, accepted.revision());
        assertTrue(fx.store.getGraph(accepted.wordingGraph().graphIri()).isPresent());
        assertEquals(1, fx.registry.latestRevision(documentId));

        assertEquals(1, fx.bus.published().size());
        JsonNode request = fx.bus.published().get(0);
        assertEquals(accepted.wordingGraph().graphIri(), request.get("wordingGraph").get("graphIri").asText());
        assertEquals(accepted.wordingGraph().revisionHash(), request.get("wordingGraph").get("revisionHash").asText());
        assertEquals(fx.minter.wording(documentId), request.get("wordingIri").asText());
        assertEquals(fx.minter.proposalGraph(documentId, 1), request.get("proposalGraphIri").asText());
        assertEquals(JobStatus.QUEUED, accepted.job().status());
    }

    /** S4-02: a correct base revision advances it, a null or wrong base revision conflicts. */
    @Test
    void enforcesOptimisticConcurrencyOnBaseRevision() {
        ApiFixture fx = new ApiFixture();
        JsonNode snapshot = TestSamples.rawNode(TestSamples.FACILITY_AGREEMENT);
        String documentId = snapshot.get("documentId").asText();
        fx.api.submitSnapshot(documentId, fx.submission(null, snapshot));

        ApiResponse<?> withCorrectBase = fx.api.submitSnapshot(documentId, fx.submission(1, snapshot));
        assertEquals(200, withCorrectBase.status());
        assertEquals(2, ((SnapshotAccepted) withCorrectBase.body()).revision());

        assertEquals(409, fx.api.submitSnapshot(documentId, fx.submission(null, snapshot)).status());
        assertEquals(409, fx.api.submitSnapshot(documentId, fx.submission(5, snapshot)).status());
    }

    /** S4-03: mismatched ids, a non-Uuid path id, and an extra property each give 400. */
    @Test
    void rejectsMismatchedOrMalformedSubmissions() {
        ApiFixture fx = new ApiFixture();
        JsonNode snapshot = TestSamples.rawNode(TestSamples.FACILITY_AGREEMENT);
        String documentId = snapshot.get("documentId").asText();

        assertEquals(400, fx.api.submitSnapshot("00000002-0000-4000-8000-000000000000",
            fx.submission(null, snapshot)).status());
        assertEquals(400, fx.api.submitSnapshot("not-a-uuid", fx.submission(null, snapshot)).status());

        ObjectNode withExtra = (ObjectNode) snapshot.deepCopy();
        withExtra.put("notInTheSchema", true);
        ApiResponse<?> extraProperty = fx.api.submitSnapshot(documentId, fx.submission(null, withExtra));
        assertEquals(400, extraProperty.status());
        assertFalse(((ErrorBody) extraProperty.body()).details().isEmpty());
    }

    /** S4-04: a snapshot naming a template that does not exist gives 404. */
    @Test
    void rejectsAnUnknownTemplate() {
        ApiFixture fx = new ApiFixture();
        ObjectNode snapshot = (ObjectNode) TestSamples.rawNode(TestSamples.FACILITY_AGREEMENT).deepCopy();
        String documentId = "00000009-0000-4000-8000-000000000000";
        snapshot.put("documentId", documentId);
        snapshot.put("templateId", "nope");

        assertEquals(404, fx.api.submitSnapshot(documentId, fx.submission(null, snapshot)).status());
    }

    /** S4-05: the bus set to fail still accepts the snapshot, with the job marked failed. */
    @Test
    void marksTheJobFailedWhenTheBusCannotPublish() {
        ApiFixture fx = new ApiFixture();
        fx.bus.failOnPublish();
        JsonNode snapshot = TestSamples.rawNode(TestSamples.SOFTWARE_LICENCE);
        String documentId = snapshot.get("documentId").asText();

        ApiResponse<?> response = fx.api.submitSnapshot(documentId, fx.submission(null, snapshot));

        assertEquals(200, response.status());
        assertEquals(JobStatus.FAILED, ((SnapshotAccepted) response.body()).job().status());
    }
}
