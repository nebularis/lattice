// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/** A bus that only remembers what was published. Jobs stay queued, so this is for tests and a broker-less run. */
public final class RecordingJobBus implements JobBus {
    private final List<String> published = new CopyOnWriteArrayList<>();
    private final List<String> longJobs = new CopyOnWriteArrayList<>();
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

    @Override
    public void publish(String jobIri, boolean longJob) {
        if (longJob) {
            longJobs.add(jobIri);
        }
        publish(jobIri);
    }

    /** What a test does when a run is published, such as answering it from inside the call, or failing. */
    public interface RunHook {
        void accept(RunMessage message) throws Exception;
    }

    private final List<RunMessage> runs = new CopyOnWriteArrayList<>();
    private volatile RunHook runHook = m -> { };

    /** Calls {@code hook} on each run published, after it is recorded. An exception it throws is the publish failing. */
    public void onRun(RunHook hook) {
        this.runHook = hook;
    }

    @Override
    public void publishRun(RunMessage message) throws Exception {
        runs.add(message);
        runHook.accept(message);
    }

    /** The runs published, in order. */
    public List<RunMessage> runs() {
        return List.copyOf(runs);
    }

    public List<String> published() {
        return List.copyOf(published);
    }

    /** The jobs published to the long queue, among {@link #published()} and those a stand-in worker ran. */
    public List<String> publishedLong() {
        return List.copyOf(longJobs);
    }
}
