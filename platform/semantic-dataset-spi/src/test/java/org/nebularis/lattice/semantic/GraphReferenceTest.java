package org.nebularis.lattice.semantic;

import static org.junit.jupiter.api.Assertions.assertThrows;
import org.junit.jupiter.api.Test;

class GraphReferenceTest {
    @Test
    void rejectsNonAbsoluteGraphIri() {
        assertThrows(IllegalArgumentException.class, () -> new GraphReference("tenant", "project", "graph", "revision"));
    }
}
