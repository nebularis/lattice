package org.nebularis.lattice.surface;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import org.nebularis.lattice.release.ContentReference;
import org.nebularis.lattice.release.ReleaseIntent;
import org.nebularis.lattice.release.ReleaseRequirements;
import org.nebularis.lattice.release.SemanticGateEvidence;
import org.nebularis.lattice.semantic.GraphReference;

public record SurfaceReleaseCandidate(
    String candidateId,
    SurfaceRevision revision,
    List<ContentReference> generatedOutputs,
    List<SemanticGateEvidence> semanticGates
) {
    public SurfaceReleaseCandidate {
        if (Objects.requireNonNull(candidateId, "candidateId").isBlank()) {
            throw new IllegalArgumentException("candidateId must not be blank");
        }
        revision = Objects.requireNonNull(revision, "revision");
        generatedOutputs = List.copyOf(generatedOutputs);
        semanticGates = List.copyOf(semanticGates);
        if (revision.state() != SurfaceRevisionState.GENERATED || revision.generatedGraph().isEmpty()) {
            throw new IllegalArgumentException("only generated revisions can become release candidates");
        }
        if (generatedOutputs.isEmpty() || semanticGates.isEmpty()) {
            throw new IllegalArgumentException("release candidates require generated outputs and semantic gate evidence");
        }
    }

    public ReleaseIntent toReleaseIntent(String correlationId, String environment, String retentionClass, ReleaseRequirements requirements) {
        List<GraphReference> graphs = new ArrayList<>();
        graphs.add(revision.contractGraph());
        graphs.add(revision.profileGraph());
        graphs.add(revision.generatedGraph().orElseThrow());
        return new ReleaseIntent(candidateId, revision.contractGraph().tenantId(), revision.contractGraph().projectId(), correlationId, environment, graphs, generatedOutputs, semanticGates, requirements, java.util.Optional.empty(), retentionClass, false);
    }
}
