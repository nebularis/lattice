package org.nebularis.lattice.release;

import java.util.List;
import java.util.Objects;
import java.util.Optional;
import org.nebularis.lattice.semantic.GraphReference;

public record ReleaseIntent(
    String releaseId,
    String tenantId,
    String projectId,
    String correlationId,
    String environment,
    List<GraphReference> graphReferences,
    List<ContentReference> generatedOutputs,
    List<SemanticGateEvidence> semanticGates,
    ReleaseRequirements requirements,
    Optional<String> rollbackTargetReleaseId,
    String retentionClass,
    boolean legalHold
) {
    public ReleaseIntent {
        ContentReference.require(releaseId, "releaseId");
        ContentReference.require(tenantId, "tenantId");
        ContentReference.require(projectId, "projectId");
        ContentReference.require(correlationId, "correlationId");
        ContentReference.require(environment, "environment");
        graphReferences = List.copyOf(graphReferences);
        generatedOutputs = List.copyOf(generatedOutputs);
        semanticGates = List.copyOf(semanticGates);
        requirements = Objects.requireNonNull(requirements, "requirements");
        rollbackTargetReleaseId = Objects.requireNonNull(rollbackTargetReleaseId, "rollbackTargetReleaseId");
        ContentReference.require(retentionClass, "retentionClass");
        if (graphReferences.isEmpty() || semanticGates.isEmpty()) {
            throw new IllegalArgumentException("release intent requires graph references and semantic gate evidence");
        }
        if (graphReferences.stream().anyMatch(graph -> !tenantId.equals(graph.tenantId()) || !projectId.equals(graph.projectId()))) {
            throw new IllegalArgumentException("every graph reference must belong to the release tenant and project");
        }
    }
}
