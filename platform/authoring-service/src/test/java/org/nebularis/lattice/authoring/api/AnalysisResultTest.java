// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.api;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.authoring.ApiFixture;
import org.nebularis.lattice.authoring.TestEvents;
import org.nebularis.lattice.authoring.TestSamples;
import org.nebularis.lattice.authoring.jobs.JobRegistry;
import org.nebularis.lattice.authoring.jobs.JobView;
import org.nebularis.lattice.authoring.json.Json;
import org.nebularis.lattice.authoring.model.JobStatus;

class AnalysisResultTest {

    /** S4-06: a completed result completes the job and the analysis is served from a second API over the same store. */
    @Test
    void completesAJobAndServesTheSameAnalysisFromAFreshApi() {
        ApiFixture fx = new ApiFixture();
        JsonNode snapshot = TestSamples.rawNode(TestSamples.FACILITY_AGREEMENT);
        String documentId = snapshot.get("documentId").asText();
        SnapshotAccepted accepted = (SnapshotAccepted) fx.api.submitSnapshot(documentId,
            fx.submission(null, snapshot)).body();
        String jobId = accepted.job().jobId();

        fx.bus.deliver(TestEvents.completedResult(fx, jobId, documentId, 1));

        assertEquals(JobStatus.COMPLETED, fx.jobs.get(jobId).orElseThrow().status());
        ApiResponse<?> analysis = fx.api.getAnalysis(documentId, "1");
        assertEquals(200, analysis.status());

        AuthoringApi second = new AuthoringApi(fx.schemas, fx.templates, fx.samples, fx.minter, fx.mapper,
            fx.validator, fx.detector, fx.templateFindings, fx.conformanceChecker, fx.store, fx.registry, fx.bus,
            new JobRegistry(), fx.clock);
        ApiResponse<?> analysisAgain = second.getAnalysis(documentId, "1");

        assertEquals(200, analysisAgain.status());
        assertEquals(Json.MAPPER.valueToTree(analysis.body()), Json.MAPPER.valueToTree(analysisAgain.body()));
    }

    /** S4-07: a failed result fails the job with its error, and the analysis stays unavailable. */
    @Test
    void marksAFailedResultAndLeavesTheAnalysisUnavailable() {
        ApiFixture fx = new ApiFixture();
        JsonNode snapshot = TestSamples.rawNode(TestSamples.SOFTWARE_LICENCE);
        String documentId = snapshot.get("documentId").asText();
        SnapshotAccepted accepted = (SnapshotAccepted) fx.api.submitSnapshot(documentId,
            fx.submission(null, snapshot)).body();
        String jobId = accepted.job().jobId();

        fx.bus.deliver(TestEvents.failedResult(jobId, documentId, 1, "wording graph not found"));

        JobView job = fx.jobs.get(jobId).orElseThrow();
        assertEquals(JobStatus.FAILED, job.status());
        assertEquals("wording graph not found", job.error());
        assertEquals(404, fx.api.getAnalysis(documentId, "1").status());
    }

    /** S4-08: a result for an unknown job, and an invalid result, are dropped without throwing. */
    @Test
    void ignoresResultsForUnknownJobsAndInvalidEvents() {
        ApiFixture fx = new ApiFixture();

        assertDoesNotThrow(() -> fx.bus.deliver(TestEvents.completedResult(fx,
            "00000009-0000-4000-8000-000000000001", "00000009-0000-4000-8000-000000000000", 1)));

        ObjectNode invalid = Json.MAPPER.createObjectNode();
        invalid.put("notAValidResult", true);
        assertDoesNotThrow(() -> fx.bus.deliver(invalid));
    }
}
