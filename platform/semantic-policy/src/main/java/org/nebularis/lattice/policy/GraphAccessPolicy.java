package org.nebularis.lattice.policy;

import org.nebularis.lattice.semantic.GraphReference;

public interface GraphAccessPolicy {
    void requireRead(Principal principal, GraphReference graph);
}
