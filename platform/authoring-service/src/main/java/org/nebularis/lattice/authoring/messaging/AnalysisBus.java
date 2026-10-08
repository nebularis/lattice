// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.messaging;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.function.Consumer;

/**
 * Where this service sends wording analysis requests and receives their results. A test seam
 * (WA4), not an SPI: see ADR-A118 decision 4. {@link InMemoryAnalysisBus} backs unit tests and
 * {@code RabbitMqAnalysisBus} (WA5) backs the runnable service.
 */
public interface AnalysisBus {
    /** Publishes an already-validated {@code wording-analysis-request} event. May throw. */
    void publish(JsonNode request);

    /** Registers the handler called for each {@code wording-analysis-result} event received. */
    void onResult(Consumer<JsonNode> handler);

    /** Whether the backing bus currently answers. Never throws. */
    boolean ping();
}
