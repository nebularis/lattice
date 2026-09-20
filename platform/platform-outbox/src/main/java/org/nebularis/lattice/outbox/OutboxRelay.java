package org.nebularis.lattice.outbox;

import java.util.List;

public final class OutboxRelay {
    private final TransactionalOutbox outbox;
    private final EventPublisher publisher;

    public OutboxRelay(TransactionalOutbox outbox, EventPublisher publisher) {
        this.outbox = outbox;
        this.publisher = publisher;
    }

    public List<OutboxRecord> relayPending() {
        return outbox.pending().stream().filter(this::publish).toList();
    }

    private boolean publish(OutboxRecord record) {
        try {
            publisher.publish(record.event());
            outbox.markPublished(record);
            return true;
        } catch (RuntimeException error) {
            return false;
        }
    }
}
