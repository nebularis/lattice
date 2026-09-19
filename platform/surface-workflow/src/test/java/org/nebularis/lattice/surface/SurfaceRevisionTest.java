package org.nebularis.lattice.surface;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import java.net.URI;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.release.ContentReference;
import org.nebularis.lattice.release.ReleaseRequirements;
import org.nebularis.lattice.release.SemanticGateEvidence;
import org.nebularis.lattice.semantic.GraphReference;

class SurfaceRevisionTest {
    private static final String DIGEST = "sha256:" + "a".repeat(64);

    @Test
    void generatedRevisionFormsAReleaseIntentWithAllGraphFamilies() {
        var revision = SurfaceRevision.draft("revision-1", "contract-1", graph("contracts"), graph("profiles"))
            .requestReview().approve("approval-1").generated(graph("generated"));
        var candidate = new SurfaceReleaseCandidate("candidate-1", revision, List.of(new ContentReference("application/n-quads", DIGEST, URI.create("https://example.test/output"))), List.of(new SemanticGateEvidence("parity", "passed", DIGEST)));
        assertEquals(3, candidate.toReleaseIntent("correlation-1", "staging", "standard", new ReleaseRequirements("https://example.test/profiles/default", DIGEST, "srf-canon/1", DIGEST, DIGEST)).graphReferences().size());
    }

    @Test
    void generationCannotBypassApproval() {
        var revision = SurfaceRevision.draft("revision-1", "contract-1", graph("contracts"), graph("profiles")).requestReview();
        assertThrows(IllegalStateException.class, () -> revision.generated(graph("generated")));
    }

    private static GraphReference graph(String family) {
        return new GraphReference("tenant", "project", "https://example.test/graphs/" + family, DIGEST);
    }
}