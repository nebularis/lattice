package org.nebularis.lattice.outbox;

import java.time.Instant;
import java.net.URI;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

public record CloudEvent(UUID id, URI source, String type, String subject, Instant time, Map<String, String> extensions, String data) {
    public CloudEvent {
        Objects.requireNonNull(id, "id");
        Objects.requireNonNull(source, "source");
        Objects.requireNonNull(type, "type");
        Objects.requireNonNull(subject, "subject");
        Objects.requireNonNull(time, "time");
        extensions = Map.copyOf(extensions);
        Objects.requireNonNull(data, "data");
    }
}
