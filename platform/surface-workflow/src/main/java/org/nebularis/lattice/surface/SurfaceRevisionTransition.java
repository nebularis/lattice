package org.nebularis.lattice.surface;

import java.util.Objects;
import java.util.Optional;
import org.nebularis.lattice.semantic.GraphReference;

public record SurfaceRevisionTransition(
    long expectedVersion,
    SurfaceRevisionAction action,
    Optional<String> approvalId,
    Optional<GraphReference> generatedGraph
) {
    public SurfaceRevisionTransition {
        if (expectedVersion < 0) {
            throw new IllegalArgumentException("expectedVersion must not be negative");
        }
        action = Objects.requireNonNull(action, "action");
        approvalId = Objects.requireNonNull(approvalId, "approvalId");
        generatedGraph = Objects.requireNonNull(generatedGraph, "generatedGraph");
        if (action == SurfaceRevisionAction.APPROVE && approvalId.isEmpty()) {
            throw new IllegalArgumentException("approval action requires approvalId");
        }
        if (action != SurfaceRevisionAction.APPROVE && approvalId.isPresent()) {
            throw new IllegalArgumentException("approvalId is only valid for approval action");
        }
        if (action == SurfaceRevisionAction.RECORD_GENERATION && generatedGraph.isEmpty()) {
            throw new IllegalArgumentException("generation action requires generatedGraph");
        }
        if (action != SurfaceRevisionAction.RECORD_GENERATION && generatedGraph.isPresent()) {
            throw new IllegalArgumentException("generatedGraph is only valid for generation action");
        }
    }
}
