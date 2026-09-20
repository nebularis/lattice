package org.nebularis.lattice.policy;

import static org.junit.jupiter.api.Assertions.assertThrows;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.semantic.GraphReference;

class TenantProjectGraphAccessPolicyTest {
    @Test
    void preventsCrossTenantRead() {
        var policy = new TenantProjectGraphAccessPolicy();
        var principal = new Principal("subject", "tenant-a", "project", Set.of("graph-reader"));
        var graph = new GraphReference("tenant-b", "project", "https://example.test/graph", "abc");
        assertThrows(SecurityException.class, () -> policy.requireRead(principal, graph));
    }
}
