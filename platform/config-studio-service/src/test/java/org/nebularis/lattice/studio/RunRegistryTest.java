// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.auth.Principal;
import org.nebularis.lattice.studio.runs.RunRegistry;
import org.nebularis.lattice.studio.runs.RunRegistry.Admission;
import org.nebularis.lattice.studio.runs.RunRegistry.Frame;
import org.nebularis.lattice.studio.runs.TabSink;

/** The registry of the runs an instance accepted, alone, with a clock and timers the test drives (ADR-A154 decisions 4 to 6, 9 and 10). */
class RunRegistryTest {
    static final Principal ADA = new Principal("ada", false);
    static final String WS = Fixture.id(1);
    static final Instant T0 = Instant.parse("2026-11-16T10:00:00Z");

    /** A clock the test moves. */
    static final class TestClock extends Clock {
        private volatile Instant now = T0;

        @Override
        public ZoneId getZone() {
            return ZoneOffset.UTC;
        }

        @Override
        public Clock withZone(ZoneId zone) {
            return this;
        }

        @Override
        public Instant instant() {
            return now;
        }

        void advanceTo(Instant at) {
            now = at;
        }
    }

    /** Timers that fire only when the test moves the clock past them. */
    static final class TestTimers implements RunRegistry.Timers {
        private record Task(Instant due, Runnable run, AtomicBoolean cancelled) {
        }

        private final TestClock clock;
        private final List<Task> tasks = Collections.synchronizedList(new ArrayList<>());

        TestTimers(TestClock clock) {
            this.clock = clock;
        }

        @Override
        public RunRegistry.Cancellable schedule(Duration delay, Runnable task) {
            Task t = new Task(clock.instant().plus(delay), task, new AtomicBoolean());
            tasks.add(t);
            return () -> {
                t.cancelled.set(true);
                tasks.remove(t);
            };
        }

        int scheduled() {
            return tasks.size();
        }

        /** Moves the clock and runs what came due, earliest first. */
        void advance(Duration by) {
            clock.now = clock.now.plus(by);
            List<Task> due;
            synchronized (tasks) {
                due = tasks.stream().filter(t -> !t.due.isAfter(clock.now)).sorted(java.util.Comparator.comparing(Task::due)).toList();
            }
            for (Task t : due) {
                if (tasks.remove(t) && !t.cancelled.get()) {
                    t.run.run();
                }
            }
        }
    }

    /** What a sink was given, and whether two threads were ever inside it together. */
    static final class Recording implements RunRegistry.Sink {
        final List<Frame> sent = Collections.synchronizedList(new ArrayList<>());
        final List<Frame> expired = Collections.synchronizedList(new ArrayList<>());
        final AtomicInteger inside = new AtomicInteger();
        volatile boolean overlapped;

        @Override
        public void send(Frame frame) {
            enter();
            sent.add(frame);
            leave();
        }

        @Override
        public void expired(Frame frame) {
            enter();
            expired.add(frame);
            leave();
        }

        private void enter() {
            if (inside.incrementAndGet() > 1) {
                overlapped = true;
            }
            Thread.yield();
        }

        private void leave() {
            inside.decrementAndGet();
        }

        List<Integer> seqs() {
            synchronized (sent) {
                return sent.stream().map(Frame::seq).toList();
            }
        }
    }

    final TestClock clock = new TestClock();
    final TestTimers timers = new TestTimers(clock);
    volatile boolean mayRead = true;
    final List<String> asked = Collections.synchronizedList(new ArrayList<>());
    RunRegistry registry;

    @BeforeEach
    void setUp() {
        registry = new RunRegistry(clock, timers, (p, ws) -> {
            asked.add(p.name() + "@" + ws);
            return mayRead;
        });
    }

    static String run(int n) {
        return "urn:lattice:studio:run:00000000-0000-4000-8000-" + String.format("%012x", n);
    }

    static String mid(String run, int seq) {
        return "{\"run\":\"" + run + "\",\"seq\":" + seq + ",\"last\":false,\"text\":\"t" + seq + "\"}";
    }

    static String end(String run, int seq) {
        return "{\"run\":\"" + run + "\",\"seq\":" + seq + ",\"last\":true,\"status\":\"succeeded\",\"conforms\":true}";
    }

    Admission accept(int n, String tab, Recording sink, long deadlineSeconds) {
        return registry.accept(run(n), ADA, tab, WS, clock.instant().plusSeconds(deadlineSeconds), sink);
    }

    @Test
    void framesGoToTheTabAndToACollectorOnceAndInTheOrderGiven() {
        List<String> published = new ArrayList<>();
        TabSink tab = new TabSink("ada", "t1", (principal, t, json) -> published.add(principal + "/" + t + "/" + json), clock,
            () -> new UUID(0, published.size() + 1));
        RunRegistry.Collector collector = new RunRegistry.Collector();
        assertTrue(registry.accept(run(1), ADA, "t1", WS, T0.plusSeconds(15), tab).accepted());
        assertTrue(registry.accept(run(2), ADA, "t2", WS, T0.plusSeconds(15), collector).accepted());
        for (int i = 0; i < 3; i++) {
            registry.frame(mid(run(1), i));
            registry.frame(mid(run(2), i));
        }
        registry.frame(end(run(1), 3));
        assertEquals(4, published.size());
        for (int i = 0; i < 3; i++) {
            assertTrue(published.get(i).startsWith("ada/t1/"), published.get(i));
            JsonObject event = JSON.parse(published.get(i).substring("ada/t1/".length()));
            assertEquals(i, event.get("data").getAsObject().get("seq").getAsNumber().value().intValue());
        }
        assertTrue(JSON.parse(published.get(3).substring("ada/t1/".length())).get("data").getAsObject().get("last").getAsBoolean().value());
        assertEquals(2, registry.size(), "run 2 is still pending, with its tab");
        registry.frame(end(run(2), 3));
        assertFalse(collector.timedOut());
        List<String> got = collector.frames();
        assertEquals(4, got.size());
        for (int i = 0; i < 3; i++) {
            assertEquals(i, JSON.parse(got.get(i)).get("seq").getAsNumber().value().intValue());
        }
        assertEquals(4, JSON.parseAny(collector.json()).getAsArray().size());
        assertEquals(0, registry.size());
    }

    @Test
    void aFrameOfARunThisInstanceDoesNotHoldIsIgnored() {
        Recording sink = new Recording();
        accept(1, "t1", sink, 15);
        registry.frame(mid(run(2), 0));
        registry.frame("not json at all");
        assertTrue(sink.sent.isEmpty());
        assertTrue(asked.isEmpty(), "no access check is made for a frame nobody holds");
        assertEquals(2, registry.size());
    }

    @Test
    void anInvalidFrameIsDroppedAndNothingIsSentAndTheRunStaysPending() {
        Recording sink = new Recording();
        String r = run(1);
        accept(1, "t1", sink, 15);
        String big = "é".repeat(24_577);
        assertEquals(49_154, big.getBytes(StandardCharsets.UTF_8).length);
        List<String> bad = List.of(
            "not json", "[]", "{}", "\"a string\"",
            "{\"run\":\"" + r + "\",\"seq\":-1,\"last\":false}",
            "{\"run\":\"" + r + "\",\"seq\":128,\"last\":false}",
            "{\"run\":\"" + r + "\",\"seq\":1.5,\"last\":false}",
            "{\"run\":\"" + r + "\",\"seq\":\"1\",\"last\":false}",
            "{\"run\":\"" + r + "\",\"last\":false}",
            "{\"run\":\"" + r + "\",\"seq\":1}",
            "{\"run\":\"" + r + "\",\"seq\":1,\"last\":\"false\"}",
            "{\"run\":\"" + r + "\",\"seq\":1,\"last\":false,\"text\":\"" + big + "\"}",
            "{\"run\":\"" + r + "\",\"seq\":1,\"last\":false,\"text\":5}",
            "{\"run\":\"" + r + "\",\"seq\":1,\"last\":false,\"extra\":1}",
            "{\"run\":\"" + r + "\",\"seq\":1,\"last\":true}",
            "{\"run\":\"" + r + "\",\"seq\":1,\"last\":true,\"status\":\"done\"}",
            "{\"run\":\"" + r + "\",\"seq\":1,\"last\":false,\"status\":\"succeeded\"}",
            "{\"run\":\"" + r + "\",\"seq\":1,\"last\":true,\"status\":\"failed\"}",
            "{\"run\":\"" + r + "\",\"seq\":1,\"last\":true,\"status\":\"succeeded\",\"message\":\"x\"}",
            "{\"run\":\"" + r + "\",\"seq\":1,\"last\":true,\"status\":\"succeeded\",\"more\":true}",
            "{\"run\":\"" + r + "\",\"seq\":1,\"last\":false,\"part\":{\"index\":0,\"role\":\"nope\",\"mediaType\":\"text/turtle\"}}",
            "{\"run\":\"" + r + "\",\"seq\":1,\"last\":false,\"part\":{\"index\":0,\"role\":\"report\"}}",
            "{\"run\":\"" + r + "\",\"seq\":1,\"last\":false,\"part\":{\"index\":0,\"role\":\"report\",\"mediaType\":\"a/b\",\"x\":1}}",
            "{\"run\":\"" + r + "\",\"seq\":1,\"last\":false,\"part\":[]}");
        for (String frame : bad) {
            registry.frame(frame);
        }
        assertTrue(sink.sent.isEmpty(), () -> "sent " + sink.sent);
        assertEquals(2, registry.size(), "the run is still pending");
        // The text at exactly the limit is valid, as is a frame with a whole part.
        registry.frame("{\"run\":\"" + r + "\",\"seq\":1,\"last\":false,\"text\":\"" + "a".repeat(49_152) + "\"}");
        registry.frame("{\"run\":\"" + r + "\",\"seq\":2,\"last\":false,\"part\":{\"index\":0,\"role\":\"report\",\"mediaType\":\"text/turtle\"},\"text\":\"\",\"more\":true}");
        registry.frame("{\"run\":\"" + r + "\",\"seq\":3,\"last\":true,\"status\":\"failed\",\"message\":\"no\"}");
        assertEquals(List.of(1, 2, 3), sink.seqs());
    }

    @Test
    void theFrameAfterThe128thEndsTheRunWithAFailedFrameSayingTheResultIsTooLarge() {
        Recording sink = new Recording();
        accept(1, "t1", sink, 15);
        for (int i = 0; i < 128; i++) {
            registry.frame(mid(run(1), i));
        }
        assertEquals(128, sink.sent.size());
        assertEquals(2, registry.size());
        registry.frame(mid(run(1), 5));
        assertEquals(129, sink.sent.size());
        JsonObject failed = JSON.parse(sink.sent.get(128).json());
        assertEquals(128, sink.sent.get(128).seq());
        assertTrue(sink.sent.get(128).last());
        assertEquals("failed", failed.get("status").getAsString().value());
        assertTrue(failed.get("message").getAsString().value().contains("too large"));
        assertEquals(0, registry.size());
        registry.frame(mid(run(1), 6));
        assertEquals(129, sink.sent.size(), "a forgotten run takes no more frames");
        assertEquals(0, timers.scheduled());
    }

    @Test
    void accessIsCheckedAtDeliveryAndARefusedFrameIsWithheldWhileALaterPermittedOneGoesOut() {
        Recording sink = new Recording();
        accept(1, "t1", sink, 15);
        registry.frame(mid(run(1), 0));
        mayRead = false;
        registry.frame(mid(run(1), 1));
        registry.frame(mid(run(1), 2));
        assertEquals(List.of(0), sink.seqs());
        assertEquals(2, registry.size(), "the run stays pending until its deadline");
        mayRead = true;
        registry.frame(mid(run(1), 3));
        registry.frame(end(run(1), 4));
        assertEquals(List.of(0, 3, 4), sink.seqs());
        assertEquals(0, registry.size());
        assertEquals("ada@" + WS, asked.get(0), "it asks about the principal and workspace the run holds");
        assertEquals(5, asked.size(), "once for each frame");
    }

    @Test
    void aRunsLastFrameIsWithheldToo() {
        Recording sink = new Recording();
        accept(1, "t1", sink, 15);
        mayRead = false;
        registry.frame(end(run(1), 0));
        assertTrue(sink.sent.isEmpty());
        assertEquals(0, registry.size(), "a last frame ends the run whether or not it was sent");
    }

    @Test
    void theDeadlineSendsOneFailedLastFrameOnePastTheHighestForwardedAndForgetsTheRun() {
        for (int forwarded : new int[] {0, 1, 4}) {
            Recording sink = new Recording();
            int n = 10 + forwarded;
            accept(n, "t" + n, sink, 15);
            for (int i = 0; i < forwarded; i++) {
                registry.frame(mid(run(n), i));
            }
            timers.advance(Duration.ofSeconds(14));
            assertTrue(sink.expired.isEmpty(), "not before the deadline");
            timers.advance(Duration.ofSeconds(1));
            assertEquals(1, sink.expired.size(), "forwarded " + forwarded);
            Frame f = sink.expired.get(0);
            assertEquals(forwarded, f.seq());
            assertTrue(f.last());
            JsonObject o = JSON.parse(f.json());
            assertEquals(run(n), o.get("run").getAsString().value());
            assertEquals("failed", o.get("status").getAsString().value());
            assertTrue(o.get("message").getAsString().value().contains("did not finish by its deadline"));
            assertEquals(forwarded, sink.sent.size());
            assertEquals(0, registry.size());
            registry.frame(end(run(n), forwarded));
            assertEquals(forwarded, sink.sent.size(), "a late frame is ignored");
            clock.now = T0;
        }
    }

    @Test
    void theDeadlineFramesSeqCountsOnlyWhatWasForwardedAndItIsCheckedForAccessToo() {
        Recording sink = new Recording();
        accept(1, "t1", sink, 15);
        registry.frame(mid(run(1), 0));
        mayRead = false;
        registry.frame(mid(run(1), 1));
        mayRead = true;
        timers.advance(Duration.ofSeconds(15));
        assertEquals(1, sink.expired.get(0).seq(), "frame 1 was withheld, so the frame after 0 is 1");

        Recording refused = new Recording();
        accept(2, "t2", refused, 15);
        mayRead = false;
        timers.advance(Duration.ofSeconds(15));
        assertTrue(refused.expired.isEmpty() && refused.sent.isEmpty());
        assertEquals(0, registry.size(), "the run is forgotten whether or not the frame could be sent");
    }

    @Test
    void noDeadlineFrameFollowsARunThatEnded() {
        Recording sink = new Recording();
        accept(1, "t1", sink, 15);
        registry.frame(end(run(1), 0));
        assertEquals(0, timers.scheduled(), "the timer went with the run");
        timers.advance(Duration.ofSeconds(60));
        assertTrue(sink.expired.isEmpty());
        assertEquals(List.of(0), sink.seqs());
    }

    @Test
    void aTabHoldsFourPendingRunsAndTheFifthIsRefusedWithTheSecondsToTheEarliestDeadline() {
        Recording sink = new Recording();
        for (int i = 1; i <= 4; i++) {
            assertTrue(accept(i, "t1", sink, 10L * i).accepted());
        }
        Admission fifth = accept(5, "t1", sink, 5);
        assertFalse(fifth.accepted());
        assertEquals(10, fifth.retryAfterSeconds());
        assertEquals(5, registry.size(), "the refused run is held nowhere");
        assertEquals(4, registry.pending("ada", "t1"));
        timers.advance(Duration.ofMillis(9_500));
        assertEquals(1, accept(5, "t1", sink, 5).retryAfterSeconds(), "a fraction of a second rounds up");
        registry.frame(end(run(2), 0));
        assertTrue(accept(5, "t1", sink, 5).accepted(), "a fifth is accepted once one ends");
        assertEquals(4, registry.pending("ada", "t1"));
        timers.advance(Duration.ofSeconds(60));
        assertEquals(0, registry.pending("ada", "t1"), "a run that expired no longer counts");
        assertTrue(accept(6, "t1", sink, 5).accepted());
    }

    @Test
    void twoTabsOfOnePrincipalAndTheSameTabOfTwoPrincipalsAreCountedApart() {
        Recording sink = new Recording();
        for (int i = 1; i <= 4; i++) {
            assertTrue(accept(i, "t1", sink, 15).accepted());
        }
        assertTrue(accept(5, "t2", sink, 15).accepted(), "another tab of ada");
        assertTrue(registry.accept(run(6), new Principal("grace", false), "t1", WS, T0.plusSeconds(15), sink).accepted(), "the same tab id of another principal");
        assertFalse(accept(7, "t1", sink, 15).accepted());
    }

    @Test
    void nothingOfARunOutlivesItInTheRegistryOrTheTimers() {
        Recording sink = new Recording();
        accept(1, "t1", sink, 15);
        accept(2, "t1", sink, 15);
        accept(3, "t2", sink, 15);
        accept(4, "t3", sink, 15);
        assertEquals(4 + 3, registry.size());
        registry.frame(end(run(1), 0));
        registry.cancel(run(2));
        registry.cancel(run(2));
        timers.advance(Duration.ofSeconds(15));
        registry.frame(mid(run(4), 0));
        assertEquals(0, registry.size());
        assertEquals(0, timers.scheduled());
        assertEquals(0, registry.pending("ada", "t1"));
    }

    @Test
    void aFrameThatBeatsTheAcceptingThreadsReturnStillEndsTheRunWithItsTimerCancelled() throws Exception {
        // The brief's order: a worker may answer before the publish call returns. Here a frame arrives from another thread right
        // after acceptance, and the run ends cleanly whichever thread gets there first.
        for (int round = 0; round < 200; round++) {
            Recording sink = new Recording();
            String r = run(1000 + round);
            Thread feeder = new Thread(() -> {
                while (registry.pending("ada", "tx") == 0) {
                    Thread.onSpinWait();
                }
                registry.frame(end(r, 0));
            });
            feeder.start();
            registry.accept(r, ADA, "tx", WS, T0.plusSeconds(15), sink);
            feeder.join();
            assertEquals(0, registry.size(), "round " + round);
            assertEquals(0, timers.scheduled(), "round " + round);
        }
    }

    @Test
    void framesOfSeveralRunsGivenByManyThreadsArriveInOrderAtEachSink() throws Exception {
        int threads = 8;
        int perThread = 2;
        int frames = 100;
        List<Recording> sinks = new ArrayList<>();
        for (int i = 0; i < threads * perThread; i++) {
            Recording sink = new Recording();
            sinks.add(sink);
            // Each run has a tab of its own, so the limit of four does not matter here.
            assertTrue(accept(i, "c" + i, sink, 100).accepted());
        }
        CountDownLatch start = new CountDownLatch(1);
        AtomicReference<Throwable> failure = new AtomicReference<>();
        List<Thread> all = new ArrayList<>();
        for (int t = 0; t < threads; t++) {
            int first = t * perThread;
            all.add(new Thread(() -> {
                try {
                    start.await();
                    for (int seq = 0; seq < frames; seq++) {
                        for (int k = 0; k < perThread; k++) {
                            registry.frame(seq == frames - 1 ? end(run(first + k), seq) : mid(run(first + k), seq));
                        }
                    }
                } catch (Throwable e) {
                    failure.set(e);
                }
            }));
        }
        // A thread that accepts and cancels other runs, and one that moves time, while the frames flow.
        all.add(new Thread(() -> {
            try {
                start.await();
                for (int i = 0; i < 500; i++) {
                    Recording other = new Recording();
                    int n = 5000 + i;
                    registry.accept(run(n), ADA, "o" + (i % 3), WS, T0.plusSeconds(100), other);
                    registry.cancel(run(n));
                }
            } catch (Throwable e) {
                failure.set(e);
            }
        }));
        all.forEach(Thread::start);
        start.countDown();
        for (Thread t : all) {
            t.join();
        }
        assertEquals(null, failure.get());
        for (int i = 0; i < sinks.size(); i++) {
            List<Integer> seqs = sinks.get(i).seqs();
            assertEquals(frames, seqs.size(), "run " + i);
            for (int s = 0; s < frames; s++) {
                assertEquals(s, seqs.get(s), "run " + i + " frame " + s);
            }
            assertFalse(sinks.get(i).overlapped);
        }
        assertEquals(0, registry.size());
        assertEquals(0, timers.scheduled());
    }

    @Test
    void framesOfOneRunGivenByTwoThreadsNeverInterleaveInsideItsSink() throws Exception {
        Recording sink = new Recording();
        accept(1, "t1", sink, 100);
        CountDownLatch start = new CountDownLatch(1);
        List<Thread> all = new ArrayList<>();
        for (int t = 0; t < 2; t++) {
            int parity = t;
            all.add(new Thread(() -> {
                try {
                    start.await();
                } catch (InterruptedException e) {
                    return;
                }
                for (int seq = parity; seq < 100; seq += 2) {
                    registry.frame(mid(run(1), seq));
                }
            }));
        }
        all.forEach(Thread::start);
        start.countDown();
        for (Thread t : all) {
            t.join();
        }
        assertEquals(100, sink.sent.size());
        assertFalse(sink.overlapped, "two threads were inside the sink at once");
        assertEquals(Set.copyOf(sink.seqs()).size(), 100);
    }

    @Test
    void theTabSinkPublishesAStructuredCloudEventWhoseDataIsTheFrameAsReceived() {
        List<String[]> published = new ArrayList<>();
        UUID id = UUID.fromString("00000000-0000-4000-8000-0000000000aa");
        TabSink tab = new TabSink("ada", "t1", (p, t, json) -> published.add(new String[] {p, t, json}), clock, () -> id);
        registry.accept(run(1), ADA, "t1", WS, T0.plusSeconds(15), tab);
        String frame = "{\"run\":\"" + run(1) + "\",\"seq\":0,\"last\":false,\"part\":{\"index\":0,\"role\":\"report\",\"mediaType\":\"text/turtle\"},\"text\":\"a é\",\"more\":true}";
        clock.now = T0.plusSeconds(3);
        registry.frame(frame);
        assertEquals(1, published.size());
        assertEquals("ada", published.get(0)[0]);
        assertEquals("t1", published.get(0)[1]);
        JsonObject event = JSON.parse(published.get(0)[2]);
        assertEquals(Set.of("specversion", "id", "source", "type", "subject", "time", "datacontenttype", "data"), Set.copyOf(event.keys()));
        assertEquals("1.0", event.get("specversion").getAsString().value());
        assertEquals(id.toString(), event.get("id").getAsString().value());
        assertEquals("urn:lattice:studio:service", event.get("source").getAsString().value());
        assertEquals("org.nebularis.lattice.studio.run.frame", event.get("type").getAsString().value());
        assertEquals(run(1), event.get("subject").getAsString().value());
        assertEquals("2026-11-16T10:00:03Z", event.get("time").getAsString().value());
        assertEquals("application/json", event.get("datacontenttype").getAsString().value());
        assertEquals(JSON.parse(frame), event.get("data"));

        timers.advance(Duration.ofSeconds(15));
        assertEquals(2, published.size(), "the deadline's frame goes to the tab as any frame does");
        JsonObject failed = JSON.parse(published.get(1)[2]);
        assertEquals("urn:lattice:studio:service", failed.get("source").getAsString().value());
        assertEquals("2026-11-16T10:00:18Z", failed.get("time").getAsString().value());
        assertEquals(1, failed.get("data").getAsObject().get("seq").getAsNumber().value().intValue());
    }

    @Test
    void aCollectorAnswersTheFramesInSequenceOrderTheFirstOfEachNumberAndNotTheDeadlineFrame() {
        RunRegistry.Collector collector = new RunRegistry.Collector();
        registry.accept(run(1), ADA, "t1", WS, T0.plusSeconds(15), collector);
        registry.frame(mid(run(1), 1));
        registry.frame(mid(run(1), 0));
        registry.frame("{\"run\":\"" + run(1) + "\",\"seq\":1,\"last\":false,\"text\":\"again\"}");
        timers.advance(Duration.ofSeconds(15));
        assertTrue(collector.timedOut());
        assertEquals(2, collector.frames().size());
        assertEquals(0, JSON.parse(collector.frames().get(0)).get("seq").getAsNumber().value().intValue());
        assertEquals("t1", JSON.parse(collector.frames().get(1)).get("text").getAsString().value(), "the first frame seen for a number is kept");
    }
}
