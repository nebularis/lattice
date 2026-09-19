package org.nebularis.lattice.surface;

import java.util.Objects;
import java.util.Optional;
import org.nebularis.lattice.semantic.GraphReference;

public record SurfaceRevision(
    String revisionId,
    String contractId,
    SurfaceRevisionState state,
    GraphReference contractGraph,
    GraphReference profileGraph,
    Optional<GraphReference> generatedGraph,
    Optional<String> approvalId
) {
    public SurfaceRevision {
        require(revisionId, "revisionId");
        require(contractId, "contractId");
        Objects.requireNonNull(state, "state");
        Objects.requireNonNull(contractGraph, "contractGraph");
        Objects.requireNonNull(profileGraph, "profileGraph");
        generatedGraph = Objects.requireNonNull(generatedGraph, "generatedGraph");
        approvalId = Objects.requireNonNull(approvalId, "approvalId");
        requireScope(contractGraph, profileGraph);
        generatedGraph.ifPresent(graph -> requireScope(contractGraph, graph));
        if ((state == SurfaceRevisionState.GENERATED || state == SurfaceRevisionState.RELEASED) && generatedGraph.isEmpty()) {
            throw new IllegalArgumentException("generated and released revisions require an immutable generated graph");
        }
        if ((state == SurfaceRevisionState.APPROVED || state == SurfaceRevisionState.GENERATED || state == SurfaceRevisionState.RELEASED) && approvalId.isEmpty()) {
            throw new IllegalArgumentException("approved, generated, and released revisions require approval evidence");
        }
    }

    public static SurfaceRevision draft(String revisionId, String contractId, GraphReference contractGraph, GraphReference profileGraph) {
        return new SurfaceRevision(revisionId, contractId, SurfaceRevisionState.DRAFT, contractGraph, profileGraph, Optional.empty(), Optional.empty());
    }

    public SurfaceRevision requestReview() {
        return transition(SurfaceRevisionState.DRAFT, SurfaceRevisionState.REVIEW_REQUESTED, generatedGraph, approvalId);
    }

    public SurfaceRevision approve(String approvedByEvidence) {
        require(approvedByEvidence, "approvedByEvidence");
        return transition(SurfaceRevisionState.REVIEW_REQUESTED, SurfaceRevisionState.APPROVED, generatedGraph, Optional.of(approvedByEvidence));
    }

    public SurfaceRevision generated(GraphReference immutableGeneratedGraph) {
        return transition(SurfaceRevisionState.APPROVED, SurfaceRevisionState.GENERATED, Optional.of(immutableGeneratedGraph), approvalId);
    }

    public SurfaceRevision release() {
        return transition(SurfaceRevisionState.GENERATED, SurfaceRevisionState.RELEASED, generatedGraph, approvalId);
    }

    public SurfaceRevision supersede() {
        if (state == SurfaceRevisionState.SUPERSEDED) {
            throw new IllegalStateException("a revision is already superseded");
        }
        return new SurfaceRevision(revisionId, contractId, SurfaceRevisionState.SUPERSEDED, contractGraph, profileGraph, generatedGraph, approvalId);
    }

    private SurfaceRevision transition(SurfaceRevisionState expected, SurfaceRevisionState next, Optional<GraphReference> nextGraph, Optional<String> nextApproval) {
        if (state != expected) {
            throw new IllegalStateException("cannot transition revision from " + state + " to " + next);
        }
        return new SurfaceRevision(revisionId, contractId, next, contractGraph, profileGraph, nextGraph, nextApproval);
    }

    private static void requireScope(GraphReference expected, GraphReference actual) {
        if (!expected.tenantId().equals(actual.tenantId()) || !expected.projectId().equals(actual.projectId())) {
            throw new IllegalArgumentException("all graph families must use the revision tenant and project scope");
        }
    }

    private static void require(String value, String name) {
        if (Objects.requireNonNull(value, name).isBlank()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
    }
}
