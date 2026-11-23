// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.BooleanSupplier;
import java.util.function.Function;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.store.Cst;

/** The run worker's consumer, with the publisher and the channel faked in memory and a clock the test sets. */
class RunWorkerTest {
    private static final Instant NOW = Instant.parse("2026-11-17T10:00:00Z");
    private static final Clock CLOCK = Clock.fixed(NOW, ZoneOffset.UTC);
    private static final SchemaCheck SCHEMA = schema();
    private static final String RUN_2 = "urn:lattice:studio:run:aaaaaaaa-5a47-4d0e-9b1a-6c7d8e9f0a1b";

    private static SchemaCheck schema() {
        try {
            return new SchemaCheck();
        } catch (IOException e) {
            throw new IllegalStateException(e);
        }
    }

    /** Publishes into memory. Everything it is given must hold against the schema, which is checked after each test. */
    private static final class FakeSink implements FrameSink {
        final List<String> log = Collections.synchronizedList(new ArrayList<>());
        final Map<String, List<String>> frames = Collections.synchronizedMap(new LinkedHashMap<>());
        final List<String> problems = Collections.synchronizedList(new ArrayList<>());
        volatile long delayMillis;

        @Override
        public void publish(String run, List<String> published) {
            if (delayMillis > 0) {
                try {
                    Thread.sleep(delayMillis);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
            List<String> all = new ArrayList<>(frames.getOrDefault(run, List.of()));
            all.addAll(published);
            frames.put(run, all);
            problems.addAll(SCHEMA.problems(published));
            log.add("publish:" + run);
        }

        List<JsonObject> of(String run) {
            return frames.getOrDefault(run, List.of()).stream().map(JSON::<JsonObject>parse).toList();
        }
    }

    /** Settles into the same log as the sink, so the test can read the order the two happened in. */
    private static final class FakeAcks implements QueueWorker.Acks {
        final FakeSink sink;

        FakeAcks(FakeSink sink) {
            this.sink = sink;
        }

        @Override
        public void ack(long tag) {
            sink.log.add("ack:" + tag);
        }

        @Override
        public void reject(long tag, boolean requeue) {
            sink.log.add((requeue ? "requeue:" : "reject:") + tag);
        }
    }

    private final FakeSink sink = new FakeSink();
    private final AtomicInteger jobReads = new AtomicInteger();
    private final List<AutoCloseable> closeables = new ArrayList<>();

    @BeforeEach
    void silence() {
        sink.log.clear();
    }

    @AfterEach
    void closeAndCheckEveryFrame() throws Exception {
        for (AutoCloseable c : closeables) {
            c.close();
        }
        assertEquals(List.of(), sink.problems, "every frame published holds against run-frame.schema.json");
    }

    private Function<String, Model> jobs() {
        return job -> {
            jobReads.incrementAndGet();
            try {
                return Examples.compileJob(false);
            } catch (IOException e) {
                throw new IllegalStateException(e);
            }
        };
    }

    private QueueWorker queue(String kind, int threads, Function<String, Model> jobs) {
        RunWorker worker = new RunWorker(kind, jobs, sink, CLOCK);
        QueueWorker queue = new QueueWorker("test-" + kind, threads, worker, new FakeAcks(sink));
        closeables.add(worker);
        closeables.add(queue);
        return queue;
    }

    private static Map<String, Object> headers(String run, String kind, String target, Instant deadline) {
        Map<String, Object> h = new HashMap<>();
        h.put("run", run);
        h.put("job", Examples.JOB);
        h.put("kind", kind);
        h.put("target", target);
        h.put("deadline", deadline.toString());
        return h;
    }

    private static Message message(long tag, boolean redelivered, Map<String, Object> headers, String contentType, String body) {
        return new Message(tag, redelivered, headers, contentType, null, null, body.getBytes(StandardCharsets.UTF_8));
    }

    private static Message sample(long tag, String run, String contentType, String body) {
        return message(tag, false, headers(run, "sample", "mapping", NOW.plusSeconds(120)), contentType, body);
    }

    private static void await(BooleanSupplier done) throws InterruptedException {
        long end = System.nanoTime() + TimeUnit.SECONDS.toNanos(10);
        while (!done.getAsBoolean()) {
            if (System.nanoTime() > end) {
                throw new AssertionError("timed out waiting");
            }
            Thread.sleep(5);
        }
    }

    private void awaitSettled(long tag) throws InterruptedException {
        await(() -> sink.log.stream().anyMatch(e -> e.endsWith(":" + tag) && !e.startsWith("publish")));
    }

    private static void assertOneFailedFrame(List<JsonObject> frames, String contains) {
        assertEquals(1, frames.size());
        JsonObject f = frames.get(0);
        assertEquals(0, f.get("seq").getAsNumber().value().intValue());
        assertTrue(f.get("last").getAsBoolean().value());
        assertEquals("failed", f.get("status").getAsString().value());
        assertTrue(f.get("message").getAsString().value().contains(contains), f.get("message").toString());
    }

    @Test
    void aSampleRunPublishesItsFramesAndIsAcknowledgedAfterThem() throws Exception {
        sink.delayMillis = 100;
        queue("sample", 2, jobs()).deliver(sample(1, Examples.RUN, "application/xml", Examples.xmlSample()));
        awaitSettled(1);
        assertEquals(List.of("publish:" + Examples.RUN, "ack:1"), sink.log, "acknowledged after publishing, not before");
        List<JsonObject> frames = sink.of(Examples.RUN);
        assertEquals("succeeded", frames.get(frames.size() - 1).get("status").getAsString().value());
        assertEquals("report", frames.get(0).get("part").getAsObject().get("role").getAsString().value());
        assertEquals(1, jobReads.get());
    }

    @Test
    void aRedeliveredRunIsNotRunButFailedAndAcknowledged() throws Exception {
        queue("sample", 2, jobs()).deliver(message(2, true, headers(Examples.RUN, "sample", "mapping", NOW.plusSeconds(60)),
            "application/xml", Examples.xmlSample()));
        awaitSettled(2);
        assertEquals(List.of("publish:" + Examples.RUN, "ack:2"), sink.log);
        assertOneFailedFrame(sink.of(Examples.RUN), "worker stopped");
        assertTrue(sink.of(Examples.RUN).get(0).get("message").getAsString().value().contains("run it again"));
        assertEquals(0, jobReads.get(), "a redelivered run is never run");
    }

    @Test
    void anExpiredRunIsAcknowledgedAndDroppedWithoutAFrame() throws Exception {
        queue("sample", 2, jobs()).deliver(message(3, false, headers(Examples.RUN, "sample", "mapping", NOW.minusSeconds(1)),
            "application/xml", Examples.xmlSample()));
        awaitSettled(3);
        assertEquals(List.of("ack:3"), sink.log);
        assertEquals(0, jobReads.get());
        queue("sample", 2, jobs()).deliver(message(4, false, headers(Examples.RUN, "sample", "mapping", NOW), "application/xml", "<a/>"));
        awaitSettled(4);
        assertEquals(List.of("ack:3", "ack:4"), sink.log, "a deadline that is now has passed");
    }

    @Test
    void aMessageThatFailsItsChecksIsRejectedWithoutRequeueAndNothingIsRun() throws Exception {
        QueueWorker q = queue("sample", 2, jobs());
        long tag = 10;
        List<Message> bad = new ArrayList<>();
        for (String header : new String[] {"run", "job", "kind", "target", "deadline"}) {
            Map<String, Object> h = headers(Examples.RUN, "sample", "mapping", NOW.plusSeconds(60));
            h.remove(header);
            bad.add(message(tag++, false, h, "application/xml", "<a/>"));
        }
        Map<String, Object> h;
        h = headers("urn:lattice:studio:run:NOT-A-UUID", "sample", "mapping", NOW.plusSeconds(60));
        bad.add(message(tag++, false, h, "application/xml", "<a/>"));
        h = headers(Examples.RUN, "sample", "mapping", NOW.plusSeconds(60));
        h.put("job", "urn:lattice:studio:job:not-an-id");
        bad.add(message(tag++, false, h, "application/xml", "<a/>"));
        bad.add(message(tag++, false, headers(Examples.RUN, "sample", "persistence", NOW.plusSeconds(60)), "application/xml", "<a/>"));
        bad.add(message(tag++, false, headers(Examples.RUN, "simulate", "mapping", NOW.plusSeconds(60)), "application/xml", "<a/>"));
        bad.add(message(tag++, false, headers(Examples.RUN, "simulate", "surface", NOW.plusSeconds(60)), "application/trig", ""));
        h = headers(Examples.RUN, "sample", "mapping", NOW.plusSeconds(60));
        h.put("deadline", "2026-11-17T10:02:00");
        bad.add(message(tag++, false, h, "application/xml", "<a/>"));
        h = headers(Examples.RUN, "sample", "mapping", NOW.plusSeconds(60));
        h.put("deadline", "soon");
        bad.add(message(tag++, false, h, "application/xml", "<a/>"));
        for (Message m : bad) {
            q.deliver(m);
        }
        for (Message m : bad) {
            awaitSettled(m.tag());
        }
        assertEquals(bad.size(), sink.log.stream().filter(e -> e.startsWith("reject:")).count(), sink.log.toString());
        assertEquals(bad.size(), sink.log.size(), "nothing was published or acknowledged: " + sink.log);
        assertEquals(0, jobReads.get());
    }

    @Test
    void aRunPastItsDeadlineIsStoppedNothingMoreIsPublishedAndItIsAcknowledged() throws Exception {
        CountDownLatch inside = new CountDownLatch(1);
        AtomicBoolean interrupted = new AtomicBoolean();
        Function<String, Model> hang = job -> {
            inside.countDown();
            try {
                new CountDownLatch(1).await();
            } catch (InterruptedException e) {
                interrupted.set(true);
            }
            return ModelFactory.createDefaultModel();
        };
        // The clock is fixed, so the timeout the worker takes from it is the 300 milliseconds between now and the deadline.
        queue("sample", 2, hang).deliver(message(5, false, headers(Examples.RUN, "sample", "mapping", NOW.plusMillis(300)),
            "application/xml", Examples.xmlSample()));
        assertTrue(inside.await(5, TimeUnit.SECONDS));
        awaitSettled(5);
        assertEquals(List.of("ack:5"), sink.log, "stopped, nothing published, acknowledged");
        await(interrupted::get);
        assertTrue(sink.frames.isEmpty());
    }

    @Test
    void anRdfSampleThatReachedTheWrongWorkerAndASurfaceStepOverAJobOfAnotherPartEachGiveTheirOneFailedFrame() throws Exception {
        QueueWorker samples = queue("sample", 2, jobs());
        samples.deliver(sample(6, Examples.RUN, "text/turtle", "<urn:a> <urn:b> <urn:c> ."));
        samples.deliver(sample(7, RUN_2, "application/n-triples; charset=utf-8", "<urn:a> <urn:b> <urn:c> ."));
        QueueWorker steps = queue("simulate", 2, jobs());
        String run3 = "urn:lattice:studio:run:bbbbbbbb-5a47-4d0e-9b1a-6c7d8e9f0a1b";
        steps.deliver(message(8, false, headers(run3, "simulate", "surface", NOW.plusSeconds(15)), "application/trig", ""));
        for (long t = 6; t <= 8; t++) {
            awaitSettled(t);
        }
        assertOneFailedFrame(sink.of(Examples.RUN), "wrong worker");
        assertOneFailedFrame(sink.of(RUN_2), "wrong worker");
        assertOneFailedFrame(sink.of(run3), "not a finished compilation of the surface part");
        assertEquals(1, jobReads.get(), "the sample runs are not run, and the step reads its job and finds it is of the mapping part");
        assertEquals(3, sink.log.stream().filter(e -> e.startsWith("ack:")).count());
    }

    @Test
    void aSurfaceStepPublishesTheRowsTheChangeAndTheContractsItTouchedAndIsAcknowledgedAfterThem() throws Exception {
        QueueWorker steps = queue("simulate", 2, job -> {
            jobReads.incrementAndGet();
            try {
                return SurfaceJob.job();
            } catch (IOException e) {
                throw new IllegalStateException(e);
            }
        });
        String trig = Files.readString(FacilityJob.SAMPLES.resolve("facility-surface-step-sector.trig"));
        steps.deliver(message(60, false, headers(Examples.RUN, "simulate", "surface", NOW.plusSeconds(15)), "application/trig", trig));
        awaitSettled(60);
        assertEquals(List.of("publish:" + Examples.RUN, "ack:60"), sink.log);
        List<JsonObject> frames = sink.of(Examples.RUN);
        assertEquals("succeeded", frames.get(frames.size() - 1).get("status").getAsString().value());
        List<String> roles = frames.stream().filter(f -> f.hasKey("part")).map(f -> f.get("part").getAsObject().get("role").getAsString().value()).toList();
        assertEquals(List.of("artefact", "artefact", "delta", "outcome"), roles);
        JsonObject first = frames.get(0).get("part").getAsObject();
        assertEquals("drawdown-sector/rows-before.trig", first.get("path").getAsString().value());
        assertEquals("application/trig", first.get("mediaType").getAsString().value());
        String outcome = frames.get(frames.size() - 2).get("text").getAsString().value();
        assertTrue(outcome.contains("Apache Jena ARQ"), outcome);
        assertTrue(outcome.contains("\"readSetTouched\" : true"), outcome);
        assertEquals(1, jobReads.get());
    }

    @Test
    void aRedeliveredSurfaceStepIsNotRunButFailedAndAcknowledged() throws Exception {
        String trig = Files.readString(FacilityJob.SAMPLES.resolve("facility-surface-step-sector.trig"));
        queue("simulate", 2, jobs()).deliver(message(61, true, headers(Examples.RUN, "simulate", "surface", NOW.plusSeconds(15)), "application/trig", trig));
        awaitSettled(61);
        assertEquals(List.of("publish:" + Examples.RUN, "ack:61"), sink.log);
        assertOneFailedFrame(sink.of(Examples.RUN), "worker stopped");
        assertEquals(0, jobReads.get(), "a redelivered step is never run");
    }

    private static Message step(long tag, String run, String trig) {
        return message(tag, false, headers(run, "simulate", "persistence", NOW.plusSeconds(15)), "application/trig", trig);
    }

    private Function<String, Model> facilityJobs() {
        return job -> {
            jobReads.incrementAndGet();
            try {
                return FacilityJob.job();
            } catch (IOException e) {
                throw new IllegalStateException(e);
            }
        };
    }

    private static List<String> roles(List<JsonObject> frames) {
        return frames.stream().filter(f -> f.hasKey("part")).map(f -> f.get("part").getAsObject().get("role").getAsString().value()).toList();
    }

    @Test
    void aPersistenceStepPublishesItsFourPartsAsFramesAndIsAcknowledgedAfterThem() throws Exception {
        String create = Files.readString(FacilityJob.SAMPLES.resolve("facility-step-create.trig"));
        queue("simulate", 2, facilityJobs()).deliver(step(60, Examples.RUN, create));
        awaitSettled(60);
        assertEquals(List.of("publish:" + Examples.RUN, "ack:60"), sink.log);
        List<JsonObject> frames = sink.of(Examples.RUN);
        assertEquals(List.of("check", "request", "delta", "outcome"), roles(frames));
        assertEquals("succeeded", frames.get(frames.size() - 1).get("status").getAsString().value());
        for (int k = 0; k < frames.size(); k++) {
            assertEquals(k, frames.get(k).get("seq").getAsNumber().value().intValue());
        }
        String outcome = frames.stream().filter(f -> f.hasKey("text")).map(f -> f.get("text").getAsString().value()).reduce("", String::concat);
        assertTrue(outcome.contains("\"outcome\" : \"applied\""), "the last part is the outcome");
        assertEquals(1, jobReads.get());
        // The frames are those of the same step run twice, with the run IRI the only difference.
        queue("simulate", 2, facilityJobs()).deliver(step(61, RUN_2, create));
        awaitSettled(61);
        assertEquals(sink.frames.get(Examples.RUN), sink.frames.get(RUN_2).stream().map(f -> f.replace(RUN_2, Examples.RUN)).toList());
    }

    @Test
    void aStepThatCannotBeRunIsOneFailedFrameAndAStepSentWithAnotherMediaTypeOrOver5MiBIsNotStarted() throws Exception {
        QueueWorker q = queue("simulate", 2, facilityJobs());
        q.deliver(step(62, Examples.RUN, ""));
        q.deliver(message(63, false, headers(RUN_2, "simulate", "persistence", NOW.plusSeconds(15)), "text/turtle", "<urn:a> <urn:b> <urn:c> ."));
        String run3 = "urn:lattice:studio:run:bbbbbbbb-5a47-4d0e-9b1a-6c7d8e9f0a1b";
        q.deliver(step(64, run3, "# " + "x".repeat(RunWorker.MAX_INPUT_BYTES)));
        String run4 = "urn:lattice:studio:run:cccccccc-5a47-4d0e-9b1a-6c7d8e9f0a1b";
        q.deliver(step(65, run4, "GRAPH <urn:g> { oops"));
        for (long t = 62; t <= 65; t++) {
            awaitSettled(t);
        }
        assertOneFailedFrame(sink.of(Examples.RUN), "The step is empty");
        assertOneFailedFrame(sink.of(RUN_2), "application/trig");
        assertOneFailedFrame(sink.of(run3), "The step is over 5 MiB");
        assertOneFailedFrame(sink.of(run4), "not valid TriG");
    }

    @Test
    void aRedeliveredStepIsFailedAndNotRunAndAStepWhoseJobIsNotAPersistenceCompilationIsFailed() throws Exception {
        queue("simulate", 2, facilityJobs()).deliver(message(66, true, headers(Examples.RUN, "simulate", "persistence", NOW.plusSeconds(15)), "application/trig",
            Files.readString(FacilityJob.SAMPLES.resolve("facility-step-create.trig"))));
        awaitSettled(66);
        assertOneFailedFrame(sink.of(Examples.RUN), "worker stopped");
        assertEquals(0, jobReads.get());
        queue("simulate", 2, jobs()).deliver(step(67, RUN_2, Files.readString(FacilityJob.SAMPLES.resolve("facility-step-create.trig"))));
        awaitSettled(67);
        assertOneFailedFrame(sink.of(RUN_2), "not a finished compilation of the persistence part");
    }

    @Test
    void aSlowStepNeverHoldsAFastOneWhileAThreadIsFreeAndOnlyDelaysItWhenEveryThreadIsHeld() throws Exception {
        CountDownLatch release = new CountDownLatch(1);
        CountDownLatch slowIsIn = new CountDownLatch(1);
        AtomicInteger calls = new AtomicInteger();
        Function<String, Model> firstIsSlow = job -> {
            if (calls.getAndIncrement() == 0) {
                slowIsIn.countDown();
                try {
                    release.await();
                } catch (InterruptedException e) {
                    throw new IllegalStateException(e);
                }
            }
            try {
                return FacilityJob.job();
            } catch (IOException e) {
                throw new IllegalStateException(e);
            }
        };
        String create = Files.readString(FacilityJob.SAMPLES.resolve("facility-step-create.trig"));
        // Two threads on the queue, as the default is: the second step is answered while the first is held.
        QueueWorker two = queue("simulate", 2, firstIsSlow);
        two.deliver(step(70, Examples.RUN, create));
        assertTrue(slowIsIn.await(5, TimeUnit.SECONDS));
        two.deliver(step(71, RUN_2, create));
        awaitSettled(71);
        assertFalse(sink.log.contains("ack:70"), "the slow step is still held");
        release.countDown();
        awaitSettled(70);
        assertEquals(sink.frames.get(Examples.RUN), sink.frames.get(RUN_2).stream().map(f -> f.replace(RUN_2, Examples.RUN)).toList());

        // One thread: the second step waits behind the first, since nothing is shared and nothing runs beside it, and is answered once it ends.
        CountDownLatch release1 = new CountDownLatch(1);
        CountDownLatch slowIsIn1 = new CountDownLatch(1);
        AtomicInteger calls1 = new AtomicInteger();
        Function<String, Model> again = job -> {
            if (calls1.getAndIncrement() == 0) {
                slowIsIn1.countDown();
                try {
                    release1.await();
                } catch (InterruptedException e) {
                    throw new IllegalStateException(e);
                }
            }
            try {
                return FacilityJob.job();
            } catch (IOException e) {
                throw new IllegalStateException(e);
            }
        };
        String run3 = "urn:lattice:studio:run:bbbbbbbb-5a47-4d0e-9b1a-6c7d8e9f0a1b";
        String run4 = "urn:lattice:studio:run:cccccccc-5a47-4d0e-9b1a-6c7d8e9f0a1b";
        QueueWorker one = queue("simulate", 1, again);
        one.deliver(step(72, run3, create));
        assertTrue(slowIsIn1.await(5, TimeUnit.SECONDS));
        one.deliver(step(73, run4, create));
        Thread.sleep(300);
        assertFalse(sink.log.contains("ack:73"), "the one thread is held by the slow step");
        release1.countDown();
        awaitSettled(72);
        awaitSettled(73);
        assertTrue(sink.log.indexOf("ack:72") < sink.log.indexOf("ack:73"));
    }

    @Test
    void aRunThatCannotStartIsOneFailedFrameForEachReason() throws Exception {
        QueueWorker q = queue("sample", 2, job -> {
            throw new IllegalStateException("the store is down");
        });
        q.deliver(sample(20, Examples.RUN, "application/xml", Examples.xmlSample()));
        awaitSettled(20);
        assertOneFailedFrame(sink.of(Examples.RUN), "could not be read");

        Model notFinished = ModelFactory.createDefaultModel();
        notFinished.createResource(Examples.JOB).addProperty(Cst.kind, Cst.Compile).addProperty(Cst.target, Cst.target("mapping"))
            .addProperty(Cst.status, Cst.Failed);
        queue("sample", 2, job -> notFinished).deliver(sample(21, RUN_2, "application/xml", Examples.xmlSample()));
        awaitSettled(21);
        assertOneFailedFrame(sink.of(RUN_2), "not a finished compilation of the mapping part");

        String run3 = "urn:lattice:studio:run:bbbbbbbb-5a47-4d0e-9b1a-6c7d8e9f0a1b";
        queue("sample", 2, jobs()).deliver(sample(22, run3, "application/json", "{not json"));
        awaitSettled(22);
        assertOneFailedFrame(sink.of(run3), "");

        String run4 = "urn:lattice:studio:run:cccccccc-5a47-4d0e-9b1a-6c7d8e9f0a1b";
        queue("sample", 2, jobs()).deliver(sample(23, run4, "application/pdf", "%PDF"));
        awaitSettled(23);
        assertOneFailedFrame(sink.of(run4), "application/xml");

        String run5 = "urn:lattice:studio:run:dddddddd-5a47-4d0e-9b1a-6c7d8e9f0a1b";
        queue("sample", 2, jobs()).deliver(sample(24, run5, "application/xml", "<a/>".repeat(RunWorker.MAX_INPUT_BYTES / 4 + 1)));
        awaitSettled(24);
        assertOneFailedFrame(sink.of(run5), "5 MiB");
    }

    @Test
    void aFailedPublishIsNotAcknowledgedButRequeuedSoTheNextWorkerSaysItWasLost() throws Exception {
        FrameSink broken = (run, frames) -> {
            throw new IOException("the broker did not confirm");
        };
        RunWorker worker = new RunWorker("sample", jobs(), broken, CLOCK);
        closeables.add(worker);
        QueueWorker q = new QueueWorker("broken", 1, worker, new FakeAcks(sink));
        closeables.add(q);
        q.deliver(sample(30, Examples.RUN, "application/xml", Examples.xmlSample()));
        awaitSettled(30);
        assertEquals(List.of("requeue:30"), sink.log);
    }

    @Test
    void twoInteractiveRunsAndTwoSampleRunsAtOnceKeepEachRunsFramesInOrderAndASampleRunHeldOpenNeverDelaysAStep() throws Exception {
        CountDownLatch release = new CountDownLatch(1);
        CountDownLatch held = new CountDownLatch(2);
        Function<String, Model> heldOpen = job -> {
            held.countDown();
            try {
                release.await();
                return Examples.compileJob(false);
            } catch (InterruptedException | IOException e) {
                throw new IllegalStateException(e);
            }
        };
        QueueWorker samples = queue("sample", 2, heldOpen);
        QueueWorker steps = queue("simulate", 2, jobs());
        String s1 = Examples.RUN;
        String s2 = RUN_2;
        String i1 = "urn:lattice:studio:run:bbbbbbbb-5a47-4d0e-9b1a-6c7d8e9f0a1b";
        String i2 = "urn:lattice:studio:run:cccccccc-5a47-4d0e-9b1a-6c7d8e9f0a1b";
        samples.deliver(sample(40, s1, "application/xml", Examples.xmlSample()));
        samples.deliver(sample(41, s2, "application/xml", Examples.xmlSample()));
        assertTrue(held.await(5, TimeUnit.SECONDS), "both sample runs are held open");
        steps.deliver(message(42, false, headers(i1, "simulate", "surface", NOW.plusSeconds(15)), "application/trig", ""));
        steps.deliver(message(43, false, headers(i2, "simulate", "persistence", NOW.plusSeconds(15)), "application/trig", ""));
        awaitSettled(42);
        awaitSettled(43);
        assertTrue(sink.log.contains("ack:42") && sink.log.contains("ack:43"), "the steps were answered while the sample runs were held");
        assertFalse(sink.log.contains("ack:40") || sink.log.contains("ack:41"));
        assertTrue(sink.frames.keySet().containsAll(List.of(i1, i2)) && !sink.frames.containsKey(s1) && !sink.frames.containsKey(s2));
        release.countDown();
        awaitSettled(40);
        awaitSettled(41);
        for (String run : new String[] {s1, s2}) {
            List<JsonObject> frames = sink.of(run);
            for (int k = 0; k < frames.size(); k++) {
                assertEquals(k, frames.get(k).get("seq").getAsNumber().value().intValue(), run + " is in order");
            }
            assertEquals("succeeded", frames.get(frames.size() - 1).get("status").getAsString().value());
        }
        assertEquals(sink.frames.get(s1), sink.frames.get(s2).stream().map(f -> f.replace(s2, s1)).toList(), "the same input gives the same frames, whichever run it was");
        String[] runs = {s1, s2, i1, i2};
        for (int k = 0; k < 4; k++) {
            int published = sink.log.indexOf("publish:" + runs[k]);
            int acked = sink.log.indexOf("ack:" + (40 + k));
            assertTrue(published >= 0 && acked > published, "the ack of " + runs[k] + " follows its publish");
        }
        assertEquals(new HashSet<>(List.of(s1, s2, i1, i2)), sink.frames.keySet());
    }

    @Test
    void theTransformsRouteAnswersAsItDidThroughTheSharedExecution() throws Exception {
        List<String> replies = new ArrayList<>();
        List<byte[]> bodies = new ArrayList<>();
        LegacyTransforms legacy = new LegacyTransforms(job -> {
            try {
                return Examples.compileJob(false);
            } catch (IOException e) {
                throw new IllegalStateException(e);
            }
        }, (replyTo, properties, body) -> {
            replies.add(replyTo + "|" + properties.getContentType() + "|" + properties.getCorrelationId());
            bodies.add(body);
        });
        String id = "00000000-0000-4000-8000-000000000002";
        Map<String, Object> h = new HashMap<>();
        h.put("job", Examples.JOB);
        Message ok = new Message(1, false, h, "application/xml", "amq.rabbitmq.reply-to.x", id, Examples.xmlSample().getBytes(StandardCharsets.UTF_8));
        assertEquals(Outcome.ACK, legacy.apply(ok));
        assertEquals(List.of("amq.rabbitmq.reply-to.x|text/turtle|" + id), replies);
        Model expected = TransformRun.run(Examples.compileJob(false), Examples.JOB, "urn:lattice:studio:transform:" + id, "application/xml", Examples.xmlSample());
        java.io.StringWriter turtle = new java.io.StringWriter();
        RDFDataMgr.write(turtle, expected, Lang.TURTLE);
        assertEquals(turtle.toString(), new String(bodies.get(0), StandardCharsets.UTF_8));
        assertEquals(Outcome.ACK, legacy.apply(new Message(2, false, h, "application/xml", null, id, new byte[0])), "no reply queue");
        assertEquals(1, replies.size(), "a request without a reply queue is dropped");
    }

    @Test
    void theConcurrencyOfARunQueueIsASettingFromOneUpAndDefaultsToTwo() {
        assertEquals(2, TransformsMain.concurrency(Map.of(), TransformsMain.INTERACTIVE_CONCURRENCY));
        assertEquals(3, TransformsMain.concurrency(Map.of(TransformsMain.SAMPLE_CONCURRENCY, " 3 "), TransformsMain.SAMPLE_CONCURRENCY));
        for (String bad : new String[] {"0", "-1", "two", "1.5"}) {
            assertThrows(IllegalArgumentException.class, () -> TransformsMain.concurrency(Map.of(TransformsMain.SAMPLE_CONCURRENCY, bad), TransformsMain.SAMPLE_CONCURRENCY), bad);
        }
    }

    /** Records what is done to a channel, in order. */
    private static Channel recordingChannel(List<Object[]> calls) {
        return (Channel) java.lang.reflect.Proxy.newProxyInstance(RunWorkerTest.class.getClassLoader(), new Class<?>[] {Channel.class},
            (self, method, args) -> {
                calls.add(new Object[] {method.getName(), args});
                return method.getReturnType() == boolean.class ? Boolean.TRUE : null;
            });
    }

    @Test
    void aFrameIsPublishedToTheEventsExchangeAsABinaryModeCloudEventAndConfirmed() throws Exception {
        List<Object[]> calls = new ArrayList<>();
        List<UUID> ids = new ArrayList<>(List.of(new UUID(0, 1), new UUID(0, 2)));
        AmqpFrameSink events = new AmqpFrameSink(recordingChannel(calls), CLOCK, () -> ids.remove(0));
        events.publish(Examples.RUN, List.of("{\"seq\":0}", "{\"seq\":1}"));
        List<String> names = calls.stream().map(c -> (String) c[0]).toList();
        assertEquals(List.of("exchangeDeclare", "confirmSelect", "basicPublish", "basicPublish", "waitForConfirmsOrDie"), names);
        Object[] first = calls.get(2);
        assertEquals("lattice.studio.events", first[1] instanceof Object[] a ? a[0] : ((Object[]) first[1])[0]);
        Object[] args = (Object[]) calls.get(2)[1];
        assertEquals("lattice.studio.events", args[0]);
        assertEquals("org.nebularis.lattice.studio.run.frame", args[1], "the type is the routing key");
        AMQP.BasicProperties p = (AMQP.BasicProperties) args[2];
        assertEquals("application/json", p.getContentType());
        assertEquals("1.0", p.getHeaders().get("cloudEvents:specversion"));
        assertEquals("org.nebularis.lattice.studio.run.frame", p.getHeaders().get("cloudEvents:type"));
        assertEquals(Examples.RUN, p.getHeaders().get("cloudEvents:subject"));
        assertEquals("urn:lattice:studio:run-worker", p.getHeaders().get("cloudEvents:source"));
        assertEquals(NOW.toString(), p.getHeaders().get("cloudEvents:time"), "the time comes from the clock");
        assertEquals(new UUID(0, 1).toString(), p.getHeaders().get("cloudEvents:id"));
        assertEquals(new UUID(0, 2).toString(), ((AMQP.BasicProperties) ((Object[]) calls.get(3)[1])[2]).getHeaders().get("cloudEvents:id"));
        assertNotEquals(p.getHeaders().get("cloudEvents:id"), ((AMQP.BasicProperties) ((Object[]) calls.get(3)[1])[2]).getHeaders().get("cloudEvents:id"));
        assertEquals("{\"seq\":0}", new String((byte[]) args[3], StandardCharsets.UTF_8), "the body is the frame");
    }
}
