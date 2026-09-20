package org.nebularis.lattice.release;

import static org.junit.jupiter.api.Assertions.assertThrows;
import java.net.URI;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.semantic.GraphReference;

class SemanticReleaseAssemblyServiceTest {
    private static final String DIGEST = "sha256:" + "a".repeat(64);

    @Test
    void rejectsReleaseWithoutAllRequiredSemanticGates() {
        var service = new SemanticReleaseAssemblyService(SemanticReleasePolicy.surfaceDefault());
        assertThrows(IllegalArgumentException.class, () -> service.assemble(intent(List.of(new SemanticGateEvidence("parity", "passed", DIGEST))));
    }

    @Test
    void coordinatorDoesNotCallAdapterWhenSemanticAssemblyFails() {
        var coordinator = new SemanticReleaseCoordinator(new SemanticReleaseAssemblyService(SemanticReleasePolicy.surfaceDefault()), new InMemoryReleaseLedger(java.time.Clock.systemUTC()));
        var adapter = new ReleaseStackAdapter() {
            public String adapterId() { return "test"; }
            public String adapterVersion() { return "1"; }
            public java.util.Set<ReleaseCapability> capabilities() { return java.util.Set.of(); }
            public ReleaseReceipt plan(ReleaseIntent ignored) { throw new AssertionError("adapter must not be called"); }
            public ReleaseReceipt publish(ReleaseIntent ignored) { throw new AssertionError("adapter must not be called"); }
        };
        assertThrows(IllegalArgumentException.class, () -> coordinator.publish(adapter, intent(List.of(new SemanticGateEvidence("parity", "passed", DIGEST))));
    }

    private static ReleaseIntent intent(List<SemanticGateEvidence> gates) {
        return new ReleaseIntent("release-1", "tenant", "project", "correlation", "staging", List.of(new GraphReference("tenant", "project", "https://example.test/graphs/contract", DIGEST)), List.of(new ContentReference("text/turtle", DIGEST, URI.create("https://example.test/output"))), gates, new ReleaseRequirements("https://example.test/profiles/default", DIGEST, "srf-canon/1", DIGEST, DIGEST), Optional.empty(), "standard", false);
    }
}