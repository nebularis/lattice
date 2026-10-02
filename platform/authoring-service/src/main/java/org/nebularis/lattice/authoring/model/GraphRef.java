// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

/**
 * A reference to a stored graph (common schema {@code $defs/GraphRef}). {@code tenantId} and
 * {@code projectId} are fixed consts of this POC: see ADR-A114.
 */
public record GraphRef(String tenantId, String projectId, String graphIri, String revisionHash) {
    public static final String TENANT_ID = "poc";
    public static final String PROJECT_ID = "word-authoring";

    public static GraphRef of(String graphIri, String revisionHash) {
        return new GraphRef(TENANT_ID, PROJECT_ID, graphIri, revisionHash);
    }
}
