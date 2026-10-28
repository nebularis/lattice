// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writes;

import java.time.Clock;
import java.time.Duration;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import org.apache.jena.rdf.model.Model;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.StudioStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Deletes the jobs that finished longer ago than the retention, through the writers, so the writer of each job's
 * workspace makes the deletion. A second instance sweeping at the same time sends deletions that find nothing.
 */
public final class Sweeper implements AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(Sweeper.class);

    private final StudioStore store;
    private final Writes writes;
    private final Clock clock;
    private final Duration retention;
    private final ScheduledExecutorService timer = Executors.newSingleThreadScheduledExecutor(Thread.ofVirtual().factory());

    public Sweeper(StudioStore store, Writes writes, Clock clock, Duration retention) {
        this.store = store;
        this.writes = writes;
        this.clock = clock;
        this.retention = retention;
    }

    public Sweeper start(Duration every) {
        timer.scheduleWithFixedDelay(() -> {
            try {
                sweep();
            } catch (RuntimeException e) {
                LOG.warn("sweeping finished jobs failed, and is tried again in {}", every, e);
            }
        }, 0, every.toMillis(), TimeUnit.MILLISECONDS);
        return this;
    }

    /** The number of jobs deleted. */
    public int sweep() {
        Model expired = store.expiredJobs(clock.instant().minus(retention));
        int[] deleted = {0};
        expired.listStatements(null, Cst.workspace, (org.apache.jena.rdf.model.RDFNode) null).forEachRemaining(s -> {
            String job = s.getSubject().getURI().substring(Graphs.JOB_PREFIX.length());
            String ws = s.getResource().getURI().substring(Graphs.WORKSPACE_PREFIX.length());
            if (Graphs.isId(job) && Graphs.isId(ws) && writes.send(Command.deleteJob(ws, job)).applied()) {
                deleted[0]++;
            }
        });
        if (deleted[0] > 0) {
            LOG.info("deleted {} job(s) finished more than {} ago", deleted[0], retention);
        }
        return deleted[0];
    }

    @Override
    public void close() {
        timer.shutdownNow();
    }
}
