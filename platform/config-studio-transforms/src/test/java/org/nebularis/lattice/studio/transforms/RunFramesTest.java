// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.store.Cst;

/** The frames of a run's result, checked against `run-frame.schema.json` and against what the waiting transform route replies for the same input. */
class RunFramesTest {
    private static final SchemaCheck SCHEMA = schema();

    private static SchemaCheck schema() {
        try {
            return new SchemaCheck();
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    static List<String> json(List<JsonObject> frames) {
        return frames.stream().map(JSON::toStringFlat).toList();
    }

    /** Every rule of the schema and of the contract across a run's frames. */
    static List<String> checked(List<JsonObject> frames) {
        List<String> text = json(frames);
        assertEquals(List.of(), SCHEMA.problems(text));
        return text;
    }

    /** The parts of a run as its frames give them, each with the text of its frames joined. */
    private static List<Map.Entry<JsonObject, String>> parts(List<JsonObject> frames) {
        List<Map.Entry<JsonObject, StringBuilder>> out = new ArrayList<>();
        for (JsonObject f : frames) {
            if (f.hasKey("part")) {
                out.add(Map.entry(f.get("part").getAsObject(), new StringBuilder()));
            }
            if (f.hasKey("text")) {
                out.get(out.size() - 1).getValue().append(f.get("text").getAsString().value());
            }
        }
        return out.stream().map(e -> Map.entry(e.getKey(), e.getValue().toString())).toList();
    }

    private static TransformRun.Result result(String media, String sample, boolean reversed) throws IOException {
        return TransformRun.execute(Examples.compileJob(reversed), Examples.JOB, media, sample);
    }

    @Test
    void aSampleRunIsTheReportThenOneArtefactForEachMappingInCanonicalOrderAndEachTextIsWhatTheTransformRouteReplies() throws IOException {
        List<JsonObject> frames = RunFrames.of(Examples.RUN, result("application/xml", Examples.xmlSample(), false));
        checked(frames);
        List<Map.Entry<JsonObject, String>> parts = parts(frames);
        JsonObject report = parts.get(0).getKey();
        assertEquals("report", report.get("role").getAsString().value());
        assertEquals("text/turtle", report.get("mediaType").getAsString().value());
        Model parsed = ModelFactory.createDefaultModel();
        RDFDataMgr.read(parsed, new StringReader(parts.get(0).getValue()), null, Lang.TURTLE);
        assertEquals(2, parsed.listStatements(null, Cst.code, "NotRun").toList().size(), "the JSON scheme and the RDF scheme were not run");
        assertTrue(parts.get(0).getValue().contains("conforms"), "the report states whether it conforms");

        Model legacy = TransformRun.run(Examples.compileJob(false), Examples.JOB, "urn:lattice:studio:transform:00000000-0000-4000-8000-000000000002",
            "application/xml", Examples.xmlSample());
        Map<String, String> expected = new TreeMap<>();
        Map<String, String> paths = new TreeMap<>();
        for (Statement s : legacy.listStatements(null, Cst.artefact, (Resource) null).toList()) {
            Resource a = s.getResource();
            expected.put(a.getProperty(Cst.group).getString(), a.getProperty(Cst.content).getString());
            paths.put(a.getProperty(Cst.group).getString(), a.getProperty(Cst.path).getString());
        }
        assertEquals(expected.size() + 1, parts.size());
        int i = 1;
        for (Map.Entry<String, String> e : expected.entrySet()) {
            JsonObject part = parts.get(i).getKey();
            assertEquals("artefact", part.get("role").getAsString().value());
            assertEquals("application/n-triples", part.get("mediaType").getAsString().value());
            assertEquals(e.getKey(), part.get("group").getAsString().value(), "the artefacts are in order of their mapping");
            assertEquals(paths.get(e.getKey()), part.get("path").getAsString().value());
            assertEquals(0, part.get("step").getAsNumber().value().intValue());
            assertEquals(e.getValue(), parts.get(i).getValue(), "the text is the legacy reply's content for " + e.getKey());
            i++;
        }
        JsonObject last = frames.get(frames.size() - 1);
        assertTrue(last.get("last").getAsBoolean().value());
        assertEquals("succeeded", last.get("status").getAsString().value());
        assertTrue(last.get("conforms").getAsBoolean().value());
        assertFalse(last.hasKey("text"));
        for (int k = 0; k < frames.size(); k++) {
            assertEquals(k, frames.get(k).get("seq").getAsNumber().value().intValue());
            assertFalse(frames.get(k).hasKey("more"), "no part of this run is cut");
        }
    }

    @Test
    void aPartLongerThanAFrameIsCutBetweenCharactersAndTheFramesJoinToTheExactText() {
        // Three- and four-byte characters placed so that the boundary falls inside one at each of the four offsets.
        for (int pad = 0; pad < 8; pad++) {
            String text = "a".repeat(RunFrames.MAX_TEXT_BYTES - 5 + pad) + "€😀€😀".repeat(30) + "z";
            List<String> pieces = RunFrames.cut(text);
            assertTrue(pieces.size() > 1, "pad " + pad);
            for (String p : pieces) {
                assertTrue(p.getBytes(StandardCharsets.UTF_8).length <= RunFrames.MAX_TEXT_BYTES, "pad " + pad);
            }
            assertEquals(text, String.join("", pieces), "pad " + pad + " lost or changed a character");
            assertFalse(String.join("", pieces).contains("�"), "pad " + pad);
        }
        String text = "a".repeat(RunFrames.MAX_TEXT_BYTES - 1) + "€".repeat(40000) + "😀".repeat(20000);
        TransformRun.Result r = new TransformRun.Result(null, List.of(new TransformRun.Output("urn:example:m#Big", "0/Big.nt", text)));
        List<JsonObject> frames = RunFrames.of(Examples.RUN, r);
        checked(frames);
        List<JsonObject> own = frames.stream().filter(f -> f.hasKey("text")).toList();
        StringBuilder joined = new StringBuilder();
        int inPart = 0;
        for (int k = 1; k < frames.size() - 1; k++) {
            JsonObject f = frames.get(k);
            if (f.hasKey("part") && f.get("part").getAsObject().get("role").getAsString().value().equals("artefact")) {
                inPart = k;
            }
            if (inPart > 0) {
                joined.append(f.get("text").getAsString().value());
                boolean lastOfPart = k == frames.size() - 2;
                assertEquals(!lastOfPart, f.hasKey("more") && f.get("more").getAsBoolean().value(), "more is true on every frame of a part but its last, frame " + k);
                assertEquals(k == inPart, f.hasKey("part"), "part is on a part's first frame only, frame " + k);
            }
        }
        assertEquals(text, joined.toString());
        assertTrue(own.size() > 3);
    }

    @Test
    void aResultOfMoreThan128FramesIsOneFailedFrameAndOneOf128IsSent() {
        for (int outputs : new int[] {126, 127, 200}) {
            List<Object> events = new ArrayList<>();
            for (int i = 0; i < outputs; i++) {
                events.add(new TransformRun.Output(String.format("urn:example:m#M%03d", i), "0/M.nt", "<urn:a> <urn:b> <urn:c> .\n"));
            }
            List<JsonObject> frames = RunFrames.of(Examples.RUN, new TransformRun.Result(null, events));
            checked(frames);
            if (outputs == 126) {
                assertEquals(RunFrames.MAX_FRAMES, frames.size(), "the report, 126 artefacts and the last frame are 128 frames");
                assertEquals("succeeded", frames.get(127).get("status").getAsString().value());
            } else {
                assertEquals(1, frames.size(), outputs + " artefacts");
                assertEquals(0, frames.get(0).get("seq").getAsNumber().value().intValue());
                assertTrue(frames.get(0).get("last").getAsBoolean().value());
                assertEquals("failed", frames.get(0).get("status").getAsString().value());
                assertTrue(frames.get(0).get("message").getAsString().value().contains("too large"));
                assertTrue(frames.get(0).get("message").getAsString().value().contains("narrow"));
            }
        }
    }

    @Test
    void theSameRunTwiceAndTheSameJobInAnotherOrderGiveTheSameFrames() throws IOException {
        List<String> first = json(RunFrames.of(Examples.RUN, result("application/xml", Examples.xmlSample(), false)));
        assertEquals(first, json(RunFrames.of(Examples.RUN, result("application/xml", Examples.xmlSample(), false))));
        assertEquals(first, json(RunFrames.of(Examples.RUN, result("application/xml", Examples.xmlSample(), true))), "artefacts added in reverse order");
        List<String> jsonFirst = json(RunFrames.of(Examples.RUN, result("application/json", Examples.jsonSample(), false)));
        assertEquals(jsonFirst, json(RunFrames.of(Examples.RUN, result("application/json", Examples.jsonSample(), true))));
        assertTrue(jsonFirst.size() > 2);
    }

    @Test
    void aFailedResultIsOneFailedFrame() {
        List<JsonObject> frames = RunFrames.of(Examples.RUN, new TransformRun.Result("xml: broken", List.of()));
        JsonObject expected = JSON.parse("{\"run\":\"" + Examples.RUN + "\",\"seq\":0,\"last\":true,\"status\":\"failed\",\"message\":\"xml: broken\"}");
        assertEquals(List.of(JSON.toStringFlat(expected)), checked(frames));
    }

    private static String mutate(String frame, java.util.function.Consumer<JsonObject> change) {
        JsonObject o = JSON.parse(frame);
        change.accept(o);
        return JSON.toStringFlat(o);
    }

    @Test
    void theSchemaCheckRefusesWhatTheSchemaRefusesAndAcceptsTheContractsExample() throws IOException {
        Path example = Path.of("..", "..", "contracts", "config-studio", "samples", "run-frames.example.json");
        List<String> frames = JSON.parseAny(Files.readString(example)).getAsArray().stream().map(JSON::toStringFlat).toList();
        assertEquals(List.of(), SCHEMA.problems(frames), "the contract's complete example");
        String ok = frames.get(1);
        assertEquals(List.of(), SCHEMA.problems(ok));
        List<String> bad = List.of(
            mutate(ok, o -> o.put("extra", 1)),
            mutate(ok, o -> o.get("part").getAsObject().put("role", "nonsense")),
            mutate(ok, o -> o.put("status", "succeeded")),
            mutate(ok, o -> o.put("seq", 129)),
            mutate(ok, o -> o.put("run", "urn:x:1")),
            mutate(frames.get(3), o -> o.put("status", "failed")),
            mutate(frames.get(3), o -> o.put("more", true)),
            mutate(ok, o -> o.put("text", "\u20ac".repeat(16385))));
        for (int i = 0; i < bad.size(); i++) {
            assertFalse(SCHEMA.problems(bad.get(i)).isEmpty(), "bad frame " + i);
        }
        assertFalse(SCHEMA.problems(List.of(frames.get(0), frames.get(2))).isEmpty(), "a gap in seq");
    }
}
