package org.nebularis.lattice.surface;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.semantic.GraphReference;

class InMemorySurfaceGraphFamilyRegistryTest {
    private static final String FIRST_DIGEST = "sha256:" + "a".repeat(64);
    private static final String SECOND_DIGEST = "sha256:" + "b".repeat(64);

    @Test
    void registrationIsIdempotentForTheSameImmutableArtifact() {
        var registry = new InMemorySurfaceGraphFamilyRegistry();
        var artifact = artifact(FIRST_DIGEST);
        registry.register(artifact);

        assertEquals(artifact, registry.register(artifact));
    }

    @Test
    void sameGraphIriCannotBeRegisteredWithADifferentRevisionHash() {
        var registry = new InMemorySurfaceGraphFamilyRegistry();
        registry.register(artifact(FIRST_DIGEST));

        assertThrows(ImmutableGraphConflictException.class, () -> registry.register(artifact(SECOND_DIGEST)));
    }

    private static SurfaceGraphArtifact artifact(String digest) {
        return new SurfaceGraphArtifact(SurfaceGraphFamily.GENERATED_OUTPUT, new GraphReference("tenant", "project", "https://example.test/graphs/generated", digest), "revision-1", Instant.EPOCH);
    }
}