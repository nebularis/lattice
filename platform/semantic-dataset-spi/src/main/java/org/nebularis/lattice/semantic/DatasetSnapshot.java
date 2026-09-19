package org.nebularis.lattice.semantic;

import java.util.Objects;

public record DatasetSnapshot(GraphReference reference, String canonicalNQuads, String contentHash) {
    public DatasetSnapshot {
        Objects.requireNonNull(reference, "reference");
        Objects.requireNonNull(canonicalNQuads, "canonicalNQuads");
        Objects.requireNonNull(contentHash, "contentHash");
    }
}
