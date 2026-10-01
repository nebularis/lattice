// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.messaging;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Consumer;

/** An {@link AnalysisBus} that records published requests and delivers results on demand, for tests. */
public final class InMemoryAnalysisBus implements AnalysisBus {
    private final List<JsonNode> published = new ArrayList<>();
    private Consumer<JsonNode> handler;
    private boolean failOnPublish;

    @Override
    public void publish(JsonNode request) {
        if (failOnPublish) {
            throw new IllegalStateException("analysis bus is set to fail");
        }
        published.add(request);
    }

    @Override
    public void onResult(Consumer<JsonNode> handler) {
        this.handler = handler;
    }

    @Override
    public boolean ping() {
        return true;
    }

    /** Test control: makes every later {@link #publish} throw. */
    public void failOnPublish() {
        this.failOnPublish = true;
    }

    /** Test control: every request handed to {@link #publish} so far, in order. */
    public List<JsonNode> published() {
        return List.copyOf(published);
    }

    /** Test control: delivers a result to the registered handler, as a real consumer would. */
    public void deliver(JsonNode result) {
        if (handler != null) {
            handler.accept(result);
        }
    }
}
