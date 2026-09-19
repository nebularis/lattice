package org.nebularis.lattice.outbox;

import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class InMemoryTransactionalOutbox implements TransactionalOutbox {
    private final Clock clock;
    private final Map<String, OutboxRecord> recordsByKey = new LinkedHashMap<>();

    public InMemoryTransactionalOutbox(Clock clock) {
        this.clock = clock;
    }

    @Override
    public synchronized OutboxRecord enqueue(String idempotencyKey, CloudEvent event) {
        return recordsByKey.computeIfAbsent(idempotencyKey, key -> new OutboxRecord(UUID.randomUUID(), key, event, Instant.now(clock), OutboxRecord.Status.PENDING));
    }

    @Override
    public synchronized List<OutboxRecord> pending() {
        return recordsByKey.values().stream().filter(record -> record.status() == OutboxRecord.Status.PENDING).sorted(Comparator.comparing(OutboxRecord::createdAt)).toList();
    }

    @Override
    public synchronized void markPublished(OutboxRecord record) {
        if (record.status() == OutboxRecord.Status.PUBLISHED) {
            return;
        }
        recordsByKey.computeIfPresent(record.idempotencyKey(), (key, existing) -> new OutboxRecord(existing.id(), key, existing.event(), existing.createdAt(), OutboxRecord.Status.PUBLISHED));
    }
}
