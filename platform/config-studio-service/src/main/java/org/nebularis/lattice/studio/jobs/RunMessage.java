// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

import java.util.Arrays;
import java.util.Objects;

/**
 * The request a run worker is sent (ADR-A154, the contract's "The message to the run worker"). {@code routingKey} is the queue of the
 * run's kind, {@code body} the input as received, {@code contentType} its media type, {@code deadline} the absolute time as text and
 * {@code expirationMillis} the time until it, after which the broker drops a request no worker took.
 */
public record RunMessage(String routingKey, String run, String job, String kind, String target, String deadline, String contentType,
                         long expirationMillis, byte[] body) {
    public RunMessage {
        Objects.requireNonNull(routingKey);
        Objects.requireNonNull(run);
        Objects.requireNonNull(job);
        Objects.requireNonNull(kind);
        Objects.requireNonNull(target);
        Objects.requireNonNull(deadline);
        Objects.requireNonNull(contentType);
        body = body.clone();
    }

    @Override
    public byte[] body() {
        return body.clone();
    }

    @Override
    public boolean equals(Object o) {
        return o instanceof RunMessage m && routingKey.equals(m.routingKey) && run.equals(m.run) && job.equals(m.job)
            && kind.equals(m.kind) && target.equals(m.target) && deadline.equals(m.deadline) && contentType.equals(m.contentType)
            && expirationMillis == m.expirationMillis && Arrays.equals(body, m.body);
    }

    @Override
    public int hashCode() {
        return Objects.hash(routingKey, run, job, kind, target, deadline, contentType, expirationMillis) * 31 + Arrays.hashCode(body);
    }
}
