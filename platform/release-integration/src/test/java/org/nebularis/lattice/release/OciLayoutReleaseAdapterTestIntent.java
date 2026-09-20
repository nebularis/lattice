package org.nebularis.lattice.release;

import java.net.URI;
import java.util.List;
import java.util.Optional;
import org.nebularis.lattice.semantic.GraphReference;

final class OciLayoutReleaseAdapterTestIntent {
    private OciLayoutReleaseAdapterTestIntent() { }
    static ReleaseIntent create() {
        String digest = "sha256:" + "a".repeat(64);
        return new ReleaseIntent("release-1", "tenant", "project", "correlation", "staging", List.of(new GraphReference("tenant", "project", "https://example.test/graph", digest)), List.of(new ContentReference("text/turtle", digest, URI.create("https://example.test/output"))), List.of(new SemanticGateEvidence("approval", "passed", digest)), new ReleaseRequirements("https://example.test/profile", digest, "srf-canon/1", digest, digest), Optional.empty(), "standard", false);
    }
}