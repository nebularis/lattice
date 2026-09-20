package org.nebularis.lattice.surface;

import java.util.NoSuchElementException;
import java.util.Objects;

/** Application boundary that applies typed lifecycle commands through optimistic concurrency. */
public final class SurfaceRevisionService {
    private final SurfaceRevisionRepository repository;

    public SurfaceRevisionService(SurfaceRevisionRepository repository) {
        this.repository = Objects.requireNonNull(repository, "repository");
    }

    public VersionedSurfaceRevision create(SurfaceRevision revision) {
        return repository.create(revision);
    }

    public VersionedSurfaceRevision transition(String revisionId, SurfaceRevisionTransition command) {
        VersionedSurfaceRevision current = repository.find(revisionId)
            .orElseThrow(() -> new NoSuchElementException("surface revision was not found: " + revisionId));
        if (current.version() != command.expectedVersion()) {
            throw new StaleSurfaceRevisionException(revisionId);
        }
        SurfaceRevision next = switch (command.action()) {
            case REQUEST_REVIEW -> current.revision().requestReview();
            case APPROVE -> current.revision().approve(command.approvalId().orElseThrow());
            case RECORD_GENERATION -> current.revision().generated(command.generatedGraph().orElseThrow());
            case RELEASE -> current.revision().release();
            case SUPERSEDE -> current.revision().supersede();
        };
        return repository.replace(revisionId, command.expectedVersion(), next);
    }
}
