// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/** A bus that only remembers what was published. Jobs stay queued, so this is for tests and a broker-less run. */
public final class RecordingJobBus implements JobBus {
    private final List<String> published = new CopyOnWriteArrayList<>();
    private volatile java.util.function.Predicate<String> worker = iri -> false;

    /** Hands each job to {@code worker}, which says whether it ran the job. Only a job it did not run is recorded. For tests that stand in for the worker. */
    public void runWith(java.util.function.Predicate<String> worker) {
        this.worker = worker;
    }

    @Override
    public void publish(String jobIri) {
        if (!worker.test(jobIri)) {
            published.add(jobIri);
        }
    }

    public List<String> published() {
        return List.copyOf(published);
    }
}
