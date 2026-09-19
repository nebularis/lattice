package org.nebularis.lattice.semantic.fuseki;

import static org.junit.jupiter.api.Assertions.assertTrue;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.semantic.DatasetCapability;

class FusekiScopedDatasetTest {
    @Test
    void declaresTheCapabilitiesImplementedByTheAdapter() {
        var dataset = new FusekiScopedDataset("http://localhost:3030/dataset");
        assertTrue(dataset.capabilities().contains(DatasetCapability.NAMED_GRAPH_READ));
    }
}