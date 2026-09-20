package org.nebularis.lattice.outbox;

public interface EventPublisher {
    void publish(CloudEvent event);
}
