// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

import java.time.Duration;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Brings the studio's projections up to date after writes (ADR-A149 decision 14). {@link #request} marks them stale, and one thread
 * runs one refresh at a time. A request that arrives while a refresh runs marks them stale again, so one more refresh follows and at
 * most one is ever waiting, however many writes came. {@link #awaitFresh} waits for a refresh that started after the call, which has
 * therefore read every write made before it.
 *
 * <p>A refresh that nothing waits for starts {@code delay} after the first request that made the projections stale, so a burst of
 * saves costs one refresh and not one each, since every refresh is two commits in the writers' queue. A wait starts one at once.
 */
public final class Refresher implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(Refresher.class);

    /** One refresh, which throws when it could not finish. */
    public interface Run {
        void once() throws Exception;
    }

    private final Run run;
    private final Duration delay;
    private final ScheduledExecutorService thread = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = new Thread(r, "studio-refresher");
        t.setDaemon(true);
        return t;
    });
    private final Object lock = new Object();
    private boolean dirty;
    private boolean running;
    private boolean scheduled;
    private int waiters;
    private long started;
    private long finished;

    public Refresher(Run run) {
        this(run, Duration.ZERO);
    }

    public Refresher(Run run, Duration delay) {
        this.run = run;
        this.delay = delay;
    }

    /** Marks the projections stale, and starts a refresh {@code delay} later if none is running or due. */
    public void request() {
        synchronized (lock) {
            dirty = true;
            if (!running && !scheduled) {
                scheduled = true;
                thread.schedule(this::start, delay.toNanos(), TimeUnit.NANOSECONDS);
            }
        }
    }

    private void start() {
        synchronized (lock) {
            scheduled = false;
            if (dirty && !running) {
                running = true;
                thread.execute(this::loop);
            }
            lock.notifyAll();
        }
    }

    /**
     * Waits until a refresh that started after this call has finished, asking for one when none is queued. A refresh that
     * failed has finished too, so the caller is released and the projections stay as they were.
     *
     * @return false when {@code timeout} passed first
     */
    public boolean awaitFresh(Duration timeout) {
        long deadline = System.nanoTime() + timeout.toNanos();
        synchronized (lock) {
            long target = started + 1;
            dirty = true;
            if (!running) {
                running = true;
                thread.execute(this::loop);
            }
            waiters++;
            try {
                return waitFor(() -> finished >= target, deadline);
            } finally {
                waiters--;
            }
        }
    }

    /** Waits until nothing is queued or running. */
    public boolean awaitIdle(Duration timeout) {
        long deadline = System.nanoTime() + timeout.toNanos();
        synchronized (lock) {
            return waitFor(() -> !dirty && !running && !scheduled, deadline);
        }
    }

    private boolean waitFor(java.util.function.BooleanSupplier done, long deadline) {
        while (!done.getAsBoolean()) {
            long left = deadline - System.nanoTime();
            if (left <= 0) {
                return false;
            }
            try {
                lock.wait(left / 1_000_000, (int) (left % 1_000_000));
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return false;
            }
        }
        return true;
    }

    private void loop() {
        boolean first = true;
        while (true) {
            synchronized (lock) {
                // Stale again after a refresh, with nobody waiting: the next one is due a delay from now, not at once.
                boolean defer = !first && waiters == 0 && !delay.isZero();
                if (!dirty || defer) {
                    running = false;
                    if (dirty && !scheduled) {
                        scheduled = true;
                        thread.schedule(this::start, delay.toNanos(), TimeUnit.NANOSECONDS);
                    }
                    lock.notifyAll();
                    return;
                }
                dirty = false;
                started++;
            }
            first = false;
            try {
                run.once();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            } catch (Exception e) {
                LOG.warn("a projection refresh failed, so the projections stay as they were until the next write", e);
            }
            synchronized (lock) {
                finished++;
                lock.notifyAll();
            }
        }
    }

    @Override
    public void close() {
        thread.shutdownNow();
    }
}
