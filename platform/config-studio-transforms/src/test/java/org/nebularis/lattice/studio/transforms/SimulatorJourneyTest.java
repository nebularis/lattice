// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonArray;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.atlas.json.JsonValue;
import org.junit.jupiter.api.Test;

/**
 * The frames the Playwright journey of the persistence simulator (SVA-P4) is answered with. The fake service of the studio's end-to-end suite cannot
 * run Jena, so it answers each step of the journey from {@code apps/config-studio/e2e/fixtures/simulator-facility-journey.json}, which holds the
 * body of each request the browser builds for the journey and the frames this worker gives for that body. This test runs each body through the run
 * worker and fails when the frames it publishes are not the fixture's, so the fixture cannot drift from what the worker does. The bodies are checked
 * against what the browser builds by {@code simulator.journey.test.ts}. Run with {@code -Djourney.update=true} to rewrite the frames from the worker,
 * and never write them by hand.
 */
class SimulatorJourneyTest {
    private static final Path FIXTURE = FacilityJob.PROFILE.resolveSibling("simulator-facility-journey.json");
    private static final Instant NOW = Instant.parse("2026-11-17T10:00:00Z");
    private static final Clock CLOCK = Clock.fixed(NOW, ZoneOffset.UTC);

    /** The frames the worker publishes for a body, as it publishes them, each checked against the frame schema. */
    private static JsonArray framesOf(String body) throws IOException {
        List<String> published = new ArrayList<>();
        try (RunWorker worker = new RunWorker("simulate", job -> {
            try {
                return FacilityJob.job();
            } catch (IOException e) {
                throw new IllegalStateException(e);
            }
        }, (run, frames) -> published.addAll(frames), CLOCK)) {
            Map<String, Object> headers = new HashMap<>();
            headers.put("run", Examples.RUN);
            headers.put("job", Examples.JOB);
            headers.put("kind", "simulate");
            headers.put("target", "persistence");
            headers.put("deadline", NOW.plusSeconds(15).toString());
            worker.apply(new Message(1, false, headers, "application/trig", null, null, body.getBytes(StandardCharsets.UTF_8)));
        }
        assertEquals(List.of(), new SchemaCheck().problems(published), "every frame holds against run-frame.schema.json");
        JsonArray out = new JsonArray();
        published.forEach(f -> out.add(JSON.parse(f)));
        return out;
    }

    private static String outcomeOf(JsonArray frames) {
        StringBuilder text = new StringBuilder();
        String role = null;
        for (JsonValue v : frames) {
            JsonObject f = v.getAsObject();
            if (f.hasKey("part")) {
                role = f.get("part").getAsObject().get("role").getAsString().value();
            }
            if ("outcome".equals(role) && f.hasKey("text")) {
                text.append(f.get("text").getAsString().value());
            }
        }
        return JSON.parse(text.toString()).get("outcome").getAsString().value();
    }

    @Test
    void theFramesOfTheSimulatorJourneyAreWhatTheRunWorkerGivesForTheStepsTheBrowserBuilds() throws IOException {
        JsonObject fixture = JSON.parse(Files.readString(FIXTURE));
        JsonArray steps = fixture.get("steps").getAsArray();
        assertFalse(steps.isEmpty(), "the fixture holds the journey's steps. Run simulator.journey.test.ts with UPDATE_JOURNEY=1 to write their bodies");
        boolean update = Boolean.getBoolean("journey.update");
        JsonArray rewritten = new JsonArray();
        for (JsonValue entry : steps) {
            JsonObject step = entry.getAsObject();
            JsonArray frames = framesOf(step.get("body").getAsString().value());
            String label = step.get("label").getAsString().value();
            assertEquals(step.get("outcome").getAsString().value(), outcomeOf(frames), "the outcome the journey expects of the step " + label);
            JsonObject next = new JsonObject();
            step.keys().forEach(k -> next.put(k, step.get(k)));
            next.put("frames", frames);
            rewritten.add(next);
            if (!update) {
                assertEquals(step.get("frames"), frames, "the frames of the step " + label + " are not what the worker gives. Run this test with -Djourney.update=true");
            }
        }
        if (update) {
            JsonObject out = new JsonObject();
            out.put("steps", rewritten);
            try (OutputStream w = Files.newOutputStream(FIXTURE)) {
                JSON.write(w, out);
                w.write('\n');
            }
        }
        assertTrue(steps.size() > 0);
    }
}
