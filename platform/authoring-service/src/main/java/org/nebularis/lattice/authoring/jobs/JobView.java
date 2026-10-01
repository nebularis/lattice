// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.jobs;

import org.nebularis.lattice.authoring.model.JobStatus;

/** The full view of a job, as the {@code job-view} schema shapes it. */
public record JobView(String jobId, String documentId, int revision, JobStatus status, String error) {
    /** This job as the smaller {@code common.schema.json#/$defs/Job} shape: id and status only. */
    public JobSummary summary() {
        return new JobSummary(jobId, status);
    }
}
