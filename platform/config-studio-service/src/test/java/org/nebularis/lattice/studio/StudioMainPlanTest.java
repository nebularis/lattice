// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.nio.file.Path;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.app.StudioConfig;
import org.nebularis.lattice.studio.app.StudioMain;
import org.nebularis.lattice.studio.app.StudioMain.Plan;

/** What the service starts for each combination of broker, events address and the broker's secret (ADR-A154 decision 10). */
class StudioMainPlanTest {
    private static StudioConfig config(String amqp, String eventsUrl, String secret) {
        return new StudioConfig(0, "127.0.0.1", Path.of("x"), null, null, "studio", null, null, amqp, Set.of(), 1L, eventsUrl, secret);
    }

    @Test
    void runsAreReadWheneverThereIsABrokerAndTabsAreServedOnlyWithEventsAndTheirSecret() {
        assertEquals(new Plan(false, false), StudioMain.plan(config(null, null, null)), "no broker, no runs");
        assertEquals(new Plan(false, false), StudioMain.plan(config(null, "ws://h/ws", "s")), "events need a broker");
        assertEquals(new Plan(true, false), StudioMain.plan(config("amqp://h", null, null)), "a broker alone reads runs");
        assertEquals(new Plan(true, false), StudioMain.plan(config("amqp://h", "ws://h/ws", null)), "events without the secret are not served");
        assertEquals(new Plan(true, false), StudioMain.plan(config("amqp://h", null, "s")));
        assertEquals(new Plan(true, true), StudioMain.plan(config("amqp://h", "ws://h/ws", "s")));
    }
}
