package org.nebularis.lattice.release;

import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

/** Verifies LATTICE semantic release evidence before delegating to a release stack. */
public final class SemanticReleaseAssemblyService {
    private final SemanticReleasePolicy policy;

    public SemanticReleaseAssemblyService(SemanticReleasePolicy policy) {
        this.policy = Objects.requireNonNull(policy, "policy");
    }

    public ReleaseIntent assemble(ReleaseIntent intent) {
        Objects.requireNonNull(intent, "intent");
        if (intent.generatedOutputs().isEmpty()) {
            throw new IllegalArgumentException("semantic release requires generated output descriptors");
        }
        Set<String> graphIdentities = new HashSet<>();
        for (var graph : intent.graphReferences()) {
            if (!graphIdentities.add(graph.graphIri() + "|" + graph.revisionHash())) {
                throw new IllegalArgumentException("semantic release contains a duplicate immutable graph reference");
            }
        }
        Set<String> gates = intent.semanticGates().stream().map(SemanticGateEvidence::gate).collect(java.util.stream.Collectors.toSet());
        if (!gates.containsAll(policy.requiredGates())) {
            throw new IllegalArgumentException("semantic release is missing required gate evidence");
        }
        return intent;
    }
}
