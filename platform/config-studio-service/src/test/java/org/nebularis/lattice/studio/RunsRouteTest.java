// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicReference;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonArray;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.vocabulary.RDF;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.jobs.RunMessage;
import org.nebularis.lattice.studio.jobs.Topology;
import org.nebularis.lattice.studio.runs.RunRegistry;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;

/** {@code POST /api/workspaces/{ws}/runs}, with a recording bus that stands in for the broker (ADR-A154, the contract's Runs section). */
class RunsRouteTest {
    private static final String WS = "/api/workspaces/" + Fixture.id(1);
    private static final Instant T0 = RunRegistryTest.T0;

    @TempDir Path dir;
    final RunRegistryTest.TestClock clock = new RunRegistryTest.TestClock();
    final RunRegistryTest.TestTimers timers = new RunRegistryTest.TestTimers(clock);
    /** What each tab was sent, as principal, tab and the event's JSON. */
    final List<String[]> tabs = Collections.synchronizedList(new ArrayList<>());
    Fixture f;
    RunRegistry registry;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir), null, Set.of(), clock);
        registry = new RunRegistry(clock, timers, f.api::mayReadWorkspace);
        f.api.runs(registry, (principal, tab, json) -> tabs.add(new String[] {principal, tab, json}));
        f.api.events("ws://127.0.0.1:15675/ws", "the-broker-secret");
        assertEquals(201, f.createWorkspace("One").status());
    }

    /** A compile job of {@code target}, finished or not, and its IRI. */
    private String compileJob(String target, boolean finished) {
        ApiResponse submitted = f.post(WS + "/jobs", "kind=compile&target=" + target, Fixture.PREFIXES + "ex:a ex:p ex:b .");
        assertEquals(202, submitted.status());
        String job = Graphs.job(submitted.headers().get("Location").substring("/api/jobs/".length()));
        if (finished) {
            Model done = f.store.graph(job);
            Resource j = done.getResource(job);
            done.removeAll(j, Cst.status, null);
            j.addProperty(Cst.status, Cst.Succeeded);
            f.store.write(List.of(), Map.of(job, done));
        }
        return job;
    }

    private static String id(String jobIri) {
        return jobIri.substring(Graphs.JOB_PREFIX.length());
    }

    private ApiResponse post(String query, String media, String body) {
        return postAs(null, query, media, body.getBytes(StandardCharsets.UTF_8));
    }

    private ApiResponse postAs(String principal, String query, String media, byte[] body) {
        Map<String, String> headers = new HashMap<>(Map.of("content-type", media));
        if (principal != null) {
            headers.put("x-lattice-principal", principal);
        }
        return f.send("POST", WS + "/runs", query, headers, body);
    }

    private ApiResponse sample(String job, String extra) {
        return post("kind=sample&target=mapping&tab=t1&job=" + id(job) + extra, "application/xml", "<a/>");
    }

    private static String text(ApiResponse r) {
        return new String(r.body(), StandardCharsets.UTF_8);
    }

    @Test
    void aSampleRunIsAcceptedAtOnceAndDescribedAsACstRunAndPublishedToItsQueue() {
        String job = compileJob("mapping", true);
        ApiResponse r = post("kind=sample&target=mapping&tab=t1&job=" + id(job), "application/xml; charset=utf-8", "<a/>");
        assertEquals(202, r.status());
        assertEquals("text/turtle; charset=utf-8", r.headers().get("Content-Type"));
        assertFalse(r.headers().containsKey("Location"), "a run cannot be read again");
        String run = "urn:lattice:studio:run:" + Fixture.id(3);
        Model m = Fixture.model(r);
        Resource node = m.getResource(run);
        assertTrue(m.contains(node, RDF.type, Cst.Run));
        assertEquals(Cst.SampleRun, node.getPropertyResourceValue(Cst.kind));
        assertEquals(Cst.target("mapping"), node.getPropertyResourceValue(Cst.target));
        assertEquals(job, node.getPropertyResourceValue(Cst.compileJob).getURI());
        assertEquals("2026-11-16T10:02:00Z", node.getProperty(Cst.deadline).getLiteral().getLexicalForm());
        assertEquals("http://www.w3.org/2001/XMLSchema#dateTime", node.getProperty(Cst.deadline).getLiteral().getDatatypeURI());
        assertEquals(1, m.listSubjects().toList().size(), "only the run is described");

        assertEquals(1, f.bus.runs().size());
        RunMessage message = f.bus.runs().get(0);
        assertEquals(new RunMessage(Topology.RUNS_ROUTING_KEY, run, job, "sample", "mapping", "2026-11-16T10:02:00Z", "application/xml",
            120_000, "<a/>".getBytes(StandardCharsets.UTF_8)), message);
        assertEquals(1, registry.pending("developer", "t1"));
    }

    @Test
    void aSimulatorStepGoesToTheInteractiveQueueWithADeadlineOf15SecondsAndTakesTrig() {
        for (String target : List.of("persistence", "surface")) {
            String job = compileJob(target, true);
            ApiResponse r = post("kind=simulate&target=" + target + "&tab=t" + target.charAt(0) + "&job=" + id(job), "application/trig", "ex:a {}");
            assertEquals(202, r.status(), text(r));
            RunMessage m = f.bus.runs().get(f.bus.runs().size() - 1);
            assertEquals(Topology.RUNS_INTERACTIVE_ROUTING_KEY, m.routingKey());
            assertEquals("simulate", m.kind());
            assertEquals(target, m.target());
            assertEquals(15_000, m.expirationMillis());
            assertEquals("2026-11-16T10:00:15Z", m.deadline());
            assertEquals("application/trig", m.contentType());
            Resource node = Fixture.model(r).getResource(m.run());
            assertEquals(Cst.SimulationStep, node.getPropertyResourceValue(Cst.kind));
            assertEquals(Cst.target(target), node.getPropertyResourceValue(Cst.target));
        }
    }

    @Test
    void aGivenDeadlineSetsTheExpirationAndIsRefusedInThePastOrBeyondTheKindsMaximum() {
        String job = compileJob("mapping", true);
        assertEquals(202, sample(job, "&deadline=2026-11-16T10:00:30Z").status());
        assertEquals(30_000, f.bus.runs().get(0).expirationMillis());
        assertEquals("2026-11-16T10:00:30Z", f.bus.runs().get(0).deadline());
        assertEquals(202, sample(job, "&deadline=2026-11-16T11:00:30%2B01:00").status(), "an offset is read, and 10:00:30 UTC is in range");
        assertEquals(30_000, f.bus.runs().get(1).expirationMillis());
        assertEquals(202, sample(job, "&deadline=2026-11-16T10:02:00Z").status(), "the maximum itself");
        for (String bad : List.of("2026-11-16T10:00:00Z", "2026-11-16T09:59:59Z", "2026-11-16T10:02:00.001Z", "2026-11-16T10:00:30", "soon", "")) {
            assertEquals(400, sample(job, "&deadline=" + bad).status(), bad);
        }
        assertEquals(3, f.bus.runs().size());
        String sim = compileJob("surface", true);
        assertEquals(400, post("kind=simulate&target=surface&tab=t1&job=" + id(sim) + "&deadline=2026-11-16T10:00:16Z", "application/trig", "").status(),
            "the maximum of a step is 15 seconds");
    }

    @Test
    void theDeadlineDefaultsFromTheClockSoItMovesWithIt() {
        String job = compileJob("mapping", true);
        clock.advanceTo(Instant.parse("2026-11-16T12:00:00Z"));
        assertEquals(202, sample(job, "").status());
        assertEquals("2026-11-16T12:02:00Z", f.bus.runs().get(0).deadline());
    }

    @Test
    void aRequestThatIsNotAWellFormedPairTabOrDeadlineIs400AndNothingIsPublished() {
        String job = compileJob("mapping", true);
        String j = "&job=" + id(job);
        for (String query : List.of("", "tab=t1" + j, "kind=sample&tab=t1" + j, "kind=sample&target=surface&tab=t1" + j,
            "kind=simulate&target=mapping&tab=t1" + j, "kind=simulate&tab=t1" + j, "kind=other&target=mapping&tab=t1" + j,
            "kind=sample&target=mapping" + j, "kind=sample&target=mapping&tab=" + j, "kind=sample&target=mapping&tab=T1" + j,
            "kind=sample&target=mapping&tab=a-b" + j, "kind=sample&target=mapping&tab=" + "a".repeat(33) + j)) {
            assertEquals(400, post(query, "application/xml", "<a/>").status(), query);
        }
        assertTrue(f.bus.runs().isEmpty());
        assertEquals(0, registry.size());
        assertEquals(202, post("kind=sample&target=mapping&tab=" + "a".repeat(32) + j, "application/xml", "<a/>").status());
    }

    @Test
    void aWorkspaceOrJobTheWorkspaceDoesNotHoldIs404() {
        String job = compileJob("mapping", true);
        assertEquals(404, f.send("POST", "/api/workspaces/" + Fixture.id(9) + "/runs", "kind=sample&target=mapping&tab=t1&job=" + id(job),
            Map.of("content-type", "application/xml"), new byte[0]).status());
        assertEquals(404, post("kind=sample&target=mapping&tab=t1&job=" + Fixture.id(99), "application/xml", "").status());
        assertEquals(404, post("kind=sample&target=mapping&tab=t1&job=not-an-id", "application/xml", "").status());
        assertEquals(404, post("kind=sample&target=mapping&tab=t1", "application/xml", "").status());
        assertTrue(f.bus.runs().isEmpty());
    }

    @Test
    void aPrincipalWhoMayNotReadTheWorkspaceGets404AndNothingIsPublishedOrHeld() {
        String job = compileJob("mapping", true);
        assertEquals(200, f.send("POST", WS + "/access", "mode=locked", Map.of("x-lattice-principal", "developer"), new byte[0]).status());
        ApiResponse r = postAs("reviewer", "kind=sample&target=mapping&tab=t1&job=" + id(job), "application/xml", "<a/>".getBytes(StandardCharsets.UTF_8));
        assertEquals(404, r.status());
        assertTrue(f.bus.runs().isEmpty());
        assertEquals(0, registry.size());
        assertEquals(202, post("kind=sample&target=mapping&tab=t1&job=" + id(job), "application/xml", "<a/>").status(), "the owner may");
    }

    @Test
    void aJobThatIsNotAFinishedCompilationOfTheTargetsPartIs409() {
        String unfinished = compileJob("mapping", false);
        assertEquals(409, sample(unfinished, "").status());
        String surface = compileJob("surface", true);
        assertEquals(409, sample(surface, "").status(), "a compilation of another part");
        String mapping = compileJob("mapping", true);
        assertEquals(409, post("kind=simulate&target=surface&tab=t1&job=" + id(mapping), "application/trig", "").status());
        ApiResponse validation = f.post(WS + "/jobs", "kind=validate&target=surface", Fixture.PREFIXES + "ex:a ex:p ex:b .");
        assertEquals(409, post("kind=simulate&target=surface&tab=t1&job=" + validation.headers().get("Location").substring("/api/jobs/".length()),
            "application/trig", "").status(), "a validation");
        assertTrue(f.bus.runs().isEmpty());
    }

    @Test
    void aMediaTypeTheKindDoesNotTakeIs415AndABodyOver5MiBIs413() {
        String job = compileJob("mapping", true);
        String surface = compileJob("surface", true);
        for (String media : List.of("application/trig", "text/plain", "")) {
            assertEquals(415, post("kind=sample&target=mapping&tab=t1&job=" + id(job), media, "").status(), media);
        }
        assertEquals(415, post("kind=simulate&target=surface&tab=t1&job=" + id(surface), "text/turtle", "").status());
        for (String media : List.of("text/turtle", "application/n-triples", "application/xml", "text/xml", "application/json")) {
            assertEquals(202, post("kind=sample&target=mapping&tab=" + media.length() + "x&job=" + id(job), media, "").status(), media);
        }
        ApiResponse big = postAs(null, "kind=sample&target=mapping&tab=t1&job=" + id(job), "application/xml", new byte[5 * 1024 * 1024 + 1]);
        assertEquals(413, big.status());
        assertEquals(202, postAs(null, "kind=sample&target=mapping&tab=t2&job=" + id(job), "application/xml", new byte[5 * 1024 * 1024]).status());
    }

    @Test
    void aFifthPendingRunOfATabIs429WithRetryAfterAndNothingIsPublishedForIt() {
        String job = compileJob("mapping", true);
        for (int i = 1; i <= 4; i++) {
            clock.advanceTo(T0.plusSeconds(i));
            assertEquals(202, sample(job, "").status());
        }
        assertEquals(4, f.bus.runs().size());
        clock.advanceTo(T0.plusSeconds(10));
        ApiResponse r = sample(job, "");
        assertEquals(429, r.status());
        assertEquals("111", r.headers().get("Retry-After"), "the earliest deadline is 10:02:01, 111 seconds after 10:00:10");
        assertEquals(4, f.bus.runs().size());
        assertEquals(4, registry.pending("developer", "t1"));
        assertEquals(202, post("kind=sample&target=mapping&tab=t2&job=" + id(job), "application/xml", "<a/>").status(), "another tab");
    }

    @Test
    void aBusThatCannotPublishMakesTheRoute503AndLeavesNothingPending() {
        String job = compileJob("mapping", true);
        f.bus.onRun(m -> {
            throw new IOException("the broker did not confirm");
        });
        for (int i = 0; i < 6; i++) {
            assertEquals(503, sample(job, "").status());
        }
        assertEquals(0, registry.size(), "no run is left pending, and so the tab's limit is not used up");
        assertEquals(0, timers.scheduled());
        f.bus.onRun(m -> { });
        assertEquals(202, sample(job, "").status());
    }

    @Test
    void aServiceWithNoBrokerAnswersRunsWith503() throws IOException {
        Fixture bare = new Fixture(Fixture.assetsDir(dir.resolve("bare")), null, Set.of(), clock);
        bare.createWorkspace("One");
        bare.post(WS + "/jobs", "kind=compile&target=mapping", Fixture.PREFIXES + "ex:a ex:p ex:b .");
        ApiResponse r = bare.send("POST", WS + "/runs", "kind=sample&target=mapping&tab=t1&job=" + Fixture.id(2), Map.of("content-type", "application/xml"), new byte[0]);
        // The job is not finished, so the checks of the job come first. A finished one reaches the 503.
        assertEquals(409, r.status());
        Model done = bare.store.graph(Graphs.job(Fixture.id(2)));
        done.removeAll(done.getResource(Graphs.job(Fixture.id(2))), Cst.status, null);
        done.getResource(Graphs.job(Fixture.id(2))).addProperty(Cst.status, Cst.Succeeded);
        bare.store.write(List.of(), Map.of(Graphs.job(Fixture.id(2)), done));
        assertEquals(503, bare.send("POST", WS + "/runs", "kind=sample&target=mapping&tab=t1&job=" + Fixture.id(2), Map.of("content-type", "application/xml"), new byte[0]).status());
        assertTrue(bare.bus.runs().isEmpty());
    }

    @Test
    void aGetOrAnotherMethodOnTheRouteIs405() {
        assertEquals(405, f.get(WS + "/runs").status());
        assertEquals("POST", f.get(WS + "/runs").headers().get("Allow"));
    }

    @Test
    void theRunIsRecordedBeforeItIsPublishedSoAFrameFromInsideThePublishCallIsDelivered() {
        String job = compileJob("mapping", true);
        // The broker's worker answers before the publish call returns.
        f.bus.onRun(m -> {
            registry.frame("{\"run\":\"" + m.run() + "\",\"seq\":0,\"last\":false,\"text\":\"early\"}");
            registry.frame("{\"run\":\"" + m.run() + "\",\"seq\":1,\"last\":true,\"status\":\"succeeded\"}");
        });
        assertEquals(202, sample(job, "").status());
        assertEquals(2, tabs.size(), "both frames reached the tab");
        assertEquals("developer", tabs.get(0)[0]);
        assertEquals("t1", tabs.get(0)[1]);
        JsonObject first = JSON.parse(tabs.get(0)[2]);
        assertEquals("early", first.get("data").getAsObject().get("text").getAsString().value());
        assertEquals(0, registry.size(), "the last frame ended the run before the answer");
    }

    @Test
    void framesReachTheSubmittingTabAsCloudEventsOnceTheRunIsAccepted() {
        String job = compileJob("mapping", true);
        assertEquals(202, sample(job, "").status());
        String run = f.bus.runs().get(0).run();
        registry.frame("{\"run\":\"" + run + "\",\"seq\":0,\"last\":false,\"text\":\"a\"}");
        registry.frame("{\"run\":\"" + run + "\",\"seq\":1,\"last\":true,\"status\":\"succeeded\",\"conforms\":true}");
        assertEquals(2, tabs.size());
        JsonObject event = JSON.parse(tabs.get(1)[2]);
        assertEquals(run, event.get("subject").getAsString().value());
        assertEquals("org.nebularis.lattice.studio.run.frame", event.get("type").getAsString().value());
        assertTrue(event.get("data").getAsObject().get("conforms").getAsBoolean().value());
        assertEquals(0, registry.size());
    }

    @Test
    void waitTrueAnswersTheFramesInSequenceOrderAs200Json() {
        String job = compileJob("mapping", true);
        f.bus.onRun(m -> {
            registry.frame("{\"run\":\"" + m.run() + "\",\"seq\":1,\"last\":false,\"text\":\"b\"}");
            registry.frame("{\"run\":\"" + m.run() + "\",\"seq\":0,\"last\":false,\"text\":\"a\",\"part\":{\"index\":0,\"role\":\"report\",\"mediaType\":\"text/turtle\"}}");
            registry.frame("{\"run\":\"" + m.run() + "\",\"seq\":2,\"last\":true,\"status\":\"succeeded\",\"conforms\":false}");
        });
        ApiResponse r = sample(job, "&wait=true");
        assertEquals(200, r.status());
        assertEquals("application/json", r.headers().get("Content-Type"));
        JsonArray frames = JSON.parseAny(text(r)).getAsArray();
        assertEquals(3, frames.size());
        for (int i = 0; i < 3; i++) {
            assertEquals(i, frames.get(i).getAsObject().get("seq").getAsNumber().value().intValue());
        }
        assertEquals("a", frames.get(0).getAsObject().get("text").getAsString().value());
        assertTrue(tabs.isEmpty(), "a waiting request has its frames on the request, not on a tab");
        assertEquals(0, registry.size());
    }

    @Test
    void waitTrueAnswersAFailedLastFrameAs200Too() {
        String job = compileJob("mapping", true);
        f.bus.onRun(m -> registry.frame("{\"run\":\"" + m.run() + "\",\"seq\":0,\"last\":true,\"status\":\"failed\",\"message\":\"cannot read the input\"}"));
        ApiResponse r = sample(job, "&wait=true");
        assertEquals(200, r.status());
        assertEquals("failed", JSON.parseAny(text(r)).getAsArray().get(0).getAsObject().get("status").getAsString().value());
    }

    @Test
    void waitTrueAnswers504WhenTheDeadlinePassesWithNoLastFrameAndForgetsTheRun() throws Exception {
        String job = compileJob("mapping", true);
        AtomicReference<ApiResponse> answer = new AtomicReference<>();
        Thread request = new Thread(() -> answer.set(sample(job, "&wait=true")));
        request.start();
        long give = System.nanoTime() + 10_000_000_000L;
        while (f.bus.runs().isEmpty() && System.nanoTime() < give) {
            Thread.onSpinWait();
        }
        assertEquals(2, registry.size(), "the run is pending while the request waits");
        assertEquals(1, f.bus.runs().size());
        // One frame came, and then nothing, so the clock passes the deadline.
        registry.frame("{\"run\":\"" + f.bus.runs().get(0).run() + "\",\"seq\":0,\"last\":false,\"text\":\"a\"}");
        timers.advance(java.time.Duration.ofSeconds(120));
        request.join(10_000);
        assertFalse(request.isAlive());
        assertNotNull(answer.get());
        assertEquals(504, answer.get().status());
        assertEquals(0, registry.size());
        assertEquals(0, timers.scheduled());
    }

    @Test
    void theStatusWarnsOfARunQueueNoWorkerConsumesLikeItDoesOfAJobQueue() throws IOException {
        Map<String, Integer> counts = new HashMap<>();
        Fixture with = new Fixture(Fixture.assetsDir(dir.resolve("status")), new org.nebularis.lattice.studio.jobs.JobBus() {
            @Override
            public void publish(String jobIri) {
            }

            @Override
            public int consumers(String queue) {
                return counts.getOrDefault(queue, -1);
            }
        });
        counts.put(Topology.JOBS_QUEUE, 1);
        counts.put(Topology.JOBS_LONG_QUEUE, 1);
        counts.put(Topology.RUNS_QUEUE, 1);
        counts.put(Topology.RUNS_INTERACTIVE_QUEUE, 0);
        String status = text(with.get("/api/status"));
        assertTrue(status.contains("No worker consumes lattice.studio.runs.interactive"), status);
        assertFalse(status.contains("No worker consumes lattice.studio.runs,"), status);
        assertFalse(status.contains("consumes lattice.studio.jobs"), status);
    }

    /** A service with a broker and no events for browsers, so no tab to forward to. */
    private Fixture withoutEvents(String name) throws IOException {
        Fixture g = new Fixture(Fixture.assetsDir(dir.resolve(name)), null, Set.of(), clock);
        RunRegistry own = new RunRegistry(clock, timers, g.api::mayReadWorkspace);
        g.api.runs(own, null);
        owned.put(g, own);
        assertEquals(201, g.createWorkspace("One").status());
        return g;
    }

    private String finishedCompile(Fixture g) {
        ApiResponse submitted = g.post(WS + "/jobs", "kind=compile&target=mapping", Fixture.PREFIXES + "ex:a ex:p ex:b .");
        String job = Graphs.job(submitted.headers().get("Location").substring("/api/jobs/".length()));
        Model done = g.store.graph(job);
        done.removeAll(done.getResource(job), Cst.status, null);
        done.getResource(job).addProperty(Cst.status, Cst.Succeeded);
        g.store.write(List.of(), Map.of(job, done));
        return job;
    }

    private ApiResponse sampleOn(Fixture g, String job, String extra) {
        return g.send("POST", WS + "/runs", "kind=sample&target=mapping&tab=t1&job=" + id(job) + extra,
            Map.of("content-type", "application/xml"), "<a/>".getBytes(StandardCharsets.UTF_8));
    }

    @Test
    void whereNoEventsAreServedARunWithoutWaitIs400AndNothingIsRecordedOrPublished() throws IOException {
        Fixture g = withoutEvents("noevents-a");
        String job = finishedCompile(g);
        ApiResponse r = sampleOn(g, job, "");
        assertEquals(400, r.status());
        assertTrue(text(r).contains("wait=true"), text(r));
        assertTrue(g.bus.runs().isEmpty());
        assertEquals(0, timers.scheduled());
    }

    @Test
    void whereNoEventsAreServedARunWithWaitTrueAnswers200WithItsFrames() throws IOException {
        Fixture g = withoutEvents("noevents-b");
        String job = finishedCompile(g);
        g.bus.onRun(m -> {
            ownRegistry(g).frame("{\"run\":\"" + m.run() + "\",\"seq\":0,\"last\":true,\"status\":\"succeeded\"}");
        });
        ApiResponse r = sampleOn(g, job, "&wait=true");
        assertEquals(200, r.status());
        assertEquals(1, JSON.parseAny(text(r)).getAsArray().size());
    }

    @Test
    void whereNoEventsAreServedARunWithWaitTrueAnswers504AtItsDeadline() throws Exception {
        Fixture g = withoutEvents("noevents-c");
        String job = finishedCompile(g);
        AtomicReference<ApiResponse> answer = new AtomicReference<>();
        Thread request = new Thread(() -> answer.set(sampleOn(g, job, "&wait=true")));
        request.start();
        long give = System.nanoTime() + 10_000_000_000L;
        while (g.bus.runs().isEmpty() && System.nanoTime() < give) {
            Thread.onSpinWait();
        }
        assertEquals(1, g.bus.runs().size());
        timers.advance(java.time.Duration.ofSeconds(120));
        request.join(10_000);
        assertFalse(request.isAlive());
        assertEquals(504, answer.get().status());
        assertEquals(0, ownRegistry(g).size());
    }

    private final Map<Fixture, RunRegistry> owned = new java.util.IdentityHashMap<>();

    private RunRegistry ownRegistry(Fixture g) {
        return owned.get(g);
    }
}
