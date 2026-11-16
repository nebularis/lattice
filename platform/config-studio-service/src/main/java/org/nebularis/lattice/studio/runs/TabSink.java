// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.runs;

import java.time.Clock;
import java.util.UUID;
import java.util.function.Supplier;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.nebularis.lattice.outbox.CloudEvent;
import org.nebularis.lattice.studio.events.Notifier;

/**
 * Forwards a run's frames to the submitting tab, each as a CloudEvent in JSON on the tab's events topic, the way a job's event reaches
 * a tab. The event's {@code data} is the frame object as it was received. Its source is the service, which published it to the tab,
 * and its time comes from the clock, so the frame the service makes at a deadline has the same form as any other.
 */
public final class TabSink implements RunRegistry.Sink {
    private final String principal;
    private final String tab;
    private final TabEvents out;
    private final Clock clock;
    private final Supplier<UUID> ids;

    public TabSink(String principal, String tab, TabEvents out, Clock clock, Supplier<UUID> ids) {
        this.principal = principal;
        this.tab = tab;
        this.out = out;
        this.clock = clock;
        this.ids = ids;
    }

    @Override
    public void send(RunRegistry.Frame frame) {
        String run = ((JsonObject) JSON.parseAny(frame.json())).get("run").getAsString().value();
        CloudEvent event = new CloudEvent(ids.get(), RunRegistry.SERVICE_SOURCE, RunRegistry.FRAME_TYPE, run, clock.instant(),
            java.util.Map.of(), frame.json());
        out.publish(principal, tab, Notifier.json(event));
    }
}
