// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.jobs;

import org.nebularis.lattice.authoring.model.JobStatus;

/** A job as the common schema's {@code Job} def shapes it: {@code jobId} and {@code status} only. */
public record JobSummary(String jobId, JobStatus status) {
}
