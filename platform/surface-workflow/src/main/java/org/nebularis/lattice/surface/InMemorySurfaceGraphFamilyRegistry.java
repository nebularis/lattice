package org.nebularis.lattice.surface;

import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

public final class InMemorySurfaceGraphFamilyRegistry implements SurfaceGraphFamilyRegistry {
    private final ConcurrentMap<GraphKey, SurfaceGraphArtifact> artifacts = new ConcurrentHashMap<>();

    @Override
    public SurfaceGraphArtifact register(SurfaceGraphArtifact artifact) {
        GraphKey key = GraphKey.from(artifact);
        return artifacts.compute(key, (ignored, existing) -> {
            if (existing == null) {
                return artifact;
            }
            if (sameArtifact(existing, artifact)) {
                return existing;
            }
            throw new ImmutableGraphConflictException(artifact.reference().graphIri());
        });
    }

    @Override
    public Optional<SurfaceGraphArtifact> findByGraphIri(String tenantId, String projectId, String graphIri) {
        return Optional.ofNullable(artifacts.get(new GraphKey(tenantId, projectId, graphIri)));
    }

    @Override
    public List<SurfaceGraphArtifact> findByOwnerRevision(String ownerRevisionId) {
        return artifacts.values().stream()
            .filter(artifact -> artifact.ownerRevisionId().equals(ownerRevisionId))
            .sorted(Comparator.comparing(artifact -> artifact.family().name()))
            .toList();
    }

    private static boolean sameArtifact(SurfaceGraphArtifact existing, SurfaceGraphArtifact incoming) {
        return existing.family() == incoming.family()
            && existing.reference().revisionHash().equals(incoming.reference().revisionHash())
            && existing.ownerRevisionId().equals(incoming.ownerRevisionId());
    }

    private record GraphKey(String tenantId, String projectId, String graphIri) {
        static GraphKey from(SurfaceGraphArtifact artifact) {
            return new GraphKey(artifact.reference().tenantId(), artifact.reference().projectId(), artifact.reference().graphIri());
        }
    }
}
