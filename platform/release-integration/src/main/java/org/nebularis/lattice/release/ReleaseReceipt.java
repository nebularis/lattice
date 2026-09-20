package org.nebularis.lattice.release;

import java.net.URI;
import java.util.Objects;
import java.util.Optional;

public record ReleaseReceipt(
    String releaseId,
    String adapterId,
    String adapterVersion,
    String correlationId,
    State state,
    String artifactDigest,
    URI artifactUri,
    Optional<URI> signatureReference,
    Optional<URI> diagnosticReference
) {
    public enum State { PLANNED, PUBLISHED, PROMOTED, ROLLED_BACK, EXPORTED, RESTORED, RETIRED, FAILED }

    public ReleaseReceipt {
        ContentReference.require(releaseId, "releaseId");
        ContentReference.require(adapterId, "adapterId");
        ContentReference.require(adapterVersion, "adapterVersion");
        ContentReference.require(correlationId, "correlationId");
        ContentReference.requireDigest(artifactDigest);
        if (artifactUri == null || !artifactUri.isAbsolute()) {
            throw new IllegalArgumentException("artifactUri must be absolute");
        }
        signatureReference = Objects.requireNonNull(signatureReference, "signatureReference");
        diagnosticReference = Objects.requireNonNull(diagnosticReference, "diagnosticReference");
    }
}
