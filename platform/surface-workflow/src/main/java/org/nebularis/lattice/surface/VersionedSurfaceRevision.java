package org.nebularis.lattice.surface;

import java.time.Instant;
import java.util.Objects;

public record VersionedSurfaceRevision(SurfaceRevision revision, long version, Instant recordedAt) {
    public VersionedSurfaceRevision {
        revision = Objects.requireNonNull(revision, "revision");
        if (version < 0) {
            throw new IllegalArgumentException("version must not be negative");
        }
        recordedAt = Objects.requireNonNull(recordedAt, "recordedAt");
    }
}
