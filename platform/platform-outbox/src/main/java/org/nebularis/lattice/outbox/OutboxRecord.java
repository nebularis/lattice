package org.nebularis.lattice.outbox;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public record OutboxRecord(UUID id, String idempotencyKey, CloudEvent event, Instant createdAt, Status status) {
    public enum Status { PENDING, PUBLISHED }

    public OutboxRecord {
        Objects.requireNonNull(id, "id");
        if (Objects.requireNonNull(idempotencyKey, "idempotencyKey").isBlank()) {
            throw new IllegalArgumentException("idempotencyKey must not be blank");
        }
        Objects.requireNonNull(event, "event");
        Objects.requireNonNull(createdAt, "createdAt");
        Objects.requireNonNull(status, "status");
    }
}
