package org.nebularis.lattice.surface;

import java.util.List;
import java.util.Optional;

public interface SurfaceRevisionRepository {
    VersionedSurfaceRevision create(SurfaceRevision revision);
    Optional<VersionedSurfaceRevision> find(String revisionId);
    List<VersionedSurfaceRevision> findByContract(String contractId);
    VersionedSurfaceRevision replace(String revisionId, long expectedVersion, SurfaceRevision nextRevision);
}
