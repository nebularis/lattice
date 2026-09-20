package org.nebularis.lattice.surface;

import java.util.NoSuchElementException;
import java.util.Objects;
import java.util.Optional;
import org.nebularis.lattice.semantic.GraphReference;

/** Framework-neutral API mapping for the typed Surface revision contract. */
public final class SurfaceRevisionApi {
    private final SurfaceRevisionRepository repository;
    private final SurfaceRevisionService service;

    public SurfaceRevisionApi(SurfaceRevisionRepository repository) {
        this.repository = Objects.requireNonNull(repository, "repository");
        this.service = new SurfaceRevisionService(repository);
    }

    public ApiResponse<RevisionView> create(CreateRevisionRequest request) {
        try {
            SurfaceRevision revision = SurfaceRevision.draft(
                request.revisionId(), request.contractId(), request.contractGraph().toDomain(), request.profileGraph().toDomain());
            return ApiResponse.created(RevisionView.from(service.create(revision)));
        } catch (IllegalArgumentException error) {
            return ApiResponse.badRequest(error.getMessage());
        }
    }

    public ApiResponse<RevisionView> get(String revisionId) {
        return repository.find(revisionId).map(revision -> ApiResponse.ok(RevisionView.from(revision)))
            .orElseGet(() -> ApiResponse.notFound("surface revision was not found: " + revisionId));
    }

    public ApiResponse<RevisionView> transition(String revisionId, TransitionRequest request) {
        try {
            return ApiResponse.ok(RevisionView.from(service.transition(revisionId, request.toDomain())));
        } catch (NoSuchElementException error) {
            return ApiResponse.notFound(error.getMessage());
        } catch (IllegalStateException error) {
            return ApiResponse.conflict(error.getMessage());
        } catch (IllegalArgumentException error) {
            return ApiResponse.badRequest(error.getMessage());
        }
    }

    public record CreateRevisionRequest(String revisionId, String contractId, GraphReferenceView contractGraph, GraphReferenceView profileGraph) {
        public CreateRevisionRequest {
            Objects.requireNonNull(revisionId, "revisionId");
            Objects.requireNonNull(contractId, "contractId");
            Objects.requireNonNull(contractGraph, "contractGraph");
            Objects.requireNonNull(profileGraph, "profileGraph");
        }
    }

    public record TransitionRequest(long expectedVersion, SurfaceRevisionAction action, Optional<String> approvalId, Optional<GraphReferenceView> generatedGraph) {
        public TransitionRequest {
            Objects.requireNonNull(action, "action");
            approvalId = Objects.requireNonNull(approvalId, "approvalId");
            generatedGraph = Objects.requireNonNull(generatedGraph, "generatedGraph");
        }

        SurfaceRevisionTransition toDomain() {
            return new SurfaceRevisionTransition(expectedVersion, action, approvalId, generatedGraph.map(GraphReferenceView::toDomain));
        }
    }

    public record GraphReferenceView(String tenantId, String projectId, String graphIri, String revisionHash) {
        GraphReference toDomain() {
            return new GraphReference(tenantId, projectId, graphIri, revisionHash);
        }

        static GraphReferenceView from(GraphReference reference) {
            return new GraphReferenceView(reference.tenantId(), reference.projectId(), reference.graphIri(), reference.revisionHash());
        }
    }

    public record RevisionView(String revisionId, String contractId, String state, GraphReferenceView contractGraph, GraphReferenceView profileGraph, Optional<GraphReferenceView> generatedGraph, Optional<String> approvalId, long version, String recordedAt) {
        static RevisionView from(VersionedSurfaceRevision versioned) {
            SurfaceRevision revision = versioned.revision();
            return new RevisionView(revision.revisionId(), revision.contractId(), revision.state().name().toLowerCase(), GraphReferenceView.from(revision.contractGraph()), GraphReferenceView.from(revision.profileGraph()), revision.generatedGraph().map(GraphReferenceView::from), revision.approvalId(), versioned.version(), versioned.recordedAt().toString());
        }
    }

    public record ApiResponse<T>(int status, T body, String error) {
        static <T> ApiResponse<T> created(T body) { return new ApiResponse<>(201, body, null); }
        static <T> ApiResponse<T> ok(T body) { return new ApiResponse<>(200, body, null); }
        static <T> ApiResponse<T> badRequest(String error) { return new ApiResponse<>(400, null, error); }
        static <T> ApiResponse<T> notFound(String error) { return new ApiResponse<>(404, null, error); }
        static <T> ApiResponse<T> conflict(String error) { return new ApiResponse<>(409, null, error); }
    }
}