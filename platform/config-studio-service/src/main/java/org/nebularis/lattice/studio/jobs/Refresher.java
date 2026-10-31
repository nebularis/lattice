// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

import java.time.Duration;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Brings the studio's projections up to date after writes (ADR-A149 decision 14). {@link #request} marks them stale, and one thread
 * runs one refresh at a time. A request that arrives while a refresh runs marks them stale again, so one more refresh follows and at
 * most one is ever waiting, however many writes came. {@link #awaitFresh} waits for a refresh that started after the call, which has
 * therefore read every write made before it.
 */
public final class Refresher implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(Refresher.class);

    /** One refresh, which throws when it could not finish. */
    public interface Run {
        void once() throws Exception;
    }

    private final Run run;
    private final ExecutorService thread = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "studio-refresher");
        t.setDaemon(true);
        return t;
    });
    private final Object lock = new Object();
    private boolean dirty;
    private boolean running;
    private long started;
    private long finished;

    public Refresher(Run run) {
        this.run = run;
    }

    /** Marks the projections stale, and starts the thread if no refresh is running. */
    public void request() {
        synchronized (lock) {
            markDirty();
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
            markDirty();
            return waitFor(() -> finished >= target, deadline);
        }
    }

    /** Waits until nothing is queued or running. */
    public boolean awaitIdle(Duration timeout) {
        long deadline = System.nanoTime() + timeout.toNanos();
        synchronized (lock) {
            return waitFor(() -> !dirty && !running, deadline);
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

    private void markDirty() {
        dirty = true;
        if (!running) {
            running = true;
            thread.execute(this::loop);
        }
    }

    private void loop() {
        while (true) {
            synchronized (lock) {
                if (!dirty) {
                    running = false;
                    lock.notifyAll();
                    return;
                }
                dirty = false;
                started++;
            }
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
