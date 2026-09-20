package org.nebularis.lattice.surface;

import java.time.Instant;
import java.util.Objects;
import org.nebularis.lattice.semantic.GraphReference;

/** Immutable graph-family registration metadata. The graph content stays in the semantic dataset. */
public record SurfaceGraphArtifact(
    SurfaceGraphFamily family,
    GraphReference reference,
    String ownerRevisionId,
    Instant registeredAt
) {
    public SurfaceGraphArtifact {
        family = Objects.requireNonNull(family, "family");
        reference = Objects.requireNonNull(reference, "reference");
        if (Objects.requireNonNull(ownerRevisionId, "ownerRevisionId").isBlank()) {
            throw new IllegalArgumentException("ownerRevisionId must not be blank");
        }
        registeredAt = Objects.requireNonNull(registeredAt, "registeredAt");
    }
}
