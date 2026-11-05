// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

/** Hands a job to the worker. The message is the job IRI and nothing else. */
public interface JobBus extends AutoCloseable {
    /** Publishes the job IRI, or throws when the broker did not take it. */
    void publish(String jobIri) throws Exception;

    /**
     * Publishes the job IRI to the queue of its lane, the long queue when {@code longJob} (see {@link Lanes}). A bus with one queue
     * publishes to it.
     */
    default void publish(String jobIri, boolean longJob) throws Exception {
        publish(jobIri);
    }

    /**
     * Asks the transforms worker to run the compile job {@code jobIri}'s transforms over {@code sample}, given as
     * {@code mediaType}, and waits up to {@code timeout} for its reply, a Turtle graph under
     * {@code urn:lattice:studio:transform:{id}} (ADR-A148). Null when no worker answered in time, as a bus without a
     * broker never does.
     */
    default byte[] transform(String id, String jobIri, String mediaType, byte[] sample, java.time.Duration timeout) throws Exception {
        return null;
    }

    /**
     * How many workers consume {@code queue}, or -1 when the bus cannot say, as one without a broker cannot. The studio warns when a
     * queue it publishes to has none (plan studio-worker-liveness, WL-Q6).
     */
    default int consumers(String queue) throws Exception {
        return -1;
    }

    @Override
    default void close() {
    }
}
