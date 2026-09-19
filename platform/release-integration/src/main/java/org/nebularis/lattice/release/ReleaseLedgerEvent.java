package org.nebularis.lattice.release;

import java.time.Instant;
import java.util.Objects;

public record ReleaseLedgerEvent(String releaseId, Kind kind, String correlationId, Instant recordedAt, String evidenceReference) {
    public enum Kind { INTENT_ASSEMBLED, RECEIPT_RECORDED, PROMOTION_REQUESTED, ROLLBACK_REQUESTED, EXPORTED, RESTORED, RETENTION_REQUESTED, FAILED }

    public ReleaseLedgerEvent {
        ContentReference.require(releaseId, "releaseId");
        Objects.requireNonNull(kind, "kind");
        ContentReference.require(correlationId, "correlationId");
        Objects.requireNonNull(recordedAt, "recordedAt");
        ContentReference.require(evidenceReference, "evidenceReference");
    }
}
