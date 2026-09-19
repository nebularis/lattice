package org.nebularis.lattice.release;

import static org.junit.jupiter.api.Assertions.assertTrue;
import java.net.URI;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.semantic.GraphReference;

class ReleaseProvenanceProjectorTest {
    private static final String DIGEST = "sha256:" + "a".repeat(64);

    @Test
    void projectsSemanticEvidenceAndArtifactReceiptWithoutRdfPayloads() {
        var intent = new ReleaseIntent("release-1", "tenant", "project", "correlation", "staging", List.of(new GraphReference("tenant", "project", "https://example.test/graph", DIGEST)), List.of(new ContentReference("text/turtle", DIGEST, URI.create("https://example.test/output"))), List.of(new SemanticGateEvidence("approval", "passed", DIGEST)), new ReleaseRequirements("https://example.test/profile", DIGEST, "srf-canon/1", DIGEST, DIGEST), Optional.empty(), "standard", false);
        var receipt = new ReleaseReceipt("release-1", "adapter", "1.0", "correlation", ReleaseReceipt.State.PUBLISHED, DIGEST, URI.create("oci://example/" + DIGEST), Optional.empty(), Optional.empty());
        String triples = new ReleaseProvenanceProjector().project(intent, receipt, List.of(new ReleaseLedgerEvent("release-1", ReleaseLedgerEvent.Kind.INTENT_ASSEMBLED, "correlation", Instant.EPOCH, "intent:release-1")));
        assertTrue(triples.contains("approvalEvidenceDigest"));
        assertTrue(triples.contains("oci://example"));
    }
}