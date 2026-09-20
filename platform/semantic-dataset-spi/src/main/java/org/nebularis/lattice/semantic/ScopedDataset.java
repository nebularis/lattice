package org.nebularis.lattice.semantic;

import java.util.Set;

public interface ScopedDataset {
    Set<DatasetCapability> capabilities();
    DatasetSnapshot read(GraphReference reference);
}
