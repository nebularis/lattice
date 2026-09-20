package org.nebularis.lattice.release;

import java.util.Set;

public record SemanticReleasePolicy(Set<String> requiredGates) {
    public SemanticReleasePolicy {
        requiredGates = Set.copyOf(requiredGates);
        if (requiredGates.isEmpty()) {
            throw new IllegalArgumentException("semantic release policy requires at least one gate");
        }
    }

    public static SemanticReleasePolicy surfaceDefault() {
        return new SemanticReleasePolicy(Set.of("approval", "determinism", "impact", "parity"));
    }
}
