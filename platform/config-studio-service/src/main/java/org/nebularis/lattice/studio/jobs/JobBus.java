// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

/** Hands a job to the worker. The message is the job IRI and nothing else. */
public interface JobBus extends AutoCloseable {
    /** Publishes the job IRI, or throws when the broker did not take it. */
    void publish(String jobIri) throws Exception;

    @Override
    default void close() {
    }
}
