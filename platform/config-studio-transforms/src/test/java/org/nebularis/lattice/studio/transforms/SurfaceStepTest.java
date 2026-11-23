// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.TreeSet;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonArray;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.atlas.json.JsonValue;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFParser;
import org.apache.jena.riot.out.NodeFmtLib;
import org.apache.jena.sparql.core.DatasetGraph;
import org.apache.jena.sparql.core.DatasetGraphFactory;
import org.apache.jena.sparql.core.Quad;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.store.Graphs;

/**
 * The surface simulator's step (SVA-S2). The expectation is {@code surface-steps/expected.json}, which
 * {@code workers/tests/test_config_studio_surface_step_fixture.py} writes with the surface compiler and keeps current, so the rows and the
 * contracts a step names are the compiler's and never written by hand here.
 */
class SurfaceStepTest {
    private static final String RUN = "urn:lattice:studio:run:3f2b8c1e-5a47-4d0e-9b1a-6c7d8e9f0a1b";
    private static final List<String> STEPS = List.of("borrower", "drawdown", "first", "repay", "sector", "subtype", "vocabulary").stream().map(n -> "facility-surface-step-" + n + ".trig").toList();
    private static final String PREFIXES = """
        @prefix cst: <https://www.nebularis.org/neuro-semantic/lattice/config-studio#> .
        @prefix ex:  <https://example.org/lending#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        """;
    private static final String STEP_OK = """
        <urn:lattice:studio:step> { <urn:lattice:studio:step> a cst:SimulationStepRequest ; cst:forPart cst:Surface ;
            cst:transactionTime "2026-04-02T09:30:00Z"^^xsd:dateTime . }
        """;
    private static final String WORLD = """
        <urn:g:facilities> {
            ex:acme-foods a ex:Borrower ; ex:borrowerSector ex:FoodProcessing .
            ex:facility-1 a ex:Facility ; ex:borrower ex:acme-foods .
            ex:drawdown-1 a ex:Drawdown ; ex:drawnUnder ex:facility-1 .
        }
        """;

    private static JsonObject expected(String step) throws IOException {
        return JSON.parse(Files.readString(java.nio.file.Path.of("src", "test", "resources", "surface-steps", "expected.json"))).getAsObject().get(step).getAsObject();
    }

    private static String sample(String name) throws IOException {
        return Files.readString(FacilityJob.SAMPLES.resolve(name));
    }

    private static PersistenceStep.Result run(String trig) throws IOException {
        return SurfaceStep.execute(SurfaceJob.job(), Examples.JOB, trig, 60_000);
    }

    private static Set<Quad> quads(String text, Lang lang) {
        DatasetGraph ds = DatasetGraphFactory.create();
        RDFParser.fromString(text, lang).parse(ds);
        Set<Quad> out = new HashSet<>();
        ds.find().forEachRemaining(out::add);
        return out;
    }

    private static Set<Quad> lines(JsonValue array) {
        StringBuilder text = new StringBuilder();
        array.getAsArray().forEach(v -> text.append(v.getAsString().value()).append('\n'));
        return quads(text.toString(), Lang.NQUADS);
    }

    private static PersistenceStep.Part part(PersistenceStep.Result r, String role, String path) {
        return r.parts().stream().filter(p -> p.role().equals(role) && (path == null || path.equals(p.path()))).findFirst().orElseThrow(() -> new AssertionError(role + " " + path));
    }

    private static JsonObject json(PersistenceStep.Result r, String role) {
        return JSON.parse(part(r, role, null).text());
    }

    private static List<String> frames(PersistenceStep.Result r) {
        return RunFrames.ofStep(RUN, r).stream().map(JSON::toStringFlat).toList();
    }

    // ---- S2-T1: the rows and the contracts the compiler gives

    @Test
    void theRowsBeforeAndAfterAndTheirChangeAreTheCompilersForEachStepOfTheSample() throws Exception {
        for (String name : STEPS) {
            JsonObject want = expected(name);
            PersistenceStep.Result r = run(sample(name));
            assertNull(r.failure(), name + ": " + r.failure());
            JsonObject contracts = want.get("contracts").getAsObject();
            JsonArray delta = json(r, "delta").get("contracts").getAsArray();
            assertEquals(contracts.keys().stream().sorted().toList(), delta.stream().map(v -> v.getAsObject().get("key").getAsString().value()).toList(), name + " keeps these contracts");
            for (String key : contracts.keys()) {
                JsonObject c = contracts.get(key).getAsObject();
                assertEquals(lines(c.get("before")), quads(part(r, "artefact", key + "/rows-before.trig").text(), Lang.TRIG), name + " " + key + " before");
                assertEquals(lines(c.get("after")), quads(part(r, "artefact", key + "/rows-after.trig").text(), Lang.TRIG), name + " " + key + " after");
                JsonObject d = delta.stream().map(JsonValue::getAsObject).filter(o -> o.get("key").getAsString().value().equals(key)).findFirst().orElseThrow();
                StringBuilder asserted = new StringBuilder();
                StringBuilder retracted = new StringBuilder();
                for (JsonValue g : d.get("graphs").getAsArray()) {
                    String graph = g.getAsObject().get("graph").getAsString().value();
                    g.getAsObject().get("asserted").getAsArray().forEach(l -> asserted.append(l.getAsString().value()).append(" <").append(graph).append("> .\n"));
                    g.getAsObject().get("retracted").getAsArray().forEach(l -> retracted.append(l.getAsString().value()).append(" <").append(graph).append("> .\n"));
                }
                assertEquals(lines(c.get("asserted")), quads(asserted.toString().replace(" . <", " <"), Lang.NQUADS), name + " " + key + " asserted");
                assertEquals(lines(c.get("retracted")), quads(retracted.toString().replace(" . <", " <"), Lang.NQUADS), name + " " + key + " retracted");
            }
            JsonObject outcome = json(r, "outcome");
            assertEquals(PersistenceStep.ENGINE, outcome.get("engine").getAsString().value());
            assertEquals(want.get("sources").getAsArray().stream().map(v -> v.getAsString().value()).toList(), outcome.get("sources").getAsArray().stream().map(v -> v.getAsString().value()).toList());
            assertEquals(want.get("reached").getAsArray().stream().map(v -> v.getAsString().value()).toList(), outcome.get("reached").getAsArray().stream().map(v -> v.getAsString().value()).toList(),
                name + " reaches the sources whose rows the compiler's rebuild changes");
            List<String> touched = outcome.get("contracts").getAsArray().stream().map(JsonValue::getAsObject)
                .filter(o -> o.get("readSetTouched").getAsBoolean().value()).map(o -> o.get("key").getAsString().value()).toList();
            assertEquals(want.get("touched").getAsArray().stream().map(v -> v.getAsString().value()).toList(), touched, name + " touches the contracts the invalidation names");
        }
    }

    @Test
    void anIndexIsListedAsNotKeptWithItsReasonAndItsReadSetStillSaysWhetherTheEditTouchedIt() throws Exception {
        PersistenceStep.Result r = run(sample("facility-surface-step-sector.trig"));
        List<JsonObject> rows = json(r, "outcome").get("contracts").getAsArray().stream().map(JsonValue::getAsObject).toList();
        assertEquals(List.of("borrower-sector", "drawdown-sector"), rows.stream().map(o -> o.get("key").getAsString().value()).toList());
        JsonObject index = rows.get(0);
        assertEquals("index", index.get("kind").getAsString().value());
        assertEquals(false, index.get("kept").getAsBoolean().value());
        assertTrue(index.get("reason").getAsString().value().contains("naming policy"));
        assertEquals(true, index.get("readSetTouched").getAsBoolean().value());
        assertEquals(List.of("artefact", "artefact", "delta", "outcome"), r.parts().stream().map(PersistenceStep.Part::role).toList(), "the index has no rows to show");
    }

    @Test
    void theStepRunsTheWritersMaintenanceOfTheJobAndNothingElse() throws Exception {
        // The rows of the sample are the writer's own: Maintenance.operations over the job's operations, a clear then a fill for each contract.
        Map<String, String> artefacts = SurfaceJob.artefacts();
        org.nebularis.lattice.studio.store.Maintenance m = org.nebularis.lattice.studio.store.Maintenance.of(artefacts.get("maintenance/partition-clear.rq"),
            Map.of(SurfaceStep.FAMILY, List.of(new org.nebularis.lattice.studio.store.Maintenance.Fill("drawdown-sector", artefacts.get("maintenance/drawdown-sector-fill-all.rq")))));
        assertEquals(2, m.operations(SurfaceStep.FAMILY, "urn:g:facilities").size());
        assertNull(m.operations(SurfaceStep.FAMILY, "urn:g:facilities").get(0).contract());
        assertEquals("drawdown-sector", m.operations(SurfaceStep.FAMILY, "urn:g:facilities").get(1).contract());
        assertEquals(Graphs.promoted("urn:g:facilities"), "urn:lattice:studio:promoted:urn:g:facilities");
    }

    // ---- S2-T2: a function of its request

    /** The TriG with each quad on a line of its own, in the order the seed gives, and the same quads for seed 0. */
    private static String shuffled(String trig, long seed) {
        DatasetGraph ds = DatasetGraphFactory.create();
        RDFParser.fromString(trig, Lang.TRIG).parse(ds);
        List<String> out = new ArrayList<>();
        ds.find().forEachRemaining(q -> {
            String triple = NodeFmtLib.strNT(q.getSubject()) + " " + NodeFmtLib.strNT(q.getPredicate()) + " " + NodeFmtLib.strNT(q.getObject()) + " .";
            out.add(Quad.isDefaultGraph(q.getGraph()) ? "{ " + triple + " }" : "<" + q.getGraph().getURI() + "> { " + triple + " }");
        });
        if (seed == 0) {
            Collections.sort(out);
        } else {
            Collections.shuffle(out, new Random(seed));
        }
        return String.join("\n", out) + "\n";
    }

    @Test
    void theSameStepGivesTheSameFramesOnARepeatAndWhenItsQuadsAreGivenInAnotherOrder() throws Exception {
        for (String name : STEPS) {
            String trig = sample(name);
            List<String> first = frames(run(shuffled(trig, 0)));
            assertTrue(first.size() >= 3, name);
            assertEquals(first, frames(run(shuffled(trig, 0))), name + " on a repeat");
            for (long seed = 1; seed <= 6; seed++) {
                assertEquals(first, frames(run(shuffled(trig, seed))), name + " with seed " + seed);
            }
            assertEquals(first, frames(run(trig)), name + " as the sample is written");
        }
    }

    @Test
    void aStepSharesNothingWithTheOneBeforeIt() throws Exception {
        String sector = sample("facility-surface-step-sector.trig");
        List<String> alone = frames(run(sample("facility-surface-step-first.trig")));
        run(sector);
        assertEquals(alone, frames(run(sample("facility-surface-step-first.trig"))));
    }

    @Test
    void anEditToTheDefaultGraphAndAnEmptyEditKeepNoRowsAndStillAnswer() throws Exception {
        String edit = PREFIXES + WORLD + STEP_OK + "<urn:lattice:studio:step/added> { ex:facility-1 ex:margin 3.5 . }\n";
        PersistenceStep.Result r = run(edit);
        assertNull(r.failure(), r.failure());
        assertEquals(List.of(), json(r, "outcome").get("sources").getAsArray().stream().toList());
        assertEquals("", part(r, "artefact", "drawdown-sector/rows-after.trig").text());
        PersistenceStep.Result none = run(PREFIXES + WORLD + STEP_OK);
        assertNull(none.failure(), none.failure());
        assertEquals(List.of(), json(none, "delta").get("contracts").getAsArray().get(0).getAsObject().get("graphs").getAsArray().stream().toList());
    }

    @Test
    void theStatedTimeReplacesNowInTheJobsOperations() throws Exception {
        String fill = """
            INSERT { GRAPH $derived { ?c <urn:p:at> ?t } } WHERE { { FILTER(ISIRI($source) && ISIRI($derived)) } GRAPH $source { ?c a <https://example.org/lending#Drawdown> } BIND(NOW() AS ?t) }
            """;
        Model job = SurfaceJob.job(a -> a.put("maintenance/drawdown-sector-fill-all.rq", fill));
        PersistenceStep.Result r = SurfaceStep.execute(job, Examples.JOB, sample("facility-surface-step-drawdown.trig"), 60_000);
        assertNull(r.failure(), r.failure());
        String rows = part(r, "artefact", "drawdown-sector/rows-after.trig").text();
        assertTrue(rows.contains("\"2026-04-02T09:30:00Z\"^^<http://www.w3.org/2001/XMLSchema#dateTime>"), rows);
        assertEquals(1, rows.lines().filter(l -> l.contains("drawdown-4")).count());
    }

    // ---- S2-T3: each failure says which part

    private static void failsWith(String trig, String message) throws IOException {
        PersistenceStep.Result r = run(trig);
        assertTrue(r.failure() != null && r.failure().contains(message), "wanted <" + message + "> in <" + r.failure() + ">");
        assertEquals(List.of(), r.parts());
        List<JsonObject> frames = RunFrames.ofStep(RUN, r);
        assertEquals(1, frames.size());
        assertEquals("failed", frames.get(0).get("status").getAsString().value());
    }

    private static String step(String body) {
        return PREFIXES + WORLD + "<urn:lattice:studio:step> { <urn:lattice:studio:step> a cst:SimulationStepRequest ; " + body + " }\n";
    }

    private static final String TIME = "cst:transactionTime \"2026-04-02T09:30:00Z\"^^xsd:dateTime";

    @Test
    void eachMissingOrMalformedPartOfTheStepIsOneFailedStepThatSaysWhichPart() throws Exception {
        failsWith("", "The step is empty");
        failsWith("<urn:a> <urn:b> .", "not valid TriG");
        failsWith(PREFIXES + WORLD, "holds no cst:SimulationStepRequest");
        failsWith(step("cst:forPart cst:Surface ; " + TIME + " .") + "<urn:lattice:studio:step> { <urn:s2> a cst:SimulationStepRequest . }", "holds 2 steps");
        failsWith(step(TIME + " ."), "does not say cst:forPart");
        failsWith(step("cst:forClass ex:Facility ; " + TIME + " ."), "names cst:forClass, as a persistence step does");
        failsWith(step("cst:forPart cst:Surface , cst:Persistence ; " + TIME + " ."), "cst:forPart once, as an IRI");
        failsWith(step("cst:forPart \"surface\" ; " + TIME + " ."), "cst:forPart once, as an IRI");
        failsWith(step("cst:forPart cst:Persistence ; " + TIME + " ."), "this run simulates the surface part");
        failsWith(step("cst:forPart cst:Surface ."), "does not say cst:transactionTime");
        failsWith(step("cst:forPart cst:Surface ; cst:transactionTime \"2026-04-02T09:30:00\"^^xsd:dateTime ."), "valid xsd:dateTime with a time zone");
        failsWith(step("cst:forPart cst:Surface ; cst:transactionTime \"yesterday\" ."), "valid xsd:dateTime with a time zone");
    }

    @Test
    void eachMalformedEditIsOneFailedStepThatSaysWhichGraph() throws Exception {
        String ok = "cst:forPart cst:Surface ; " + TIME + " .";
        failsWith(step(ok) + "<urn:lattice:studio:step/payload> { ex:a ex:b ex:c . }", "<urn:lattice:studio:step/payload> is reserved for the step");
        failsWith(step(ok) + "<urn:lattice:studio:step/addedtoo> { ex:a ex:b ex:c . }", "is reserved for the step");
        failsWith(step(ok) + "<urn:lattice:studio:step/added/urn%3Ag%3> { ex:a ex:b ex:c . }", "not percent-encoded as ENCODE_FOR_URI writes it");
        failsWith(step(ok) + "<urn:lattice:studio:step/added/urn%3Ag%ZZfacilities> { ex:a ex:b ex:c . }", "not percent-encoded as ENCODE_FOR_URI writes it");
        failsWith(step(ok) + "<urn:lattice:studio:step/added/facilities> { ex:a ex:b ex:c . }", "which is not an IRI");
        failsWith(step(ok) + "<urn:lattice:studio:step/removed/urn%3Ag%20x> { ex:a ex:b ex:c . }", "which is not an IRI");
        failsWith(step(ok) + "<urn:lattice:studio:step/added/urn%3Alattice%3Astudio%3Astep> { ex:a ex:b ex:c . }", "edits a graph that is reserved for the step");
        failsWith(step(ok) + "<urn:lattice:studio:step/added/urn%3Alattice%3Astudio%3Apromoted%3Aurn%3Ag%3Afacilities> { ex:a ex:b ex:c . }", "edits the derived rows");
        failsWith(step(ok) + "<urn:lattice:studio:step/added/urn%3Ag%3Afacilities> { ex:a ex:b ex:c . }\n<urn:lattice:studio:step/removed/urn%3Ag%3Afacilities> { ex:a ex:b ex:c . }",
            "both adds and removes");
    }

    @Test
    void aJobThatIsNotAFinishedSurfaceCompilationOrLacksWhatTheStepNeedsIsOneFailedStep() throws Exception {
        String trig = sample("facility-surface-step-sector.trig");
        assertTrue(SurfaceStep.execute(FacilityJob.job(), Examples.JOB, trig, 60_000).failure().contains("not a finished compilation of the surface part"));
        Model unfinished = SurfaceJob.job();
        unfinished.removeAll(unfinished.createResource(Examples.JOB), org.nebularis.lattice.studio.store.Cst.status, null);
        assertTrue(SurfaceStep.execute(unfinished, Examples.JOB, trig, 60_000).failure().contains("not a finished compilation of the surface part"));
        assertTrue(SurfaceStep.execute(SurfaceJob.job(a -> a.remove("maintenance/manifest.json")), Examples.JOB, trig, 60_000).failure().contains("no maintenance manifest"));
        assertTrue(SurfaceStep.execute(SurfaceJob.job(a -> a.put("maintenance/manifest.json", "{")), Examples.JOB, trig, 60_000).failure().contains("maintenance manifest could not be read"));
        assertTrue(SurfaceStep.execute(SurfaceJob.job(a -> a.put("maintenance/manifest.json", "[{\"key\": \"k\"}]")), Examples.JOB, trig, 60_000).failure().contains("without a key, a contract and a kind"));
        assertTrue(SurfaceStep.execute(SurfaceJob.job(a -> a.remove("maintenance/drawdown-sector-fill-all.rq")), Examples.JOB, trig, 60_000).failure()
            .contains("names fill of the contract drawdown-sector, which the job does not hold"));
        assertTrue(SurfaceStep.execute(SurfaceJob.job(a -> a.remove("maintenance/partition-clear.rq")), Examples.JOB, trig, 60_000).failure().contains("no partition clear"));
        assertTrue(SurfaceStep.execute(SurfaceJob.job(a -> a.put("maintenance/drawdown-sector-read-set.rq", "CONSTRUCT {")), Examples.JOB, trig, 60_000).failure()
            .contains("read set of the contract drawdown-sector is not a query Jena reads"));
        assertTrue(SurfaceStep.execute(SurfaceJob.job(a -> a.put("maintenance/drawdown-sector-read-set.rq", "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o . FILTER(NOW() > ?o) }")), Examples.JOB, trig, 60_000).failure()
            .contains("reads the clock"));
        assertTrue(SurfaceStep.execute(SurfaceJob.job(a -> a.put("maintenance/drawdown-sector-fill-all.rq", "INSERT DATA {")), Examples.JOB, trig, 60_000).failure()
            .contains("did not parse once its source was bound"));
        assertTrue(SurfaceStep.execute(SurfaceJob.job(a -> a.put("maintenance/drawdown-sector-fill-all.rq", "LOAD <urn:x:nothing> INTO GRAPH $derived")), Examples.JOB, trig, 60_000).failure()
            .contains("Jena could not run the maintenance of the contract drawdown-sector"));
    }

    @Test
    void eachRowIsAttributedToTheContractWhoseFillWroteIt() throws Exception {
        Model job = SurfaceJob.job(a -> {
            a.put("maintenance/zeta-fill-all.rq", a.get("maintenance/drawdown-sector-fill-all.rq").replace("exec#drawdownSector", "exec#other"));
            a.put("maintenance/manifest.json", a.get("maintenance/manifest.json").replace("]", ",{\"key\": \"zeta\", \"contract\": \"urn:c:zeta\", \"kind\": \"promotion\", \"fill\": \"zeta-fill-all.rq\"}]"));
        });
        PersistenceStep.Result r = SurfaceStep.execute(job, Examples.JOB, sample("facility-surface-step-drawdown.trig"), 60_000);
        assertNull(r.failure(), r.failure());
        String first = part(r, "artefact", "drawdown-sector/rows-after.trig").text();
        String second = part(r, "artefact", "zeta/rows-after.trig").text();
        assertEquals(4, first.lines().filter(l -> l.contains("exec#drawdownSector")).count());
        assertEquals(0, first.lines().filter(l -> l.contains("exec#other")).count());
        assertEquals(4, second.lines().filter(l -> l.contains("exec#other")).count());
        assertEquals(0, second.lines().filter(l -> l.contains("exec#drawdownSector")).count());
    }

    // ---- S2-T4: the frames are bounded

    @Test
    void aResultOverTheFrameBoundIsOneFailedFrameThatSaysSo() throws Exception {
        // Seventy contracts keep two parts each, which is more frames than a run may send.
        Map<String, String> artefacts = SurfaceJob.artefacts();
        Map<String, String> many = new LinkedHashMap<>();
        many.put("maintenance/partition-clear.rq", artefacts.get("maintenance/partition-clear.rq"));
        JsonArray manifest = new JsonArray();
        for (int i = 0; i < 70; i++) {
            String key = String.format("c%02d", i);
            JsonObject entry = new JsonObject();
            entry.put("key", key);
            entry.put("contract", "https://example.org/lending#" + key);
            entry.put("kind", "promotion");
            entry.put("fill", key + "-fill-all.rq");
            manifest.add(entry);
            many.put("maintenance/" + key + "-fill-all.rq", artefacts.get("maintenance/drawdown-sector-fill-all.rq"));
        }
        many.put("maintenance/manifest.json", JSON.toString(manifest));
        PersistenceStep.Result r = SurfaceStep.execute(SurfaceJob.build(many), Examples.JOB, sample("facility-surface-step-drawdown.trig"), 60_000);
        assertNull(r.failure(), r.failure());
        assertEquals(142, r.parts().size());
        List<JsonObject> frames = RunFrames.ofStep(RUN, r);
        assertEquals(1, frames.size());
        assertEquals("failed", frames.get(0).get("status").getAsString().value());
        assertTrue(frames.get(0).get("message").getAsString().value().contains("too large"));
    }

    @Test
    void aPartOverTheLargestFrameIsCutIntoFramesThatJoinToTheText() throws Exception {
        // A world of 1,500 drawdowns gives rows of about 220 KB, which are cut at 48 KiB and join again.
        StringBuilder world = new StringBuilder("<urn:g:facilities> {\n    ex:acme-foods a ex:Borrower ; ex:borrowerSector ex:FoodProcessing .\n    ex:facility-1 a ex:Facility ; ex:borrower ex:acme-foods .\n");
        StringBuilder added = new StringBuilder();
        for (int i = 0; i < 1_500; i++) {
            added.append("    ex:drawdown-").append(i).append(" a ex:Drawdown ; ex:drawnUnder ex:facility-1 .\n");
        }
        String trig = PREFIXES + world + "}\n" + STEP_OK + "<urn:lattice:studio:step/added/urn%3Ag%3Afacilities> {\n" + added + "}\n";
        PersistenceStep.Result r = run(trig);
        assertNull(r.failure(), r.failure());
        String rows = part(r, "artefact", "drawdown-sector/rows-after.trig").text();
        assertTrue(rows.getBytes(java.nio.charset.StandardCharsets.UTF_8).length > RunFrames.MAX_TEXT_BYTES);
        List<JsonObject> frames = RunFrames.ofStep(RUN, r);
        assertEquals("succeeded", frames.get(frames.size() - 1).get("status").getAsString().value());
        StringBuilder joined = new StringBuilder();
        boolean inRows = false;
        for (JsonObject f : frames) {
            if (f.hasKey("part")) {
                JsonObject p = f.get("part").getAsObject();
                inRows = p.hasKey("path") && p.get("path").getAsString().value().equals("drawdown-sector/rows-after.trig");
                if (p.hasKey("path")) {
                    assertEquals("drawdown-sector", p.get("group").getAsString().value());
                }
            }
            if (f.hasKey("text")) {
                assertTrue(f.get("text").getAsString().value().getBytes(java.nio.charset.StandardCharsets.UTF_8).length <= RunFrames.MAX_TEXT_BYTES);
                if (inRows) {
                    joined.append(f.get("text").getAsString().value());
                }
            }
        }
        assertEquals(rows, joined.toString());
        assertEquals(new TreeSet<>(List.of("artefact", "delta", "outcome")), r.parts().stream().map(PersistenceStep.Part::role).collect(java.util.stream.Collectors.toCollection(TreeSet::new)));
    }
}
