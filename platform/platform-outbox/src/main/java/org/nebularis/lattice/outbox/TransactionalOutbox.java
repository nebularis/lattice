package org.nebularis.lattice.outbox;

import java.util.List;

public interface TransactionalOutbox {
    OutboxRecord enqueue(String idempotencyKey, CloudEvent event);
    List<OutboxRecord> pending();
    void markPublished(OutboxRecord record);
}
