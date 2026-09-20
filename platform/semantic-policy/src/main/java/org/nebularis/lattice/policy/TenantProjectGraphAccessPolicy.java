package org.nebularis.lattice.policy;

import org.nebularis.lattice.semantic.GraphReference;

public final class TenantProjectGraphAccessPolicy implements GraphAccessPolicy {
    @Override
    public void requireRead(Principal principal, GraphReference graph) {
        if (!principal.tenantId().equals(graph.tenantId()) || !principal.projectId().equals(graph.projectId()) || !principal.hasRole("graph-reader")) {
            throw new SecurityException("principal cannot read the requested graph scope");
        }
    }
}
