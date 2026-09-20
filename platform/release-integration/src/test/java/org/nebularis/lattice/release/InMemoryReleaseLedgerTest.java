package org.nebularis.lattice.release;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import java.net.URI;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.semantic.GraphReference;

class InMemoryReleaseLedgerTest {
    private static final String DIGEST = "sha256:" + "a".repeat(64);

    @Test
    void recordsReceiptOnlyAfterSemanticIntent() {
        var ledger = new InMemoryReleaseLedger(Clock.fixed(Instant.EPOCH, ZoneOffset.UTC));
        var receipt = new ReleaseReceipt("release-1", "adapter", "1.0", "correlation", ReleaseReceipt.State.PUBLISHED, DIGEST, URI.create("oci://example/" + DIGEST), Optional.empty(), Optional.empty());
        assertThrows(IllegalStateException.class, () -> ledger.recordReceipt(receipt));
        ledger.recordIntent(intent());
        ledger.recordReceipt(receipt);
        assertEquals(2, ledger.events("release-1").size());
    }

    private static ReleaseIntent intent() {
        return new ReleaseIntent("release-1", "tenant", "project", "correlation", "staging", List.of(new GraphReference("tenant", "project", "https://example.test/graph", DIGEST)), List.of(new ContentReference("text/turtle", DIGEST, URI.create("https://example.test/output"))), List.of(new SemanticGateEvidence("approval", "passed", DIGEST)), new ReleaseRequirements("https://example.test/profile", DIGEST, "srf-canon/1", DIGEST, DIGEST), Optional.empty(), "standard", false);
    }
}