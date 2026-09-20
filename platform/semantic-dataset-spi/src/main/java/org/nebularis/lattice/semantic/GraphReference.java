package org.nebularis.lattice.semantic;

import java.util.Objects;

public record GraphReference(String tenantId, String projectId, String graphIri, String revisionHash) {
    public GraphReference {
        requireValue(tenantId, "tenantId");
        requireValue(projectId, "projectId");
        requireValue(graphIri, "graphIri");
        requireValue(revisionHash, "revisionHash");
        if (!graphIri.startsWith("http://") && !graphIri.startsWith("https://")) {
            throw new IllegalArgumentException("graphIri must be an absolute HTTP(S) IRI");
        }
    }

    private static void requireValue(String value, String name) {
        if (Objects.requireNonNull(value, name).isBlank()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
    }
}
