package org.nebularis.lattice.surface;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.semantic.GraphReference;

class InMemorySurfaceRevisionRepositoryTest {
    private static final String DIGEST = "sha256:" + "a".repeat(64);

    @Test
    void staleReplacementCannotOverwriteTheNewerRevision() {
        var repository = new InMemorySurfaceRevisionRepository(Clock.fixed(Instant.EPOCH, ZoneOffset.UTC));
        var created = repository.create(SurfaceRevision.draft("revision-1", "contract-1", graph("contract"), graph("profile")));
        var requested = repository.replace("revision-1", created.version(), created.revision().requestReview());

        assertEquals(1, requested.version());
        assertThrows(StaleSurfaceRevisionException.class, () -> repository.replace("revision-1", created.version(), created.revision().supersede()));
        assertEquals(SurfaceRevisionState.REVIEW_REQUESTED, repository.find("revision-1").orElseThrow().revision().state());
    }

    @Test
    void commandServiceAppliesTransitionsWithTheReadVersion() {
        var repository = new InMemorySurfaceRevisionRepository(Clock.fixed(Instant.EPOCH, ZoneOffset.UTC));
        var service = new SurfaceRevisionService(repository);
        var created = service.create(SurfaceRevision.draft("revision-1", "contract-1", graph("contract"), graph("profile")));

        var requested = service.transition("revision-1", new SurfaceRevisionTransition(created.version(), SurfaceRevisionAction.REQUEST_REVIEW, Optional.empty(), Optional.empty()));

        assertEquals(SurfaceRevisionState.REVIEW_REQUESTED, requested.revision().state());
        assertThrows(StaleSurfaceRevisionException.class, () -> service.transition("revision-1", new SurfaceRevisionTransition(created.version(), SurfaceRevisionAction.REQUEST_REVIEW, Optional.empty(), Optional.empty())));
    }

    private static GraphReference graph(String family) {
        return new GraphReference("tenant", "project", "https://example.test/graphs/" + family, DIGEST);
    }
}