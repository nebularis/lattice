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
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.vocabulary.RDF;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.store.Cst;

/**
 * The frames the XML and JSON sample runs of the Playwright journeys (SVA-M3b) are answered with. The fake service of the studio's end-to-end suite cannot
 * run Saxon or JOLT, so it answers each run from {@code apps/config-studio/e2e/fixtures/sample-runs.json}, which holds the compilation of each workspace
 * as the compiler gave it, the sample the author gives and the frames a worker gave for it. This test runs each XML or JSON sample over its workspace's
 * compilation through the run worker and fails when the frames it publishes are not the fixture's, so the fixture cannot drift from what the worker does.
 * The compilations and the Turtle runs are kept current by {@code workers/tests/test_config_studio_sample_runs.py}, and the bodies and samples by
 * {@code sample.journey.test.ts}. Run with {@code -Dsamples.update=true} to rewrite the frames from the worker, and never write them by hand.
 */
class SampleRunsTest {
    private static final Path FIXTURE = Path.of("..", "..", "apps", "config-studio", "e2e", "fixtures", "sample-runs.json");
    private static final Instant NOW = Instant.parse("2026-11-20T10:00:00Z");
    private static final Clock CLOCK = Clock.fixed(NOW, ZoneOffset.UTC);

    private static String text(JsonObject o, String key) {
        return o.get(key).getAsString().value();
    }

    /** The compile job as the run worker reads it from the store: the artefacts the compiler gave, each with its group, path, media type and text. */
    private static Model compileJob(JsonObject workspace) {
        Model m = ModelFactory.createDefaultModel();
        Resource job = m.createResource(Examples.JOB).addProperty(RDF.type, Cst.Job).addProperty(Cst.kind, Cst.Compile)
            .addProperty(Cst.target, Cst.target("mapping")).addProperty(Cst.status, Cst.Succeeded);
        int n = 0;
        for (JsonValue v : workspace.get("compiled").getAsArray()) {
            JsonObject a = v.getAsObject();
            job.addProperty(Cst.artefact, m.createResource(Examples.JOB + "#artefact-" + ++n).addProperty(Cst.group, text(a, "group"))
                .addProperty(Cst.path, text(a, "path")).addProperty(Cst.mediaType, text(a, "mediaType")).addProperty(Cst.content, text(a, "content")));
        }
        return m;
    }

    /** The frames the worker publishes for a sample, as it publishes them, each checked against the frame schema. */
    private static JsonArray framesOf(JsonObject workspace, String mediaType, String sample) throws IOException {
        Model job = compileJob(workspace);
        List<String> published = new ArrayList<>();
        try (RunWorker worker = new RunWorker("sample", iri -> job, (run, frames) -> published.addAll(frames), CLOCK)) {
            Map<String, Object> headers = new HashMap<>();
            headers.put("run", Examples.RUN);
            headers.put("job", Examples.JOB);
            headers.put("kind", "sample");
            headers.put("target", "mapping");
            headers.put("deadline", NOW.plusSeconds(120).toString());
            worker.apply(new Message(1, false, headers, mediaType, null, null, sample.getBytes(StandardCharsets.UTF_8)));
        }
        assertEquals(List.of(), new SchemaCheck().problems(published), "every frame holds against run-frame.schema.json");
        JsonArray out = new JsonArray();
        published.forEach(f -> out.add(JSON.parse(f)));
        return out;
    }

    private static JsonObject workspace(JsonArray workspaces, String id) {
        for (JsonValue v : workspaces) {
            if (text(v.getAsObject(), "id").equals(id)) {
                return v.getAsObject();
            }
        }
        throw new IllegalStateException("the fixture holds no workspace " + id);
    }

    @Test
    void theFramesOfTheXmlAndJsonRunsAreWhatTheRunWorkerGivesForTheSamplesTheJourneysGive() throws IOException {
        JsonObject fixture = JSON.parse(Files.readString(FIXTURE));
        JsonArray workspaces = fixture.get("workspaces").getAsArray();
        JsonArray runs = fixture.get("runs").getAsArray();
        boolean update = Boolean.getBoolean("samples.update");
        JsonArray rewritten = new JsonArray();
        int mine = 0;
        for (JsonValue entry : runs) {
            JsonObject run = entry.getAsObject();
            if (!text(run, "worker").equals("java")) {
                rewritten.add(run);
                continue;
            }
            mine++;
            String id = text(run, "id");
            JsonObject ws = workspace(workspaces, text(run, "workspace"));
            assertFalse(ws.get("compiled").getAsArray().isEmpty(), "the fixture holds the compilation of " + text(run, "workspace")
                + ". Run test_config_studio_sample_runs.py with LATTICE_WRITE_SAMPLE_RUNS=1 to write it");
            JsonArray frames = framesOf(ws, text(run, "mediaType"), text(run, "sample"));
            assertEquals("succeeded", frames.get(frames.size() - 1).getAsObject().get("status").getAsString().value(), "the run " + id + " succeeds");
            JsonObject next = new JsonObject();
            run.keys().forEach(k -> next.put(k, run.get(k)));
            next.put("frames", frames);
            rewritten.add(next);
            if (!update) {
                assertEquals(run.get("frames"), frames, "the frames of the run " + id + " are not what the worker gives. Run this test with -Dsamples.update=true");
            }
        }
        if (update) {
            JsonObject out = new JsonObject();
            fixture.keys().forEach(k -> out.put(k, fixture.get(k)));
            out.put("runs", rewritten);
            try (OutputStream w = Files.newOutputStream(FIXTURE)) {
                JSON.write(w, out);
                w.write('\n');
            }
        }
        assertTrue(mine > 0, "the fixture holds a run for the Java run worker");
    }
}
