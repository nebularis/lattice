// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.api;

import java.util.List;
import org.nebularis.lattice.authoring.detection.Detection;
import org.nebularis.lattice.authoring.jobs.JobSummary;
import org.nebularis.lattice.authoring.model.GraphRef;
import org.nebularis.lattice.authoring.template.Finding;
import org.nebularis.lattice.authoring.validation.ValidationReportView;

/** The response of a successful {@code submitSnapshot}: the {@code snapshot-accepted} schema's shape. */
public record SnapshotAccepted(
    String documentId,
    int revision,
    GraphRef wordingGraph,
    ValidationReportView validation,
    List<Detection> detections,
    List<Finding> templateFindings,
    JobSummary job
) {
    public SnapshotAccepted {
        detections = List.copyOf(detections);
        templateFindings = List.copyOf(templateFindings);
    }
}
