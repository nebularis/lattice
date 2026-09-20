package org.nebularis.lattice.release;

import java.util.Objects;

/** Semantic evidence LATTICE requires before an external release stack is invoked. */
public record ReleaseRequirements(
    String profileId,
    String profileRevisionHash,
    String canonicalisationVersion,
    String approvalEvidenceDigest,
    String impactEvidenceDigest
) {
    public ReleaseRequirements {
        ContentReference.require(profileId, "profileId");
        ContentReference.requireDigest(profileRevisionHash);
        ContentReference.require(canonicalisationVersion, "canonicalisationVersion");
        ContentReference.requireDigest(approvalEvidenceDigest);
        ContentReference.requireDigest(impactEvidenceDigest);
    }
}
