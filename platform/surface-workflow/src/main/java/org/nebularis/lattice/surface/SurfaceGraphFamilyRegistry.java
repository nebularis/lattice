package org.nebularis.lattice.surface;

import java.util.List;
import java.util.Optional;

public interface SurfaceGraphFamilyRegistry {
    SurfaceGraphArtifact register(SurfaceGraphArtifact artifact);
    Optional<SurfaceGraphArtifact> findByGraphIri(String tenantId, String projectId, String graphIri);
    List<SurfaceGraphArtifact> findByOwnerRevision(String ownerRevisionId);
}
