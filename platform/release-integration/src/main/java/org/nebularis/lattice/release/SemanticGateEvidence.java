package org.nebularis.lattice.release;

public record SemanticGateEvidence(String gate, String outcome, String evidenceDigest) {
    public SemanticGateEvidence {
        ContentReference.require(gate, "gate");
        if (!"passed".equals(outcome)) {
            throw new IllegalArgumentException("only passed semantic gates can form a release intent");
        }
        ContentReference.requireDigest(evidenceDigest);
    }
}
