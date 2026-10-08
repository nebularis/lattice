// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.api;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.List;
import org.nebularis.lattice.authoring.model.GraphRef;
import org.nebularis.lattice.authoring.template.Finding;

/**
 * The response of {@code GET .../analysis}: the worker's own {@code analysis} JSON (already
 * validated against the common schema's {@code Analysis} def when it arrived), plus this
 * service's conformance findings and the proposal graph reference.
 */
public record AnalysisView(String documentId, int revision, JsonNode analysis, List<Finding> conformance,
                           GraphRef proposalGraph) {
    public AnalysisView {
        conformance = List.copyOf(conformance);
    }
}
