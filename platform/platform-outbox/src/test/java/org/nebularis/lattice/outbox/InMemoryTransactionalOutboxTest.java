package org.nebularis.lattice.outbox;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import java.net.URI;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class InMemoryTransactionalOutboxTest {
    @Test
    void retriesWithTheSameIdempotencyKeyProduceOnePendingRecord() {
        var outbox = new InMemoryTransactionalOutbox(Clock.fixed(Instant.EPOCH, ZoneOffset.UTC));
        var event = new CloudEvent(UUID.randomUUID(), URI.create("https://example.test/platform"), "org.nebularis.graph.validate", "job", Instant.EPOCH, Map.of("correlationid", "correlation"), "{}");
        outbox.enqueue("job-1", event);
        outbox.enqueue("job-1", event);
        assertEquals(1, outbox.pending().size());
    }

    @Test
    void failedPublicationRemainsPendingForRetry() {
        var outbox = new InMemoryTransactionalOutbox(Clock.fixed(Instant.EPOCH, ZoneOffset.UTC));
        var event = new CloudEvent(UUID.randomUUID(), URI.create("https://example.test/platform"), "org.nebularis.graph.validate", "job", Instant.EPOCH, Map.of(), "{}");
        outbox.enqueue("job-1", event);
        var relay = new OutboxRelay(outbox, ignored -> { throw new IllegalStateException("broker unavailable"); });
        assertTrue(relay.relayPending().isEmpty());
        assertEquals(1, outbox.pending().size());
    }
}
