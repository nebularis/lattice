// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.store;

import java.util.Optional;
import org.apache.jena.rdf.model.Model;

/**
 * Where this service keeps named graphs. A test seam (WA4), not an SPI: see ADR-A114 decision 4.
 * {@link org.nebularis.lattice.authoring.store.InMemoryAuthoringStore} backs unit tests and
 * {@code FusekiAuthoringStore} (WA5) backs the runnable service.
 */
public interface AuthoringStore {
    /** Blocks until the backing store answers, or throws. Called once at startup. */
    void ensureReady();

    /** Whether the backing store currently answers. Never throws. */
    boolean ping();

    void putGraph(String graphIri, Model model);

    Optional<Model> getGraph(String graphIri);
}
