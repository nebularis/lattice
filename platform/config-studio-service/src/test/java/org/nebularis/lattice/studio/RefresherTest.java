// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Path;
import java.time.Clock;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import org.apache.jena.rdf.model.Model;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiRequest;
import org.nebularis.lattice.studio.api.StudioApi;
import org.nebularis.lattice.studio.jobs.JobBus;
import org.nebularis.lattice.studio.jobs.Refresher;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;

/** The refresh queue: one refresh at a time, at most one waiting, and a wait that sees every write made before it (ADR-A149 decision 14). */
class RefresherTest {
    private static final Duration SECONDS = Duration.ofSeconds(10);

    /** A refresh that runs when the test lets it, and records how many ran and how many ran at once. */
    private static final class Gated implements Refresher.Run {
        final List<CountDownLatch> started = new CopyOnWriteArrayList<>();
        final List<CountDownLatch> release = new CopyOnWriteArrayList<>();
        final AtomicInteger running = new AtomicInteger();
        final AtomicInteger most = new AtomicInteger();
        final AtomicInteger finished = new AtomicInteger();

        Gated(int runs) {
            for (int i = 0; i < runs; i++) {
                started.add(new CountDownLatch(1));
                release.add(new CountDownLatch(1));
            }
        }

        @Override
        public void once() throws InterruptedException {
            int n = finished.get();
            most.accumulateAndGet(running.incrementAndGet(), Math::max);
            started.get(n).countDown();
            release.get(n).await();
            running.decrementAndGet();
            finished.incrementAndGet();
        }
    }

    private static void await(CountDownLatch latch) throws InterruptedException {
        assertTrue(latch.await(10, TimeUnit.SECONDS));
    }

    @Test
    void manyRequestsDuringARefreshQueueOneMoreAndNeverTwoAtOnce() throws Exception {
        Gated run = new Gated(3);
        try (Refresher refresher = new Refresher(run)) {
            refresher.request();
            await(run.started.get(0));
            for (int i = 0; i < 20; i++) {
                refresher.request();
            }
            run.release.get(0).countDown();
            await(run.started.get(1));
            run.release.get(1).countDown();
            assertTrue(refresher.awaitIdle(SECONDS));
            assertEquals(2, run.finished.get(), "twenty requests during one refresh run one more");
            assertEquals(1, run.most.get());
            assertFalse(run.started.get(2).await(100, TimeUnit.MILLISECONDS), "nothing is marked, so nothing runs");
        }
    }

    @Test
    void awaitFreshReturnsOnlyAfterARefreshThatStartedAfterTheCall() throws Exception {
        Gated run = new Gated(3);
        try (Refresher refresher = new Refresher(run)) {
            refresher.request();
            await(run.started.get(0));
            AtomicBoolean returned = new AtomicBoolean();
            CountDownLatch waiting = new CountDownLatch(1);
            Thread waiter = new Thread(() -> {
                waiting.countDown();
                refresher.awaitFresh(SECONDS);
                returned.set(true);
            });
            waiter.start();
            await(waiting);
            run.release.get(0).countDown();
            await(run.started.get(1));
            assertFalse(returned.get(), "the refresh that was running when it called had read nothing it wrote");
            run.release.get(1).countDown();
            waiter.join(10_000);
            assertTrue(returned.get());
            assertEquals(2, run.finished.get());
        }
    }

    @Test
    void awaitFreshAsksForARefreshWhenNoneIsQueuedAndGivesUpAtItsTimeout() throws Exception {
        Gated run = new Gated(1);
        try (Refresher refresher = new Refresher(run)) {
            assertFalse(refresher.awaitFresh(Duration.ofMillis(200)), "the refresh it asked for is held, so the wait times out");
            await(run.started.get(0));
            run.release.get(0).countDown();
            assertTrue(refresher.awaitIdle(SECONDS));
        }
    }

    @Test
    void aRefreshThatFailsReleasesItsWaitersAndTheNextRequestRunsAgain() throws Exception {
        AtomicInteger runs = new AtomicInteger();
        try (Refresher refresher = new Refresher(() -> {
            if (runs.incrementAndGet() == 1) {
                throw new IllegalStateException("the worker is down");
            }
        })) {
            assertTrue(refresher.awaitFresh(SECONDS));
            assertTrue(refresher.awaitFresh(SECONDS));
            assertEquals(2, runs.get());
        }
    }

    /** A bus that holds the first refresh job until the test lets it go, then hands each to the stand-in worker. */
    private static final class GatedBus implements JobBus {
        final Fixture f;
        final CountDownLatch entered = new CountDownLatch(1);
        final CountDownLatch gate = new CountDownLatch(1);
        final AtomicInteger refreshes = new AtomicInteger();

        GatedBus(Fixture f) {
            this.f = f;
        }

        @Override
        public void publish(String jobIri) throws InterruptedException {
            refreshes.incrementAndGet();
            entered.countDown();
            gate.await();
            f.refreshWorker.handle(jobIri);
        }
    }

    @Test
    void savesDuringARefreshQueueOneMoreRefreshJobAndAWriteWaitsForOneThatReadsIt(@TempDir Path dir) throws Exception {
        Fixture f = new Fixture(Fixture.assetsDir(dir));
        GatedBus bus = new GatedBus(f);
        StudioApi api = new StudioApi(f.store, Fixture.OPS, f.writes, bus, Clock.systemUTC(), () -> new UUID(0, 1), f.assets);
        String workspace = Fixture.id(1);
        Map<String, String> headers = new HashMap<>(Map.of("content-type", Fixture.TURTLE));
        AtomicInteger created = new AtomicInteger();
        Thread create = new Thread(() -> created.set(api.handle(new ApiRequest("POST", "/api/workspaces", null, headers,
            (Fixture.PREFIXES + "ex:a ex:p ex:b .").getBytes(java.nio.charset.StandardCharsets.UTF_8))).status()));
        create.start();
        await(bus.entered);
        for (int revision = 0; revision < 3; revision++) {
            Map<String, String> put = new HashMap<>(Map.of("content-type", Fixture.TURTLE, "if-match", "\"" + revision + "\""));
            assertEquals(204, api.handle(new ApiRequest("PUT", "/api/workspaces/" + workspace + "/graphs/surface", null, put,
                (Fixture.PREFIXES + "ex:cfg <https://www.nebularis.org/neuro-semantic/lattice/surface#label> \"v" + revision + "\" .").getBytes(java.nio.charset.StandardCharsets.UTF_8))).status());
        }
        assertEquals(1, bus.refreshes.get(), "three saves during a refresh queue no job of their own");
        assertEquals(0, created.get(), "the creation still waits for its refresh");
        bus.gate.countDown();
        create.join(10_000);
        assertEquals(201, created.get());
        assertTrue(api.awaitProjections(SECONDS));
        assertEquals(2, bus.refreshes.get(), "the three saves ran one more refresh job");
        Model summaries = f.store.summaries();
        assertEquals(3, summaries.getRequiredProperty(summaries.createResource(Graphs.workspace(workspace)), Cst.revision("surface")).getLong());
    }
}
