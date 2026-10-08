// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.jobs;

import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.UnaryOperator;
import org.nebularis.lattice.authoring.model.JobStatus;

/** Jobs live only in memory (decision WA-D10): a restart loses in-flight jobs, not analyses. */
public final class JobRegistry {
    private final Map<String, JobView> byId = new ConcurrentHashMap<>();

    public JobView queue(String jobId, String documentId, int revision) {
        JobView view = new JobView(jobId, documentId, revision, JobStatus.QUEUED, null);
        byId.put(jobId, view);
        return view;
    }

    public Optional<JobView> complete(String jobId) {
        return update(jobId, view -> new JobView(view.jobId(), view.documentId(), view.revision(),
            JobStatus.COMPLETED, null));
    }

    public Optional<JobView> fail(String jobId, String error) {
        return update(jobId, view -> new JobView(view.jobId(), view.documentId(), view.revision(),
            JobStatus.FAILED, error));
    }

    public Optional<JobView> get(String jobId) {
        return Optional.ofNullable(byId.get(jobId));
    }

    private Optional<JobView> update(String jobId, UnaryOperator<JobView> change) {
        return Optional.ofNullable(byId.computeIfPresent(jobId, (id, view) -> change.apply(view)));
    }
}
