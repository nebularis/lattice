package org.nebularis.lattice.release;

import java.time.Clock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

public final class InMemoryReleaseLedger implements ReleaseLedger {
    private final Clock clock;
    private final Map<String, ReleaseIntent> intents = new HashMap<>();
    private final Map<String, ReleaseReceipt> receipts = new HashMap<>();
    private final Map<String, List<ReleaseLedgerEvent>> events = new HashMap<>();

    public InMemoryReleaseLedger(Clock clock) {
        this.clock = clock;
    }

    @Override
    public synchronized void recordIntent(ReleaseIntent intent) {
        ReleaseIntent existing = intents.putIfAbsent(intent.releaseId(), intent);
        if (existing != null && !existing.equals(intent)) {
            throw new IllegalStateException("release ID was reused for different semantic intent");
        }
        recordEvent(new ReleaseLedgerEvent(intent.releaseId(), ReleaseLedgerEvent.Kind.INTENT_ASSEMBLED, intent.correlationId(), Instant.now(clock), "intent:" + intent.releaseId()));
    }

    @Override
    public synchronized void recordReceipt(ReleaseReceipt receipt) {
        if (!intents.containsKey(receipt.releaseId())) {
            throw new IllegalStateException("release receipt has no recorded semantic intent");
        }
        receipts.put(receipt.releaseId(), receipt);
        recordEvent(new ReleaseLedgerEvent(receipt.releaseId(), ReleaseLedgerEvent.Kind.RECEIPT_RECORDED, receipt.correlationId(), Instant.now(clock), receipt.artifactDigest()));
    }

    @Override
    public synchronized void recordEvent(ReleaseLedgerEvent event) {
        events.computeIfAbsent(event.releaseId(), ignored -> new ArrayList<>()).add(event);
    }

    public synchronized Optional<ReleaseIntent> findIntent(String releaseId) {
        return Optional.ofNullable(intents.get(releaseId));
    }

    public synchronized Optional<ReleaseReceipt> findLatestReceipt(String releaseId) {
        return Optional.ofNullable(receipts.get(releaseId));
    }

    @Override
    public synchronized List<ReleaseLedgerEvent> events(String releaseId) {
        return events.getOrDefault(releaseId, List.of()).stream().sorted(Comparator.comparing(ReleaseLedgerEvent::recordedAt)).toList();
    }
}
