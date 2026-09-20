package org.nebularis.lattice.policy;

import java.util.Set;

public record Principal(String subject, String tenantId, String projectId, Set<String> roles) {
    public boolean hasRole(String role) {
        return roles.contains(role);
    }
}
