package org.nebularis.lattice.surface;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

public final class InMemorySurfaceRevisionRepository implements SurfaceRevisionRepository {
    private final Clock clock;
    private final ConcurrentMap<String, VersionedSurfaceRevision> revisions = new ConcurrentHashMap<>();

    public InMemorySurfaceRevisionRepository(Clock clock) {
        this.clock = clock;
    }

    @Override
    public VersionedSurfaceRevision create(SurfaceRevision revision) {
        VersionedSurfaceRevision created = new VersionedSurfaceRevision(revision, 0, Instant.now(clock));
        if (revisions.putIfAbsent(revision.revisionId(), created) != null) {
            throw new IllegalArgumentException("surface revision already exists: " + revision.revisionId());
        }
        return created;
    }

    @Override
    public Optional<VersionedSurfaceRevision> find(String revisionId) {
        return Optional.ofNullable(revisions.get(revisionId));
    }

    @Override
    public List<VersionedSurfaceRevision> findByContract(String contractId) {
        return revisions.values().stream()
            .filter(revision -> revision.revision().contractId().equals(contractId))
            .sorted(java.util.Comparator.comparing(revision -> revision.revision().revisionId()))
            .toList();
    }

    @Override
    public VersionedSurfaceRevision replace(String revisionId, long expectedVersion, SurfaceRevision nextRevision) {
        if (!revisionId.equals(nextRevision.revisionId())) {
            throw new IllegalArgumentException("revision ID cannot change during replacement");
        }
        return revisions.compute(revisionId, (key, current) -> {
            if (current == null || current.version() != expectedVersion) {
                throw new StaleSurfaceRevisionException(revisionId);
            }
            return new VersionedSurfaceRevision(nextRevision, current.version() + 1, Instant.now(clock));
        });
    }
}
